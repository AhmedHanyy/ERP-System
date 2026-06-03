import sys
import os
import pandas as pd
from sqlalchemy import create_url, text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

# Table mapping from model tablename to schema prefix
OPERATIONAL_TABLES = [
    'users',
    'categories',
    'products',
    'product_variants',
    'customers',
    'orders',
    'order_items',
    'inventory',
    'inventory_logs',
    'suppliers',
    'procurement_requests',
    'audit_logs',
    'notifications'
]

def migrate_database():
    app = create_app()
    sqlite_url = f"sqlite:///{os.path.join(app.config['BASE_DIR'], '..', 'smarterp.db')}"
    postgres_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    
    if not (postgres_url.startswith('postgresql') or postgres_url.startswith('postgres')):
        print("Error: SQLALCHEMY_DATABASE_URI is not a PostgreSQL connection URI.")
        print(f"Current URI: {postgres_url}")
        print("Please configure DATABASE_URL environment variable to run PostgreSQL migration.")
        return

    print("--- STARTING DATABASE MIGRATION ---")
    print(f"Source (SQLite): {sqlite_url}")
    print(f"Target (PostgreSQL): {postgres_url}")
    
    # Establish connection engines
    sqlite_engine = db.create_engine(sqlite_url, {})
    
    with app.app_context():
        print("\nStep 1: Creating database schemas and tables in PostgreSQL...")
        # db.create_all() will create operational tables in operational schema, and warehouse tables in warehouse schema
        db.create_all()
        print("PostgreSQL tables successfully verified/created.")
        
        print("\nStep 2: Transferring table contents...")
        for table in OPERATIONAL_TABLES:
            try:
                # Read from SQLite
                df = pd.read_sql(f"SELECT * FROM {table}", sqlite_engine)
                print(f"  - Read {len(df)} rows from SQLite table: '{table}'")
                
                if len(df) == 0:
                    print(f"  - Table '{table}' is empty, skipping load.")
                    continue
                
                # Write to PostgreSQL operational schema
                # We clear existing table first since we are migrating fresh
                with db.engine.connect() as pg_conn:
                    pg_conn.execute(text(f"TRUNCATE TABLE operational.{table} CASCADE;"))
                    pg_conn.commit()
                
                df.to_sql(
                    name=table,
                    con=db.engine,
                    schema='operational',
                    if_exists='append',
                    index=False
                )
                print(f"  - Successfully loaded {len(df)} rows into operational.{table} in PostgreSQL.")
            except Exception as e:
                print(f"  - Error migrating table '{table}': {e}")
        
        print("\nStep 3: Resetting sequence IDs in PostgreSQL operational schema...")
        for table in OPERATIONAL_TABLES:
            try:
                with db.engine.connect() as pg_conn:
                    # Retrieve the maximum id in table to set the sequence
                    res = pg_conn.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM operational.{table}")).scalar()
                    next_val = int(res) + 1
                    
                    # Update PostgreSQL identity sequence
                    seq_name_query = text(f"""
                        SELECT pg_get_serial_sequence('operational.{table}', 'id')
                    """)
                    seq_name = pg_conn.execute(seq_name_query).scalar()
                    
                    if seq_name:
                        pg_conn.execute(text(f"SELECT setval('{seq_name}', {next_val}, false)"))
                        pg_conn.commit()
                        print(f"  - Sequence for operational.{table} reset to {next_val}.")
                    else:
                        print(f"  - No serial sequence found for operational.{table}, skipping reset.")
            except Exception as e:
                print(f"  - Error resetting sequence on '{table}': {e}")
                
    print("\n--- DATABASE MIGRATION COMPLETED SUCCESSFULLY ---")

if __name__ == '__main__':
    migrate_database()
