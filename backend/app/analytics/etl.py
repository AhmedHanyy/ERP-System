"""
ETL Pipeline — Data preprocessing layer (Analytics adapter).
─────────────────────────────────────────────────────────────
This is the boundary between the Warehouse schema and all analytics modules.

KEY FILTERING RULE:
  All queries filter IsSynthetic = FALSE by default.
  Synthetic records exist ONLY for ML model training (forecasting, segmentation).
  They must NEVER appear in financial dashboards or business reporting.

  To include synthetic data (for ML use):
    extract_sales_data(include_synthetic=True)
"""
import pandas as pd
import numpy as np
from datetime import datetime
from app import db
import sqlalchemy


def extract_sales_data(include_synthetic: bool = False) -> pd.DataFrame:
    """
    Extract sales data from the Warehouse schema for analytics.

    OUTPUT SCHEMA (analytics contract):
      order_id, order_date, customer_id, product_id, product_name,
      product_type, category, quantity, unit_price, cost, revenue, profit,
      discount_code, order_shipping, is_synthetic, financial_status

    Args:
        include_synthetic: If True, include synthetic historical records.
                           Default False — dashboards and KPIs use real data only.
    """
    is_pg  = db.engine.dialect.name == 'postgresql'
    schema = 'warehouse.' if is_pg else ''

    synth_filter = '' if include_synthetic else 'AND fs."IsSynthetic" = FALSE'

    query = f"""
        SELECT
            fs."OrderNumber"        AS order_id,
            fs."ShopifyOrderID"     AS shopify_order_id,
            d."FullDate"            AS order_date,
            fs."CustomerKey"        AS customer_id,
            fs."ProductKey"         AS product_id,
            p."Title"               AS product_name,
            p."ProductType"         AS product_type,
            p."Category"            AS category,
            p."ProductFamily"       AS product_family,
            p."Fit"                 AS fit,
            p."Graphic"             AS graphic,
            p."VariantName"         AS variant_name,
            p."Size"                AS size,
            p."Color"               AS color,
            p."IsCostEstimated"     AS is_cost_estimated,
            fs."Quantity"           AS quantity,
            fs."UnitPrice"          AS unit_price,
            fs."CompareAtPrice"     AS compare_at_price,
            fs."UnitCost"           AS cost,
            fs."GrossRevenue"       AS revenue,
            fs."NetProfit"          AS profit,
            fs."DiscountAmount"     AS discount_amount,
            fs."DiscountCode"       AS discount_code,
            fs."OrderSubtotal"      AS order_subtotal,
            fs."OrderShipping"      AS order_shipping,
            fs."FinancialStatus"    AS financial_status,
            fs."FulfillmentStatus"  AS fulfillment_status,
            fs."PaymentMethod"      AS payment_method,
            fs."IsSynthetic"        AS is_synthetic,
            fs."IsCancelled"        AS is_cancelled,
            fs."RiskLevel"          AS risk_level
        FROM {schema}fact_sales fs
        JOIN {schema}dim_product p  ON fs."ProductKey"  = p."ProductKey"
                                    AND p."IsCurrent"   = TRUE
        JOIN {schema}dim_date d     ON fs."DateKey"     = d."DateKey"
        WHERE fs."FinancialStatus" != 'voided'
          AND fs."IsCancelled" = FALSE
          AND fs."ProductKey" != 0
          {synth_filter}
    """
    df = pd.read_sql(query, db.engine)
    df['order_date'] = pd.to_datetime(df['order_date'])
    return df


def extract_customer_data(include_synthetic: bool = False) -> pd.DataFrame:
    """
    Extract customer purchase summary from Warehouse for RFM analysis.
    Uses real orders only by default (IsSynthetic=False).
    """
    is_pg  = db.engine.dialect.name == 'postgresql'
    schema = 'warehouse.' if is_pg else ''

    synth_filter = '' if include_synthetic else 'AND fs."IsSynthetic" = FALSE'

    query = f"""
        SELECT
            c."CustomerKey"       AS customer_id,
            c."FirstName" || ' ' || c."LastName" AS customer_name,
            c."Email"             AS email,
            c."Region"            AS region,
            c."RFM_Segment"       AS segment,
            c."IsFraudRisk"       AS is_fraud_risk,
            c."CustomerTags"      AS tags,
            c."LifetimeTotalSpent"  AS lifetime_spent,
            c."LifetimeTotalOrders" AS lifetime_orders,
            fs."OrderNumber"      AS order_id,
            d."FullDate"          AS order_date,
            fs."GrossRevenue"     AS total_amount
        FROM {schema}dim_customer c
        JOIN {schema}fact_sales fs ON c."CustomerKey" = fs."CustomerKey"
        JOIN {schema}dim_date d    ON fs."DateKey"    = d."DateKey"
        WHERE fs."FinancialStatus" != 'voided'
          AND fs."IsCancelled" = FALSE
          {synth_filter}
    """
    df = pd.read_sql(query, db.engine)
    df['order_date'] = pd.to_datetime(df['order_date'])
    return df


def extract_basket_data() -> pd.DataFrame:
    """
    Extract basket data for Market Basket Analysis.
    Uses REAL orders only — synthetic baskets would distort association rules.

    CRITICAL: Groups at ProductFamily + Graphic level to prevent:
    - Spurious color-to-color associations (White Top -> Black Top = same product!)
    - Over-aggregation (all basics become one item)
    Uses ProductFamily as the item identifier (e.g., "Washed Oversized T-Shirt").
    """
    is_pg  = db.engine.dialect.name == 'postgresql'
    schema = 'warehouse.' if is_pg else ''

    query = f"""
        SELECT
            fs."OrderNumber"   AS order_id,
            COALESCE(p."ProductFamily", p."ProductType", 'Other') AS product_name,
            fs."Quantity"      AS quantity
        FROM {schema}fact_sales fs
        JOIN {schema}dim_product p ON fs."ProductKey" = p."ProductKey"
                                   AND p."IsCurrent"  = TRUE
        WHERE fs."IsSynthetic"     = FALSE
          AND fs."IsCancelled"     = FALSE
          AND fs."FinancialStatus" != 'voided'
          AND fs."ProductKey"      != 0
          AND p."ProductFamily" IS NOT NULL
    """
    df = pd.read_sql(query, db.engine)
    return df


def preprocess_sales(df: pd.DataFrame) -> pd.DataFrame:
    """Transform: clean and enrich sales data with date features."""
    df = df.dropna(subset=['order_date', 'product_id', 'customer_id'])
    df = df[df['quantity'] > 0]
    df = df[df['unit_price'] >= 0]

    df['year']        = df['order_date'].dt.year
    df['month']       = df['order_date'].dt.month
    df['week']        = df['order_date'].dt.isocalendar().week.astype(int)
    df['day_of_week'] = df['order_date'].dt.dayofweek
    df['date']        = df['order_date'].dt.date

    return df


def get_daily_sales_df(include_synthetic: bool = False) -> pd.DataFrame:
    """OLAP-ready daily sales aggregation (real data only by default)."""
    df    = preprocess_sales(extract_sales_data(include_synthetic=include_synthetic))
    daily = df.groupby('date').agg(
        revenue=('revenue', 'sum'),
        profit=('profit', 'sum'),
        orders=('order_id', 'nunique'),
        units=('quantity', 'sum')
    ).reset_index()
    daily['date'] = pd.to_datetime(daily['date'])
    return daily.sort_values('date')


def get_daily_sales_df_with_synthetic() -> pd.DataFrame:
    """Daily sales including synthetic — for forecasting model training only."""
    return get_daily_sales_df(include_synthetic=True)


def get_product_sales_df(include_synthetic: bool = False) -> pd.DataFrame:
    """
    OLAP-ready product performance aggregation — sourced from OPERATIONAL DB.

    Uses Order + OrderItem + Product instead of warehouse FactSales because the
    warehouse has a known product-mapping gap: ~2,887 sweatpants units (including
    Shopify's #1 product "Baggy Wide Leg - Black") are in ProductKey=0 and thus
    invisible or misattributed in FactSales. The operational DB has correct
    attribution for all 6,699 orders and matches Shopify's product rankings.

    NOTE: include_synthetic param is kept for API compatibility but has no effect
    since the operational DB does not contain synthetic records.
    """
    from app.models import Order, OrderItem, Product
    from app.models.product import Category
    from sqlalchemy import func

    rows = db.session.query(
        Product.id.label('product_id'),
        Product.name.label('product_name'),
        Category.name.label('category_name'),
        func.sum(OrderItem.quantity).label('units_sold'),
        func.sum(OrderItem.quantity * OrderItem.unit_price).label('revenue'),
        func.sum(OrderItem.quantity * Product.cost).label('cogs'),
        func.count(OrderItem.order_id.distinct()).label('order_count'),
    ).join(OrderItem, OrderItem.product_id == Product.id
    ).join(Order, OrderItem.order_id == Order.id
    ).outerjoin(Category, Product.category_id == Category.id
    ).filter(Order.status != 'Cancelled'
    ).group_by(Product.id, Product.name, Category.name
    ).order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc()
    ).all()

    records = []
    for r in rows:
        revenue = float(r.revenue or 0)
        cogs    = float(r.cogs or 0)
        records.append({
            'product_name':      r.product_name,
            'product_type':      r.category_name or 'Unknown',
            'category':          r.category_name or 'Unknown',
            'product_id':        r.product_id,
            'units_sold':        int(r.units_sold or 0),
            'revenue':           revenue,
            'profit':            round(revenue - cogs, 2),
            'order_count':       int(r.order_count or 0),
            'is_cost_estimated': 0,
        })

    return pd.DataFrame(records) if records else pd.DataFrame(columns=[
        'product_name', 'product_type', 'category', 'product_id',
        'units_sold', 'revenue', 'profit', 'order_count', 'is_cost_estimated'
    ])



def get_discount_performance_df() -> pd.DataFrame:
    """
    Real order discount code performance analysis.
    Filters real orders only — discount code analysis must reflect real campaigns.
    """
    is_pg  = db.engine.dialect.name == 'postgresql'
    schema = 'warehouse.' if is_pg else ''

    query = f"""
        SELECT
            COALESCE(fs."DiscountCode", 'No Discount') AS discount_code,
            COUNT(DISTINCT fs."OrderNumber")            AS order_count,
            SUM(fs."GrossRevenue")                     AS total_revenue,
            SUM(fs."DiscountAmount")                   AS total_discount_given,
            AVG(fs."OrderSubtotal")                    AS avg_order_value
        FROM {schema}fact_sales fs
        WHERE fs."IsSynthetic"     = FALSE
          AND fs."IsCancelled"     = FALSE
          AND fs."FinancialStatus" != 'voided'
        GROUP BY fs."DiscountCode"
        ORDER BY order_count DESC
    """
    return pd.read_sql(query, db.engine)


def get_geographic_sales_df() -> pd.DataFrame:
    """Sales by governorate — real orders only."""
    is_pg  = db.engine.dialect.name == 'postgresql'
    schema = 'warehouse.' if is_pg else ''

    query = f"""
        SELECT
            c."Region"                              AS governorate,
            COUNT(DISTINCT fs."OrderNumber")        AS order_count,
            SUM(fs."GrossRevenue")                  AS total_revenue,
            AVG(fs."OrderSubtotal")                 AS avg_order_value
        FROM {schema}fact_sales fs
        JOIN {schema}dim_customer c ON fs."CustomerKey" = c."CustomerKey"
        WHERE fs."IsSynthetic"     = FALSE
          AND fs."IsCancelled"     = FALSE
          AND fs."FinancialStatus" != 'voided'
        GROUP BY c."Region"
        ORDER BY total_revenue DESC
    """
    return pd.read_sql(query, db.engine)
