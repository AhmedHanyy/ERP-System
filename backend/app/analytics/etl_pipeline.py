"""
ETL Pipeline — Leveld ERP Warehouse
=====================================
Loads real Shopify data into the warehouse schema, then appends
synthetic historical records for forecasting/analytics use.

DATA FLOW:
  Real Shopify CSVs → Extract → Transform → Load (real records, IsSynthetic=False)
  Synthetic Generator → Generate → Append (synthetic records, IsSynthetic=True)

KEY DESIGN PRINCIPLES:
  - Real records are loaded FIRST and never overwritten by synthetics
  - Synthetic records use real catalog SKUs, real customer pool, real distributions
  - All warehouse tables carry full business context (DiscountCode, tags, etc.)
  - FactProcurement uses demo stubs (IsReal=False) until real Excel is provided
  - DimSupplier uses labeled demo data (IsReal=False)
"""
import os
import sys
import math
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import text

from app import db
from app.models import (
    Customer, Product, ProductVariant, Order, OrderItem, Supplier, ProcurementRequest,
)
from app.models.warehouse import (
    DimCustomer, DimProduct, DimDate, DimSupplier, DimChannel,
    FactSales, FactInventory, FactProcurement, FactReturns, ETLRun
)
from app.analytics.synthetic_generator import (
    build_product_catalog,
    compute_product_weights,
    build_category_cost_ratios,
    compute_cost_for_variant,
    generate_synthetic_sales,
    generate_demo_procurement,
    get_demo_suppliers_df,
)

# ─── File Paths ───────────────────────────────────────────────────────────────
BASE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'shopify')
ORDERS_CSV    = os.path.join(BASE_DIR, 'orders_export_1.csv')
CUSTOMERS_CSV = os.path.join(BASE_DIR, 'customers_export.csv')
PRODUCTS_CSV  = os.path.join(BASE_DIR, 'products_export_1.csv')

# ─── Database Config ──────────────────────────────────────────────────────────
DATABASE_URL   = os.environ.get('DATABASE_URL', '')
IS_POSTGRES    = DATABASE_URL.startswith('postgresql') or DATABASE_URL.startswith('postgres')
SCHEMA_PREFIX  = 'warehouse.' if IS_POSTGRES else ''
SCHEMA_NAME    = 'warehouse' if IS_POSTGRES else None

# ─── City / Governorate Normalisation Map ────────────────────────────────────
GOVERNORATE_MAP = {
    'cairo': 'Cairo', 'القاهرة': 'Cairo', 'القاهره': 'Cairo', 'c': 'Cairo',
    'new cairo': 'Cairo', 'rehab': 'Cairo', 'madinaty': 'Cairo', 'maadi': 'Cairo',
    'nasr city': 'Cairo', 'heliopolis': 'Cairo', 'sherouk': 'Cairo',
    'rehab city': 'Cairo', 'shorouk': 'Cairo', 'madinty': 'Cairo',
    'fifth settlement': 'Cairo', 'التجمع الخامس': 'Cairo', 'el maadi': 'Cairo',
    'egypt': 'Cairo',  # generic "Egypt" → default to Cairo
    'alexandria': 'Alexandria', 'alex': 'Alexandria',
    'الاسكندريه': 'Alexandria', 'الاسكندرية': 'Alexandria',
    'الإسكندرية': 'Alexandria', 'alx': 'Alexandria',
    'اسكندرية': 'Alexandria', 'اسكندريه': 'Alexandria',
    'giza': 'Giza', 'gz': 'Giza', 'الجيزة': 'Giza', 'الجيزه': 'Giza',
    'sheikh zayed': 'Giza', 'الشيخ زايد': 'Giza',
    '6 october': 'Giza', '6th of october': 'Giza', '٦ اكتوبر': 'Giza',
    'dokki': 'Giza', 'مهندسين': 'Giza', 'mohandeseen': 'Giza', 'mohandessin': 'Giza',
    'agouza': 'Giza', 'haram': 'Giza', 'faisal': 'Giza',
    'suez': 'Suez', 'السويس': 'Suez',
    'ismailia': 'Ismailia', 'الاسماعيليه': 'Ismailia', 'الإسماعيلية': 'Ismailia',
    'zagazig': 'Sharqia', 'الزقازيق': 'Sharqia',
    'tanta': 'Gharbia', 'طنطا': 'Gharbia',
    'mansoura': 'Dakahlia', 'المنصورة': 'Dakahlia',
    'banha': 'Qalyubia', 'بنها': 'Qalyubia', 'kb': 'Qalyubia',
    'hurghada': 'Red Sea', 'الغردقة': 'Red Sea',
    'sharm': 'South Sinai', 'portsaid': 'Port Said', 'دمياط': 'Damietta',
    'assiut': 'Assiut', 'أسيوط': 'Assiut',
    'luxor': 'Luxor', 'الأقصر': 'Luxor',
    'aswan': 'Aswan', 'أسوان': 'Aswan',
    'sohag': 'Sohag', 'سوهاج': 'Sohag',
    'minya': 'Minya', 'المنيا': 'Minya',
    'fayoum': 'Fayoum', 'الفيوم': 'Fayoum',
    'beni suef': 'Beni Suef', 'بني سويف': 'Beni Suef',
}


def clean_city(city_val: str) -> str:
    """Normalize Egyptian city/governorate name."""
    if not isinstance(city_val, str) or not city_val.strip():
        return 'Cairo'
    city_lower = city_val.strip().lower()
    for pattern, gov in GOVERNORATE_MAP.items():
        if pattern in city_lower:
            return gov
    return city_val.strip().title()


def truncate_table(conn, table_name: str):
    """Safely truncate a warehouse table."""
    if IS_POSTGRES:
        conn.execute(text(f'TRUNCATE TABLE warehouse."{table_name}" CASCADE;'))
    else:
        conn.execute(text(f'DELETE FROM "{table_name}";'))
    conn.commit()


def safe_str(val, default='') -> str:
    if pd.isna(val) or val is None:
        return default
    return str(val).strip()


def safe_float(val, default=0.0) -> float:
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def safe_int(val, default=0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ─── MAIN ETL PIPELINE ───────────────────────────────────────────────────────

def run_etl_pipeline():
    start_time = datetime.utcnow()
    print('=' * 60)
    print('Leveld ERP — Warehouse ETL Pipeline')
    print(f'Started: {start_time.isoformat()}')
    print('=' * 60)

    etl_run = ETLRun(start_time=start_time, status='Running')
    db.session.add(etl_run)
    db.session.commit()

    try:
        # ── EXTRACT ──────────────────────────────────────────────────────────
        print('\n[1/8] Extracting source data...')
        orders_df   = pd.read_csv(ORDERS_CSV,    low_memory=False)
        customers_df = pd.read_csv(CUSTOMERS_CSV, low_memory=False)
        products_df  = pd.read_csv(PRODUCTS_CSV,  low_memory=False)

        print(f'  Orders rows:    {len(orders_df):,}')
        print(f'  Customers rows: {len(customers_df):,}')
        print(f'  Products rows:  {len(products_df):,}')

        # Forward-fill order metadata across multi-row orders
        ORDER_META_COLS = [
            'Financial Status', 'Fulfillment Status', 'Currency', 'Subtotal',
            'Shipping', 'Taxes', 'Total', 'Discount Code', 'Discount Amount',
            'Shipping Method', 'Created at', 'Billing Name', 'Billing Street',
            'Billing City', 'Billing Zip', 'Billing Province', 'Billing Country',
            'Billing Phone', 'Shipping Name', 'Shipping City', 'Shipping Country',
            'Shipping Phone', 'Payment Method', 'Risk Level', 'Notes',
            'Cancelled at', 'Refunded Amount', 'Id', 'Tags', 'Source',
            'Outstanding Balance', 'Payment Terms Name',
        ]
        orders_df.sort_values('Name', inplace=True)
        orders_df[ORDER_META_COLS] = orders_df.groupby('Name')[ORDER_META_COLS].ffill()
        orders_df['Created_dt'] = pd.to_datetime(orders_df['Created at'], utc=True, errors='coerce')

        # ── DIM DATE ─────────────────────────────────────────────────────────
        print('\n[2/8] Building DimDate...')
        min_date = datetime(2023, 1, 1)
        max_date = datetime.now() + timedelta(days=60)
        date_records = []
        for dt in pd.date_range(start=min_date, end=max_date, freq='D'):
            date_records.append({
                'DateKey':   int(dt.strftime('%Y%m%d')),
                'FullDate':  dt.date(),
                'Year':      dt.year,
                'Quarter':   (dt.month - 1) // 3 + 1,
                'Month':     dt.month,
                'MonthName': dt.strftime('%B'),
                'Day':       dt.day,
                'DayOfWeek': dt.strftime('%A'),
                'IsWeekend': dt.weekday() in [4, 5],  # Fri + Sat = Egyptian weekend
            })
        dim_date_df = pd.DataFrame(date_records)
        print(f'  DimDate rows: {len(dim_date_df):,}')

        # ── DIM CUSTOMER ─────────────────────────────────────────────────────
        print('\n[3/8] Transforming DimCustomer...')
        FRAUD_KEYWORDS = ['fraud', 'banned', 'bad customer', 'theif', 'theft']

        cust_records = []
        customers_df['Customer ID_clean'] = (
            customers_df['Customer ID'].astype(str).str.strip().str.replace("'", '')
        )

        for _, row in customers_df.iterrows():
            # Phone resolution
            phone_default = safe_str(row.get('Default Address Phone')).replace("'", '')
            phone_main    = safe_str(row.get('Phone')).replace("'", '').replace('+', '')
            phone         = phone_main if phone_main and phone_main not in ('nan', '') else phone_default

            # City normalization
            city_raw  = safe_str(row.get('Default Address City'))
            city_norm = clean_city(city_raw)

            # Tags and fraud detection
            tags_raw   = safe_str(row.get('Tags', ''))
            is_fraud   = any(kw in tags_raw.lower() for kw in FRAUD_KEYWORDS)

            # LTV from customers export
            lifetime_spent  = safe_float(row.get('Total Spent', 0))
            lifetime_orders = safe_int(row.get('Total Orders', 0))

            cust_records.append({
                'ShopifyCustomerID':   row['Customer ID_clean'],
                'FirstName':           safe_str(row.get('First Name')),
                'LastName':            safe_str(row.get('Last Name')),
                'Email':               safe_str(row.get('Email')).lower(),
                'Phone':               phone,
                'City':                city_raw if city_raw else 'Unknown',
                'Region':              city_norm,
                'Country':             safe_str(row.get('Default Address Country Code'), 'EG'),
                'AcceptsMarketing':    str(row.get('Accepts Email Marketing', 'no')).lower() == 'yes',
                'RFM_Segment':         'New',
                'CustomerTags':        tags_raw if tags_raw else None,
                'CustomerNote':        safe_str(row.get('Note')) if pd.notna(row.get('Note')) else None,
                'IsFraudRisk':         is_fraud,
                'LifetimeTotalSpent':  lifetime_spent,
                'LifetimeTotalOrders': lifetime_orders,
            })

        dim_cust_df = pd.DataFrame(cust_records)
        dim_cust_df.drop_duplicates(subset=['ShopifyCustomerID'], inplace=True)
        
        # Align RFM_Segment with operational customer database
        try:
            op_custs = db.session.query(Customer.email, Customer.segment).all()
            email_to_segment = {c.email.lower().strip(): c.segment for c in op_custs if c.email}
            dim_cust_df['RFM_Segment'] = dim_cust_df['Email'].str.strip().str.lower().map(email_to_segment).fillna('New')
        except Exception as e:
            print(f"  Could not align RFM segments: {e}")
            
        print(f'  DimCustomer rows: {len(dim_cust_df):,} ({dim_cust_df["IsFraudRisk"].sum()} fraud-flagged)')

        # ── DIM SUPPLIER (extracted from operational tables) ──────────────────
        print('\n[4/8] Extracting DimSupplier from operational suppliers...')
        suppliers = Supplier.query.all()
        supplier_records = []
        for s in suppliers:
            supplier_records.append({
                'SupplierKey':      s.id,
                'SupplierName':     s.name,
                'ContactPerson':    s.contact_person,
                'Phone':            s.phone,
                'SupplierType':     s.notes, # Feathers is 'Printed Products Supplier', Printlet is 'Non-Printed (Basic) Products Supplier'
                'Country':          'Egypt',
                'LeadTimeDays_Avg': s.lead_time_days,
                'MinOrderQty':      100 if s.id == 1 else 200,
                'Rating':           s.rating,
                'Status':           'Active' if s.is_active else 'Inactive',
                'IsReal':           s.is_real,
            })
        dim_supplier_df = pd.DataFrame(supplier_records)
        print(f'  DimSupplier rows: {len(dim_supplier_df):,}')

        # ── DIM CHANNEL ──────────────────────────────────────────────────────
        dim_channel_df = pd.DataFrame([
            {'ChannelKey': 1, 'ChannelName': 'Online Storefront'},
            {'ChannelKey': 2, 'ChannelName': 'Retail POS'},
            {'ChannelKey': 3, 'ChannelName': 'Mobile Application'},
            {'ChannelKey': 4, 'ChannelName': 'B2B Portal'},
        ])

        # ── DIM PRODUCT (SCD Type 2) ──────────────────────────────────────────
        print('\n[5/8] Transforming DimProduct (SCD Type 2)...')
        catalog_df = build_product_catalog(products_df)

        # Build category cost ratios from real cost data
        category_ratios = build_category_cost_ratios(catalog_df)
        global_ratio    = 0.45  # Egyptian fashion apparel fallback

        # Load existing DimProduct for SCD2 comparison
        existing_products = {}
        try:
            existing_rows = db.session.query(DimProduct).filter_by(IsCurrent=True).all()
            existing_products = {p.SKU: p for p in existing_rows}
        except Exception as e:
            print(f'  No existing DimProduct found: {e}')

        new_product_inserts = []
        scd2_updates        = []
        sku_to_prod_key     = {}
        handled_skus        = set()
        next_prod_key = max((p.ProductKey for p in existing_products.values()), default=0) + 1

        for _, variant in catalog_df.iterrows():
            sku = variant['SKU']
            if sku in handled_skus:
                continue
            handled_skus.add(sku)

            cost, is_cost_estimated = compute_cost_for_variant(
                variant.to_dict(), category_ratios, global_ratio
            )

            row_data = {
                'ProductKey':     next_prod_key,
                'SKU':            sku,
                'Handle':         variant['Handle'],
                'Title':          variant['Title'],
                'Category':       variant['Category'],
                'ProductType':    variant['ProductType'],
                'ProductFamily':  variant.get('ProductFamily'),
                'Fit':            variant.get('Fit'),
                'Graphic':        variant.get('Graphic'),
                'VariantName':    variant.get('VariantName'),
                'Size':           variant['Size'],
                'Color':          variant['Color'],
                'Fabric':         variant['Fabric'],
                'TargetGender':   variant['TargetGender'],
                'SizesOffered':   variant['SizesOffered'],
                'Barcode':        variant['Barcode'],
                'Price':          variant['Price'],
                'CompareAtPrice': variant['CompareAtPrice'],
                'Cost':           round(cost, 4),
                'IsCostEstimated':is_cost_estimated,
                'Vendor':         variant['Vendor'],
                'Status':         variant['Status'],
                'IsActive':       variant['Status'] == 'active',
                'RowStartDate':   start_time,
                'RowEndDate':     None,
                'IsCurrent':      True,
            }

            existing_p = existing_products.get(sku)
            if existing_p:
                changed = (
                    abs(existing_p.Price - variant['Price']) > 0.01
                    or abs(existing_p.Cost - cost) > 0.01
                    or existing_p.Title != variant['Title']
                    or existing_p.Status != variant['Status']
                )
                if changed:
                    scd2_updates.append({'ProductKey': existing_p.ProductKey})
                    new_product_inserts.append(row_data)
                    sku_to_prod_key[sku] = next_prod_key
                    next_prod_key += 1
                else:
                    sku_to_prod_key[sku] = existing_p.ProductKey
            else:
                new_product_inserts.append(row_data)
                sku_to_prod_key[sku] = next_prod_key
                next_prod_key += 1

        # Apply SCD2 expirations
        if scd2_updates:
            for upd in scd2_updates:
                db.session.query(DimProduct).filter_by(
                    ProductKey=upd['ProductKey']
                ).update({'RowEndDate': start_time, 'IsCurrent': False})
            db.session.commit()
            print(f'  SCD2 expired: {len(scd2_updates)} product rows')

        if new_product_inserts:
            pd.DataFrame(new_product_inserts).to_sql(
                name='dim_product', con=db.engine, schema=SCHEMA_NAME,
                if_exists='append', index=False
            )

        # Refresh SKU → ProductKey mapping
        all_current = db.session.query(DimProduct).filter_by(IsCurrent=True).all()
        sku_to_prod_key  = {p.SKU: p.ProductKey for p in all_current}
        sku_to_cost      = {p.SKU: p.Cost       for p in all_current}
        sku_to_price     = {p.SKU: p.Price      for p in all_current}

        # Build a map of ProductKey to IsPrinted
        prod_key_to_is_printed = {}
        for p in all_current:
            title = (p.Title or '').lower()
            ptype = (p.ProductType or '').lower()
            pfamily = (p.ProductFamily or '').lower()
            is_printed = 'printed' in title or 'graphic' in title or 'printed' in ptype or 'graphic' in ptype or 'printed' in pfamily or 'graphic' in pfamily
            prod_key_to_is_printed[p.ProductKey] = is_printed
        print(f'  DimProduct rows (current): {len(sku_to_prod_key):,}')

        # ── LOAD DIMENSION TABLES ─────────────────────────────────────────────
        print('\n[6/8] Loading dimension tables...')
        dims_to_load = [
            ('dim_date',     dim_date_df),
            ('dim_customer', dim_cust_df),
            ('dim_supplier', dim_supplier_df),
            ('dim_channel',  dim_channel_df),
        ]
        for tname, tdf in dims_to_load:
            with db.engine.connect() as conn:
                truncate_table(conn, tname)
            tdf.to_sql(
                name=tname, con=db.engine, schema=SCHEMA_NAME,
                if_exists='append', index=False
            )
            print(f'  Loaded {len(tdf):,} rows -> {SCHEMA_PREFIX}{tname}')

        # Build customer email → CustomerKey map
        db_custs          = db.session.query(DimCustomer).all()
        email_to_cust_key = {c.Email.lower(): c.CustomerKey for c in db_custs if c.Email}
        customer_keys     = [c.CustomerKey for c in db_custs]
        default_cust_key  = customer_keys[0] if customer_keys else 1

        # ── TRANSFORM REAL SHOPIFY ORDERS → FACT SALES ───────────────────────
        print('\n[7/8] Transforming real Shopify orders -> FactSales...')

        def resolve_product_key(sku_clean: str, item_name: str) -> int:
            """SKU → Title → base-title fallback for product resolution."""
            if sku_clean and sku_clean in sku_to_prod_key:
                return sku_to_prod_key[sku_clean]
            # Title exact match
            for p in all_current:
                if p.Title == item_name:
                    return p.ProductKey
            # Base title prefix match
            base = item_name.split(' - ')[0].strip() if item_name else ''
            if base:
                for p in all_current:
                    if p.Title and p.Title.startswith(base):
                        return p.ProductKey
            return list(sku_to_prod_key.values())[0] if sku_to_prod_key else 1

        real_sales_records = []
        for _, row in orders_df.iterrows():
            sku_clean  = str(row.get('Lineitem sku', '')).strip().replace("'", '')
            sku_clean  = sku_clean if sku_clean and sku_clean != 'nan' else ''
            item_name  = safe_str(row.get('Lineitem name', ''))
            email      = safe_str(row.get('Email', '')).lower().replace("'", '')

            prod_key   = resolve_product_key(sku_clean, item_name)
            cust_key   = email_to_cust_key.get(email, default_cust_key)

            dt = row['Created_dt']
            if pd.isna(dt):
                dt = datetime.now()
            date_key = int(dt.strftime('%Y%m%d'))

            qty          = safe_int(row.get('Lineitem quantity', 1), 1)
            unit_price   = safe_float(row.get('Lineitem price', 0))
            compare_at   = safe_float(row.get('Lineitem compare at price', 0)) or None
            line_discount = safe_float(row.get('Lineitem discount', 0))

            # Cost resolution
            unit_cost = sku_to_cost.get(sku_clean, unit_price * global_ratio)
            if unit_cost <= 0:
                unit_cost = unit_price * global_ratio

            gross_rev = qty * unit_price
            cogs      = qty * unit_cost
            net_profit = gross_rev - line_discount - cogs

            fin_status  = safe_str(row.get('Financial Status'), 'pending')
            is_cancelled = pd.notna(row.get('Cancelled at')) and str(row.get('Cancelled at')) != 'nan'

            # Shopify numeric order ID
            shopify_id_raw = row.get('Id')
            shopify_id = str(int(float(shopify_id_raw))) if pd.notna(shopify_id_raw) else None

            shipping_city_raw = safe_str(row.get('Shipping City'))
            shipping_city_norm = clean_city(shipping_city_raw)
            shipping_fee = 50.0 if shipping_city_norm in ('Cairo', 'Giza') else 70.0
            
            supplier_key = 1 if prod_key_to_is_printed.get(prod_key, False) else 2

            real_sales_records.append({
                'DateKey':          date_key,
                'CustomerKey':      cust_key,
                'ProductKey':       prod_key,
                'SupplierKey':      supplier_key,
                'ChannelKey':       1,  # Online only
                'OrderNumber':      safe_str(row.get('Name')),
                'ShopifyOrderID':   shopify_id,
                'IsSynthetic':      False,
                'IsCancelled':      is_cancelled,
                'Quantity':         qty,
                'UnitPrice':        unit_price,
                'CompareAtPrice':   compare_at,
                'UnitCost':         round(unit_cost, 4),
                'DiscountAmount':   line_discount,
                'GrossRevenue':     round(gross_rev, 2),
                'COGS':             round(cogs, 2),
                'NetProfit':        round(net_profit, 2),
                'DiscountCode':     safe_str(row.get('Discount Code')) or None,
                'OrderSubtotal':    safe_float(row.get('Subtotal')) or None,
                'OrderShipping':    shipping_fee,
                'FinancialStatus':  fin_status,
                'FulfillmentStatus':safe_str(row.get('Fulfillment Status'), 'unfulfilled'),
                'PaymentMethod':    safe_str(row.get('Payment Method'), 'Cash on Delivery (COD)'),
                'RiskLevel':        safe_str(row.get('Risk Level'), 'Low'),
            })

        real_sales_df = pd.DataFrame(real_sales_records)
        print(f'  Real Shopify line items: {len(real_sales_df):,}')
        print(f'  Unique real orders:      {real_sales_df["OrderNumber"].nunique():,}')
        print(f'  Cancelled:               {real_sales_df["IsCancelled"].sum():,}')

        # ── GENERATE SYNTHETIC SALES ──────────────────────────────────────────
        print('\n  Generating synthetic historical sales...')
        product_weights = compute_product_weights(catalog_df, orders_df)

        synth_sales_df = generate_synthetic_sales(
            catalog_df       = catalog_df,
            product_weights  = product_weights,
            category_ratios  = category_ratios,
            customer_keys    = customer_keys,
            customer_email_to_key = email_to_cust_key,
            start_date       = datetime(2023, 1, 1),
            end_date         = datetime(2025, 12, 31),
            target_orders    = 18000,
            random_seed      = 42,
        )

        # Resolve ProductKey for synthetic records using variant catalog index
        if not synth_sales_df.empty and '_VariantIdx' not in synth_sales_df.columns:
            # Product key was not in the returned df (it's assigned below)
            pass

        # Map variant catalog index → ProductKey for synthetic records
        if not synth_sales_df.empty:
            # Re-run with variant index to get ProductKey
            catalog_sku_list = catalog_df['SKU'].tolist()
            # The generator already dropped _VariantIdx — remap via SKU position
            # Regenerate with ProductKey directly via sku_to_prod_key
            synth_sales_df = generate_synthetic_sales_with_keys(
                catalog_df       = catalog_df,
                product_weights  = product_weights,
                category_ratios  = category_ratios,
                customer_keys    = customer_keys,
                customer_email_to_key = email_to_cust_key,
                sku_to_prod_key  = sku_to_prod_key,
                start_date       = datetime(2023, 1, 1),
                end_date         = datetime(2025, 12, 31),
                target_orders    = 18000,
                random_seed      = 42,
            )

        # Combine real + synthetic
        combined_sales_df = pd.concat([real_sales_df, synth_sales_df], ignore_index=True)
        print(f'  Combined FactSales rows: {len(combined_sales_df):,} '
              f'(real={len(real_sales_df):,}, synthetic={len(synth_sales_df):,})')

        # ── FACT INVENTORY (from real products snapshot) ──────────────────────
        print('\n  Building FactInventory from real product snapshot...')
        inventory_records = []
        current_date_key  = int(datetime.utcnow().strftime('%Y%m%d'))

        for _, variant in catalog_df.iterrows():
            sku      = variant['SKU']
            prod_key = sku_to_prod_key.get(sku)
            if not prod_key:
                continue

            qoh      = int(variant.get('InventoryQty', 0))
            # Reorder point: 5 units (conservative for fashion startup)
            reorder_pt  = 5
            reorder_qty = 50
            days_supply = qoh / 1.0  # placeholder; 1 unit/day conservative

            status = 'Stockout' if qoh == 0 else ('Low Stock' if qoh <= reorder_pt else 'Healthy')

            inventory_records.append({
                'DateKey':         current_date_key,
                'ProductKey':      prod_key,
                'QuantityOnHand':  qoh,
                'ReorderPoint':    reorder_pt,
                'ReorderQuantity': reorder_qty,
                'DaysOfSupply':    round(days_supply, 1),
                'StockStatus':     status,
            })

        fact_inventory_df = pd.DataFrame(inventory_records)
        print(f'  FactInventory rows: {len(fact_inventory_df):,}')

        # ── FACT PROCUREMENT (extracted from operational tables) ──────────────
        print('\n  Extracting FactProcurement from operational procurement_requests...')
        proc_requests = ProcurementRequest.query.all()
        procurement_records = []
        for pr in proc_requests:
            prod_sku = pr.product.sku if pr.product else None
            prod_key = sku_to_prod_key.get(prod_sku)
            if not prod_key:
                prod_key = list(sku_to_prod_key.values())[0] if sku_to_prod_key else 1
            
            date_key = int(pr.requested_at.strftime('%Y%m%d'))
            received_date_key = int(pr.received_at.strftime('%Y%m%d')) if pr.received_at else None
            
            lead_time = None
            if pr.received_at:
                lead_time = (pr.received_at - pr.requested_at).days
            
            procurement_records.append({
                'DateKey':           date_key,
                'SupplierKey':       pr.supplier_id,
                'ProductKey':        prod_key,
                'QuantityRequested': pr.quantity,
                'UnitCost':          pr.unit_cost,
                'TotalCost':         pr.total_cost,
                'LeadTimeDays':      lead_time,
                'ReceivedDateKey':   received_date_key,
                'Status':            pr.status,
                'IsReal':            pr.is_real,
            })
        fact_procurement_df = pd.DataFrame(procurement_records)
        print(f'  FactProcurement rows: {len(fact_procurement_df):,}')

        # ── LOAD FACT TABLES ──────────────────────────────────────────────────
        print('\n[8/8] Loading Fact tables...')
        facts_to_load = [
            ('fact_sales',        combined_sales_df),
            ('fact_inventory',    fact_inventory_df),
            ('fact_procurement',  fact_procurement_df),
        ]
        for tname, tdf in facts_to_load:
            with db.engine.connect() as conn:
                truncate_table(conn, tname)
            tdf.to_sql(
                name=tname, con=db.engine, schema=SCHEMA_NAME,
                if_exists='append', index=False
            )
            print(f'  Loaded {len(tdf):,} rows -> {SCHEMA_PREFIX}{tname}')

        # Clear FactReturns (no real return data)
        with db.engine.connect() as conn:
            truncate_table(conn, 'fact_returns')
        print(f'  FactReturns cleared (no real return data in Shopify export)')

        # ── FINALIZE ─────────────────────────────────────────────────────────
        etl_run.end_time       = datetime.utcnow()
        etl_run.status         = 'Completed'
        etl_run.rows_extracted = len(orders_df) + len(customers_df) + len(products_df)
        etl_run.rows_loaded    = len(combined_sales_df) + len(fact_procurement_df) + len(fact_inventory_df)
        etl_run.real_rows      = len(real_sales_df)
        etl_run.synthetic_rows = len(synth_sales_df)
        db.session.commit()

        duration = (etl_run.end_time - start_time).total_seconds()
        print(f'\n[OK] ETL Pipeline Completed in {duration:.1f}s')
        print(f'  Real records:      {len(real_sales_df):,}')
        print(f'  Synthetic records: {len(synth_sales_df):,}')
        print(f'  Total in warehouse: {len(combined_sales_df):,}')
        return True

    except Exception as exc:
        import traceback
        err_msg = traceback.format_exc()
        print(f'\n[ERROR] ETL Pipeline Failed: {exc}')
        etl_run.end_time = datetime.utcnow()
        etl_run.status   = 'Failed'
        etl_run.errors   = err_msg
        db.session.commit()
        return False


# ─── Inline synthetic generation WITH ProductKey resolution ──────────────────

def generate_synthetic_sales_with_keys(
    catalog_df, product_weights, category_ratios,
    customer_keys, customer_email_to_key, sku_to_prod_key,
    start_date, end_date, target_orders=18000, random_seed=42
) -> pd.DataFrame:
    """
    Wrapper around the synthetic generator that resolves ProductKey
    from the live sku_to_prod_key map.

    This is needed because the generator module does not have access
    to the warehouse dimension keys — those are resolved post-load here.
    """
    from app.analytics.synthetic_generator import (
        ORDER_ROWS_PROBS, QTY_VALUES, QTY_WEIGHTS,
        FIN_STATUS_VALUES, FIN_STATUS_WEIGHTS,
        SHIPPING_VALUES, SHIPPING_WEIGHTS_NORM,
        HOUR_WEIGHTS_NORM, DOW_WEIGHTS,
        DISCOUNT_RATE, DISCOUNT_CODES, DISCOUNT_WEIGHTS,
        compute_cost_for_variant,
    )

    np.random.seed(random_seed)
    catalog_idx   = list(range(len(catalog_df)))
    total_days    = (end_date - start_date).days
    synth_order_id = 10000
    records        = []
    current_date   = start_date

    # Map CustomerKey -> shipping fee
    cust_shipping_map = {}
    for c in db.session.query(DimCustomer.CustomerKey, DimCustomer.Region).all():
        city = c.Region or 'Cairo'
        fee = 50.0 if city in ('Cairo', 'Giza') else 70.0
        cust_shipping_map[c.CustomerKey] = fee

    # Map ProductKey -> IsPrinted
    prod_key_to_is_printed = {}
    for p in db.session.query(DimProduct.ProductKey, DimProduct.Title, DimProduct.ProductType, DimProduct.ProductFamily).all():
        title = (p.Title or '').lower()
        ptype = (p.ProductType or '').lower()
        pfamily = (p.ProductFamily or '').lower()
        is_printed = 'printed' in title or 'graphic' in title or 'printed' in ptype or 'graphic' in ptype or 'printed' in pfamily or 'graphic' in pfamily
        prod_key_to_is_printed[p.ProductKey] = is_printed

    # Precompute ProductKey per catalog row
    catalog_prod_keys = []
    for _, v in catalog_df.iterrows():
        pk = sku_to_prod_key.get(v['SKU'])
        if not pk:
            pk = list(sku_to_prod_key.values())[0] if sku_to_prod_key else 1
        catalog_prod_keys.append(pk)

    orders_generated = 0

    while current_date <= end_date and orders_generated < target_orders:
        days_from_start = (current_date - start_date).days
        progress = days_from_start / max(total_days, 1)
        daily_target = 10 + 50 * (progress ** 1.5)

        dow = current_date.strftime('%A')
        dow_factor = DOW_WEIGHTS.get(dow, 1/7) / (1/7)
        n_orders_today = max(1, int(np.random.poisson(daily_target * dow_factor)))

        for _ in range(n_orders_today):
            if orders_generated >= target_orders:
                break

            synth_order_id += 1
            orders_generated += 1
            order_num = f'#SYN-{synth_order_id}'

            hour = int(np.random.choice(range(24), p=HOUR_WEIGHTS_NORM))
            date_key = int(current_date.strftime('%Y%m%d'))

            fin_status   = str(np.random.choice(FIN_STATUS_VALUES, p=FIN_STATUS_WEIGHTS))
            is_cancelled = (fin_status == 'voided')

            has_discount  = bool(np.random.random() < DISCOUNT_RATE)
            discount_code = str(np.random.choice(DISCOUNT_CODES, p=DISCOUNT_WEIGHTS)) if has_discount else None

            cust_key     = int(np.random.choice(customer_keys))

            # Map shipping based on customer's city
            shipping = cust_shipping_map.get(cust_key, 70.0)

            n_rows_vals  = list(ORDER_ROWS_PROBS.keys())
            n_rows_probs = list(ORDER_ROWS_PROBS.values())
            n_line_items = int(np.random.choice(n_rows_vals, p=n_rows_probs))

            order_subtotal = 0.0
            order_line_recs = []

            for item_i in range(n_line_items):
                vi   = int(np.random.choice(catalog_idx, p=product_weights))
                var  = catalog_df.iloc[vi]
                pk   = catalog_prod_keys[vi]

                qty        = int(np.random.choice(QTY_VALUES, p=QTY_WEIGHTS))
                price      = float(var['Price'])
                compare_at = float(var['CompareAtPrice']) if var.get('CompareAtPrice') else None
                cost, _    = compute_cost_for_variant(var.to_dict(), category_ratios)

                line_disc = 0.0
                if has_discount and discount_code == 'LEVELD10' and item_i == 0:
                    line_disc = round(price * qty * 0.10, 2)

                gross_rev  = round(qty * price, 2)
                cogs_val   = round(qty * cost, 2)
                net_profit = round(gross_rev - line_disc - cogs_val, 2)
                order_subtotal += gross_rev

                order_line_recs.append({
                    'DateKey':          date_key,
                    'CustomerKey':      cust_key,
                    'ProductKey':       pk,
                    'SupplierKey':      1 if prod_key_to_is_printed.get(pk, False) else 2,
                    'ChannelKey':       1,            # ALWAYS Online
                    'OrderNumber':      order_num,
                    'ShopifyOrderID':   None,
                    'IsSynthetic':      True,
                    'IsCancelled':      is_cancelled,
                    'Quantity':         qty,
                    'UnitPrice':        price,
                    'CompareAtPrice':   compare_at,
                    'UnitCost':         round(cost, 4),
                    'DiscountAmount':   line_disc,
                    'GrossRevenue':     gross_rev,
                    'COGS':             cogs_val,
                    'NetProfit':        net_profit,
                    'DiscountCode':     discount_code,
                    'OrderSubtotal':    None,
                    'OrderShipping':    shipping,
                    'FinancialStatus':  fin_status,
                    'FulfillmentStatus': 'fulfilled' if fin_status == 'paid' else 'unfulfilled',
                    'PaymentMethod':    'Cash on Delivery (COD)',  # ALWAYS COD
                    'RiskLevel':        'Low',                     # ALWAYS Low
                })

            for rec in order_line_recs:
                rec['OrderSubtotal'] = round(order_subtotal, 2)
                records.append(rec)

        current_date += timedelta(days=1)

    df = pd.DataFrame(records)
    print(f'  Synthetic: {len(df):,} line items across {df["OrderNumber"].nunique():,} orders')
    return df
