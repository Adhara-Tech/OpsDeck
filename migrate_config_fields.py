import sqlite3
import os

db_path = os.path.join(os.getcwd(), 'data', 'renewals.db')
print(f"Connecting to {db_path}...")

try:
    con = sqlite3.connect(db_path, timeout=10)
    cur = con.cursor()
    
    cur.execute("PRAGMA table_info(change)")
    columns = [row[1] for row in cur.fetchall()]
    
    if 'configuration_id' not in columns:
        print("Adding 'configuration_id'...")
        cur.execute("ALTER TABLE change ADD COLUMN configuration_id INTEGER REFERENCES configuration(id)")
    else:
        print("'configuration_id' already exists.")

    if 'configuration_version_id' not in columns:
        print("Adding 'configuration_version_id'...")
        cur.execute("ALTER TABLE change ADD COLUMN configuration_version_id INTEGER REFERENCES configuration_version(id)")
    else:
        print("'configuration_version_id' already exists.")
        
    con.commit()
    print("Migration successful.")
    con.close()
except Exception as e:
    print(f"Error: {e}")
