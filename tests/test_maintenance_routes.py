"""
Tests for src/routes/maintenance.py
Covers: list_logs, log_detail, new_log, edit_log
"""
import pytest
from datetime import date, timedelta
from src import db
from src.models import MaintenanceLog, Asset, Peripheral, User


@pytest.fixture
def maintenance_data(app):
    """Creates sample data for maintenance testing."""
    with app.app_context():
        # Create technician user
        technician = User(name="Tech Support", email="tech@test.com", role="user")
        technician.set_password("password")
        db.session.add(technician)
        db.session.commit()

        # Create asset
        asset = Asset(
            name="Server 01",
            status="In Use",
            brand="HP"
        )
        db.session.add(asset)
        db.session.commit()

        # Create peripheral
        peripheral = Peripheral(
            name="Network Switch",
            brand="Cisco"
        )
        db.session.add(peripheral)
        db.session.commit()

        # Create existing maintenance log
        log = MaintenanceLog(
            event_type="Repair",
            description="Replaced power supply",
            status="Completed",
            event_date=date.today() - timedelta(days=7),
            ticket_link="https://tickets.example.com/123",
            notes="Replaced with new PSU",
            assigned_to_id=technician.id,
            asset_id=asset.id
        )
        db.session.add(log)
        db.session.commit()

        yield {
            'log_id': log.id,
            'asset_id': asset.id,
            'peripheral_id': peripheral.id,
            'technician_id': technician.id
        }


# --- List Logs ---

def test_list_logs_loads(auth_client, maintenance_data):
    """Test that maintenance log list page loads successfully."""
    response = auth_client.get('/maintenance/')
    assert response.status_code == 200


def test_list_logs_shows_existing(auth_client, maintenance_data):
    """Test that list shows existing maintenance logs."""
    response = auth_client.get('/maintenance/')
    assert response.status_code == 200
    assert b'Repair' in response.data or b'Replaced power supply' in response.data


# --- Log Detail ---

def test_log_detail_loads(auth_client, maintenance_data):
    """Test that maintenance log detail page loads successfully."""
    response = auth_client.get(f'/maintenance/{maintenance_data["log_id"]}')
    assert response.status_code == 200


def test_log_detail_shows_info(auth_client, maintenance_data):
    """Test that log detail shows maintenance information."""
    response = auth_client.get(f'/maintenance/{maintenance_data["log_id"]}')
    assert response.status_code == 200
    assert b'Replaced power supply' in response.data


def test_log_detail_not_found(auth_client, maintenance_data):
    """Test 404 for non-existent maintenance log."""
    response = auth_client.get('/maintenance/99999')
    assert response.status_code == 404


# --- New Log ---

def test_new_log_form_loads(auth_client, maintenance_data):
    """Test that new maintenance log form loads successfully."""
    response = auth_client.get('/maintenance/new')
    assert response.status_code == 200


def test_new_log_form_with_preselected_asset(auth_client, maintenance_data):
    """Test form loads with preselected asset."""
    response = auth_client.get(f'/maintenance/new?asset_id={maintenance_data["asset_id"]}')
    assert response.status_code == 200


def test_new_log_form_with_preselected_peripheral(auth_client, maintenance_data):
    """Test form loads with preselected peripheral."""
    response = auth_client.get(f'/maintenance/new?peripheral_id={maintenance_data["peripheral_id"]}')
    assert response.status_code == 200


def test_new_log_form_with_event_type(auth_client, maintenance_data):
    """Test form loads with preselected event type."""
    response = auth_client.get('/maintenance/new?event_type=Upgrade')
    assert response.status_code == 200


def test_new_log_post_success(auth_client, maintenance_data, app):
    """Test creating new maintenance log via POST."""
    data = {
        'event_type': 'Inspection',
        'description': 'Annual hardware inspection',
        'status': 'Completed',
        'event_date': date.today().strftime('%Y-%m-%d'),
        'ticket_link': 'https://tickets.example.com/456',
        'notes': 'All hardware checked',
        'assigned_to_id': maintenance_data['technician_id'],
        'asset_id': maintenance_data['asset_id']
    }
    response = auth_client.post('/maintenance/new', data=data, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        log = MaintenanceLog.query.filter_by(description='Annual hardware inspection').first()
        assert log is not None
        assert log.event_type == 'Inspection'


def test_new_log_for_peripheral(auth_client, maintenance_data, app):
    """Test creating maintenance log for peripheral."""
    data = {
        'event_type': 'Repair',
        'description': 'Fixed network switch port',
        'status': 'In Progress',
        'event_date': date.today().strftime('%Y-%m-%d'),
        'peripheral_id': maintenance_data['peripheral_id']
    }
    response = auth_client.post('/maintenance/new', data=data, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        log = MaintenanceLog.query.filter_by(description='Fixed network switch port').first()
        assert log is not None
        assert log.peripheral_id == maintenance_data['peripheral_id']


def test_new_log_minimal_data(auth_client, maintenance_data, app):
    """Test creating log with minimal required data."""
    data = {
        'event_type': 'Other',
        'description': 'General maintenance',
        'status': 'Planned',
        'event_date': date.today().strftime('%Y-%m-%d')
    }
    response = auth_client.post('/maintenance/new', data=data, follow_redirects=True)
    assert response.status_code == 200


# --- Edit Log ---

def test_edit_log_form_loads(auth_client, maintenance_data):
    """Test that edit maintenance log form loads with existing data."""
    response = auth_client.get(f'/maintenance/{maintenance_data["log_id"]}/edit')
    assert response.status_code == 200
    assert b'Replaced power supply' in response.data


def test_edit_log_post_success(auth_client, maintenance_data, app):
    """Test updating maintenance log via POST."""
    data = {
        'event_type': 'Upgrade',
        'description': 'Upgraded to higher wattage PSU',
        'status': 'Completed',
        'event_date': date.today().strftime('%Y-%m-%d'),
        'ticket_link': 'https://tickets.example.com/789',
        'notes': 'Upgraded from 500W to 750W',
        'assigned_to_id': maintenance_data['technician_id'],
        'asset_id': maintenance_data['asset_id']
    }
    response = auth_client.post(
        f'/maintenance/{maintenance_data["log_id"]}/edit',
        data=data,
        follow_redirects=True
    )
    assert response.status_code == 200

    with app.app_context():
        log = db.session.get(MaintenanceLog, maintenance_data['log_id'])
        assert log.event_type == 'Upgrade'
        assert log.description == 'Upgraded to higher wattage PSU'


def test_edit_log_change_status(auth_client, maintenance_data, app):
    """Test changing log status."""
    data = {
        'event_type': 'Repair',
        'description': 'Replaced power supply',
        'status': 'Pending Parts',
        'event_date': date.today().strftime('%Y-%m-%d')
    }
    response = auth_client.post(
        f'/maintenance/{maintenance_data["log_id"]}/edit',
        data=data,
        follow_redirects=True
    )
    assert response.status_code == 200

    with app.app_context():
        log = db.session.get(MaintenanceLog, maintenance_data['log_id'])
        assert log.status == 'Pending Parts'


def test_edit_log_not_found(auth_client, maintenance_data):
    """Test 404 when editing non-existent log."""
    response = auth_client.get('/maintenance/99999/edit')
    assert response.status_code == 404
