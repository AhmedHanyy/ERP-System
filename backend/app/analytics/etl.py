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
    Extract: Pull sales data from the OLAP Warehouse schema.
    ─────────────────────────────────────────────
    OUTPUT SCHEMA (analytics contract):
      order_id, order_date, customer_id, product_id, product_name,
      category_id, quantity, unit_price, cost, revenue, profit
    """
    is_pg = db.engine.dialect.name == 'postgresql'
    schema = 'warehouse.' if is_pg else ''
    
    # Use appropriate quotes based on dialect (PostgreSQL requires double quotes for mixed-case columns)
    query = f"""
        SELECT 
            fs."OrderNumber"       AS order_id,
            d."FullDate"           AS order_date,
            fs."CustomerKey"       AS customer_id,
            fs."ProductKey"        AS product_id,
            p."Title"              AS product_name,
            0                      AS category_id,
            fs."Quantity"          AS quantity,
            fs."UnitPrice"         AS unit_price,
            fs."UnitCost"          AS cost,
            fs."GrossRevenue"      AS revenue,
            fs."NetProfit"         AS profit
        FROM {schema}fact_sales fs
        JOIN {schema}dim_product p ON fs."ProductKey" = p."ProductKey"
        JOIN {schema}dim_date d ON fs."DateKey" = d."DateKey"
        WHERE fs."FinancialStatus" != 'voided'
    """
    df = pd.read_sql(query, db.engine)
    df['order_date'] = pd.to_datetime(df['order_date'])
    return df


def extract_customer_data() -> pd.DataFrame:
    """
    Extract: Customer purchase summary from Warehouse for RFM.
    """
    is_pg = db.engine.dialect.name == 'postgresql'
    schema = 'warehouse.' if is_pg else ''
    
    query = f"""
        SELECT
            c."CustomerKey"       AS customer_id,
            c."FirstName" || ' ' || c."LastName" AS customer_name,
            c."Email"             AS email,
            c."RFM_Segment"       AS segment,
            fs."OrderNumber"      AS order_id,
            d."FullDate"          AS order_date,
            fs."GrossRevenue"     AS total_amount
        FROM {schema}dim_customer c
        JOIN {schema}fact_sales fs ON c."CustomerKey" = fs."CustomerKey"
        JOIN {schema}dim_date d ON fs."DateKey" = d."DateKey"
        WHERE fs."FinancialStatus" != 'voided'
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
