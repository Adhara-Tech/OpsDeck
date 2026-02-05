"""
Extended tests for Audits module.
Tests for features not covered in test_audits.py:
- Lock/unlock functionality
- PDF export
- Participant management  
- Audit and item-level attachments
- API status update endpoint
- Audit header update
"""
import io
import json
from src.models import db
from src.models.audits import ComplianceAudit, AuditControlItem
from src.models.security import Framework, FrameworkControl
from src.models.auth import User
from src.utils.timezone_helper import now


def test_lock_audit(auth_client, app):
    """Test locking an audit to prevent modifications."""
    with app.app_context():
        # Setup: Create framework and audit
        fw = Framework(name='Lock Test Framework', is_custom=True)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Lock Test Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        audit_id = audit.id
        
        # Verify it starts unlocked
        assert audit.is_locked is False
    
    # Action: Lock the audit
    response = auth_client.post(f'/security/audits/{audit_id}/lock', follow_redirects=True)
    
    # Verify
    assert response.status_code == 200
    assert b'Audit has been locked' in response.data
    
    with app.app_context():
        audit = db.session.get(ComplianceAudit, audit_id)
        assert audit.is_locked is True
        assert audit.locked_at is not None


def test_unlock_audit(auth_client, app):
    """Test unlocking a locked audit."""
    with app.app_context():
        # Setup: Create and lock an audit
        fw = Framework(name='Unlock Test Framework', is_custom=True)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Unlock Test Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        audit.locked_at = now()
        db.session.commit()
        audit_id = audit.id
        
        # Verify it's locked
        assert audit.is_locked is True
    
    # Action: Unlock the audit
    response = auth_client.post(f'/security/audits/{audit_id}/unlock', follow_redirects=True)
    
    # Verify
    assert response.status_code == 200
    assert b'Audit has been unlocked' in response.data
    
    with app.app_context():
        audit = db.session.get(ComplianceAudit, audit_id)
        assert audit.is_locked is False
        assert audit.locked_at is None


def test_locked_audit_prevents_modification(auth_client, app):
    """Verify that locked audits cannot be modified via update_audit_items."""
    with app.app_context():
        # Setup: Create and lock an audit
        fw = Framework(name='Protection Test Framework', is_custom=True)
        control = FrameworkControl(control_id='PROT.1', name='Test Control')
        fw.framework_controls.append(control)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Protection Test Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        audit.locked_at = now()
        db.session.commit()
        audit_id = audit.id
        item = audit.audit_items.first()
        item_id = item.id
    
    # Action: Try to update audit items while locked
    data = {
        f'item_{item_id}_status': 'Compliant',
        f'item_{item_id}_internal_comments': 'Attempted update'
    }
    response = auth_client.post(
        f'/security/audits/{audit_id}/update',
        data=data,
        follow_redirects=True
    )
    
    # Verify: Update was blocked
    assert response.status_code == 200
    assert b'locked' in response.data.lower()
    
    # Verify item wasn't changed
    with app.app_context():
        item = db.session.get(AuditControlItem, item_id)
        assert item.status == 'Pending'  # Should still be default


def test_export_pdf(auth_client, app):
    """Test PDF export functionality."""
    with app.app_context():
        # Setup: Create audit
        fw = Framework(name='Export PDF Framework', is_custom=True)
        control = FrameworkControl(
            control_id='EXP.1',
            name='Export Test Control',
            description='Control for PDF export testing'
        )
        fw.framework_controls.append(control)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='PDF Export Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        audit_id = audit.id
    
    # Action: Request PDF export
    response = auth_client.get(f'/security/audits/{audit_id}/export')
    
    # Verify
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    assert response.headers.get('Content-Disposition')
    assert 'defense_pack' in response.headers.get('Content-Disposition')


def test_add_participant(auth_client, app):
    """Test adding a participant to an audit."""
    with app.app_context():
        # Setup: Create audit and additional user
        fw = Framework(name='Participant Framework', is_custom=True)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Participant Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        
        participant = User(name='Team Member', email='member@test.com', role='user')
        participant.set_password('password')
        db.session.add(participant)
        db.session.commit()
        
        audit_id = audit.id
        participant_id = participant.id
        
        # Verify no participants initially
        assert len(audit.participants) == 0
    
    # Action: Add participant
    data = {'user_id': participant_id}
    response = auth_client.post(
        f'/security/audits/{audit_id}/participants/add',
        data=data,
        follow_redirects=True
    )
    
    # Verify
    assert response.status_code == 200
    assert b'added to the team' in response.data
    
    with app.app_context():
        audit = db.session.get(ComplianceAudit, audit_id)
        assert len(audit.participants) == 1
        assert audit.participants[0].id == participant_id


def test_remove_participant(auth_client, app):
    """Test removing a participant from an audit."""
    with app.app_context():
        # Setup: Create audit with participant
        fw = Framework(name='Remove Participant Framework', is_custom=True)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Remove Participant Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        
        participant = User(name='To Remove', email='remove@test.com', role='user')
        participant.set_password('password')
        db.session.add(participant)
        db.session.commit()
        
        audit.participants.append(participant)
        db.session.commit()
        
        audit_id = audit.id
        participant_id = participant.id
        
        # Verify participant exists
        assert len(audit.participants) == 1
    
    # Action: Remove participant
    response = auth_client.post(
        f'/security/audits/{audit_id}/participants/{participant_id}/remove',
        follow_redirects=True
    )
    
    # Verify
    assert response.status_code == 200
    assert b'removed from the team' in response.data
    
    with app.app_context():
        audit = db.session.get(ComplianceAudit, audit_id)
        assert len(audit.participants) == 0


def test_participant_lock_check(auth_client, app):
    """Verify participants cannot be added/removed when audit is locked."""
    with app.app_context():
        # Setup: Create locked audit
        fw = Framework(name='Locked Participant Framework', is_custom=True)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Locked Participant Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        audit.locked_at = now()
        db.session.commit()
        
        participant = User(name='Locked Test User', email='locked@test.com', role='user')
        participant.set_password('password')
        db.session.add(participant)
        db.session.commit()
        
        audit_id = audit.id
        participant_id = participant.id
    
    # Action: Try to add participant to locked audit
    data = {'user_id': participant_id}
    response = auth_client.post(
        f'/security/audits/{audit_id}/participants/add',
        data=data,
        follow_redirects=True
    )
    
    # Verify: Addition was blocked
    assert response.status_code == 200
    assert b'locked' in response.data.lower()
    
    with app.app_context():
        audit = db.session.get(ComplianceAudit, audit_id)
        assert len(audit.participants) == 0


def test_upload_audit_attachment(auth_client, app):
    """Test uploading a global audit-level attachment."""
    with app.app_context():
        # Setup: Create audit
        fw = Framework(name='Audit Attachment Framework', is_custom=True)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Attachment Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        audit_id = audit.id
    
    # Action: Upload file
    file_data = io.BytesIO(b"Audit documentation content")
    data = {'file': (file_data, 'audit_doc.pdf')}
    
    response = auth_client.post(
        f'/security/audits/{audit_id}/attachments/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    
    # Verify
    assert response.status_code == 200
    assert b'uploaded successfully' in response.data
    
    with app.app_context():
        audit = db.session.get(ComplianceAudit, audit_id)
        assert audit.attachments.count() > 0
        attachment = audit.attachments.first()
        assert attachment.linkable_type == 'ComplianceAudit'
        assert attachment.linkable_id == audit_id


def test_upload_item_attachment(auth_client, app):
    """Test uploading evidence to a specific audit control item."""
    with app.app_context():
        # Setup: Create audit with item
        fw = Framework(name='Item Attachment Framework', is_custom=True)
        control = FrameworkControl(control_id='ATT.1', name='Test Control')
        fw.framework_controls.append(control)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Item Attachment Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        audit_id = audit.id
        item = audit.audit_items.first()
        item_id = item.id
    
    # Action: Upload evidence file
    file_data = io.BytesIO(b"Evidence for control compliance")
    data = {'file': (file_data, 'evidence.pdf')}
    
    response = auth_client.post(
        f'/security/audits/{audit_id}/item/{item_id}/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    
    # Verify
    assert response.status_code == 200
    assert b'Evidence uploaded' in response.data or b'uploaded' in response.data
    
    with app.app_context():
        item = db.session.get(AuditControlItem, item_id)
        assert item.attachments.count() > 0
        attachment = item.attachments.first()
        assert attachment.linkable_type == 'AuditControlItem'
        assert attachment.linkable_id == item_id


def test_attachment_lock_check(auth_client, app):
    """Verify attachments cannot be uploaded when audit is locked."""
    with app.app_context():
        # Setup: Create locked audit
        fw = Framework(name='Locked Attachment Framework', is_custom=True)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Locked Attachment Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        audit.locked_at = now()
        db.session.commit()
        audit_id = audit.id
    
    # Action: Try to upload file to locked audit
    file_data = io.BytesIO(b"Should not upload")
    data = {'file': (file_data, 'blocked.pdf')}
    
    response = auth_client.post(
        f'/security/audits/{audit_id}/attachments/upload',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    
    # Verify: Upload was blocked
    assert response.status_code == 200
    assert b'locked' in response.data.lower()
    
    with app.app_context():
        audit = db.session.get(ComplianceAudit, audit_id)
        assert audit.attachments.count() == 0


def test_api_update_control_status(auth_client, app):
    """Test the AJAX API endpoint for updating control status."""
    with app.app_context():
        # Setup: Create audit with control item
        fw = Framework(name='API Test Framework', is_custom=True)
        control = FrameworkControl(control_id='API.1', name='API Control')
        fw.framework_controls.append(control)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='API Test Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        item = audit.audit_items.first()
        item_id = item.id
        
        # Verify initial status
        assert item.status == 'Pending'
    
    # Action: Update status via API
    response = auth_client.post(
        f'/security/audits/api/control/{item_id}/status',
        data=json.dumps({'status': 'Compliant'}),
        content_type='application/json'
    )
    
    # Verify
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['success'] is True
    assert json_data['new_status'] == 'Compliant'
    
    with app.app_context():
        item = db.session.get(AuditControlItem, item_id)
        assert item.status == 'Compliant'


def test_api_status_lock_check(auth_client, app):
    """Verify API endpoint respects audit lock status."""
    with app.app_context():
        # Setup: Create locked audit
        fw = Framework(name='API Lock Framework', is_custom=True)
        control = FrameworkControl(control_id='LOCK.1', name='Lock Control')
        fw.framework_controls.append(control)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='API Lock Audit',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        audit.locked_at = now()
        db.session.commit()
        
        item = audit.audit_items.first()
        item_id = item.id
    
    # Action: Try to update status via API while locked
    response = auth_client.post(
        f'/security/audits/api/control/{item_id}/status',
        data=json.dumps({'status': 'Compliant'}),
        content_type='application/json'
    )
    
    # Verify: Request was rejected
    assert response.status_code == 403
    json_data = response.get_json()
    assert json_data['success'] is False
    assert 'locked' in json_data['error'].lower()


def test_update_audit_header(auth_client, app):
    """Test updating audit header metadata."""
    with app.app_context():
        # Setup: Create audit
        fw = Framework(name='Header Update Framework', is_custom=True)
        db.session.add(fw)
        db.session.commit()
        
        lead = User.query.first()
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Original Name',
            auditor_contact_id=None,
            internal_lead_id=lead.id,
            copy_links=False
        )
        audit_id = audit.id
    
    # Action: Update audit header
    data = {
        'status': 'In Progress',
        'start_date': '2024-01-01',
        'end_date': '2024-12-31'
    }
    response = auth_client.post(
        f'/security/audits/{audit_id}/header',
        data=data,
        follow_redirects=True
    )
    
    # Verify
    assert response.status_code == 200
    assert b'updated' in response.data.lower()
    
    with app.app_context():
        audit = db.session.get(ComplianceAudit, audit_id)
        assert audit.status == 'In Progress'
