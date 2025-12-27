import pytest
from src.models import BusinessService, User
from src import db

# --- Fixtures ---

@pytest.fixture
def service_data(app):
    """Creates a sample service for testing."""
    with app.app_context():
        # Ensure we have a user to be the owner
        owner = User.query.filter_by(email='admin@test.com').first()
        if not owner:
            owner = User(name='Service Owner', email='owner@test.com', role='admin')
            db.session.add(owner)
            db.session.commit()
            
        service = BusinessService(
            name='Core API',
            description='Main backend API service',
            status='Active',
            owner_id=owner.id
        )
        db.session.add(service)
        db.session.commit()
        
        yield {
            'id': service.id,
            'owner_id': owner.id
        }

# --- Tests ---

def test_list_services_route(auth_client, service_data):
    """Test that the service list loads and shows our service."""
    response = auth_client.get('/services/')  # Verify this route prefix
    assert response.status_code == 200
    assert b'Core API' in response.data

def test_create_service_route(auth_client, app):
    """Test creating a new service via POST."""
    with app.app_context():
        owner = User.query.first()
        
    data = {
        'name': 'New Payment Gateway',
        'description': 'Integration with Stripe',
        'status': 'Draft',
        'owner_id': owner.id
    }
    
    # Verify the endpoint '/services/new' exists in your routes
    response = auth_client.post('/services/new', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'New Payment Gateway' in response.data
    
    with app.app_context():
        service = BusinessService.query.filter_by(name='New Payment Gateway').first()
        assert service is not None
        assert service.status == 'Draft'

def test_service_detail_route(auth_client, service_data):
    """Test the detail view of a service."""
    response = auth_client.get(f"/services/{service_data['id']}")
    assert response.status_code == 200
    assert b'Core API' in response.data
    assert b'Main backend API service' in response.data

def test_edit_service_route(auth_client, service_data):
    """Test updating an existing service."""
    data = {
        'name': 'Core API v2',
        'description': 'Updated description',
        'status': 'Deprecated',
        'owner_id': service_data['owner_id']
    }
    
    url = f"/services/{service_data['id']}/edit"
    response = auth_client.post(url, data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Core API v2' in response.data
    
    # Verify DB update
    with auth_client.application.app_context():
        service = db.session.get(BusinessService, service_data['id'])
        assert service.name == 'Core API v2'
        assert service.status == 'Deprecated'

def test_delete_service_route(auth_client, service_data):
    """Test deleting (or archiving) a service."""
    # Assuming the route is /services/<id>/delete
    url = f"/services/{service_data['id']}/delete"
    response = auth_client.post(url, follow_redirects=True)
    
    assert response.status_code == 200
    
    with auth_client.application.app_context():
        service = db.session.get(BusinessService, service_data['id'])
        # If your app deletes rows:
        assert service is None
        # OR if your app archives rows (soft delete):
        # assert service.is_archived is True