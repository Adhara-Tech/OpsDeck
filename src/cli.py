import click
import csv
import os
import secrets
import string
from datetime import datetime
from .extensions import db
# Import all necessary models
from .models import User, Asset, Peripheral, Location, Supplier, Contact

def generate_secure_password(length=12):
    """Generates a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for i in range(length))

def register_commands(app):
    """Registers the CLI command groups in the application."""
    
    @app.cli.group()
    def data_import():
        """Commands to bulk import data from CSV files."""
        pass

    # --- 1. IMPORT USERS (SECURE MODE) ---
    @data_import.command('users')
    @click.argument('filename')
    def import_users(filename):
        """Imports users from CSV. Columns: name, email"""
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found.")
            return

        print(f"{'USER':<30} | {'EMAIL':<30} | {'GENERATED PASSWORD'}")
        print("-" * 85)

        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            skipped = 0
            
            for row in reader:
                email = row['email'].strip()
                name = row['name'].strip()
                
                # Check if user already exists
                if User.query.filter_by(email=email).first():
                    skipped += 1
                    continue
                
                # Generate random password
                random_pw = generate_secure_password()
                
                # Force role='user' for security reasons
                user = User(name=name, email=email, role='user')
                user.set_password(random_pw)
                
                db.session.add(user)
                
                # Print credentials for admin usage
                print(f"{name:<30} | {email:<30} | {random_pw}")
                count += 1
            
            db.session.commit()
            print("-" * 85)
            print(f"✅ Process finished. Users created: {count}. Skipped (already existed): {skipped}.")

    # --- 2. IMPORT SUPPLIERS ---
    @data_import.command('suppliers')
    @click.argument('filename')
    def import_suppliers(filename):
        """Imports suppliers. Columns: name, email, phone, address, compliance_status"""
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found.")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            skipped = 0
            for row in reader:
                name = row['name'].strip()
                if Supplier.query.filter_by(name=name).first():
                    skipped += 1
                    continue

                supplier = Supplier(
                    name=name,
                    email=row.get('email'),
                    phone=row.get('phone'),
                    address=row.get('address'),
                    compliance_status=row.get('compliance_status', 'Pending')
                )
                db.session.add(supplier)
                count += 1
            
            db.session.commit()
            print(f"✅ Suppliers created: {count}. Skipped (already existed): {skipped}.")

    # --- 3. IMPORT CONTACTS ---
    @data_import.command('contacts')
    @click.argument('filename')
    def import_contacts(filename):
        """Imports contacts. Columns: name, email, phone, role, supplier_name"""
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found.")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                # Find supplier by name
                sup_name = row.get('supplier_name', '').strip()
                if not sup_name:
                    print(f"⚠️ Skipping contact '{row['name']}': missing 'supplier_name'")
                    continue

                supplier = Supplier.query.filter_by(name=sup_name).first()
                if not supplier:
                    # Create stub supplier if it doesn't exist
                    supplier = Supplier(name=sup_name, compliance_status='Pending')
                    db.session.add(supplier)
                    db.session.commit() # Commit needed to get ID
                    print(f"🏢 Supplier created automatically: {sup_name}")

                contact = Contact(
                    name=row['name'],
                    email=row.get('email'),
                    phone=row.get('phone'),
                    role=row.get('role'),
                    supplier_id=supplier.id
                )
                db.session.add(contact)
                count += 1
            
            db.session.commit()
            print(f"✅ Contacts imported: {count}.")

    # --- 4. IMPORT ASSETS ---
    @data_import.command('assets')
    @click.argument('filename')
    def import_assets(filename):
        """Imports assets. Columns: name, model, brand, serial_number, location_name, status, cost, warranty_length"""
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found.")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                # Location Logic
                loc_name = row.get('location_name')
                location_id = None
                if loc_name:
                    loc = Location.query.filter_by(name=loc_name).first()
                    if not loc:
                        loc = Location(name=loc_name)
                        db.session.add(loc)
                        db.session.commit()
                        print(f"📍 Location created: {loc_name}")
                    location_id = loc.id

                # Date Parsing Logic
                p_date = None
                if row.get('purchase_date'):
                    try:
                        p_date = datetime.strptime(row['purchase_date'], '%Y-%m-%d').date()
                    except ValueError:
                        pass

                asset = Asset(
                    name=row['name'],
                    model=row.get('model'),
                    brand=row.get('brand'),
                    serial_number=row.get('serial_number'),
                    status=row.get('status', 'In Use'),
                    location_id=location_id,
                    purchase_date=p_date,
                    cost=float(row['cost']) if row.get('cost') else 0.0,
                    warranty_length=int(row['warranty_length']) if row.get('warranty_length') else 0
                )
                db.session.add(asset)
                count += 1
            
            db.session.commit()
            print(f"✅ Assets imported: {count}.")

    # --- 5. IMPORT PERIPHERALS ---
    @data_import.command('peripherals')
    @click.argument('filename')
    def import_peripherals(filename):
        """Imports peripherals. Columns: name, type, brand, serial_number, status"""
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found.")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                peripheral = Peripheral(
                    name=row['name'],
                    type=row.get('type', 'Accessory'),
                    brand=row.get('brand'),
                    serial_number=row.get('serial_number'),
                    status=row.get('status', 'In Use')
                )
                db.session.add(peripheral)
                count += 1
            
            db.session.commit()
            print(f"✅ Peripherals imported: {count}.")