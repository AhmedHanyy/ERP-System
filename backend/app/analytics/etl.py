"""
ETL Pipeline — Data preprocessing layer.
This is the boundary between OLTP (raw transactional data) and OLAP (analytics-ready data).

NOTE: When real dataset arrives, this is the primary file to update.
The functions here define the data contracts that all analytics modules depend on.
Changing input column names or structure here → update analytics modules accordingly.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app import db
from app.models import Order, OrderItem, Product, Customer, Inventory
import sqlalchemy


def extract_sales_data() -> pd.DataFrame:
    """
    Extract: Pull raw order/item data from OLTP.
    ─────────────────────────────────────────────
    OUTPUT SCHEMA (analytics contract):
      order_id, order_date, customer_id, product_id, product_name,
      category_id, quantity, unit_price, cost, revenue, profit
    
    NOTE: When real dataset replaces mock data, ensure these column names
    are preserved OR update all downstream analytics functions.
    """
    query = """
        SELECT 
            o.id            AS order_id,
            o.created_at    AS order_date,
            o.customer_id,
            o.status,
            oi.product_id,
            p.name          AS product_name,
            p.category_id,
            oi.quantity,
            oi.unit_price,
            p.cost,
            (oi.quantity * oi.unit_price)        AS revenue,
            (oi.quantity * (oi.unit_price - p.cost)) AS profit
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN products p ON oi.product_id = p.id
        WHERE o.status != 'Cancelled'
    """
    df = pd.read_sql(query, db.engine)
    df['order_date'] = pd.to_datetime(df['order_date'])
    return df


def extract_customer_data() -> pd.DataFrame:
    """
    Extract: Customer purchase summary for RFM computation.
    OUTPUT SCHEMA: customer_id, customer_name, email, segment,
                   order_date, total_amount
    """
    query = """
        SELECT
            c.id        AS customer_id,
            c.name      AS customer_name,
            c.email,
            c.segment,
            o.id        AS order_id,
            o.created_at AS order_date,
            o.total_amount
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        WHERE o.status != 'Cancelled'
    """
    df = pd.read_sql(query, db.engine)
    df['order_date'] = pd.to_datetime(df['order_date'])
    return df


def preprocess_sales(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform: Clean and enrich sales data.
    - Remove nulls
    - Add date features
    - Compute derived fields
    """
    df = df.dropna(subset=['order_date', 'product_id', 'customer_id'])
    df = df[df['quantity'] > 0]
    df = df[df['unit_price'] >= 0]

    # Add date features
    df['year']       = df['order_date'].dt.year
    df['month']      = df['order_date'].dt.month
    df['week']       = df['order_date'].dt.isocalendar().week.astype(int)
    df['day_of_week'] = df['order_date'].dt.dayofweek
    df['date']       = df['order_date'].dt.date

    return df


def get_daily_sales_df() -> pd.DataFrame:
    """OLAP-ready daily sales aggregation."""
    df = preprocess_sales(extract_sales_data())
    daily = df.groupby('date').agg(
        revenue=('revenue', 'sum'),
        profit=('profit', 'sum'),
        orders=('order_id', 'nunique'),
        units=('quantity', 'sum')
    ).reset_index()
    daily['date'] = pd.to_datetime(daily['date'])
    return daily.sort_values('date')


def get_product_sales_df() -> pd.DataFrame:
    """OLAP-ready product performance aggregation."""
    df = preprocess_sales(extract_sales_data())
    return df.groupby(['product_id', 'product_name', 'category_id']).agg(
        units_sold=('quantity', 'sum'),
        revenue=('revenue', 'sum'),
        profit=('profit', 'sum'),
        order_count=('order_id', 'nunique')
    ).reset_index().sort_values('revenue', ascending=False)
