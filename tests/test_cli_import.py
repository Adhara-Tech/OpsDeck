import pytest
from src.models import User, Supplier, Contact, Asset, Peripheral, Location, Software, Subscription, Budget, Risk, RiskCategory
# Note: Software, Subscription, Budget are imported from 'Asset' alias in previous step or src.models root for tests
from src.extensions import db


@pytest.fixture
def csv_dir(tmp_path):
    """Creates a temporary directory for CSV files."""
    return tmp_path


def test_import_users_basic(app, csv_dir):
    """Test basic user import from CSV."""
    # Create CSV file
    csv_file = csv_dir / "users.csv"
    csv_file.write_text(
        "name,email\n"
        "Alice Johnson,alice@example.com\n"
        "Bob Smith,bob@example.com\n"
    )
    
    # Get initial user count
    with app.app_context():
        initial_count = User.query.count()
    
    # Run import command
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'users', str(csv_file)])
    
    # Verify output
    assert result.exit_code == 0
    assert "Users created: 2" in result.output
    assert "alice@example.com" in result.output
    assert "bob@example.com" in result.output
    
    # Verify database
    with app.app_context():
        assert User.query.count() == initial_count + 2  # 2 new users added
        alice = User.query.filter_by(email='alice@example.com').first()
        assert alice is not None
        assert alice.name == 'Alice Johnson'
        assert alice.role == 'user'
        # Verify password was set (hash should exist)
        assert alice.password_hash is not None


def test_import_users_skip_duplicates(app, csv_dir):
    """Test that duplicate users are skipped."""
    # Create a user first
    with app.app_context():
        existing_user = User(name='Existing User', email='existing@example.com', role='user')
        existing_user.set_password('password123')
        db.session.add(existing_user)
        db.session.commit()
    
    # Create CSV with duplicate email
    csv_file = csv_dir / "users.csv"
    csv_file.write_text(
        "name,email\n"
        "Existing User,existing@example.com\n"
        "New User,new@example.com\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'users', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Users created: 1" in result.output
    assert "Skipped (already existed): 1" in result.output


def test_import_users_file_not_found(app):
    """Test error handling when CSV file doesn't exist."""
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'users', 'nonexistent.csv'])
    
    assert result.exit_code == 0  # Command runs but reports error
    assert "Error: File 'nonexistent.csv' not found" in result.output


def test_import_suppliers_basic(app, csv_dir):
    """Test basic supplier import."""
    csv_file = csv_dir / "suppliers.csv"
    csv_file.write_text(
        "name,email,phone,address,compliance_status\n"
        "Acme Corp,contact@acme.com,555-0199,123 Main St,Approved\n"
        "Tech Inc,sales@tech.com,555-0200,456 Oak Ave,Pending\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'suppliers', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Suppliers created: 2" in result.output
    
    with app.app_context():
        acme = Supplier.query.filter_by(name='Acme Corp').first()
        assert acme is not None
        assert acme.email == 'contact@acme.com'
        assert acme.phone == '555-0199'
        assert acme.compliance_status == 'Approved'


def test_import_suppliers_with_website(app, csv_dir):
    """Test importing suppliers with website column."""
    csv_file = csv_dir / "suppliers_website.csv"
    csv_file.write_text(
        "name,email,website,compliance_status\n"
        "Web Corp,web@corp.com,https://webcorp.com,Approved\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'suppliers', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Suppliers created: 1" in result.output
    
    with app.app_context():
        supplier = Supplier.query.filter_by(name='Web Corp').first()
        assert supplier is not None
        assert supplier.website == 'https://webcorp.com'


def test_import_suppliers_with_semicolon(app, csv_dir):
    """Test importing suppliers with semicolon delimiter."""
    csv_file = csv_dir / "suppliers_semicolon.csv"
    csv_file.write_text(
        "name;email;phone;compliance_status\n"
        "Semi Corp;semi@corp.com;555-5555;Approved\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'suppliers', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Suppliers created: 1" in result.output
    
    with app.app_context():
        supplier = Supplier.query.filter_by(name='Semi Corp').first()
        assert supplier is not None
        assert supplier.email == 'semi@corp.com'


def test_import_suppliers_skip_duplicates(app, csv_dir):
    """Test that duplicate suppliers are skipped."""
    with app.app_context():
        existing = Supplier(name='Existing Corp', email='test@existing.com')
        db.session.add(existing)
        db.session.commit()
    
    csv_file = csv_dir / "suppliers.csv"
    csv_file.write_text(
        "name,email,phone,compliance_status\n"
        "Existing Corp,duplicate@test.com,555-9999,Approved\n"
        "New Corp,new@corp.com,555-1111,Pending\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'suppliers', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Suppliers created: 1" in result.output
    assert "Skipped (already existed): 1" in result.output


def test_import_contacts_basic(app, csv_dir):
    """Test basic contact import."""
    # Create supplier first
    with app.app_context():
        supplier = Supplier(name='Test Supplier', email='supplier@test.com')
        db.session.add(supplier)
        db.session.commit()
    
    csv_file = csv_dir / "contacts.csv"
    csv_file.write_text(
        "name,supplier_name,email,phone,role\n"
        "John Doe,Test Supplier,john@test.com,555-1234,Account Manager\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'contacts', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Contacts imported: 1" in result.output
    
    with app.app_context():
        contact = Contact.query.filter_by(email='john@test.com').first()
        assert contact is not None
        assert contact.name == 'John Doe'
        assert contact.role == 'Account Manager'
        assert contact.supplier.name == 'Test Supplier'


def test_import_contacts_auto_create_supplier(app, csv_dir):
    """Test that missing suppliers are auto-created."""
    csv_file = csv_dir / "contacts.csv"
    csv_file.write_text(
        "name,supplier_name,email,role\n"
        "Jane Smith,New Supplier,jane@new.com,Sales Lead\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'contacts', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Supplier created automatically: New Supplier" in result.output
    assert "Contacts imported: 1" in result.output
    
    with app.app_context():
        supplier = Supplier.query.filter_by(name='New Supplier').first()
        assert supplier is not None
        assert supplier.compliance_status == 'Pending'


def test_import_contacts_missing_supplier_name(app, csv_dir):
    """Test that contacts without supplier_name are skipped."""
    csv_file = csv_dir / "contacts.csv"
    csv_file.write_text(
        "name,supplier_name,email\n"
        "Invalid Contact,,invalid@test.com\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'contacts', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Skipping contact 'Invalid Contact': missing 'supplier_name'" in result.output


def test_import_assets_basic(app, csv_dir):
    """Test basic asset import."""
    csv_file = csv_dir / "assets.csv"
    csv_file.write_text(
        "name,model,brand,serial_number,location_name,status,cost,purchase_date,warranty_length\n"
        "MacBook Pro,MBP16,Apple,C02XYZ123,HQ Office,In Use,2499.00,2023-01-15,24\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'assets', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Assets imported: 1" in result.output
    
    with app.app_context():
        asset = Asset.query.filter_by(serial_number='C02XYZ123').first()
        assert asset is not None
        assert asset.name == 'MacBook Pro'
        assert asset.brand == 'Apple'
        assert asset.cost == 2499.00
        assert asset.warranty_length == 24
        assert asset.location.name == 'HQ Office'


def test_import_assets_auto_create_location(app, csv_dir):
    """Test that missing locations are auto-created."""
    csv_file = csv_dir / "assets.csv"
    csv_file.write_text(
        "name,location_name,status,cost\n"
        "Test Asset,New Location,In Stock,100.00\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'assets', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Location created: New Location" in result.output
    assert "Assets imported: 1" in result.output
    
    with app.app_context():
        location = Location.query.filter_by(name='New Location').first()
        assert location is not None


def test_import_assets_invalid_date(app, csv_dir):
    """Test that invalid dates are handled gracefully."""
    csv_file = csv_dir / "assets.csv"
    csv_file.write_text(
        "name,purchase_date,cost\n"
        "Test Asset,invalid-date,100.00\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'assets', str(csv_file)])
    
    # Should still import, just with null date
    assert result.exit_code == 0
    assert "Assets imported: 1" in result.output
    
    with app.app_context():
        asset = Asset.query.filter_by(name='Test Asset').first()
        assert asset is not None
        assert asset.purchase_date is None


def test_import_assets_skip_duplicates(app, csv_dir):
    """Test that duplicate assets (by serial number) are skipped."""
    # Create asset first
    with app.app_context():
        asset = Asset(name='Existing Asset', serial_number='SN123', status='In Use', cost=100.0)
        db.session.add(asset)
        db.session.commit()
    
    csv_file = csv_dir / "assets.csv"
    csv_file.write_text(
        "name,serial_number,cost\n"
        "Existing Asset,SN123,500.00\n"
        "New Asset,SN456,200.00\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'assets', str(csv_file)])

    assert result.exit_code == 0
    assert "Assets imported: 1" in result.output
    assert "Skipped: 1" in result.output
    assert "Skipped existing asset" in result.output

    with app.app_context():
        # Cost should NOT update
        asset = Asset.query.filter_by(serial_number='SN123').first()
        assert asset.cost == 100.0
        # New asset should exist
        new_asset = Asset.query.filter_by(serial_number='SN456').first()
        assert new_asset is not None


def test_import_peripherals_basic(app, csv_dir):
    """Test basic peripheral import."""
    csv_file = csv_dir / "peripherals.csv"
    csv_file.write_text(
        "name,type,brand,serial_number,status\n"
        "Dell Monitor 27,Monitor,Dell,CN-0X123,In Use\n"
        "Logitech Mouse,Mouse,Logitech,SN998877,In Stock\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'peripherals', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Peripherals imported: 2" in result.output
    
    with app.app_context():
        monitor = Peripheral.query.filter_by(serial_number='CN-0X123').first()
        assert monitor is not None
        assert monitor.name == 'Dell Monitor 27'
        assert monitor.type == 'Monitor'
        assert monitor.brand == 'Dell'


def test_import_peripherals_default_values(app, csv_dir):
    """Test that default values are applied correctly."""
    csv_file = csv_dir / "peripherals.csv"
    csv_file.write_text(
        "name\n"
        "Generic Peripheral\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'peripherals', str(csv_file)])
    
    assert result.exit_code == 0
    
    with app.app_context():
        peripheral = Peripheral.query.filter_by(name='Generic Peripheral').first()
        assert peripheral is not None
        assert peripheral.type == 'Accessory'  # Default value
        assert peripheral.status == 'In Use'  # Default value


def test_import_users_password_generation(app, csv_dir):
    """Test that generated passwords are secure and unique."""
    csv_file = csv_dir / "users.csv"
    csv_file.write_text(
        "name,email\n"
        "User1,user1@test.com\n"
        "User2,user2@test.com\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'users', str(csv_file)])
    
    assert result.exit_code == 0
    
    # Extract passwords from output (they should be displayed)
    output_lines = result.output.split('\n')
    passwords = []
    for line in output_lines:
        if 'user1@test.com' in line or 'user2@test.com' in line:
            # Password should be the last column
            parts = line.split('|')
            if len(parts) >= 3:
                password = parts[-1].strip()
                passwords.append(password)
    
    # Verify passwords were generated
    assert len(passwords) == 2
    # Verify passwords are different
    assert passwords[0] != passwords[1]
    # Verify passwords are at least 12 characters
    assert all(len(p) >= 12 for p in passwords)


def test_import_software_basic(app, csv_dir):
    """Test software import with supplier assignment."""
    # Create supplier and user first
    with app.app_context():
        supplier = Supplier(name='Adobe', email='support@adobe.com')
        db.session.add(supplier)
        user = User(name='IT Manager', email='it@example.com', role='admin')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
    
    csv_file = csv_dir / "software.csv"
    csv_file.write_text(
        "name,category,description,supplier_name,owner_email\n"
        "Adobe Creative Cloud,Design,Creative Suite,Adobe,it@example.com\n"
        "Slack,Communication,Chat app,Unknown Supplier,unknown@example.com\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'software', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Software imported: 2" in result.output
    
    with app.app_context():
        # First software: Should have supplier and owner
        adobe = Software.query.filter_by(name='Adobe Creative Cloud').first()
        assert adobe is not None
        assert adobe.supplier.name == 'Adobe'
        assert adobe.owner.email == 'it@example.com'
        
        # Second software: Supplier/Owner not found -> Should be None (optional linking)
        slack = Software.query.filter_by(name='Slack').first()
        assert slack is not None
        assert slack.supplier_id is None
        assert slack.owner_id is None


def test_import_subscriptions_basic(app, csv_dir):
    """Test subscription import with validation."""
    with app.app_context():
        # Setup dependencies
        supplier = Supplier(name='Microsoft', email='ms@example.com')
        db.session.add(supplier)
        
        software = Software(name='Office 365', category='Productivity')
        db.session.add(software)
        
        budget = Budget(name='IT Budget 2024', amount=10000.0)
        db.session.add(budget)
        
        user = User(name='Jane Doe', email='jane@example.com', role='user')
        user.set_password('pw')
        db.session.add(user)
        
        db.session.commit()
    
    csv_file = csv_dir / "subscriptions.csv"
    csv_file.write_text(
        "name,type,cost,supplier_name,renewal_date,period_type,software_name,budget_name,assigned_user_email,auto_renew\n"
        "M365 Business,SaaS,150.00,Microsoft,2025-01-01,monthly,Office 365,IT Budget 2024,jane@example.com,yes\n"
        "Invalid Sub,SaaS,100.00,Missing Supplier,2025-01-01,yearly,,,,no\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'subscriptions', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Subscriptions imported: 1" in result.output
    assert "Skipped (missing supplier): 1" in result.output
    
    with app.app_context():
        sub = Subscription.query.filter_by(name='M365 Business').first()
        assert sub is not None
        assert sub.cost == 150.00
        assert sub.supplier.name == 'Microsoft'
        assert sub.software.name == 'Office 365'
        assert sub.budget.name == 'IT Budget 2024'
        assert sub.user.email == 'jane@example.com'
        assert sub.budget.name == 'IT Budget 2024'
        assert sub.user.email == 'jane@example.com'
        assert sub.auto_renew is True


def test_import_risks_basic(app, csv_dir):
    """Test basic risk import with categories."""
    csv_file = csv_dir / "risks.csv"
    csv_file.write_text(
        "name,likelihood,impact,description,category\n"
        "Data Breach,4,5,Unauthorized access to sensitive data,\"Confidentiality, Legal\"\n"
        "Server Outage,3,4,Data center power loss,Availability\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'risks', str(csv_file)])
    
    assert result.exit_code == 0
    assert "Risks imported: 2" in result.output
    
    with app.app_context():
        # First risk
        breach = Risk.query.filter_by(risk_description='Data Breach').first()
        assert breach is not None
        assert breach.inherent_likelihood == 4
        assert breach.inherent_impact == 5
        # Residuals should default to inherent
        assert breach.residual_likelihood == 4
        assert breach.residual_impact == 5
        assert breach.extended_description == 'Unauthorized access to sensitive data'
        
        # Check categories
        cats = [c.category for c in breach.categories]
        assert 'Confidentiality' in cats
        assert 'Legal' in cats
        
        # Second risk
        outage = Risk.query.filter_by(risk_description='Server Outage').first()
        assert outage is not None
        assert outage.categories.first().category == 'Availability'


def test_import_risks_validation(app, csv_dir):
    """Test validation (missing name/impact/likelihood)."""
    # Get initial count
    with app.app_context():
        initial_count = Risk.query.count()

    csv_file = csv_dir / "risks.csv"
    csv_file.write_text(
        "name,likelihood,impact\n"
        ",5,5\n"
        "Valid Risk,5,5\n"
    )
    
    runner = app.test_cli_runner()
    result = runner.invoke(args=['data-import', 'risks', str(csv_file)])
    
    assert result.exit_code == 0
    # Should skip the blank name row (or fail it), but count valid one
    
    with app.app_context():
        # Expect exactly 1 new risk
        assert Risk.query.count() == initial_count + 1
        assert Risk.query.filter_by(risk_description='Valid Risk').first() is not None
