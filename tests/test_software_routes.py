"""
Tests for src/routes/software.py
Covers: list_software, detail, add_software, edit_software
"""
import pytest
from src import db
from src.models import Software, User, Supplier, License

@pytest.fixture
def software_data(app):
    """Creates sample data for software testing using get_or_create pattern."""
    with app.app_context():
        # 1. Get or Create Owner User
        # The auth_client fixture creates 'Admin', let's use a different one or checking if exists
        user = User.query.filter_by(email="owner@software.com").first()
        if not user:
            user = User(name="Software Owner", email="owner@software.com", role="user")
            user.set_password("password")
            db.session.add(user)
            db.session.commit()

        # 2. Get or Create Supplier
        supplier = Supplier.query.filter_by(email="adobe@supplier.com").first()
        if not supplier:
            supplier = Supplier(name="Adobe Systems", email="adobe@supplier.com")
            db.session.add(supplier)
            db.session.commit()

        # 3. Get or Create Software
        software = Software.query.filter_by(name="Adobe Creative Cloud").first()
        if not software:
            software = Software(
                name="Adobe Creative Cloud",
                category="Design",
                description="Creative Suite",
                owner_id=user.id,
                owner_type="user",
                supplier_id=supplier.id
            )
            db.session.add(software)
            db.session.commit()
        
        # 4. Get or Create License attached to software
        lic = License.query.filter_by(license_key="ADOBE-CC-2025").first()
        if not lic:
            from datetime import timedelta
            from src.utils.timezone_helper import today
            lic = License(
                name="CC User License",
                license_key="ADOBE-CC-2025",
                software_id=software.id,
                user_id=user.id,
                expiry_date=today() + timedelta(days=365),
                cost=600.0,
                currency="USD"
            )
            db.session.add(lic)
            db.session.commit()

        yield {
            'software_id': software.id,
            'user_id': user.id,
            'supplier_id': supplier.id
        }


def test_list_software_loads(auth_client, software_data):
    """Test that software list page loads."""
    response = auth_client.get('/software/')
    assert response.status_code == 200
    assert b'Adobe Creative Cloud' in response.data


def test_software_detail_loads(auth_client, software_data):
    """Test that software detail page loads."""
    response = auth_client.get(f'/software/{software_data["software_id"]}')
    assert response.status_code == 200
    assert b'Adobe Creative Cloud' in response.data


def test_software_detail_not_found(auth_client):
    """Test 404 for non-existent software."""
    response = auth_client.get('/software/999999')
    assert response.status_code == 404


def test_add_software_form_loads(auth_client):
    """Test that add software form loads."""
    response = auth_client.get('/software/new')
    assert response.status_code == 200
    assert b'Add Software' in response.data or b'New Software' in response.data


def test_add_software_post_success(auth_client, app):
    """Test adding new software."""
    # Ensure unique name for this test
    unique_name = "New Test Software 2025"
    
    # Check if exists and delete if necessary (cleanup) 
    # though usually init_database handles this, but auth_client might not clear immediately if shared
    with app.app_context():
        existing = Software.query.filter_by(name=unique_name).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

    response = auth_client.post('/software/new', data={
        'name': unique_name,
        'category': 'Testing',
        'description': 'Description',
        'owner': 'user_1', # Simulating a user owner, ID 1 usually exists (admin)
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Software added successfully' in response.data or unique_name.encode() in response.data


def test_edit_software_form_loads(auth_client, software_data):
    """Test that edit software form loads."""
    response = auth_client.get(f'/software/{software_data["software_id"]}/edit')
    assert response.status_code == 200
    assert b'Adobe Creative Cloud' in response.data


def test_edit_software_post_success(auth_client, software_data, app):
    """Test updating software."""
    response = auth_client.post(f'/software/{software_data["software_id"]}/edit', data={
        'name': 'Adobe CC Updated',
        'category': 'Design Tools',
        'description': 'Updated Description',
        'owner': f'user_{software_data["user_id"]}'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    with app.app_context():
        sw = db.session.get(Software, software_data['software_id'])
        assert sw.name == 'Adobe CC Updated'
        # Revert name for other tests if using shared fixture? 
        # But 'function' scope fixture handles reset generally. 
        # If conflicts occur, names should be unique per test or cleanup used.
