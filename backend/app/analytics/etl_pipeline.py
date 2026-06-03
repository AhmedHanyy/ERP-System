import os
import re
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import text

from app import db
from app.models import (
    Customer, Product, ProductVariant, Order, OrderItem, Supplier, ProcurementRequest,
    DimCustomer, DimProduct, DimDate, DimSupplier, DimChannel, FactSales, FactInventory, FactProcurement, FactReturns, ETLRun
)

# File Paths
orders_csv_path = r"d:\ahmed\Year3\GP-SmartERP\SmartERP\backend\data\shopify\orders_export_1.csv"
customers_csv_path = r"d:\ahmed\Year3\GP-SmartERP\SmartERP\backend\data\shopify\customers_export.csv"
products_csv_path = r"d:\ahmed\Year3\GP-SmartERP\SmartERP\backend\data\shopify\products_export_1.csv"
cogs_csv_path = r"d:\ahmed\Year3\GP-SmartERP\SmartERP\backend\data\shopify\cogs_export.csv"

# Configuration
DATABASE_URL = os.environ.get('DATABASE_URL', '')
IS_POSTGRES = DATABASE_URL.startswith('postgresql') or DATABASE_URL.startswith('postgres')
SCHEMA_PREFIX = 'warehouse.' if IS_POSTGRES else ''
OP_SCHEMA_PREFIX = 'operational.' if IS_POSTGRES else ''
SCHEMA_NAME = 'warehouse' if IS_POSTGRES else None

def truncate_table(conn, table_name):
    if IS_POSTGRES:
        conn.execute(text(f"TRUNCATE TABLE warehouse.{table_name} CASCADE;"))
    else:
        conn.execute(text(f"DELETE FROM {table_name};"))
    conn.commit()

# Governorate Normalization Map
GOVERNORATE_MAP = {
    'cairo': 'Cairo', 'القاهرة': 'Cairo', 'القاهره': 'Cairo', 'c': 'Cairo', 'new cairo': 'Cairo', 'rehab': 'Cairo',
    'madinaty': 'Cairo', 'maadi': 'Cairo', 'nasr city': 'Cairo', 'heliopolis': 'Cairo', 'sherouk': 'Cairo', 'rehab city': 'Cairo',
    'shorouk': 'Cairo', 'madinty': 'Cairo', 'fifth settlement': 'Cairo', 'egypt': 'Cairo',
    'alexandria': 'Alexandria', 'alex': 'Alexandria', 'الاسكندريه': 'Alexandria', 'الاسكندرية': 'Alexandria', 
    'الإسكندرية': 'Alexandria', 'alx': 'Alexandria', 'اسكندرية': 'Alexandria', 'اسكندريه': 'Alexandria',
    'giza': 'Giza', 'gz': 'Giza', 'الجيزة': 'Giza', 'الجيزه': 'Giza', 'جيزة': 'Giza', 'جيزه': 'Giza',
    'sheikh zayed': 'Giza', 'الشيخ زايد': 'Giza', '6 october': 'Giza', '6th of october': 'Giza', '٦ اكتوبر': 'Giza',
    'dokki': 'Giza', 'مهندسين': 'Giza', 'mohandseen': 'Giza', 'agouza': 'Giza', 'haram': 'Giza', 'faisal': 'Giza',
    'suez': 'Suez', 'السويس': 'Suez', 'ismailia': 'Ismailia', 'الاسماعيليه': 'Ismailia',
    'zagazig': 'Sharqia', 'الزقازيق': 'Sharqia', 'tanta': 'Gharbia', 'طنطا': 'Gharbia',
    'mansoura': 'Dakahlia', 'المنصورة': 'Dakahlia', 'banha': 'Qalyubia', 'بنها': 'Qalyubia', 'kb': 'Qalyubia',
    'hurghada': 'Red Sea', 'الغردقة': 'Red Sea', 'sharm': 'South Sinai', 'portsaid': 'Port Said', 'دمياط': 'Damietta'
}

def clean_city(city_val):
    if not isinstance(city_val, str):
        return 'Cairo' # Default fallback
    city_clean = city_val.strip().lower()
    for pattern, gov in GOVERNORATE_MAP.items():
        if pattern in city_clean:
            return gov
    return 'Cairo' # Fallback

def get_base_title(name):
    if not isinstance(name, str):
        return ""
    # Split by ' - ' and remove size or color
    parts = name.split(' - ')
    if len(parts) > 1:
        # Check if last part is size/color
        last = parts[-1].strip()
        if last in ['S', 'M', 'L', 'XL', '2XL', '3XL', 'Small', 'Medium', 'Large', 'XLarge', 'Free Size', 'One Size']:
            return ' - '.join(parts[:-1])
    return parts[0]

def run_etl_pipeline():
    start_time = datetime.utcnow()
    print("ETL Pipeline Started...")
    
    # Create an ETL Run record
    etl_run = ETLRun(start_time=start_time, status='Running')
    db.session.add(etl_run)
    db.session.commit()
    
    try:
        # ─── EXTRACT STAGE ──────────────────────────────────────────────────
        print("Extracting datasets...")
        orders_df = pd.read_csv(orders_csv_path, low_memory=False)
        customers_df = pd.read_csv(customers_csv_path, low_memory=False)
        products_df = pd.read_csv(products_csv_path, low_memory=False)
        
        # Read Excel COGS if exists
        cogs_dict = {}
        if os.path.exists(cogs_csv_path):
            try:
                cogs_df = pd.read_csv(cogs_csv_path)
                cogs_df['SKU'] = cogs_df['SKU'].astype(str).str.strip().str.replace("'", "")
                cogs_dict = dict(zip(cogs_df['SKU'], cogs_df['Cost']))
                print(f"Loaded {len(cogs_dict)} cost rules from Excel COGS export.")
            except Exception as e:
                print(f"Warning loading Excel COGS: {e}")

        # ─── CLEAN & PREPARE DIMDATE ───────────────────────────────────────
        print("Building DimDate...")
        # Get date range from orders
        orders_df['Created at_dt'] = pd.to_datetime(orders_df['Created at'], errors='coerce')
        min_date = datetime(2023, 1, 1) # Start scale data from 2023
        max_date = datetime.now() + timedelta(days=30)
        
        date_range = pd.date_range(start=min_date, end=max_date, freq='D')
        date_records = []
        for dt in date_range:
            date_key = int(dt.strftime('%Y%m%d'))
            date_records.append({
                'DateKey': date_key,
                'FullDate': dt.date(),
                'Year': dt.year,
                'Quarter': (dt.month - 1) // 3 + 1,
                'Month': dt.month,
                'MonthName': dt.strftime('%B'),
                'Day': dt.day,
                'DayOfWeek': dt.strftime('%A'),
                'IsWeekend': dt.weekday() in [4, 5] # Friday & Saturday in Egypt
            })
        dim_date_df = pd.DataFrame(date_records)
        
        # ─── CLEAN & PREPARE DIMCUSTOMER ──────────────────────────────────
        print("Transforming DimCustomer...")
        customers_df['Customer ID_clean'] = customers_df['Customer ID'].astype(str).str.strip().str.replace("'", "")
        customers_df['Default Address Phone_clean'] = customers_df['Default Address Phone'].astype(str).str.strip().str.replace("'", "")
        customers_df['Phone_clean'] = customers_df['Phone'].astype(str).str.strip().str.replace("'", "")
        
        # Resolve Phone
        customers_df['Resolved_Phone'] = customers_df['Phone_clean'].where(
            customers_df['Phone_clean'].notna() & (customers_df['Phone_clean'] != 'nan'),
            customers_df['Default Address Phone_clean']
        )
        customers_df['Resolved_Phone'] = customers_df['Resolved_Phone'].replace('nan', '')
        
        # Normalize City / Governorate
        customers_df['Normalized_City'] = customers_df['Default Address City'].apply(clean_city)
        
        dim_cust_records = []
        for idx, row in customers_df.iterrows():
            dim_cust_records.append({
                'ShopifyCustomerID': row['Customer ID_clean'],
                'FirstName': row['First Name'] if pd.notna(row['First Name']) else '',
                'LastName': row['Last Name'] if pd.notna(row['Last Name']) else '',
                'Email': row['Email'] if pd.notna(row['Email']) else '',
                'Phone': row['Resolved_Phone'],
                'City': row['Default Address City'] if pd.notna(row['Default Address City']) else 'Cairo',
                'Region': row['Normalized_City'],
                'Country': row['Default Address Country Code'] if pd.notna(row['Default Address Country Code']) else 'EG',
                'AcceptsMarketing': str(row['Accepts Email Marketing']).lower() == 'yes',
                'RFM_Segment': 'New'
            })
        dim_cust_df = pd.DataFrame(dim_cust_records)
        dim_cust_df.drop_duplicates(subset=['ShopifyCustomerID'], inplace=True)
        
        # ─── CLEAN & PREPARE DIMSUPPLIER ───────────────────────────────────
        print("Building DimSupplier...")
        # Create standard suppliers based on product vendors
        unique_vendors = products_df['Vendor'].dropna().unique()
        if len(unique_vendors) == 0:
            unique_vendors = ['Leveld', 'Local Wear', 'Egyptian Apparel Co.']
            
        supplier_records = []
        for idx, vendor in enumerate(unique_vendors):
            supplier_records.append({
                'SupplierKey': idx + 1,
                'SupplierName': f"{vendor} Supplier Co.",
                'ContactPerson': f"Manager of {vendor}",
                'WhatsAppNumber': f"+2010{1000000 + idx}",
                'Rating': round(np.random.uniform(3.8, 4.9), 2),
                'Status': 'Active'
            })
        dim_supplier_df = pd.DataFrame(supplier_records)
        vendor_to_supplier_key = {row['SupplierName'].split(' ')[0]: row['SupplierKey'] for idx, row in dim_supplier_df.iterrows()}

        # ─── CLEAN & PREPARE DIMPRODUCT (SCD TYPE 2) ──────────────────────
        print("Transforming DimProduct (incorporating SCD Type 2 logic)...")
        # Build category average cost map to solve missing cost
        products_df['Variant Price_num'] = pd.to_numeric(products_df['Variant Price'], errors='coerce').fillna(0.0)
        products_df['Cost per item_num'] = pd.to_numeric(products_df['Cost per item'], errors='coerce').fillna(0.0)
        
        cat_cost_ratios = {}
        for cat, group in products_df.groupby('Product Category'):
            has_cost = group[(group['Cost per item_num'] > 0) & (group['Variant Price_num'] > 0)]
            if len(has_cost) > 0:
                ratio = (has_cost['Cost per item_num'] / has_cost['Variant Price_num']).mean()
                cat_cost_ratios[cat] = ratio
        global_avg_ratio = 0.55
        
        # Extract existing active DimProduct records to verify changes (SCD 2)
        existing_products = {}
        try:
            existing_rows = db.session.query(DimProduct).filter_by(IsCurrent=True).all()
            existing_products = {p.SKU: p for p in existing_rows}
        except Exception as e:
            print(f"No existing DimProduct table found or readable: {e}")
            
        new_product_inserts = []
        scd2_updates = []
        
        # Clean product variant details
        products_df['Variant SKU_clean'] = products_df['Variant SKU'].astype(str).str.strip().str.replace("'", "")
        # Filter rows where SKU is present and it is a variant definition (not just image rows)
        variant_rows = products_df[products_df['Variant SKU_clean'].notna() & (products_df['Variant SKU_clean'] != 'nan') & (products_df['Variant SKU_clean'] != '')]
        
        # Keep track of handled SKUs to avoid duplicates in source
        handled_skus = set()
        
        # Helper to extract option value
        def extract_option(row, opt_name):
            for i in range(1, 4):
                if row.get(f'Option{i} Name') == opt_name:
                    return row.get(f'Option{i} Value')
            return ''

        # Map to track current SKU -> ProductKey after database operations
        sku_to_prod_key = {}
        next_prod_key = 1
        
        if existing_products:
            next_prod_key = max(p.ProductKey for p in existing_products.values()) + 1
            
        for idx, row in variant_rows.iterrows():
            sku = row['Variant SKU_clean']
            if sku in handled_skus:
                continue
            handled_skus.add(sku)
            
            title = row['Title'] if pd.notna(row['Title']) else ''
            category = row['Product Category'] if pd.notna(row['Product Category']) else 'General Apparel'
            price = float(row['Variant Price_num'])
            vendor = row['Vendor'] if pd.notna(row['Vendor']) else 'Leveld'
            status = row['Status'] if pd.notna(row['Status']) else 'active'
            
            # Resolve Cost per item hierarchy
            cost = 0.0
            if sku in cogs_dict:
                cost = float(cogs_dict[sku])
            elif float(row['Cost per item_num']) > 0:
                cost = float(row['Cost per item_num'])
            elif category in cat_cost_ratios:
                cost = price * cat_cost_ratios[category]
            else:
                cost = price * global_avg_ratio
            
            size = extract_option(row, 'size') or extract_option(row, 'Size')
            color = extract_option(row, 'color') or extract_option(row, 'Color')
            
            # Compare with existing active product variant
            existing_p = existing_products.get(sku)
            
            if existing_p:
                # Check for changes in Price, Cost, Title, or Category (attributes trigger SCD 2)
                attributes_changed = (
                    abs(existing_p.Price - price) > 0.01 or
                    abs(existing_p.Cost - cost) > 0.01 or
                    existing_p.Title != title or
                    existing_p.Category != category or
                    existing_p.Status != status
                )
                
                if attributes_changed:
                    # Close old record
                    scd2_updates.append({
                        'ProductKey': existing_p.ProductKey,
                        'RowEndDate': start_time,
                        'IsCurrent': False
                    })
                    
                    # Insert new active record
                    new_product_inserts.append({
                        'ProductKey': next_prod_key,
                        'SKU': sku,
                        'Handle': row['Handle'],
                        'Title': title,
                        'Category': category,
                        'Size': size,
                        'Color': color,
                        'Price': price,
                        'Cost': cost,
                        'Vendor': vendor,
                        'Status': status,
                        'IsActive': True,
                        'RowStartDate': start_time,
                        'RowEndDate': None,
                        'IsCurrent': True
                    })
                    sku_to_prod_key[sku] = next_prod_key
                    next_prod_key += 1
                else:
                    # No changes, keep existing key
                    sku_to_prod_key[sku] = existing_p.ProductKey
            else:
                # Completely new product
                new_product_inserts.append({
                    'ProductKey': next_prod_key,
                    'SKU': sku,
                    'Handle': row['Handle'] if pd.notna(row['Handle']) else '',
                    'Title': title,
                    'Category': category,
                    'Size': size,
                    'Color': color,
                    'Price': price,
                    'Cost': cost,
                    'Vendor': vendor,
                    'Status': status,
                    'IsActive': True,
                    'RowStartDate': start_time,
                    'RowEndDate': None,
                    'IsCurrent': True
                })
                sku_to_prod_key[sku] = next_prod_key
                next_prod_key += 1
        
        # Load DimProduct changes to DB
        if scd2_updates:
            print(f"  - Expiring {len(scd2_updates)} obsolete SCD Type 2 product rows...")
            for update in scd2_updates:
                db.session.query(DimProduct).filter_by(ProductKey=update['ProductKey']).update({
                    'RowEndDate': update['RowEndDate'],
                    'IsCurrent': update['IsCurrent']
                })
            db.session.commit()
            
        if new_product_inserts:
            print(f"  - Inserting {len(new_product_inserts)} new SCD Type 2 product rows...")
            # We can use pd.DataFrame to write them
            dim_prod_new_df = pd.DataFrame(new_product_inserts)
            dim_prod_new_df.to_sql(
                name='dim_product',
                con=db.engine,
                schema=SCHEMA_NAME,
                if_exists='append',
                index=False
            )
            
        # Re-fetch all current products to establish mapping
        all_current_products = db.session.query(DimProduct).filter_by(IsCurrent=True).all()
        sku_to_prod_key = {p.SKU: p.ProductKey for p in all_current_products}
        sku_to_cost = {p.SKU: p.Cost for p in all_current_products}
        sku_to_price = {p.SKU: p.Price for p in all_current_products}
        sku_to_supplier = {p.SKU: vendor_to_supplier_key.get(p.Vendor, 1) for p in all_current_products}

        # ─── BUILD DIMCHANNEL ───────────────────────────────────────────────
        channel_records = [
            {'ChannelKey': 1, 'ChannelName': 'Online Storefront'},
            {'ChannelKey': 2, 'ChannelName': 'Retail POS'},
            {'ChannelKey': 3, 'ChannelName': 'Mobile Application'},
            {'ChannelKey': 4, 'ChannelName': 'B2B Portal'}
        ]
        dim_channel_df = pd.DataFrame(channel_records)
        
        # ─── EXTRACT & CLEAN REAL SHOPIFY SALES (Source of Truth) ────────────
        print("Extracting and Cleaning real Shopify orders...")
        # Forward fill order metadata
        order_meta_cols = [
            'Financial Status', 'Fulfillment Status', 'Accepts Marketing', 'Currency',
            'Subtotal', 'Shipping', 'Taxes', 'Total', 'Discount Code', 'Discount Amount',
            'Shipping Method', 'Created at', 'Billing Name', 'Billing Street', 'Billing City',
            'Billing Zip', 'Billing Province', 'Billing Country', 'Billing Phone',
            'Shipping Name', 'Shipping Street', 'Shipping Address1', 'Shipping Address2',
            'Shipping Company', 'Shipping City', 'Shipping Zip', 'Shipping Province',
            'Shipping Country', 'Shipping Phone', 'Payment Method', 'Risk Level'
        ]
        
        # Sort by Name and then apply forward fill grouped by Name
        orders_df.sort_values(by=['Name'], inplace=True)
        orders_df[order_meta_cols] = orders_df.groupby('Name')[order_meta_cols].ffill()
        
        # Clean quotes
        orders_df['Lineitem sku_clean'] = orders_df['Lineitem sku'].astype(str).str.strip().str.replace("'", "")
        orders_df['Email_clean'] = orders_df['Email'].astype(str).str.strip().str.replace("'", "").replace('nan', '')
        orders_df['Phone_clean'] = orders_df['Phone'].astype(str).str.strip().str.replace("'", "").replace('nan', '')
        
        # We need a dictionary to map Shopify Customer Email to CustomerKey
        # First load DimCustomer so we have keys
        # We write DimCustomer to DB first to generate keys
        print("Loading DimCustomer to Database...")
        # We truncate first for clean load
        with db.engine.connect() as pg_conn:
            truncate_table(pg_conn, 'dim_customer')
            
        dim_cust_df.to_sql(
            name='dim_customer',
            con=db.engine,
            schema=SCHEMA_NAME,
            if_exists='append',
            index=False
        )
        
        # Map Customer IDs/Emails to keys
        db_customers = db.session.query(DimCustomer).all()
        cust_email_to_key = {c.Email.lower(): c.CustomerKey for c in db_customers if c.Email}
        cust_id_to_key = {c.ShopifyCustomerID: c.CustomerKey for c in db_customers if c.ShopifyCustomerID}
        default_customer_key = db_customers[0].CustomerKey if db_customers else 1
        
        # Create fact sales records from Shopify orders
        real_sales_records = []
        
        # Build lookup lists for SKU fallback
        product_catalog_titles = {p.Title: p.SKU for p in all_current_products}
        
        print("Mapping line items to products (SKU resolution hierarchy)...")
        for idx, row in orders_df.iterrows():
            sku = row['Lineitem sku_clean']
            item_name = row['Lineitem name']
            
            prod_key = None
            resolved_sku = None
            
            # Step 1: Match on SKU
            if sku in sku_to_prod_key:
                prod_key = sku_to_prod_key[sku]
                resolved_sku = sku
            else:
                # Step 2: Match by Base Title
                base_title = get_base_title(item_name)
                if base_title in product_catalog_titles:
                    resolved_sku = product_catalog_titles[base_title]
                    prod_key = sku_to_prod_key[resolved_sku]
                else:
                    # Step 3: Match on exact Item Name as Title
                    if item_name in product_catalog_titles:
                        resolved_sku = product_catalog_titles[item_name]
                        prod_key = sku_to_prod_key[resolved_sku]
                    
            # Step 4: Unknown product fallback
            if not prod_key:
                # Create a generic placeholder key or use the first product as stub
                resolved_sku = 'UNKNOWN_SKU'
                prod_key = list(sku_to_prod_key.values())[0] if sku_to_prod_key else 1
                
            # Get customer key
            email = row['Email_clean'].lower()
            cust_key = cust_email_to_key.get(email, default_customer_key)
            
            # DateKey
            dt = row['Created at_dt']
            if pd.isna(dt):
                dt = datetime.now()
            date_key = int(dt.strftime('%Y%m%d'))
            
            qty = int(row['Lineitem quantity'])
            price = float(row['Lineitem price'])
            cost = sku_to_cost.get(resolved_sku, price * global_avg_ratio)
            discount = float(row['Lineitem discount']) if pd.notna(row['Lineitem discount']) else 0.0
            
            revenue = (qty * price) - discount
            cogs = qty * cost
            profit = revenue - cogs
            
            supplier_key = sku_to_supplier.get(resolved_sku, 1)
            
            real_sales_records.append({
                'DateKey': date_key,
                'CustomerKey': cust_key,
                'ProductKey': prod_key,
                'SupplierKey': supplier_key,
                'ChannelKey': 1, # Online Storefront
                'OrderNumber': row['Name'],
                'Quantity': qty,
                'UnitPrice': price,
                'UnitCost': cost,
                'DiscountAmount': discount,
                'GrossRevenue': qty * price,
                'COGS': cogs,
                'NetProfit': profit,
                'FinancialStatus': row['Financial Status'] if pd.notna(row['Financial Status']) else 'paid',
                'FulfillmentStatus': row['Fulfillment Status'] if pd.notna(row['Fulfillment Status']) else 'fulfilled',
                'PaymentMethod': row['Payment Method'] if pd.notna(row['Payment Method']) else 'Cash on Delivery (COD)',
                'RiskLevel': row['Risk Level'] if pd.notna(row['Risk Level']) else 'Low'
            })
            
        real_sales_df = pd.DataFrame(real_sales_records)
        print(f"Successfully processed {len(real_sales_df)} real Shopify sale lines.")
        
        # ─── DATASET SCALING & HISTORICAL EXPANSION (25,000+ orders) ──────────
        print("\n--- SYNTHETIC DATA GENERATOR: Historical Expansion ---")
        # Target scale: ~35,000 orders total
        target_orders = 35000
        current_orders = len(real_sales_df)
        synthetic_needed = target_orders - current_orders
        
        print(f"Real Shopify sales lines: {current_orders}")
        print(f"Generating {synthetic_needed} synthetic historical sales lines to scale dataset to {target_orders}...")
        
        # Profile real data to match distributions
        # Seasonality (month weights)
        month_counts = real_sales_df['DateKey'].apply(lambda k: int(str(k)[4:6])).value_counts(normalize=True)
        month_weights = [month_counts.get(m, 1/12) for m in range(1, 13)]
        month_weights /= sum(month_weights) # normalize
        
        # Product popularity distribution
        prod_popularity = real_sales_df['ProductKey'].value_counts(normalize=True)
        prod_keys = list(sku_to_prod_key.values())
        prod_weights = [prod_popularity.get(pk, 1/len(prod_keys)) for pk in prod_keys]
        prod_weights /= sum(prod_weights) # normalize
        
        # Customer ordering probability
        customer_keys = [c.CustomerKey for c in db_customers]
        cust_weights = np.random.zipf(a=1.5, size=len(customer_keys)) # Long-tail distribution
        cust_weights = cust_weights / sum(cust_weights)
        
        # Seasonality multiplier function (adds winter spike, summer dip)
        def get_seasonality_factor(dt):
            month = dt.month
            if month in [11, 12, 1]: # Winter sales
                return 1.4
            if month in [6, 7, 8]: # Summer dip
                return 0.7
            return 1.0
            
        # Generate synthetic orders
        synth_sales_records = []
        
        # We backfill between 2023-01-01 and 2026-02-01
        start_history = datetime(2023, 1, 1)
        end_history = datetime(2026, 2, 1)
        total_days = (end_history - start_history).days
        
        print("  - Simulating historical sales transactions...")
        np.random.seed(42)
        
        # Grouped order generation to keep OrderNumbers clean
        synth_order_id = 10000
        lines_generated = 0
        
        while lines_generated < synthetic_needed:
            # Generate one order with 1-3 items
            synth_order_id += 1
            order_num = f"#SYN-{synth_order_id}"
            
            # Select order date based on random day in range + seasonality filter
            random_day = np.random.randint(0, total_days)
            order_date = start_history + timedelta(days=random_day)
            
            # Re-roll if it fails a seasonality weight check (simulating realistic seasonality)
            month = order_date.month
            season_factor = get_seasonality_factor(order_date)
            if np.random.uniform(0, 1.4) > season_factor:
                # Skip or re-roll date
                order_date = order_date + timedelta(days=np.random.randint(-15, 15))
            
            date_key = int(order_date.strftime('%Y%m%d'))
            
            # Select customer
            cust_key = np.random.choice(customer_keys, p=cust_weights)
            
            # Select payment and risk status
            pay_method = np.random.choice(['Cash on Delivery (COD)', 'Credit Card', 'Mobile Wallet'], p=[0.7, 0.25, 0.05])
            risk = np.random.choice(['Low', 'Medium', 'High'], p=[0.92, 0.06, 0.02])
            fin_status = np.random.choice(['paid', 'pending', 'voided'], p=[0.9, 0.08, 0.02])
            
            # Items in basket
            num_items = np.random.choice([1, 2, 3, 4], p=[0.6, 0.25, 0.1, 0.05])
            
            for _ in range(num_items):
                # Pick product
                prod_key = np.random.choice(prod_keys, p=prod_weights)
                
                # Retrieve price/cost of that product
                # Get the SKU for the product key
                p_sku = next(k for k, v in sku_to_prod_key.items() if v == prod_key)
                price = sku_to_price.get(p_sku, 500.0)
                cost = sku_to_cost.get(p_sku, price * global_avg_ratio)
                
                qty = np.random.choice([1, 2, 5], p=[0.85, 0.12, 0.03])
                discount = 0.0
                if np.random.uniform(0, 1) < 0.15: # 15% orders discounted
                    discount = round(price * qty * np.random.choice([0.1, 0.2]), 2)
                    
                revenue = (qty * price) - discount
                cogs = qty * cost
                profit = revenue - cogs
                
                supplier_key = sku_to_supplier.get(p_sku, 1)
                channel_key = np.random.choice([1, 2, 3], p=[0.8, 0.15, 0.05]) # Web, Retail, Mobile App
                
                synth_sales_records.append({
                    'DateKey': date_key,
                    'CustomerKey': cust_key,
                    'ProductKey': prod_key,
                    'SupplierKey': supplier_key,
                    'ChannelKey': int(channel_key),
                    'OrderNumber': order_num,
                    'Quantity': qty,
                    'UnitPrice': price,
                    'UnitCost': cost,
                    'DiscountAmount': discount,
                    'GrossRevenue': qty * price,
                    'COGS': cogs,
                    'NetProfit': profit,
                    'FinancialStatus': fin_status,
                    'FulfillmentStatus': 'fulfilled',
                    'PaymentMethod': pay_method,
                    'RiskLevel': risk
                })
                lines_generated += 1
                
        synth_sales_df = pd.DataFrame(synth_sales_records)
        print(f"Generated {len(synth_sales_df)} synthetic sale lines.")
        
        # Combine FactSales datasets
        combined_sales_df = pd.concat([real_sales_df, synth_sales_df], ignore_index=True)
        print(f"Total Combined DW Sales Records: {len(combined_sales_df)}")

        # ─── SYNTHETIC PROCUREMENT LOGS GENERATOR ──────────────────────────
        print("\n--- SYNTHETIC DATA GENERATOR: Procurement Expansion ---")
        # Generate Suppliers, PO requests, lead times
        procurement_records = []
        po_id = 5000
        
        # Group sales by Date and Product to compute daily velocity
        sales_by_day = combined_sales_df.groupby(['DateKey', 'ProductKey'])['Quantity'].sum().reset_index()
        avg_velocity = sales_by_day.groupby('ProductKey')['Quantity'].mean().to_dict()
        
        print("  - Simulating historical supply chain and procurement cycles...")
        # Generate POs over the timeline (2023-2026)
        # For each supplier and product, generate replenishment POs when stock falls
        for prod_key in prod_keys:
            p_sku = next(k for k, v in sku_to_prod_key.items() if v == prod_key)
            cost = sku_to_cost.get(p_sku, 100.0)
            supplier_key = sku_to_supplier.get(p_sku, 1)
            
            daily_vel = avg_velocity.get(prod_key, 0.2)
            # Reorder point: 7 days lead time * velocity * safety factor
            reorder_pt = int(math.ceil(7 * daily_vel * 1.5))
            reorder_qty = max(50, int(math.ceil(30 * daily_vel))) # order 30 days of supply
            
            # Generate POs chronologically
            current_sim_date = start_history
            while current_sim_date < end_history:
                # Generate a PO every 2-3 months on average
                po_interval = np.random.randint(45, 90)
                current_sim_date += timedelta(days=po_interval)
                if current_sim_date >= end_history:
                    break
                
                po_id += 1
                req_date_key = int(current_sim_date.strftime('%Y%m%d'))
                
                # Lead time calculation: baseline 6 days + variance
                lead_time = int(np.random.randint(5, 12))
                received_date = current_sim_date + timedelta(days=lead_time)
                rec_date_key = int(received_date.strftime('%Y%m%d'))
                
                # Random status: 90% received, 5% sent/confirmed, 5% cancelled
                status = np.random.choice(['Received', 'Confirmed', 'Cancelled'], p=[0.9, 0.05, 0.05])
                
                rec_key = rec_date_key if status == 'Received' else None
                actual_lead = lead_time if status == 'Received' else None
                
                procurement_records.append({
                    'DateKey': req_date_key,
                    'SupplierKey': supplier_key,
                    'ProductKey': prod_key,
                    'QuantityRequested': reorder_qty,
                    'UnitCost': cost,
                    'TotalCost': reorder_qty * cost,
                    'LeadTimeDays': actual_lead,
                    'ReceivedDateKey': rec_key,
                    'Status': status
                })
                
        fact_procurement_df = pd.DataFrame(procurement_records)
        print(f"Generated {len(fact_procurement_df)} replenishment purchase orders.")

        # ─── FACT INVENTORY SNAPSHOT GENERATOR ────────────────────────────
        print("\n--- SYNTHETIC DATA GENERATOR: Inventory Snapshots ---")
        # Generate current inventory levels in FactInventory
        inventory_records = []
        current_date_key = int(datetime.utcnow().strftime('%Y%m%d'))
        
        for prod_key in prod_keys:
            p_sku = next(k for k, v in sku_to_prod_key.items() if v == prod_key)
            daily_vel = avg_velocity.get(prod_key, 0.2)
            reorder_pt = int(math.ceil(7 * daily_vel * 1.5))
            reorder_qty = max(50, int(math.ceil(30 * daily_vel)))
            
            # Draw a realistic current stock (e.g. standard stockout or low-stock simulation)
            qoh = int(np.random.randint(int(reorder_pt * 0.5), int(reorder_qty * 1.5)))
            
            days_supply = qoh / daily_vel if daily_vel > 0 else 999.0
            status = 'Healthy'
            if qoh == 0:
                status = 'Stockout'
            elif qoh <= reorder_pt:
                status = 'Low Stock'
                
            inventory_records.append({
                'DateKey': current_date_key,
                'ProductKey': prod_key,
                'QuantityOnHand': qoh,
                'ReorderPoint': reorder_pt,
                'ReorderQuantity': reorder_qty,
                'DaysOfSupply': round(days_supply, 1),
                'StockStatus': status
            })
        fact_inventory_df = pd.DataFrame(inventory_records)
        print(f"Generated current inventory snapshots for {len(fact_inventory_df)} product variants.")

        # ─── LOAD WAREHOUSE TABLES TO DATABASE ─────────────────────────────
        print("\nLoading Warehouse Dimensions & Facts into database...")
        
        # Tables to truncate and reload
        tables_to_load = [
            ('dim_date', dim_date_df),
            ('dim_supplier', dim_supplier_df),
            ('dim_channel', dim_channel_df),
            ('fact_sales', combined_sales_df),
            ('fact_procurement', fact_procurement_df),
            ('fact_inventory', fact_inventory_df)
        ]
        
        for name, df in tables_to_load:
            try:
                # Truncate
                with db.engine.connect() as pg_conn:
                    truncate_table(pg_conn, name)
                
                # Bulk insert via Pandas
                df.to_sql(
                    name=name,
                    con=db.engine,
                    schema=SCHEMA_NAME,
                    if_exists='append',
                    index=False
                )
                print(f"  - Loaded {len(df)} rows into {SCHEMA_PREFIX}{name}.")
            except Exception as e:
                print(f"  - Error loading {name}: {e}")
                
        # Also ensure fact_returns exists but has 0 rows (as per constraint)
        try:
            with db.engine.connect() as pg_conn:
                truncate_table(pg_conn, 'fact_returns')
            print("  - FactReturns table truncated (kept empty per requirements).")
        except Exception as e:
            print(f"  - Warning resetting FactReturns: {e}")

        # Update ETLRun to Completed
        etl_run.end_time = datetime.utcnow()
        etl_run.status = 'Completed'
        etl_run.rows_extracted = int(len(orders_df) + len(customers_df) + len(products_df))
        etl_run.rows_loaded = int(len(combined_sales_df) + len(fact_procurement_df) + len(fact_inventory_df))
        db.session.commit()
        print("ETL Pipeline Successfully Completed!")
        return True
        
    except Exception as e:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"ETL Pipeline Failed: {e}")
        
        etl_run.end_time = datetime.utcnow()
        etl_run.status = 'Failed'
        etl_run.errors = err_msg
        db.session.commit()
        return False

import math
