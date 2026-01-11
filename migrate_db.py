from app import create_app
from src.extensions import db
from sqlalchemy import text
from dotenv import load_dotenv
import os

load_dotenv()

app = create_app()

with app.app_context():
    print(f"Using Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print("Checking database schema...")
    try:
        # Check if column exists
        result = db.session.execute(text("PRAGMA table_info('change')")).fetchall()
        columns = [row[1] for row in result]
        
        if 'requires_approval' in columns:
            print("Column 'requires_approval' already exists.")
        else:
            print("Column 'requires_approval' NOT found. Adding it...")
            db.session.execute(text("ALTER TABLE change ADD COLUMN requires_approval BOOLEAN DEFAULT 1"))
            db.session.commit()
            print("Column added successfully.")
            
    except Exception as e:
        print(f"Error: {e}")
