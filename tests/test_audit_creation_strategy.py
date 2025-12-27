from datetime import date
from src.models import db
from src.models.audits import ComplianceAudit
from src.models.security import Framework, FrameworkControl
from src.models.auth import User

def test_audit_creation_strategies_route(auth_client, app):
    """
    Test the Audit Creation Route strategies (Scratch vs Clone).
    """
    with app.app_context():
        # --- SETUP ---
        # 1. Create Framework & Controls
        fw = Framework(name='Strategy Test FW', is_custom=True)
        c1 = FrameworkControl(control_id='S.1', name='Control 1')
        fw.framework_controls.append(c1)
        db.session.add(fw)
        db.session.flush() # Flush to get ID
        fw_id = fw.id
        
        # 2. Create User
        lead = User(name='Lead Strategy', email='strat@test.com', role='admin')
        lead.set_password('pass')
        db.session.add(lead)
        db.session.commit()
        lead_id = lead.id

    with app.app_context():
        # client = auth_client(app) -- Incorrect
        client = auth_client
        response = client.post('/security/audits/new', data={
            'creation_strategy': 'scratch',
            'name': 'Scratch Audit',
            'framework_id': fw_id,
            'internal_lead_id': lead_id,
            'copy_links': 'on'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Audit created successfully' in response.data
        
        # Verify DB
        audit = ComplianceAudit.query.filter_by(name='Scratch Audit').first()
        assert audit is not None
        assert audit.framework_id == fw_id
        assert audit.audit_items.count() == 1
        assert audit.audit_items.first().status == 'Pending'
        
        # Save ID for cloning
        source_audit_id = audit.id

    # --- TEST 2: CLONE STRATEGY ---
    with app.app_context():
        client = auth_client
        response = client.post('/security/audits/new', data={
            'creation_strategy': 'clone',
            'source_audit_id': source_audit_id,
            'internal_lead_id': lead_id,
            'target_date': '2025-12-31'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert b'Audit created successfully' in response.data
        
        # Verify DB
        cloned_audit = ComplianceAudit.query.filter(ComplianceAudit.name.like('Renewal%Scratch Audit')).first()
        assert cloned_audit is not None
        assert cloned_audit.id != source_audit_id
        assert cloned_audit.end_date == date(2025, 12, 31)
        assert cloned_audit.audit_items.first().status == 'Pending'
