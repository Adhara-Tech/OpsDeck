import click
import csv
import os
import secrets
from .utils.helpers import generate_secure_password, get_csv_reader
from datetime import datetime
from .extensions import db
# Import all necessary models
from .models import User, Asset, Peripheral, Location, Supplier, Contact, Software, Subscription, Budget, Risk, RiskCategory

def register_commands(app):
    
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
            reader = get_csv_reader(f)
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
        """Imports suppliers. Columns: name, email, phone, address, website, compliance_status"""
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found.")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            reader = get_csv_reader(f)
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
                    website=row.get('website'),
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
            reader = get_csv_reader(f)
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
            reader = get_csv_reader(f)
            count = 0
            skipped = 0
            for row in reader:
                # Check for duplicates
                serial = row.get('serial_number')
                if serial and Asset.query.filter_by(serial_number=serial).first():
                    print(f"⚠️ Skipped existing asset: {row['name']} ({serial})")
                    skipped += 1
                    continue

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
            print(f"✅ Assets imported: {count}. Skipped: {skipped}.")

    # --- 5. IMPORT PERIPHERALS ---
    @data_import.command('peripherals')
    @click.argument('filename')
    def import_peripherals(filename):
        """Imports peripherals. Columns: name, type, brand, serial_number, status"""
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found.")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            reader = get_csv_reader(f)
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

    # --- 6. IMPORT SOFTWARE ---
    @data_import.command('software')
    @click.argument('filename')
    def import_software(filename):
        """Imports software. Columns: name, category, description, supplier_name, owner_email, iso_27001_controls"""
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found.")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            reader = get_csv_reader(f)
            count = 0
            skipped = 0
            for row in reader:
                name = row['name'].strip()
                if Software.query.filter_by(name=name).first():
                    skipped += 1
                    continue

                # Optional Supplier Linking
                supplier_id = None
                sup_name = row.get('supplier_name')
                if sup_name:
                    supplier = Supplier.query.filter_by(name=sup_name.strip()).first()
                    if supplier:
                        supplier_id = supplier.id

                # Optional Owner Linking (User)
                owner_id, owner_type = None, None
                owner_email = row.get('owner_email')
                if owner_email:
                    user = User.query.filter_by(email=owner_email.strip()).first()
                    if user:
                        owner_id = user.id
                        owner_type = 'user'

                software = Software(
                    name=name,
                    category=row.get('category'),
                    description=row.get('description'),
                    supplier_id=supplier_id,
                    owner_id=owner_id,
                    owner_type=owner_type,
                    iso_27001_control_references=row.get('iso_27001_controls')
                )
                db.session.add(software)
                count += 1
            
            db.session.commit()
            print(f"✅ Software imported: {count}. Skipped (already existed): {skipped}.")

    # --- 7. IMPORT SUBSCRIPTIONS ---
    @data_import.command('subscriptions')
    @click.argument('filename')
    def import_subscriptions(filename):
        """Imports subscriptions. Columns: name, type, cost, supplier_name, renewal_date..."""
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found.")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            reader = get_csv_reader(f)
            count = 0
            skipped_missing_supplier = 0
            
            for row in reader:
                # MANDATORY: Supplier
                sup_name = row.get('supplier_name', '').strip()
                if not sup_name:
                    skipped_missing_supplier += 1
                    continue
                    
                supplier = Supplier.query.filter_by(name=sup_name).first()
                if not supplier:
                    print(f"⚠️ Skipped '{row.get('name')}': Supplier '{sup_name}' not found.")
                    skipped_missing_supplier += 1
                    continue

                # Optional Links
                software_id = None
                soft_name = row.get('software_name')
                if soft_name:
                    soft = Software.query.filter_by(name=soft_name.strip()).first()
                    if soft: software_id = soft.id
                
                budget_id = None
                bud_name = row.get('budget_name')
                if bud_name:
                    bud = Budget.query.filter_by(name=bud_name.strip()).first()
                    if bud: budget_id = bud.id
                
                user_id = None
                u_email = row.get('assigned_user_email')
                if u_email:
                    u = User.query.filter_by(email=u_email.strip()).first()
                    if u: user_id = u.id

                # Parsing
                try:
                    r_date = datetime.strptime(row.get('renewal_date', ''), '%Y-%m-%d').date()
                except ValueError:
                    r_date = datetime.today().date() # Fallback

                auto_renew = row.get('auto_renew', '').lower() in ['yes', 'y', 'true', '1']
                cost = float(row.get('cost')) if row.get('cost') else 0.0

                sub = Subscription(
                    name=row.get('name'),
                    subscription_type=row.get('type', 'SaaS'),
                    description=row.get('description'),
                    cost=cost,
                    currency=row.get('currency', 'EUR'),
                    renewal_date=r_date,
                    renewal_period_type=row.get('period_type', 'yearly'),
                    renewal_period_value=int(row.get('period_value', 1)),
                    auto_renew=auto_renew,
                    supplier_id=supplier.id,
                    software_id=software_id,
                    budget_id=budget_id,
                    user_id=user_id
                )
                db.session.add(sub)
                count += 1
            
            db.session.commit()
            print(f"✅ Subscriptions imported: {count}. Skipped (missing supplier): {skipped_missing_supplier}.")

    # --- 8. IMPORT RISKS ---
    @data_import.command('risks')
    @click.argument('filename')
    def import_risks(filename):
        """Imports risks. Columns: name, likelihood, impact, description, category"""
        if not os.path.exists(filename):
            print(f"❌ Error: File '{filename}' not found.")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            reader = get_csv_reader(f)
            count = 0
            
            for row in reader:
                name = row.get('name', '').strip()
                if not name:
                    continue  # Skip rows without a name

                try:
                    likelihood = int(row.get('likelihood', 1))
                    impact = int(row.get('impact', 1))
                except ValueError:
                    print(f"⚠️ Warning: Invalid score for risk '{name}'. Defaulting to 1.")
                    likelihood = 1
                    impact = 1

                risk = Risk(
                    risk_description=name,
                    inherent_likelihood=likelihood,
                    inherent_impact=impact,
                    residual_likelihood=likelihood, # Default to inherent
                    residual_impact=impact,         # Default to inherent
                    extended_description=row.get('description')
                )
                db.session.add(risk)
                db.session.flush() # Flush to get ID for categories

                # Category Parsing
                raw_cats = row.get('category', '')
                if raw_cats:
                    for cat in raw_cats.split(','):
                        clean_cat = cat.strip()
                        if clean_cat:
                            db.session.add(RiskCategory(risk_id=risk.id, category=clean_cat))
                
                count += 1
            
            db.session.commit()
            print(f"✅ Risks imported: {count}.")