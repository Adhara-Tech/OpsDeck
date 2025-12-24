import pytest
from src.models import SecurityActivity, ActivityExecution, ActivityRelatedObject, User, Group, Tag, Asset, Attachment
from src import db
from datetime import date

# --- Model Tests ---

def test_security_activity_model(app, init_database):
    """Test standard activity creation and relationships."""
    with app.app_context():
        # Setup
        user = User(name='Test User', email='test@user.com')
        db.session.add(user)
        tag = Tag(name='Security')
        db.session.add(tag)
        db.session.commit()

        activity = SecurityActivity(
            name='Access Review',
            description='Monthly review of user permissions',
            frequency='monthly',
            owner_id=user.id,
            owner_type='User'
        )
        activity.participants.append(user)
        activity.tags.append(tag)
        db.session.add(activity)
        db.session.commit()

        # Verify
        saved = SecurityActivity.query.filter_by(name='Access Review').first()
        assert saved is not None
        assert saved.owner.name == 'Test User'
        assert saved.participants[0].name == 'Test User'
        assert saved.tags[0].name == 'Security'
        assert saved.executions.count() == 0

def test_activity_execution_lifecycle(app, init_database):
    """Test recording an execution and its relationship."""
    with app.app_context():
        # Setup
        user = User(name='Executor', email='executor@test.com')
        db.session.add(user)
        activity = SecurityActivity(name='Audit', frequency='annual')
        db.session.add(activity)
        db.session.commit()

        execution = ActivityExecution(
            activity_id=activity.id,
            executor_id=user.id,
            execution_date=date.today(),
            status='success',
            outcome_notes='Everything looks good.'
        )
        db.session.add(execution)
        db.session.commit()

        # Verify
        assert activity.executions.count() == 1
        assert activity.executions.first().status == 'success'
        assert activity.executions.order_by(ActivityExecution.execution_date.desc()).first().id == execution.id

def test_polymorphic_owner_group(app, init_database):
    """Test group as activity owner."""
    with app.app_context():
        group = Group(name='Security Team')
        db.session.add(group)
        db.session.commit()

        activity = SecurityActivity(
            name='Vuln Scan',
            owner_id=group.id,
            owner_type='Group'
        )
        db.session.add(activity)
        db.session.commit()

        assert activity.owner.name == 'Security Team'
        assert isinstance(activity.owner, Group)

def test_activity_related_objects(app, init_database):
    """Test linking an asset to an activity."""
    with app.app_context():
        activity = SecurityActivity(name='Asset Review')
        db.session.add(activity)
        asset = Asset(name='Core Server', status='Active')
        db.session.add(asset)
        db.session.commit()

        link = ActivityRelatedObject(
            activity_id=activity.id,
            related_object_id=asset.id,
            related_object_type='Asset'
        )
        db.session.add(link)
        db.session.commit()

        assert activity.related_object_links[0].related_object.name == 'Core Server'
        assert isinstance(activity.related_object_links[0].related_object, Asset)

# --- Route Tests ---

def test_activity_list_route(auth_client):
    """Verify that the activity list page loads."""
    response = auth_client.get('/security/activities/')
    assert response.status_code == 200
    assert b'Security Activities' in response.data

def test_create_activity_route(auth_client, app):
    """Test creating a new activity via web route."""
    with app.app_context():
        user = User.query.first() # Admin from auth_client fixture
    
    data = {
        'name': 'New Pentest',
        'description': 'Annual pentest',
        'frequency': 'annual',
        'owner_type': 'User',
        'user_owner_id': user.id
    }
    response = auth_client.post('/security/activities/new', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Security Activity created successfully' in response.data
    assert b'New Pentest' in response.data

def test_activity_detail_route(auth_client, app):
    """Test the detail view of an activity."""
    with app.app_context():
        activity = SecurityActivity(name='Detailed Task')
        db.session.add(activity)
        db.session.commit()
        activity_id = activity.id

    response = auth_client.get(f'/security/activities/{activity_id}')
    assert response.status_code == 200
    assert b'Detailed Task' in response.data

def test_edit_activity_route(auth_client, app):
    """Test editing an existing activity."""
    with app.app_context():
        activity = SecurityActivity(name='Old Name')
        db.session.add(activity)
        db.session.commit()
        activity_id = activity.id

    data = {'name': 'Updated Name', 'frequency': 'monthly'}
    response = auth_client.post(f'/security/activities/{activity_id}/edit', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Security Activity updated successfully' in response.data
    assert b'Updated Name' in response.data

def test_record_execution_route(auth_client, app):
    """Test recording an execution via route."""
    with app.app_context():
        activity = SecurityActivity(name='Run Task')
        db.session.add(activity)
        db.session.commit()
        activity_id = activity.id
        user_id = User.query.first().id

    data = {
        'executor_id': user_id,
        'execution_date': '2023-12-01',
        'status': 'success',
        'outcome_notes': 'Task completed well.'
    }
    response = auth_client.post(f'/security/activities/{activity_id}/execute', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Execution recorded successfully' in response.data
    assert b'Task completed well.' in response.data

def test_link_object_route(auth_client, app):
    """Test linking an object via the AJAX-backed route."""
    with app.app_context():
        activity = SecurityActivity(name='Link Test')
        db.session.add(activity)
        asset = Asset(name='Target Asset', status='Active')
        db.session.add(asset)
        db.session.commit()
        activity_id = activity.id
        asset_id = asset.id

    data = {
        'object_type': 'Asset',
        'object_id': asset_id
    }
    response = auth_client.post(f'/security/activities/{activity_id}/link-object', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b'Asset linked successfully' in response.data
    
    with app.app_context():
        act = SecurityActivity.query.get(activity_id)
        assert len(act.related_object_links) == 1
        assert act.related_object_links[0].related_object_id == asset_id

def test_get_objects_by_type_json(auth_client, app):
    """Test the JSON endpoint for dynamic loading."""
    with app.app_context():
        asset = Asset(name='JSON Asset', status='Active')
        db.session.add(asset)
        db.session.commit()

    response = auth_client.get('/security/activities/get-objects-by-type?type=Asset')
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'objects' in json_data
    assert any(obj['name'] == 'JSON Asset' for obj in json_data['objects'])

def test_unlink_object_route(auth_client, app):
    """Test removing a link."""
    with app.app_context():
        activity = SecurityActivity(name='Unlink Test')
        db.session.add(activity)
        asset = Asset(name='Remove Me', status='Active')
        db.session.add(asset)
        db.session.commit()
        
        link = ActivityRelatedObject(activity_id=activity.id, related_object_id=asset.id, related_object_type='Asset')
        db.session.add(link)
        db.session.commit()
        activity_id = activity.id
        link_id = link.id

    response = auth_client.post(f'/security/activities/{activity_id}/unlink-object/{link_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b'Object unlinked successfully' in response.data
    
    with app.app_context():
        assert ActivityRelatedObject.query.get(link_id) is None

def test_delete_activity_route(auth_client, app):
    """Test deleting an activity delete its execution too."""
    with app.app_context():
        activity = SecurityActivity(name='Delete Me')
        db.session.add(activity)
        db.session.commit()
        activity_id = activity.id
        
        execution = ActivityExecution(activity_id=activity_id, executor_id=User.query.first().id, status='in_progress', execution_date=date.today())
        db.session.add(execution)
        db.session.commit()
        execution_id = execution.id

    response = auth_client.post(f'/security/activities/{activity_id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert b'has been deleted' in response.data
    
    with app.app_context():
        assert SecurityActivity.query.get(activity_id) is None
        assert ActivityExecution.query.get(execution_id) is None
