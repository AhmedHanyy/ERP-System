import sys
import os
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, r"d:\ahmed\Year3\GP-SmartERP\SmartERP\backend")

from app import create_app, db

def export_synthetic_data():
    app = create_app()
    export_dir = r"d:\ahmed\Year3\GP-SmartERP\SmartERP\backend\data\shopify"
    
    with app.app_context():
        # Detect SQLite vs Postgres schema syntax
        is_pg = db.engine.dialect.name == 'postgresql'
        schema = 'warehouse.' if is_pg else ''
        
        print("Exporting synthetic warehouse records to CSV...")
        
        # 1. Export Synthetic Sales (where OrderNumber starts with #SYN-)
        sales_query = f"""
            SELECT * FROM {schema}fact_sales 
            WHERE "OrderNumber" LIKE '#SYN-%'
        """
        synth_sales = pd.read_sql(sales_query, db.engine)
        sales_file = os.path.join(export_dir, "synthetic_sales_export.csv")
        synth_sales.to_csv(sales_file, index=False)
        print(f"  - Exported {len(synth_sales)} synthetic sales rows to {sales_file}")
        
        # 2. Export Synthetic Procurement POs (entire table is synthetic)
        proc_query = f"SELECT * FROM {schema}fact_procurement"
        synth_proc = pd.read_sql(proc_query, db.engine)
        proc_file = os.path.join(export_dir, "synthetic_procurement_export.csv")
        synth_proc.to_csv(proc_file, index=False)
        print(f"  - Exported {len(synth_proc)} synthetic procurement rows to {proc_file}")
        
        # 3. Export Combined Sales (real + synthetic)
        all_sales_query = f"SELECT * FROM {schema}fact_sales"
        all_sales = pd.read_sql(all_sales_query, db.engine)
        comb_sales_file = os.path.join(export_dir, "combined_sales_export.csv")
        all_sales.to_csv(comb_sales_file, index=False)
        print(f"  - Exported {len(all_sales)} combined sales rows to {comb_sales_file}")

if __name__ == '__main__':
    export_synthetic_data()
