"""
RFM Customer Segmentation Module
──────────────────────────────────
Method: RFM scoring + K-Means clustering (k=4 segments)

RFM Dimensions:
  R (Recency)   — Days since last purchase (lower = better)
  F (Frequency) — Number of distinct orders (higher = better)
  M (Monetary)  — Total spend (higher = better)

Segments: Champion | Loyal | At-Risk | Lost

NOTE: When real dataset arrives:
- Recalibrate RFM score thresholds based on actual customer distribution
- K value (number of clusters) may need tuning
- Consider adding CLV (Customer Lifetime Value) prediction layer
"""
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from .etl import extract_customer_data
from app import db
from app.models import Customer


SEGMENT_MAP = {
    'Champion': 'Champion',
    'Loyal':    'Loyal',
    'New':      'New',
    'At-Risk':  'At-Risk',
    'Lost':     'Lost',
}

SEGMENT_CONFIG = {
    'Champion': {'color': '#10B981', 'description': 'Bought recently, buy often, spend the most'},
    'Loyal':    {'color': '#6366F1', 'description': 'Buy regularly and respond well to promotions'},
    'New':      {'color': '#0EA5E9', 'description': 'Bought recently, only one order'},
    'At-Risk':  {'color': '#F59E0B', 'description': 'Used to buy often but haven\'t recently'},
    'Lost':     {'color': '#F43F5E', 'description': 'Lowest RFM scores, haven\'t purchased in a long time'},
}


def compute_rfm() -> dict:
    """
    Full RFM analysis pipeline.
    Returns: per-customer RFM data + segment summary.
    """
    df = extract_customer_data()

    if df.empty:
        return {'error': 'No data available', 'customers': [], 'segments': []}

    snapshot_date = df['order_date'].max() + pd.Timedelta(days=1)

    # Aggregate per customer
    rfm = df.groupby('customer_id').agg(
        customer_name=('customer_name', 'first'),
        email=('email', 'first'),
        recency=('order_date', lambda x: (snapshot_date - x.max()).days),
        frequency=('order_id', 'nunique'),
        monetary=('total_amount', 'sum')
    ).reset_index()

    # RFM Score: Recency (1-5, lower days = higher score)
    # Use quantile-based binning. For recency: lower days = better score.
    try:
        rfm['r_score'] = pd.qcut(rfm['recency'], 5, labels=[5, 4, 3, 2, 1], duplicates='drop').astype(float)
    except ValueError:
        rfm['r_score'] = 3.0

    # Frequency scoring: use ABSOLUTE thresholds so single-purchase customers
    # cannot randomly land in the top score tier due to qcut tie-breaking.
    # Most customers in a DTC brand buy once — this should not equal "Champion".
    def score_frequency(f):
        if f >= 5:   return 5.0
        elif f >= 3: return 4.0
        elif f >= 2: return 3.0
        else:        return 1.0   # 1 purchase → lowest frequency score

    rfm['f_score'] = rfm['frequency'].apply(score_frequency)

    # Monetary scoring: quantile-based
    try:
        rfm['m_score'] = pd.qcut(rfm['monetary'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5], duplicates='drop').astype(float)
    except ValueError:
        rfm['m_score'] = 3.0

    rfm['rfm_score'] = (rfm['r_score'] + rfm['f_score'] + rfm['m_score']) / 3

    # Rule-based segment classification.
    # Champions: recent, frequent (3+), AND high monetary — not just recent+any-frequency.
    def classify_rfm_row(row):
        r = row['r_score']
        f = row['f_score']
        m = row['m_score']
        freq = row['frequency']
        if r >= 4 and f >= 4 and m >= 4:
            return 'Champion'
        elif freq == 1 and r >= 4:
            return 'New'               # Recent one-time buyer
        elif r >= 3 and f >= 3:
            return 'Loyal'
        elif r <= 2 and f >= 3:
            return 'At-Risk'           # Frequent but gone cold
        elif r <= 2 and f <= 1:
            return 'Lost'
        elif r >= 3:
            return 'Loyal'
        else:
            return 'Lost'

    rfm['segment'] = rfm.apply(classify_rfm_row, axis=1)

    # Resolve operational Customer.id using email to prevent warehouse/operational key mismatch
    op_cust_ids = db.session.query(Customer.id, Customer.email).all()
    email_to_id = {c.email.lower().strip(): c.id for c in op_cust_ids if c.email}

    # Fast bulk update the Customer model in operational DB
    update_mappings = []
    for _, row in rfm.iterrows():
        email_clean = (row['email'] or '').lower().strip()
        op_id = email_to_id.get(email_clean)
        if op_id:
            update_mappings.append({
                'id': op_id,
                'segment': row['segment'],
                'rfm_score': round(float(row['rfm_score']), 2)
            })
            
    db.session.bulk_update_mappings(Customer, update_mappings)
    db.session.commit()

    # Segment summary
    segment_summary = rfm.groupby('segment').agg(
        count=('customer_id', 'count'),
        avg_monetary=('monetary', 'mean'),
        avg_frequency=('frequency', 'mean'),
        avg_recency=('recency', 'mean')
    ).reset_index()

    customers_data = [
        {
            'customer_id': int(row['customer_id']),
            'customer_name': row['customer_name'],
            'email': row['email'],
            'recency_days': int(row['recency']),
            'frequency': int(row['frequency']),
            'monetary': round(float(row['monetary']), 2),
            'r_score': float(row['r_score']) if pd.notna(row['r_score']) else 3,
            'f_score': float(row['f_score']) if pd.notna(row['f_score']) else 3,
            'm_score': float(row['m_score']) if pd.notna(row['m_score']) else 3,
            'rfm_score': round(float(row['rfm_score']), 2),
            'segment': row['segment'],
        }
        for _, row in rfm.iterrows()
    ]

    segments_data = [
        {
            'segment': row['segment'],
            'count': int(row['count']),
            'avg_monetary': round(float(row['avg_monetary']), 2),
            'avg_frequency': round(float(row['avg_frequency']), 2),
            'avg_recency_days': round(float(row['avg_recency']), 1),
            **SEGMENT_CONFIG.get(row['segment'], {'color': '#6366F1', 'description': ''})
        }
        for _, row in segment_summary.iterrows()
    ]

    return {
        'customers': customers_data,
        'segments': segments_data,
        'model_info': {
            'method': 'Parametric RFM Decision Rules',
            'snapshot_date': str(snapshot_date.date()),
            'total_customers': len(rfm),
        }
    }
