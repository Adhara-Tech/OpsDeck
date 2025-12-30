"""
Tests for CostCenter routes
Migrated from test_zero_coverage_routes.py
"""
from src.models import CostCenter


def test_cost_center_routes(auth_client, init_database):
    """Test cost center CRUD routes."""
    db = init_database
    
    # 1. New Cost Center
    resp = auth_client.post('/cost-centers/new', data={
        'code': 'CC-TEST',
        'name': 'Test Center',
        'description': 'Description'
    }, follow_redirects=True)
    assert resp.status_code == 200
    
    cc = CostCenter.query.filter_by(code='CC-TEST').first()
    assert cc is not None
    assert cc.name == 'Test Center'
    
    # 2. List
    resp = auth_client.get('/cost-centers/')
    assert resp.status_code == 200
    assert b'Test Center' in resp.data
    
    # 3. Edit
    resp = auth_client.post(f'/cost-centers/{cc.id}/edit', data={
        'code': 'CC-TEST-UPDATED',
        'name': 'Test Center Updated',
        'description': 'Updated Desc'
    }, follow_redirects=True)
    
    cc = db.session.get(CostCenter, cc.id)
    assert cc.name == 'Test Center Updated'
    
    # 4. Detail
    resp = auth_client.get(f'/cost-centers/{cc.id}')
    assert resp.status_code == 200
    assert b'Test Center Updated' in resp.data
    
    # 5. Delete
    resp = auth_client.post(f'/cost-centers/{cc.id}/delete', follow_redirects=True)
    assert CostCenter.query.count() == 0
