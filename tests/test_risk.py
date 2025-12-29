"""
Tests for Risk module - models and routes
Migrated from test_missing_coverage.py and test_zero_coverage_routes.py
"""
import pytest
from datetime import date, timedelta
from src.models import (
    Risk, RiskAffectedItem, RiskReference, Framework, FrameworkControl, 
    ComplianceLink, Asset, User, Documentation
)


# --- Model Tests ---

def test_risk_framework_compliance(init_database):
    """Test Risk, Framework, and ComplianceLink model creation."""
    db = init_database
    
    # 1. Framework & Control
    fw = Framework(name="NIST CSF", description="Cybersecurity Framework", is_active=True)
    db.session.add(fw)
    db.session.commit()
    assert repr(fw) == f"<Framework {fw.id}: NIST CSF (Activo)>"
    
    ctrl = FrameworkControl(framework_id=fw.id, control_id="ID.AM-1", name="Asset Management")
    db.session.add(ctrl)
    db.session.commit()
    assert repr(ctrl) == f"<FrameworkControl {ctrl.id}: ID.AM-1>"
    
    # 2. Risk Creation
    risk = Risk(
        risk_description="Data Loss",
        inherent_impact=5,
        inherent_likelihood=4,
        residual_impact=2,
        residual_likelihood=2,
        status="Identified"
    )
    db.session.add(risk)
    db.session.commit()
    
    assert risk.inherent_score == 20
    assert risk.residual_score == 4
    assert risk.criticality_level == 'Low'
    assert risk.risk_reduction_percentage == 80.0
    
    # 3. Risk Affected Item (Asset)
    asset = Asset(name="Database Server", status="In Use")
    db.session.add(asset)
    db.session.commit()
    
    affected = RiskAffectedItem(
        risk_id=risk.id,
        linkable_type="Asset",
        linkable_id=asset.id
    )
    db.session.add(affected)
    db.session.commit()
    
    assert affected.item == asset
    assert risk.affected_asset_ids == [asset.id]
    
    # 4. Risk Reference (Documentation)
    doc = Documentation(name="Risk Policy", external_link="http://policy.com")
    db.session.add(doc)
    db.session.commit()
    
    ref = RiskReference(
        risk_id=risk.id,
        linkable_type="Documentation",
        linkable_id=doc.id
    )
    db.session.add(ref)
    db.session.commit()
    
    assert ref.item == doc
    
    # 5. Compliance Link (Control -> Asset)
    link = ComplianceLink(
        framework_control_id=ctrl.id,
        linkable_type="Asset",
        linkable_id=asset.id,
        description="Asset is managed in CMDB"
    )
    db.session.add(link)
    db.session.commit()
    
    assert link.linked_object == asset


# --- Route Tests ---

def test_risk_routes(auth_client, init_database):
    """Test risk CRUD routes."""
    db = init_database
    user = User(name="Risk Owner", email="risk@test.com")
    db.session.add(user)
    db.session.commit()
    
    # 1. New Risk
    resp = auth_client.post('/risk/new', data={
        'risk_description': 'Data Breach',
        'owner_id': user.id,
        'status': 'Identified',
        'treatment_strategy': 'Mitigate',
        'inherent_impact': '5',
        'inherent_likelihood': '4',
        'residual_impact': '3',
        'residual_likelihood': '2',
        'category_ids': ['Data Security', 'Compliance']
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Risk has been successfully logged' in resp.data
    
    risk = Risk.query.filter_by(risk_description='Data Breach').first()
    assert risk is not None
    assert risk.inherent_score == 20
    
    # 2. Dashboard
    resp = auth_client.get('/risk/dashboard')
    assert resp.status_code == 200
    assert b'Data Breach' in resp.data
    
    # 3. Add Affected Item
    asset = Asset(name="Critical Server", status="In Use")
    db.session.add(asset)
    db.session.commit()
    
    resp = auth_client.post(f'/risk/{risk.id}/affected_items/add', data={
        'linkable_type': 'Asset',
        'linkable_id': asset.id
    }, follow_redirects=True)
    assert b'Affected item added successfully' in resp.data
    assert risk.affected_items.count() == 1
    
    # 4. API Endpoints
    resp = auth_client.get('/risk/api/items/Asset')
    assert resp.status_code == 200
    assert b'Critical Server' in resp.data
    
    # 5. Remove Item
    item = risk.affected_items.first()
    resp = auth_client.post(f'/risk/affected_items/{item.id}/delete', follow_redirects=True)
    assert b'Affected item removed' in resp.data
