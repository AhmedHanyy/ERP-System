"""
Phase A — Operational Data Loader
===================================
Replaces demo/seed data in the ERP operational tables with REAL Shopify data.

DATA FLOW:
  Shopify CSVs → Extract → Transform → Load into Operational ORM tables

TABLES POPULATED:
  - categories          (derived from product families)
  - products            (one row per unique product handle/title)
  - product_variants    (one row per variant SKU)
  - customers           (real Shopify customers)
  - orders              (real Shopify orders)
  - order_items         (real Shopify line items → linked to operational products)
  - inventory           (snapshot from Shopify inventory qty)

TABLES INTENTIONALLY NOT TOUCHED:
  - suppliers           (real suppliers pending; keep demo stubs)
  - procurement_requests(auto-generated later)
  - users               (managed by migrate_v2.py)
  - warehouse tables    (populated by Phase B ETL pipeline)

STRATEGY:
  - Uses build_product_catalog() from synthetic_generator for normalisation
  - Products are keyed by Handle (one product per handle, not per variant)
  - Product variants become ProductVariant rows linked to parent product
  - Orders use real Shopify Name (#1001, #1002...) as order_number
  - Customers linked via email match
  - Missing customer emails fallback to an "Unknown" customer
"""

import os
import sys
import re
import math
import pandas as pd
import numpy as np
from datetime import datetime

# Make sure app is importable
sys.path.insert(0, r'd:\ahmed\Year3\GP-SmartERP\SmartERP\backend')

from app import create_app, db
from app.models import (
    Category, Product, ProductVariant,
    Customer, Order, OrderItem,
    Inventory, InventoryLog,
)
from app.analytics.synthetic_generator import (
    build_product_catalog,
    build_category_cost_ratios,
    compute_cost_for_variant,
)
from app.analytics.etl_pipeline import clean_city

# ─── File Paths ────────────────────────────────────────────────────────────────
BASE_DIR      = r'd:\ahmed\Year3\GP-SmartERP\SmartERP\backend\data\shopify'
ORDERS_CSV    = os.path.join(BASE_DIR, 'orders_export_1.csv')
CUSTOMERS_CSV = os.path.join(BASE_DIR, 'customers_export.csv')
PRODUCTS_CSV  = os.path.join(BASE_DIR, 'products_export_1.csv')

# ─── Helpers ──────────────────────────────────────────────────────────────────
def safe_str(val, default='') -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    s = str(val).strip()
    return s if s and s.lower() != 'nan' else default


def safe_float(val, default=0.0) -> float:
    """Convert to float; return default if value is None, NaN, or non-numeric."""
    try:
        result = float(val)
        # pandas NaN converts without raising but is still NaN
        if result != result:  # fastest NaN check
            return default
        return result
    except (TypeError, ValueError):
        return default


def safe_int(val, default=0) -> int:
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default


# ─── Map catalog category names to ERP-friendly names ─────────────────────────
CATEGORY_ICONS = {
    'T-Shirts':     'fa-shirt',
    'Hoodies':      'fa-hoodie',
    'Sweatshirts':  'fa-sweatshirt',
    'Bottoms':      'fa-pants',
    "Women's Tops": 'fa-person-dress',
    'Linen':        'fa-leaf',
    'Other':        'fa-tag',
}

# Map Shopify financial/fulfillment status → ERP order status
def map_order_status(fin_status: str, fulfill_status: str, cancelled_at) -> str:
    """
    Shopify → ERP status mapping:
      - Cancelled at is set          → Cancelled
      - voided                       → Cancelled
      - paid + fulfilled             → Delivered
      - paid + unfulfilled/partial   → Shipped (being prepared)
      - pending                      → Pending
    """
    if pd.notna(cancelled_at) and str(cancelled_at).strip() not in ('', 'nan'):
        return 'Cancelled'
    fin  = str(fin_status).lower().strip() if pd.notna(fin_status) else ''
    ful  = str(fulfill_status).lower().strip() if pd.notna(fulfill_status) else ''
    if fin == 'voided':
        return 'Cancelled'
    if fin == 'paid' and 'fulfilled' in ful and 'unfulfilled' not in ful:
        return 'Delivered'
    if fin == 'paid':
        return 'Shipped'
    if fin == 'pending':
        return 'Pending'
    return 'Pending'


# ─── PHASE A MAIN ─────────────────────────────────────────────────────────────
def run_phase_a():
    app = create_app()
    with app.app_context():
        start = datetime.utcnow()
        print('=' * 65)
        print('PHASE A — Operational Data Loader')
        print(f'Started: {start.isoformat()}')
        print('=' * 65)

        # ── EXTRACT ─────────────────────────────────────────────────────────
        print('\n[1/7] Extracting Shopify CSVs...')
        orders_df    = pd.read_csv(ORDERS_CSV,    low_memory=False)
        customers_df = pd.read_csv(CUSTOMERS_CSV, low_memory=False)
        products_df  = pd.read_csv(PRODUCTS_CSV,  low_memory=False)
        print(f'  orders_export rows:    {len(orders_df):,}')
        print(f'  customers_export rows: {len(customers_df):,}')
        print(f'  products_export rows:  {len(products_df):,}')

        # Forward-fill order metadata across multi-row orders
        ORDER_META_COLS = [
            'Financial Status', 'Fulfillment Status', 'Currency', 'Subtotal',
            'Shipping', 'Taxes', 'Total', 'Discount Code', 'Discount Amount',
            'Shipping Method', 'Created at', 'Billing Name', 'Billing Street',
            'Billing City', 'Billing Zip', 'Billing Province', 'Billing Country',
            'Billing Phone', 'Shipping Name', 'Shipping City', 'Shipping Country',
            'Shipping Phone', 'Payment Method', 'Risk Level', 'Notes',
            'Cancelled at', 'Refunded Amount', 'Id', 'Tags', 'Source',
        ]
        orders_df.sort_values('Name', inplace=True)
        orders_df[ORDER_META_COLS] = orders_df.groupby('Name')[ORDER_META_COLS].ffill()
        orders_df['Created_dt'] = pd.to_datetime(orders_df['Created at'], utc=True, errors='coerce')

        # ── BUILD CATALOG ────────────────────────────────────────────────────
        print('\n[2/7] Building product catalog from Shopify CSV...')
        catalog_df = build_product_catalog(products_df)
        print(f'  Catalog variants:       {len(catalog_df):,}')
        print(f'  Unique handles:         {catalog_df["Handle"].nunique():,}')
        print(f'  Unique categories:      {catalog_df["Category"].nunique():,}')

        category_ratios = build_category_cost_ratios(catalog_df)
        global_ratio    = 0.45

        # ── CLEAR OPERATIONAL DATA ───────────────────────────────────────────
        print('\n[3/7] Clearing existing operational data...')
        # Delete in dependency order (children first)
        InventoryLog.query.delete()
        Inventory.query.delete()
        OrderItem.query.delete()
        Order.query.delete()
        Customer.query.delete()
        ProductVariant.query.delete()
        Product.query.delete()
        Category.query.delete()
        db.session.commit()
        print('  All operational tables cleared.')

        # ── LOAD CATEGORIES ──────────────────────────────────────────────────
        print('\n[4/7] Loading categories...')
        category_names = sorted(catalog_df['Category'].dropna().unique())
        cat_name_to_id = {}
        for cname in category_names:
            cat = Category(
                name=cname,
                icon=CATEGORY_ICONS.get(cname, 'fa-tag'),
            )
            db.session.add(cat)
            db.session.flush()  # get ID before commit
            cat_name_to_id[cname] = cat.id
        db.session.commit()
        print(f'  Categories loaded: {len(cat_name_to_id)}')
        for n, i in cat_name_to_id.items():
            print(f'    [{i}] {n}')

        # ── LOAD PRODUCTS + VARIANTS ─────────────────────────────────────────
        print('\n[5/7] Loading products and variants...')

        # Group catalog by Handle → one Product per Handle
        # All variants of that handle → ProductVariant rows
        handle_to_product_id = {}  # handle -> operational product id
        sku_to_product_id    = {}  # sku    -> operational product id (for order linking)
        products_loaded = 0
        variants_loaded = 0

        # Group by handle
        handles = catalog_df['Handle'].unique()
        for handle in handles:
            group = catalog_df[catalog_df['Handle'] == handle].copy()
            first_row = group.iloc[0]

            # Pick the "base" product price — median price of all variants
            base_price = float(group['Price'].median())

            cost_val, _ = compute_cost_for_variant(first_row.to_dict(), category_ratios, global_ratio)
            base_cost   = round(cost_val, 2)

            category_name = safe_str(first_row.get('Category'), 'Other')
            cat_id = cat_name_to_id.get(category_name)

            # Build description from product metadata
            product_type = safe_str(first_row.get('ProductType'), '')
            family       = safe_str(first_row.get('ProductFamily'), '')
            fabric       = safe_str(first_row.get('Fabric'), '')
            gender       = safe_str(first_row.get('TargetGender'), '')
            desc_parts = []
            if product_type:
                desc_parts.append(product_type)
            if fabric:
                desc_parts.append(f'Fabric: {fabric}')
            if gender:
                desc_parts.append(f'Gender: {gender}')
            description = ' | '.join(desc_parts) if desc_parts else None

            # Lifecycle stage based on inventory
            total_qty = group['InventoryQty'].sum()
            if total_qty == 0:
                lifecycle = 'Decline'
            elif total_qty > 100:
                lifecycle = 'Growth'
            elif total_qty > 20:
                lifecycle = 'Maturity'
            else:
                lifecycle = 'Decline'

            # Determine is_active from status
            is_active = str(first_row.get('Status', 'active')).lower() == 'active'

            # Use the handle-based auto-SKU for parent (use SKU of first variant as product SKU)
            # For the parent product, use the "base" SKU which is the first variant's SKU
            parent_sku = safe_str(first_row.get('SKU'))

            product = Product(
                name            = safe_str(first_row.get('Title'), handle),
                sku             = parent_sku,
                category_id     = cat_id,
                price           = base_price,
                cost            = base_cost,
                description     = description,
                is_active       = is_active,
                lifecycle_stage = lifecycle,
            )
            db.session.add(product)
            db.session.flush()

            handle_to_product_id[handle] = product.id
            sku_to_product_id[parent_sku] = product.id
            products_loaded += 1

            # Load variants (all rows in the group including first)
            for _, var_row in group.iterrows():
                var_sku     = safe_str(var_row.get('SKU'))
                size        = safe_str(var_row.get('Size'), '')
                color       = safe_str(var_row.get('Color'), 'N/A')
                variant_nm  = safe_str(var_row.get('VariantName'), size or color)
                var_price   = float(var_row.get('Price', base_price))

                # sku_suffix: extract the part after the last '-' if it's a size
                sku_suffix = size.upper() if size else var_sku[-4:] if len(var_sku) > 4 else var_sku

                var_type = 'Size' if size else 'Color'

                var = ProductVariant(
                    product_id = product.id,
                    name       = variant_nm,
                    type       = var_type,
                    sku_suffix = sku_suffix[:20],
                    price_adj  = round(var_price - base_price, 2),
                    stock      = safe_int(var_row.get('InventoryQty'), 0),
                )
                db.session.add(var)
                sku_to_product_id[var_sku] = product.id
                variants_loaded += 1

        db.session.commit()
        print(f'  Products loaded:  {products_loaded:,}')
        print(f'  Variants loaded:  {variants_loaded:,}')

        # ── LOAD INVENTORY ────────────────────────────────────────────────────
        print('\n  Loading inventory snapshots...')
        inv_loaded = 0
        for handle, prod_id in handle_to_product_id.items():
            group = catalog_df[catalog_df['Handle'] == handle]
            total_qty = int(group['InventoryQty'].sum())

            inv = Inventory(
                product_id         = prod_id,
                quantity           = total_qty,
                reorder_point      = 10,
                reorder_quantity   = 50,
                warehouse_location = 'Main Warehouse',
                last_restocked     = datetime.utcnow(),
            )
            db.session.add(inv)
            inv_loaded += 1

        db.session.commit()
        print(f'  Inventory records loaded: {inv_loaded:,}')

        # ── LOAD CUSTOMERS ────────────────────────────────────────────────────
        print('\n[6/7] Loading customers...')
        FRAUD_KEYWORDS = ['fraud', 'banned', 'bad customer', 'theif', 'theft']
        email_to_customer_id = {}  # email → operational customer id
        customers_loaded = 0
        skipped_duplicates = 0

        # Sort so most recent / most orders comes first (for dedup on email)
        customers_df_sorted = customers_df.copy()
        customers_df_sorted['Total Orders_num'] = pd.to_numeric(
            customers_df_sorted['Total Orders'], errors='coerce'
        ).fillna(0)
        customers_df_sorted = customers_df_sorted.sort_values('Total Orders_num', ascending=False)

        for _, row in customers_df_sorted.iterrows():
            email = safe_str(row.get('Email')).lower().replace("'", '')
            if not email or email in email_to_customer_id:
                skipped_duplicates += 1
                continue

            first_name = safe_str(row.get('First Name'))
            last_name  = safe_str(row.get('Last Name'))
            full_name  = f'{first_name} {last_name}'.strip() or 'Unknown Customer'

            phone_main    = safe_str(row.get('Phone')).replace("'", '').replace('+', '')
            phone_default = safe_str(row.get('Default Address Phone')).replace("'", '')
            phone = phone_main if phone_main and phone_main not in ('nan', '') else phone_default

            city_raw  = safe_str(row.get('Default Address City'))
            city_norm = clean_city(city_raw)

            address_parts = [
                safe_str(row.get('Default Address Street')),
                safe_str(row.get('Default Address City')),
            ]
            address = ', '.join(p for p in address_parts if p) or None

            country = safe_str(row.get('Default Address Country Code'), 'EG')

            tags_raw = safe_str(row.get('Tags', ''))
            is_fraud = any(kw in tags_raw.lower() for kw in FRAUD_KEYWORDS)
            segment = 'Fraud Risk' if is_fraud else 'New'

            cust = Customer(
                name       = full_name,
                email      = email,
                phone      = phone or None,
                address    = address,
                city       = city_norm,
                country    = country,
                segment    = segment,
            )
            db.session.add(cust)
            db.session.flush()
            email_to_customer_id[email] = cust.id
            customers_loaded += 1

            if customers_loaded % 1000 == 0:
                db.session.commit()
                print(f'    ...{customers_loaded:,} customers loaded')

        db.session.commit()
        print(f'  Customers loaded:  {customers_loaded:,}')
        print(f'  Duplicates skipped: {skipped_duplicates:,}')

        # Create a fallback "Unknown" customer for orders without a matched email
        unknown_cust = Customer(
            name       = 'Unknown Customer',
            email      = 'unknown@leveld.store',
            phone      = None,
            address    = None,
            city       = 'Cairo',
            country    = 'EG',
            segment    = 'New',
        )
        db.session.add(unknown_cust)
        db.session.flush()
        fallback_customer_id = unknown_cust.id
        db.session.commit()
        print(f'  Fallback customer id: {fallback_customer_id}')

        # ── LOAD ORDERS + ORDER ITEMS ─────────────────────────────────────────
        print('\n[7/7] Loading orders and line items...')

        # Get a fallback product for unresolvable line items
        fallback_product = Product.query.order_by(Product.id).first()
        fallback_product_id = fallback_product.id if fallback_product else None
        if not fallback_product_id:
            print('  [WARN] No products found — order items cannot be linked!')

        orders_loaded     = 0
        items_loaded      = 0
        unresolved_items  = 0
        order_name_to_id  = {}  # Shopify order name (#1001) → operational order id

        # Group all rows by order Name
        order_groups = orders_df.groupby('Name')

        for order_name, group in order_groups:
            meta = group.iloc[0]  # Order-level metadata from first row

            email = safe_str(meta.get('Email', '')).lower().replace("'", '')
            customer_id = email_to_customer_id.get(email, fallback_customer_id)

            # Status mapping
            fin_status    = safe_str(meta.get('Financial Status'), 'pending')
            fulfill_status= safe_str(meta.get('Fulfillment Status'), 'unfulfilled')
            cancelled_at  = meta.get('Cancelled at')
            erp_status    = map_order_status(fin_status, fulfill_status, cancelled_at)

            raw_total    = meta.get('Total')
            raw_discount = meta.get('Discount Amount')
            raw_shipping = meta.get('Shipping')
            total_amount = safe_float(raw_total,    0.0)
            discount     = safe_float(raw_discount, 0.0)
            shipping_fee = safe_float(raw_shipping, 0.0)

            notes = safe_str(meta.get('Notes'))

            # Parse created_at
            created_at = meta.get('Created_dt')
            if pd.isna(created_at) or created_at is None:
                created_at = datetime.utcnow()
            else:
                # Convert tz-aware to naive UTC
                try:
                    created_at = created_at.to_pydatetime().replace(tzinfo=None)
                except Exception:
                    created_at = datetime.utcnow()

            order = Order(
                order_number = str(order_name),
                customer_id  = customer_id,
                status       = erp_status,
                total_amount = total_amount,
                discount     = discount,
                shipping_fee = shipping_fee,
                notes        = notes or None,
                created_at   = created_at,
                updated_at   = created_at,
            )
            db.session.add(order)
            db.session.flush()
            order_name_to_id[order_name] = order.id
            orders_loaded += 1

            # Line items
            for _, row in group.iterrows():
                sku_raw   = safe_str(row.get('Lineitem sku', '')).replace("'", '')
                item_name = safe_str(row.get('Lineitem name', ''))
                qty       = safe_int(row.get('Lineitem quantity', 1), 1)
                unit_price= safe_float(row.get('Lineitem price', 0))

                # Resolve product_id: SKU → Handle prefix → Name match → fallback
                prod_id = sku_to_product_id.get(sku_raw)

                if not prod_id and item_name:
                    # Try exact title match
                    base_title = item_name.split(' - ')[0].strip()
                    prod = Product.query.filter(Product.name == base_title).first()
                    if prod:
                        prod_id = prod.id

                if not prod_id:
                    prod_id = fallback_product_id
                    unresolved_items += 1

                item = OrderItem(
                    order_id   = order.id,
                    product_id = prod_id,
                    quantity   = qty,
                    unit_price = unit_price,
                )
                db.session.add(item)
                items_loaded += 1

            if orders_loaded % 500 == 0:
                db.session.commit()
                print(f'    ...{orders_loaded:,} orders loaded')

        db.session.commit()
        print(f'  Orders loaded:        {orders_loaded:,}')
        print(f'  Order items loaded:   {items_loaded:,}')
        print(f'  Unresolved items:     {unresolved_items:,}')

        # ── SUMMARY ──────────────────────────────────────────────────────────
        duration = (datetime.utcnow() - start).total_seconds()
        print()
        print('=' * 65)
        print(f'PHASE A COMPLETE in {duration:.1f}s')
        print('=' * 65)
        print(f'  Categories:    {len(cat_name_to_id):,}')
        print(f'  Products:      {products_loaded:,}')
        print(f'  Variants:      {variants_loaded:,}')
        print(f'  Inventory:     {inv_loaded:,}')
        print(f'  Customers:     {customers_loaded:,}')
        print(f'  Orders:        {orders_loaded:,}')
        print(f'  Order Items:   {items_loaded:,}')
        print()
        print('  Operational tables now reflect REAL Shopify business data.')
        print('  Run the ETL pipeline next to rebuild the warehouse from these tables.')

        return True


if __name__ == '__main__':
    success = run_phase_a()
    sys.exit(0 if success else 1)
