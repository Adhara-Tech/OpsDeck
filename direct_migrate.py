import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'data', 'renewals.db')
print(f"Connecting to {db_path}...")

try:
    con = sqlite3.connect(db_path, timeout=10)
    cur = con.cursor()
    
    # Check if column exists
    cur.execute("PRAGMA table_info(change)")
    columns = [row[1] for row in cur.fetchall()]
    
    if 'requires_approval' in columns:
        print("Column 'requires_approval' already exists.")
    else:
        print("Adding column 'requires_approval'...")
        cur.execute("ALTER TABLE change ADD COLUMN requires_approval BOOLEAN DEFAULT 1")
        con.commit()
        print("Success: Column added.")

    con.close()
except Exception as e:
    print(f"Error: {e}")
