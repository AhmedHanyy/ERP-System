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
    0: 'Champion',
    1: 'Loyal',
    2: 'At-Risk',
    3: 'Lost',
}

SEGMENT_CONFIG = {
    'Champion': {'color': '#10B981', 'description': 'Bought recently, buy often, spend the most'},
    'Loyal':    {'color': '#6366F1', 'description': 'Buy regularly and respond well to promotions'},
    'At-Risk':  {'color': '#F59E0B', 'description': 'Used to buy often but haven\'t recently'},
    'Lost':     {'color': '#F43F5E', 'description': 'Lowest RFM scores, haven\'t purchased in a long time'},
}


def compute_rfm() -> dict:
    """
    Full RFM analysis pipeline.
    Returns: per-customer RFM data + cluster assignments + segment summary.
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

    # Normalize for clustering
    scaler = StandardScaler()
    # For recency: invert so higher = better (lower days = more recent)
    rfm_scaled = rfm[['recency', 'frequency', 'monetary']].copy()
    rfm_scaled['recency'] = -rfm_scaled['recency']  # flip sign
    X_scaled = scaler.fit_transform(rfm_scaled)

    # K-Means clustering
    n_clusters = min(4, len(rfm))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    rfm['cluster'] = kmeans.fit_predict(X_scaled)

    # Map clusters to meaningful segments based on centroid ordering
    # Sort clusters by combined RFM "goodness" (high freq+monetary, low recency days)
    cluster_means = rfm.groupby('cluster').agg(
        avg_recency=('recency', 'mean'),
        avg_frequency=('frequency', 'mean'),
        avg_monetary=('monetary', 'mean')
    )
    cluster_means['score'] = (
        -cluster_means['avg_recency'] +
        cluster_means['avg_frequency'] * 10 +
        cluster_means['avg_monetary'] / 100
    )
    sorted_clusters = cluster_means.sort_values('score', ascending=False).index.tolist()
    cluster_to_segment = {cluster: SEGMENT_MAP.get(i, f'Group {i}')
                          for i, cluster in enumerate(sorted_clusters)}
    rfm['segment'] = rfm['cluster'].map(cluster_to_segment)

    # Compute RFM score (1-5 scale per dimension)
    rfm['r_score'] = pd.qcut(rfm['recency'], 5, labels=[5,4,3,2,1], duplicates='drop').astype(float)
    rfm['f_score'] = pd.qcut(rfm['frequency'].rank(method='first'), 5, labels=[1,2,3,4,5], duplicates='drop').astype(float)
    rfm['m_score'] = pd.qcut(rfm['monetary'].rank(method='first'), 5, labels=[1,2,3,4,5], duplicates='drop').astype(float)
    rfm['rfm_score'] = (rfm['r_score'] + rfm['f_score'] + rfm['m_score']) / 3

    # Update customer segments in DB
    for _, row in rfm.iterrows():
        customer = Customer.query.get(int(row['customer_id']))
        if customer:
            customer.segment   = row['segment']
            customer.rfm_score = round(float(row['rfm_score']), 2)
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
            'method': 'RFM + K-Means (k=4)',
            'snapshot_date': str(snapshot_date.date()),
            'total_customers': len(rfm),
        }
    }
