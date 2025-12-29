"""
Tests for License routes
Migrated from test_zero_coverage_routes.py
"""
import pytest
from src.models import License, User


def test_license_routes(auth_client, init_database):
    """Test license CRUD routes."""
    db = init_database
    
    # Create dependencies
    user = User(name="License User", email="lic@test.com")
    db.session.add(user)
    db.session.commit()
    
    # 1. New License (Standalone)
    resp = auth_client.post('/licenses/new', data={
        'name': 'Test License',
        'license_key': 'KEY-123',
        'cost': '100',
        'currency': 'USD',
        'user_id': user.id,
        'link_type': 'subscription'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'License added successfully' in resp.data
    
    lic = License.query.filter_by(name='Test License').first()
    assert lic is not None
    
    # Retry with correct type to test cost
    resp = auth_client.post('/licenses/new', data={
        'name': 'Paid License',
        'license_key': 'KEY-456',
        'cost': '100',
        'currency': 'USD',
        'user_id': user.id,
        'link_type': 'software'
    }, follow_redirects=True)
    
    lic2 = License.query.filter_by(name='Paid License').first()
    assert lic2.cost == 100.0
    
    # 2. Edit License
    resp = auth_client.post(f'/licenses/{lic.id}/edit', data={
        'name': 'Updated License',
        'cost': '150',
        'currency': 'EUR',
        'link_type': 'none'
    }, follow_redirects=True)
    assert b'License updated successfully' in resp.data
    
    # 3. Archive/Restore
    resp = auth_client.post(f'/licenses/{lic.id}/archive', follow_redirects=True)
    assert b'has been archived' in resp.data
    
    resp = auth_client.get('/licenses/archived')
    assert b'Updated License' in resp.data
    
    resp = auth_client.post(f'/licenses/{lic.id}/restore', follow_redirects=True)
    assert b'has been restored' in resp.data
