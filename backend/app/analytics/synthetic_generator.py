"""
Synthetic Data Generator — Leveld ERP
======================================
Purpose: Generate historically-realistic synthetic sales and procurement
         records for forecasting model training and segmentation analytics.

DESIGN PRINCIPLES (from business data audit):
  - Leveld is online-only (ChannelKey=1 always)
  - 99.97% Cash on Delivery (COD only for payment method)
  - All products from real Shopify catalog (real SKUs, titles, prices)
  - All customers from real Shopify customer pool (no invented profiles)
  - Product weights derived from real sales velocity in orders_export_1.csv
  - Order size distributions mirror real order patterns
  - All synthetic records carry IsSynthetic=True and OrderNumber='#SYN-XXXX'

WHAT THIS MODULE DOES NOT DO:
  - Generate fake payment methods (Credit Card, Mobile Wallet)
  - Generate fake sales channels (Retail POS, Mobile App, B2B)
  - Generate fake customers
  - Generate fake product SKUs or names
  - Auto-generate real procurement data (no real supplier data exists)
"""
import os
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ─── File Paths ───────────────────────────────────────────────────────────────
BASE_DATA_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'data', 'shopify'
)
ORDERS_CSV    = os.path.join(BASE_DATA_PATH, 'orders_export_1.csv')
CUSTOMERS_CSV = os.path.join(BASE_DATA_PATH, 'customers_export.csv')
PRODUCTS_CSV  = os.path.join(BASE_DATA_PATH, 'products_export_1.csv')


# ─── Business-Accurate Distributions (measured from real data) ────────────────

# Order size distribution: rows per order (line items, not quantity)
# Source: orders_export_1.csv, groupby Name, size()
ORDER_ROWS_PROBS = {1: 0.600, 2: 0.243, 3: 0.091, 4: 0.038, 5: 0.018, 6: 0.007, 7: 0.002, 8: 0.001}

# Line item quantity distribution
# Source: Lineitem quantity value counts
QTY_VALUES  = [1, 2, 3]
QTY_WEIGHTS = [0.85, 0.12, 0.03]

# Financial status distribution (excluding voided from paid/pending split)
# Source: order_level Financial Status value counts: paid=2297, pending=2527, voided=168
FIN_STATUS_VALUES  = ['paid', 'pending', 'voided']
FIN_STATUS_WEIGHTS = [0.456, 0.500, 0.044]   # voided ≈ cancellation rate 2.4%→4.4% of non-paid

# Shipping cost distribution
# Source: order_level Shipping value_counts
SHIPPING_VALUES  = [60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 100.0, 150.0]
SHIPPING_WEIGHTS = [0.28, 0.22, 0.09, 0.07, 0.03, 0.01, 0.005, 0.005]
SHIPPING_WEIGHTS_NORM = [w / sum(SHIPPING_WEIGHTS) for w in SHIPPING_WEIGHTS]

# Customer repeat behavior: % of orders from each segment
# Source: orders_per_customer value_counts
# 84.8% 1-order, 11.7% 2-order, 3.5% 3+
# For synthetic generation: we select customers with weighted preference for multi-buyers
CUSTOMER_REPEAT_WEIGHTS = None  # computed at runtime from real data

# City/governorate distribution (normalized from real shipping cities)
# Source: order_level Shipping City after normalization
CITY_DISTRIBUTION = [
    ('Cairo',       0.56),
    ('Giza',        0.18),
    ('Alexandria',  0.12),
    ('Mansoura',    0.03),
    ('Tanta',       0.02),
    ('Zagazig',     0.02),
    ('Ismailia',    0.02),
    ('Other',       0.05),
]

# Day-of-week weights (Monday peaks slightly)
# Source: order_level['Created at'].dt.day_name() value counts
DOW_WEIGHTS = {
    'Monday': 0.157, 'Tuesday': 0.135, 'Wednesday': 0.124,
    'Thursday': 0.137, 'Friday': 0.153, 'Saturday': 0.150, 'Sunday': 0.143
}
DOW_LIST     = list(DOW_WEIGHTS.keys())
DOW_PROB     = list(DOW_WEIGHTS.values())

# Hour-of-day weights (peak evening 21-23h)
# Source: order_level Hour value counts
HOUR_WEIGHTS = [
    277,208,130,144,89,138,158,210,269,314,306,348,345,366,
    309,341,318,346,345,362,348,446,425,325
]
HOUR_WEIGHTS_NORM = [w / sum(HOUR_WEIGHTS) for w in HOUR_WEIGHTS]

# Discount code distribution
# Source: 2.6% of orders have a discount code
# FREESHIPPING: 140/176 = 79.5% | LEVELD10: 35/176 = 19.9%
DISCOUNT_RATE = 0.026
DISCOUNT_CODES   = ['FREESHIPPING', 'LEVELD10']
DISCOUNT_WEIGHTS = [0.795, 0.205]

# Product type revenue weights (derived from orders_export_1.csv matching)
# Used to weight product selection toward real best-sellers
PRODUCT_TYPE_WEIGHTS = {
    'Printed Oversized T-Shirt':    0.35,
    'Basic Oversized T-Shirt':      0.22,
    'Printed Oversized Hoodie':     0.12,
    'Wide Leg Sweatpants':          0.07,
    'Printed Crewneck Sweatshirt':  0.06,
    'Basic Oversized Hoodie':       0.05,
    'Straight Leg Sweatpants':      0.04,
    'Ringer Baby Tee':              0.02,
    'Basic Crewneck Sweatshirt':    0.02,
    'Polo T-Shirts':                0.01,
    'DEFAULT':                      0.04,  # all other types combined
}

# Size popularity weights (derived from real line items — large sizes dominate)
SIZE_WEIGHTS = {'XS': 0.02, 'S': 0.12, 'M': 0.20, 'L': 0.25, 'XL': 0.22, '2XL': 0.19}


def _normalize_size(size_val):
    """Map variant size values to canonical labels."""
    if not isinstance(size_val, str):
        return None
    s = size_val.strip().upper()
    map_ = {
        'XS': 'XS', 'S': 'S', 'SMALL': 'S',
        'M': 'M', 'MEDIUM': 'M',
        'L': 'L', 'LARGE': 'L',
        'XL': 'XL', 'X-LARGE': 'XL', 'XLARGE': 'XL',
        '2XL': '2XL', 'XXL': '2XL', '2X-LARGE': '2XL',
        'SMALL / MEDIUM': 'S',  # unisex catch-all → map to S
    }
    return map_.get(s, s)


def build_product_catalog(products_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a clean product variant catalog with only real Shopify SKUs.
    Returns a DataFrame with one row per usable variant.
    Only includes variants where we have a usable identifier (SKU or Handle).
    """
    df = products_df.copy()
    df['Variant Price_num'] = pd.to_numeric(df['Variant Price'], errors='coerce')
    df['Cost_num']          = pd.to_numeric(df['Cost per item'], errors='coerce')
    df['Inventory_num']     = pd.to_numeric(df['Variant Inventory Qty'], errors='coerce').fillna(0)

    # Forward-fill product-level fields from parent rows
    product_level_cols = [
        'Title', 'Product Category', 'Type', 'Tags', 'Vendor', 'Status', 'Published',
        'Color (product.metafields.shopify.color-pattern)',
        'Fabric (product.metafields.shopify.fabric)',
        'Target gender (product.metafields.shopify.target-gender)',
        'Size (product.metafields.shopify.size)',
    ]
    df = df.sort_values('Handle')
    for col in product_level_cols:
        if col in df.columns:
            df[col] = df.groupby('Handle')[col].ffill()

    # Keep only rows with a price
    df = df[df['Variant Price_num'] > 0].copy()

    # Build canonical variant rows
    variants = []
    for _, row in df.iterrows():
        sku = str(row.get('Variant SKU', '')).strip().replace("'", "")
        handle = str(row.get('Handle', '')).strip()

        # Skip rows with no usable key
        if not sku or sku == 'nan' or not handle:
            continue

        title      = str(row.get('Title', '')).strip() if pd.notna(row.get('Title')) else ''
        prod_type  = str(row.get('Type', '')).strip() if pd.notna(row.get('Type')) else ''
        category   = str(row.get('Product Category', '')).strip() if pd.notna(row.get('Product Category')) else ''
        color      = str(row.get('Color (product.metafields.shopify.color-pattern)', '')).strip() if pd.notna(row.get('Color (product.metafields.shopify.color-pattern)')) else ''
        fabric     = str(row.get('Fabric (product.metafields.shopify.fabric)', '')).strip() if pd.notna(row.get('Fabric (product.metafields.shopify.fabric)')) else ''
        gender     = str(row.get('Target gender (product.metafields.shopify.target-gender)', '')).strip() if pd.notna(row.get('Target gender (product.metafields.shopify.target-gender)')) else ''
        sizes_all  = str(row.get('Size (product.metafields.shopify.size)', '')).strip() if pd.notna(row.get('Size (product.metafields.shopify.size)')) else ''
        compare_at = float(row['Variant Compare At Price']) if pd.notna(row.get('Variant Compare At Price')) else None
        cost_raw   = row['Cost_num']
        price      = float(row['Variant Price_num'])

        # Size from Option1 Value
        opt1_name = str(row.get('Option1 Name', '')).strip().lower() if pd.notna(row.get('Option1 Name')) else ''
        opt1_val  = str(row.get('Option1 Value', '')).strip() if pd.notna(row.get('Option1 Value')) else ''
        size_val  = opt1_val if 'size' in opt1_name else ''
        size_canonical = _normalize_size(size_val) if size_val else None

        # Barcode
        barcode = str(row.get('Variant Barcode', '')).strip().replace("'", "")
        barcode = barcode if barcode and barcode != 'nan' else None

        variants.append({
            'SKU': sku,
            'Handle': handle,
            'Title': title,
            'ProductType': prod_type,
            'Category': category,
            'Size': size_canonical,
            'Color': color,
            'Fabric': fabric,
            'TargetGender': gender,
            'SizesOffered': sizes_all,
            'Price': price,
            'CompareAtPrice': compare_at,
            'Cost_raw': cost_raw,
            'IsCostReal': pd.notna(cost_raw) and float(cost_raw) > 0 if pd.notna(cost_raw) else False,
            'Barcode': barcode,
            'Vendor': str(row.get('Vendor', 'Leveld')),
            'Status': str(row.get('Status', 'active')),
            'InventoryQty': int(row['Inventory_num']),
        })

    return pd.DataFrame(variants)


def compute_product_weights(catalog_df: pd.DataFrame, orders_df: pd.DataFrame) -> np.ndarray:
    """
    Compute per-variant selection weights from real order sales velocity.
    Variants that appear in more real orders get higher weight.
    Falls back to product-type weights for variants with no order history.
    """
    # Count real order occurrences per line item name
    name_counts = orders_df['Lineitem name'].value_counts().to_dict()
    sku_counts  = orders_df['Lineitem sku'].value_counts().to_dict()

    weights = []
    for _, row in catalog_df.iterrows():
        sku   = row['SKU']
        title = row['Title']
        size  = row.get('Size', '')

        # Try SKU match first
        w = sku_counts.get(sku, 0)

        # Try full line item name match (Title + Size)
        if w == 0 and title and size:
            name_key = f"{title} - {size}"
            w = name_counts.get(name_key, 0)

        # Try base title match only
        if w == 0 and title:
            title_base = title.split(' - ')[0].strip()
            w = sum(v for k, v in name_counts.items() if title_base in k)
            w = w / max(1, len([k for k in name_counts if title_base in k]))  # normalize per variant

        # Fallback to product-type weight
        if w == 0:
            prod_type = row.get('ProductType', '')
            w = PRODUCT_TYPE_WEIGHTS.get(prod_type, PRODUCT_TYPE_WEIGHTS['DEFAULT']) * 10

        weights.append(max(w, 0.01))  # ensure no zero weights

    weights_arr = np.array(weights, dtype=float)
    return weights_arr / weights_arr.sum()


def compute_cost_for_variant(row: dict, category_ratios: dict, global_ratio: float = 0.45) -> tuple:
    """
    Resolve cost using the audit-defined hierarchy:
    1. Real cost from products export (Cost per item field)
    2. Category average cost ratio (from variants with real cost)
    3. Global fallback ratio (45% — matches Egyptian apparel margins)
    Returns (cost, is_estimated).
    """
    price = row['Price']
    if row['IsCostReal']:
        return float(row['Cost_raw']), False

    category = row.get('Category', '')
    if category in category_ratios:
        return price * category_ratios[category], True

    return price * global_ratio, True


def build_category_cost_ratios(catalog_df: pd.DataFrame) -> dict:
    """Compute average cost/price ratio per category using only real cost data."""
    ratios = {}
    has_real = catalog_df[catalog_df['IsCostReal']].copy()
    has_real['ratio'] = has_real['Cost_raw'] / has_real['Price']

    for cat, grp in has_real.groupby('Category'):
        ratios[cat] = float(grp['ratio'].mean())

    return ratios


def generate_synthetic_sales(
    catalog_df: pd.DataFrame,
    product_weights: np.ndarray,
    category_ratios: dict,
    customer_keys: list,
    customer_email_to_key: dict,
    start_date: datetime = None,
    end_date: datetime = None,
    target_orders: int = 18000,
    random_seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic sales records for historical backfill.

    RULES ENFORCED (business-accurate):
    - ChannelKey = 1 (Online Storefront — Leveld is online-only)
    - PaymentMethod = 'Cash on Delivery (COD)' always
    - RiskLevel = 'Low' always (99.9% real rate)
    - All product selections from real catalog
    - All customer selections from real customer pool
    - Order size distribution mirrors real data
    - Financial status mirrors real data (44% paid, 50% pending, 4.4% voided)
    - Discount code rate = 2.6% of orders
    - IsSynthetic = True on all records
    """
    if start_date is None:
        start_date = datetime(2023, 1, 1)
    if end_date is None:
        end_date = datetime(2025, 12, 31)

    np.random.seed(random_seed)

    catalog_idx   = list(range(len(catalog_df)))
    total_days    = (end_date - start_date).days
    synth_order_id = 10000

    # Volume ramp: early 2023 = lower volume, late 2025 = higher
    # Simulate business growth from ~10 orders/day to ~60 orders/day
    def daily_volume_target(date: datetime) -> float:
        days_from_start = (date - start_date).days
        progress = days_from_start / total_days  # 0.0 → 1.0
        return 10 + 50 * (progress ** 1.5)  # non-linear growth curve

    records = []
    current_date = start_date

    while current_date <= end_date and synth_order_id - 10000 < target_orders:
        # How many orders today?
        daily_target = daily_volume_target(current_date)

        # Apply day-of-week seasonality
        dow = current_date.strftime('%A')
        dow_factor = DOW_WEIGHTS.get(dow, 1 / 7) / (1 / 7)  # normalize to mean=1.0
        n_orders_today = max(1, int(np.random.poisson(daily_target * dow_factor)))

        for _ in range(n_orders_today):
            if synth_order_id - 10000 >= target_orders:
                break

            synth_order_id += 1
            order_num = f'#SYN-{synth_order_id}'

            # Order timestamp: real hour distribution
            hour = np.random.choice(range(24), p=HOUR_WEIGHTS_NORM)
            minute = np.random.randint(0, 60)
            order_dt = current_date.replace(hour=hour, minute=minute)
            date_key = int(order_dt.strftime('%Y%m%d'))

            # Financial status
            fin_status = np.random.choice(FIN_STATUS_VALUES, p=FIN_STATUS_WEIGHTS)
            is_cancelled = (fin_status == 'voided')

            # Shipping cost
            shipping = float(np.random.choice(SHIPPING_VALUES, p=SHIPPING_WEIGHTS_NORM))

            # Discount
            has_discount = np.random.random() < DISCOUNT_RATE
            discount_code = None
            if has_discount:
                discount_code = np.random.choice(DISCOUNT_CODES, p=DISCOUNT_WEIGHTS)

            # Customer selection
            cust_key = int(np.random.choice(customer_keys))

            # Number of line items in order
            n_rows_probs = list(ORDER_ROWS_PROBS.values())
            n_rows_vals  = list(ORDER_ROWS_PROBS.keys())
            n_line_items = np.random.choice(n_rows_vals, p=n_rows_probs)

            order_subtotal = 0.0
            order_line_records = []

            for item_i in range(n_line_items):
                # Select product variant by real sales weight
                variant_idx = np.random.choice(catalog_idx, p=product_weights)
                variant = catalog_df.iloc[variant_idx]

                qty = int(np.random.choice(QTY_VALUES, p=QTY_WEIGHTS))
                price = float(variant['Price'])
                compare_at = variant.get('CompareAtPrice')
                compare_at = float(compare_at) if compare_at else None

                cost, is_cost_estimated = compute_cost_for_variant(
                    variant.to_dict(), category_ratios
                )

                # Discount: apply line-item discount proportionally
                line_discount = 0.0
                if has_discount and discount_code == 'LEVELD10' and item_i == 0:
                    # LEVELD10: 10% off subtotal, apply to first item
                    line_discount = round(price * qty * 0.10, 2)
                elif has_discount and discount_code == 'FREESHIPPING':
                    # FREESHIPPING: discount is on shipping only, not line items
                    line_discount = 0.0

                gross_rev = round(qty * price, 2)
                cogs      = round(qty * cost, 2)
                net_profit = round(gross_rev - line_discount - cogs, 2)
                order_subtotal += gross_rev

                order_line_records.append({
                    'DateKey':          date_key,
                    'CustomerKey':      cust_key,
                    'ProductKey':       0,          # filled from dim after load
                    '_VariantIdx':      variant_idx, # temp field for ProductKey resolution
                    'SupplierKey':      1,          # default supplier
                    'ChannelKey':       1,          # ALWAYS Online — Leveld is online-only
                    'OrderNumber':      order_num,
                    'ShopifyOrderID':   None,       # synthetic: no real Shopify ID
                    'IsSynthetic':      True,
                    'IsCancelled':      is_cancelled,
                    'Quantity':         qty,
                    'UnitPrice':        price,
                    'CompareAtPrice':   compare_at,
                    'UnitCost':         round(cost, 4),
                    'DiscountAmount':   line_discount,
                    'GrossRevenue':     gross_rev,
                    'COGS':             cogs,
                    'NetProfit':        net_profit,
                    'DiscountCode':     discount_code,
                    'OrderSubtotal':    None,       # filled after all line items
                    'OrderShipping':    shipping,
                    'FinancialStatus':  fin_status,
                    'FulfillmentStatus':'fulfilled' if fin_status == 'paid' else 'unfulfilled',
                    'PaymentMethod':    'Cash on Delivery (COD)',  # ALWAYS COD
                    'RiskLevel':        'Low',                     # ALWAYS Low
                })

            # Fill order subtotal on all line items of this order
            for rec in order_line_records:
                rec['OrderSubtotal'] = round(order_subtotal, 2)
                records.append(rec)

        current_date += timedelta(days=1)

    df = pd.DataFrame(records)
    if df.empty:
        return df

    # Drop the temp variant index column
    df.drop(columns=['_VariantIdx'], errors='ignore', inplace=True)
    print(f"[SyntheticGenerator] Generated {len(df):,} synthetic line items across "
          f"{df['OrderNumber'].nunique():,} synthetic orders.")
    return df


def generate_demo_procurement(
    dim_supplier_df: pd.DataFrame,
    catalog_df: pd.DataFrame,
    sku_to_prod_key: dict,
    category_ratios: dict,
    start_date: datetime = None,
    end_date: datetime = None,
    random_seed: int = 42,
) -> pd.DataFrame:
    """
    Generate CLEARLY LABELED demo procurement records.

    IMPORTANT:
    - All records have IsReal=False
    - These are illustrative simulations only
    - Do NOT use for real supplier performance KPIs
    - Real procurement data awaits Excel supplier input

    Business rules for Leveld (fashion brand):
    - Purchases blank garments, not finished products
    - MOQ typically 50–200 units per SKU per color
    - Lead times: 5–14 days (local Egyptian suppliers)
    - Payment: typically 50% upfront, 50% on delivery
    """
    if start_date is None:
        start_date = datetime(2023, 1, 1)
    if end_date is None:
        end_date = datetime(2025, 12, 31)

    np.random.seed(random_seed)

    records = []
    po_id = 5000
    supplier_keys = list(dim_supplier_df['SupplierKey'].values)

    # Use only active catalog variants for procurement simulation
    active_variants = catalog_df[catalog_df['Status'] == 'active'].copy()
    if active_variants.empty:
        active_variants = catalog_df.copy()

    for _, variant in active_variants.iterrows():
        sku = variant['SKU']
        prod_key = sku_to_prod_key.get(sku)
        if not prod_key:
            continue

        price = variant['Price']
        cost, _ = compute_cost_for_variant(variant.to_dict(), category_ratios)

        # Match supplier type: T-shirts/basics → Egyptian Textile Mills
        # Printed items → Delta Print House
        prod_type = str(variant.get('ProductType', '')).lower()
        if 'printed' in prod_type or 'graphic' in prod_type:
            supplier_key = 2  # Delta Print House
        elif 'pants' in prod_type or 'sweatpants' in prod_type:
            supplier_key = 3  # Misr Fabric Corp
        else:
            supplier_key = 1  # Egyptian Textile Mills Co.

        # Ensure supplier key exists
        if supplier_key not in supplier_keys:
            supplier_key = supplier_keys[0] if supplier_keys else 1

        # Generate POs chronologically (every 60-90 days per variant)
        sim_date = start_date + timedelta(days=np.random.randint(0, 30))
        while sim_date < end_date:
            po_id += 1
            po_interval = int(np.random.randint(60, 90))
            sim_date += timedelta(days=po_interval)
            if sim_date >= end_date:
                break

            date_key = int(sim_date.strftime('%Y%m%d'))
            lead_time = int(np.random.randint(5, 14))
            received_date = sim_date + timedelta(days=lead_time)
            rec_date_key = int(received_date.strftime('%Y%m%d'))

            moq = int(np.random.choice([50, 100, 150, 200], p=[0.4, 0.35, 0.15, 0.10]))
            status = np.random.choice(
                ['Received', 'Confirmed', 'Cancelled'],
                p=[0.88, 0.07, 0.05]
            )

            records.append({
                'DateKey':           date_key,
                'SupplierKey':       supplier_key,
                'ProductKey':        prod_key,
                'QuantityRequested': moq,
                'UnitCost':          round(cost, 2),
                'TotalCost':         round(moq * cost, 2),
                'LeadTimeDays':      lead_time if status == 'Received' else None,
                'ReceivedDateKey':   rec_date_key if status == 'Received' else None,
                'Status':            status,
                'IsReal':            False,  # DEMO DATA — not real procurement
            })

    df = pd.DataFrame(records)
    print(f"[SyntheticGenerator] Generated {len(df):,} demo procurement records (IsReal=False).")
    return df


# ─── Static Reference Data ────────────────────────────────────────────────────

DEMO_SUPPLIERS = [
    {
        'SupplierKey':      1,
        'SupplierName':     'Egyptian Textile Mills Co.',
        'ContactPerson':    'Ahmed Nour',
        'Phone':            '+20 2 2345 6789',
        'SupplierType':     'Blank Garment',
        'Country':          'Egypt',
        'LeadTimeDays_Avg': 7,
        'MinOrderQty':      100,
        'Rating':           4.5,
        'Status':           'Active',
        'IsReal':           False,
    },
    {
        'SupplierKey':      2,
        'SupplierName':     'Delta Print House',
        'ContactPerson':    'Maged Samir',
        'Phone':            '+20 50 123 4567',
        'SupplierType':     'Print Shop',
        'Country':          'Egypt',
        'LeadTimeDays_Avg': 5,
        'MinOrderQty':      50,
        'Rating':           4.3,
        'Status':           'Active',
        'IsReal':           False,
    },
    {
        'SupplierKey':      3,
        'SupplierName':     'Misr Fabric Corp.',
        'ContactPerson':    'Khaled Hassan',
        'Phone':            '+20 55 987 6543',
        'SupplierType':     'Fabric',
        'Country':          'Egypt',
        'LeadTimeDays_Avg': 10,
        'MinOrderQty':      200,
        'Rating':           4.1,
        'Status':           'Active',
        'IsReal':           False,
    },
    {
        'SupplierKey':      4,
        'SupplierName':     'Local Packaging Supplies',
        'ContactPerson':    'Rania Fathy',
        'Phone':            '+20 10 567 8901',
        'SupplierType':     'Packaging',
        'Country':          'Egypt',
        'LeadTimeDays_Avg': 3,
        'MinOrderQty':      500,
        'Rating':           4.7,
        'Status':           'Active',
        'IsReal':           False,
    },
]


def get_demo_suppliers_df() -> pd.DataFrame:
    """Return the demo supplier dimension records."""
    return pd.DataFrame(DEMO_SUPPLIERS)
