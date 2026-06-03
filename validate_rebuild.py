import sys, os, types
sys.path.insert(0, 'backend')

# Monkeypatch Flask/SQLAlchemy to test generator in isolation
flask_mod = types.ModuleType('flask')
flask_mod.Flask = lambda *a, **k: None
sys.modules['flask'] = flask_mod

fake_sa = types.ModuleType('flask_sqlalchemy')
class FakeSQLAlchemy:
    def __init__(self, *a, **k): pass
    Model = object
    Column = Integer = String = Float = Boolean = Text = Date = DateTime = None
fake_sa.SQLAlchemy = FakeSQLAlchemy
sys.modules['flask_sqlalchemy'] = fake_sa
app_mod = types.ModuleType('app')
app_mod.db = None
sys.modules['app'] = app_mod
sys.modules['app.models'] = types.ModuleType('app.models')
sys.modules['app.models.warehouse'] = types.ModuleType('app.models.warehouse')

import pandas as pd
import numpy as np
from datetime import datetime

from app.analytics.synthetic_generator import (
    build_product_catalog, compute_product_weights,
    build_category_cost_ratios, generate_synthetic_sales,
    get_demo_suppliers_df,
)

BASE = 'backend/data/shopify'
orders_df   = pd.read_csv(f'{BASE}/orders_export_1.csv',  low_memory=False)
products_df = pd.read_csv(f'{BASE}/products_export_1.csv', low_memory=False)

print('=== BUILDING CATALOG ===')
catalog     = build_product_catalog(products_df)
cat_ratios  = build_category_cost_ratios(catalog)
weights     = compute_product_weights(catalog, orders_df)

print(f'Catalog variants: {len(catalog):,}')
print(f'Variants with real cost: {catalog["IsCostReal"].sum()}')
print(f'Weight sum: {weights.sum():.6f}')
print(f'Category ratios:')
for k, v in cat_ratios.items():
    print(f'  {k[:60]}: {v:.3f}')

print('\n=== DEMO SUPPLIERS ===')
suppliers = get_demo_suppliers_df()
all_false = (suppliers['IsReal'] == False).all()
print(f'Count: {len(suppliers)} | All IsReal=False: {all_false}')
print(suppliers[['SupplierName','SupplierType','IsReal']].to_string(index=False))

print('\n=== GENERATING SYNTHETIC SALES (200 orders) ===')
synth = generate_synthetic_sales(
    catalog_df           = catalog,
    product_weights      = weights,
    category_ratios      = cat_ratios,
    customer_keys        = list(range(1, 201)),
    customer_email_to_key= {},
    start_date           = datetime(2024, 1, 1),
    end_date             = datetime(2024, 3, 31),
    target_orders        = 200,
    random_seed          = 42,
)

print(f'Rows: {len(synth):,} | Orders: {synth["OrderNumber"].nunique():,}')

print('\n=== VALIDATION CHECKS ===')
errors = []

checks = [
    ('IsSynthetic=True',      bool(synth['IsSynthetic'].all())),
    ('ChannelKey=1',          bool((synth['ChannelKey']==1).all())),
    ('PaymentMethod=COD',     bool((synth['PaymentMethod']=='Cash on Delivery (COD)').all())),
    ('RiskLevel=Low',         bool((synth['RiskLevel']=='Low').all())),
    ('OrderNum starts #SYN-', bool(synth['OrderNumber'].str.startswith('#SYN-').all())),
    ('ShopifyOrderID=None',   bool(synth['ShopifyOrderID'].isna().all())),
    ('GrossRevenue>0',        bool((synth[synth['FinancialStatus']!='voided']['GrossRevenue']>0).all())),
    ('UnitCost>0',            bool((synth['UnitCost']>0).all())),
    ('Price realistic',       bool(((synth['UnitPrice'] >= 100) & (synth['UnitPrice'] <= 2000)).all())),
]

for name, result in checks:
    mark = 'PASS' if result else 'FAIL'
    print(f'  {mark}: {name}')
    if not result:
        errors.append(name)

order_level = synth.drop_duplicates('OrderNumber')
disc_rate   = order_level['DiscountCode'].notna().mean()
canc_rate   = order_level['IsCancelled'].mean()
fin_counts  = order_level['FinancialStatus'].value_counts().to_dict()

print(f'\nDiscount rate:     {disc_rate:.1%} (target ~2.6%)')
print(f'Cancellation rate: {canc_rate:.1%} (target ~2.4%)')
print(f'Financial status:  {fin_counts}')
print(f'Shipping range:    {synth["OrderShipping"].min():.0f}–{synth["OrderShipping"].max():.0f} EGP')
print(f'Discount codes:    {synth["DiscountCode"].value_counts(dropna=False).to_dict()}')

print()
if errors:
    print(f'VALIDATION FAILED — {len(errors)} errors: {errors}')
    sys.exit(1)
else:
    print('ALL VALIDATIONS PASSED')
    print('Synthetic data generator produces business-accurate records.')
