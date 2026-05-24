import sqlite3
import os

# Updated path based on discovery
db_path = 'backend/smarterp.db'

if os.path.exists(db_path):
    print(f"Connecting to database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Add lifecycle_stage to products
        print("Attempting to add 'lifecycle_stage' column to 'products' table...")
        cursor.execute("ALTER TABLE products ADD COLUMN lifecycle_stage VARCHAR(50) DEFAULT 'Growth'")
        print("Success: 'lifecycle_stage' added.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Notice: 'lifecycle_stage' already exists.")
        else:
            print(f"Error adding lifecycle_stage: {e}")

    conn.commit()
    conn.close()
    print("Database sync complete. Please restart your backend server.")
else:
    print(f"FATAL: Database not found at {db_path}. Please check your current directory.")
