import sys, os, types, io
import importlib.util
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

gen = load_module('synthetic_generator', 'app/analytics/synthetic_generator.py')

import pandas as pd
import numpy as np
from datetime import datetime

orders_df   = pd.read_csv('data/shopify/orders_export_1.csv',  low_memory=False)
products_df = pd.read_csv('data/shopify/products_export_1.csv', low_memory=False)

print('=== CATALOG ===')
catalog     = gen.build_product_catalog(products_df)
cat_ratios  = gen.build_category_cost_ratios(catalog)
weights     = gen.compute_product_weights(catalog, orders_df)
n_real_cost = catalog['IsCostReal'].sum()
print(f'Variants: {len(catalog)} | Real cost: {n_real_cost} | Weight sum: {weights.sum():.6f}')
print('Category ratios:')
for k, v in cat_ratios.items():
    print(f'  {k[:60]}: {v:.3f}')

print('\n=== DEMO SUPPLIERS ===')
suppliers = gen.get_demo_suppliers_df()
all_demo  = (suppliers['IsReal'] == False).all()
print(f'Count: {len(suppliers)} | All IsReal=False: {all_demo}')
for _, row in suppliers.iterrows():
    print(f'  {row["SupplierName"]}: {row["SupplierType"]} (IsReal={row["IsReal"]})')

print('\n=== SYNTHETIC SALES (200 orders) ===')
synth = gen.generate_synthetic_sales(
    catalog_df=catalog,
    product_weights=weights,
    category_ratios=cat_ratios,
    customer_keys=list(range(1, 201)),
    customer_email_to_key={},
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 3, 31),
    target_orders=200,
    random_seed=42,
)
print(f'Rows: {len(synth)} | Orders: {synth["OrderNumber"].nunique()}')

print('\n=== VALIDATION CHECKS ===')
errors = []

def chk(name, result):
    ok = bool(result)
    print(f'  {"PASS" if ok else "FAIL"}: {name}')
    if not ok:
        errors.append(name)

chk('IsSynthetic=True',    synth['IsSynthetic'].all())
chk('ChannelKey=1',        (synth['ChannelKey'] == 1).all())
chk('PaymentMethod=COD',   (synth['PaymentMethod'] == 'Cash on Delivery (COD)').all())
chk('RiskLevel=Low',       (synth['RiskLevel'] == 'Low').all())
chk('OrderNum starts #SYN-', synth['OrderNumber'].str.startswith('#SYN-').all())
chk('ShopifyOrderID=None', synth['ShopifyOrderID'].isna().all())
chk('UnitCost>0',          (synth['UnitCost'] > 0).all())

non_voided = synth[synth['FinancialStatus'] != 'voided']
chk('GrossRevenue>0 (non-voided)', (non_voided['GrossRevenue'] > 0).all())
chk('Price 100-2000 EGP',  ((synth['UnitPrice'] >= 100) & (synth['UnitPrice'] <= 2000)).all())

print('\n=== DISTRIBUTION CHECKS ===')
ol = synth.drop_duplicates('OrderNumber')
disc_rate = ol['DiscountCode'].notna().mean()
canc_rate = ol['IsCancelled'].mean()
fin_counts = ol['FinancialStatus'].value_counts().to_dict()
ship_vals  = synth['OrderShipping'].value_counts().head(5).to_dict()

print(f'Discount rate:  {disc_rate:.1%} (target ~2.6%)')
print(f'Cancellation:   {canc_rate:.1%}  (target ~2.4%)')
print(f'Financial:      {fin_counts}')
print(f'Shipping:       {ship_vals}')

disc_by_code = synth.drop_duplicates('OrderNumber')['DiscountCode'].value_counts(dropna=False).to_dict()
print(f'Discount codes: {disc_by_code}')

print()
if errors:
    print(f'VALIDATION FAILED — {len(errors)} errors: {errors}')
    sys.exit(1)
else:
    print('ALL VALIDATIONS PASSED')
    print('Synthetic data generator is business-accurate.')
