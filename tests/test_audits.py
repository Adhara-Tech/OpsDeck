"""
Tests for the Audits Defense Room functionality.
Covers snapshot isolation, SOA workflow, evidence management, and cascade deletion.
"""
import pytest
from src.models import db
from src.models.audits import ComplianceAudit, AuditControlItem, AuditControlLink
from src.models.security import Framework, FrameworkControl, ComplianceLink
from src.models.assets import Asset
from src.models.core import Attachment
from src.models.auth import User
from src.models.crm import Contact
from src.models.procurement import Supplier


def test_audit_snapshot_isolation(auth_client, app):
    """
    Test 1: Snapshot e Independencia
    Verifica que el snapshot es inmutable y no se ve afectado por cambios al framework.
    """
    with app.app_context():
        # Setup: Create Framework with Control
        fw = Framework(name='Isolation Test Framework', is_custom=True)
        control = FrameworkControl(
            control_id='ISO.1',
            name='Original Control Name',
            description='Original Description'
        )
        fw.framework_controls.append(control)
        db.session.add(fw)
        db.session.commit()
        
        fw_id = fw.id
        control_id = control.id
        
        # Create an Asset to link
        asset = Asset(name='Test Asset for Link', serial_number='LINK-001')
        db.session.add(asset)
        db.session.commit()
        asset_id = asset.id
        
        # Create a ComplianceLink on the Framework Control
        compliance_link = ComplianceLink(
            framework_control_id=control_id,
            linkable_type='Asset',
            linkable_id=asset_id,
            description='Original link to asset'
        )
        db.session.add(compliance_link)
        db.session.commit()
        
        # Create Internal Lead
        lead = User.query.first()
        if not lead:
            lead = User(name='Test Lead', email='lead@test.com', role='admin')
            lead.set_password('password')
            db.session.add(lead)
            db.session.commit()
        lead_id = lead.id

    # Action: Create Audit Snapshot with copy_links=True
    with app.app_context():
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw_id,
            name='Isolation Test Audit',
            auditor_contact_id=None,
            internal_lead_id=lead_id,
            copy_links=True
        )
        audit_id = audit.id
        
        # Verify: AuditControlItem created with correct text
        item = audit.audit_items.first()
        assert item is not None
        assert item.control_code == 'ISO.1'
        assert item.control_title == 'Original Control Name'
        assert item.control_description == 'Original Description'
        item_id = item.id
        
        # Verify: AuditControlLink was copied
        audit_link = item.linked_objects.first()
        assert audit_link is not None
        assert audit_link.linkable_type == 'Asset'
        assert audit_link.linkable_id == asset_id

    # FIRE TEST: Modify the original Framework Control
    with app.app_context():
        original_control = FrameworkControl.query.get(control_id)
        original_control.name = 'MODIFIED Control Name'
        original_control.description = 'MODIFIED Description'
        db.session.commit()

    # Assertion: AuditControlItem MUST retain the OLD text (Snapshot is immutable)
    with app.app_context():
        audit_item = AuditControlItem.query.get(item_id)
        assert audit_item.control_title == 'Original Control Name', \
            "Snapshot was mutated! Expected 'Original Control Name'"
        assert audit_item.control_description == 'Original Description', \
            "Snapshot was mutated! Expected 'Original Description'"
        
        # Also verify the framework actually changed (to prove the test is valid)
        original_control = FrameworkControl.query.get(control_id)
        assert original_control.name == 'MODIFIED Control Name'


def test_audit_defense_workflow(auth_client, app):
    """
    Test 2: SOA y Auditor Externo
    Verifica el workflow de defensa con auditor externo y campos SOA.
    """
    with app.app_context():
        # Setup: Create Framework
        fw = Framework(name='Defense Workflow Framework', is_custom=True)
        c1 = FrameworkControl(control_id='DEF.1', name='Applicable Control')
        c2 = FrameworkControl(control_id='DEF.2', name='Non-Applicable Control')
        fw.framework_controls.extend([c1, c2])
        db.session.add(fw)
        db.session.commit()
        fw_id = fw.id
        
        # Create Supplier and Contact (External Auditor)
        supplier = Supplier(name='Audit Firm LLC')
        db.session.add(supplier)
        db.session.commit()
        
        contact = Contact(
            name='John Auditor',
            email='john@auditfirm.com',
            phone='+1234567890',
            role='Lead Auditor',
            supplier_id=supplier.id
        )
        db.session.add(contact)
        db.session.commit()
        contact_id = contact.id
        
        # Create Internal Lead
        lead = User.query.first()
        lead_id = lead.id

    # Action: Create Audit with External Auditor
    with app.app_context():
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw_id,
            name='Defense Workflow Audit',
            auditor_contact_id=contact_id,
            internal_lead_id=lead_id,
            copy_links=False
        )
        audit_id = audit.id
        
        # Verify auditor is assigned
        assert audit.auditor is not None
        assert audit.auditor.name == 'John Auditor'
        assert audit.auditor.email == 'john@auditfirm.com'
        
        # Get the "Non-Applicable" item
        items = audit.audit_items.all()
        na_item = next((i for i in items if i.control_code == 'DEF.2'), None)
        assert na_item is not None
        na_item_id = na_item.id
        
        applicable_item = next((i for i in items if i.control_code == 'DEF.1'), None)
        applicable_item_id = applicable_item.id

    # Action: Mark one item as Non-Applicable with justification
    with app.app_context():
        item = AuditControlItem.query.get(na_item_id)
        item.is_applicable = False
        item.justification = 'Legacy system - control not relevant'
        item.status = 'Compliant'  # N/A items are typically marked compliant
        db.session.commit()

    # Verification: Changes persist and don't affect other items
    with app.app_context():
        na_item = AuditControlItem.query.get(na_item_id)
        assert na_item.is_applicable is False
        assert na_item.justification == 'Legacy system - control not relevant'
        
        # Other item should remain unchanged
        applicable_item = AuditControlItem.query.get(applicable_item_id)
        assert applicable_item.is_applicable is True
        assert applicable_item.justification is None


def test_audit_evidence_management(auth_client, app):
    """
    Test 3: Gestión de Evidencias
    Verifica que la evidencia está asociada a la Auditoría, NO al Framework base.
    """
    with app.app_context():
        # Setup: Create Framework with Control
        fw = Framework(name='Evidence Test Framework', is_custom=True)
        control = FrameworkControl(control_id='EVI.1', name='Evidence Control')
        fw.framework_controls.append(control)
        db.session.add(fw)
        db.session.commit()
        fw_id = fw.id
        control_id = control.id
        
        # Create Assets
        asset1 = Asset(name='Original Asset', serial_number='EVI-001')
        asset2 = Asset(name='New Audit Asset', serial_number='EVI-002')
        db.session.add_all([asset1, asset2])
        db.session.commit()
        asset1_id = asset1.id
        asset2_id = asset2.id
        
        # Create Internal Lead
        lead = User.query.first()
        lead_id = lead.id

    # Action: Create Audit
    with app.app_context():
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw_id,
            name='Evidence Test Audit',
            auditor_contact_id=None,
            internal_lead_id=lead_id,
            copy_links=False
        )
        audit_id = audit.id
        item = audit.audit_items.first()
        item_id = item.id

    # Action: Add Attachment to Audit Item
    with app.app_context():
        attachment = Attachment(
            filename='evidence_document.pdf',
            secure_filename='evidence_12345.pdf',
            linkable_type='AuditControlItem',
            linkable_id=item_id
        )
        db.session.add(attachment)
        db.session.commit()
        attachment_id = attachment.id

    # Action: Add new AuditControlLink to a different Asset
    with app.app_context():
        audit_link = AuditControlLink(
            audit_item_id=item_id,
            linkable_type='Asset',
            linkable_id=asset2_id,
            description='New evidence added during audit'
        )
        db.session.add(audit_link)
        db.session.commit()
        audit_link_id = audit_link.id

    # Verification: Evidence is associated with Audit, NOT Framework
    with app.app_context():
        # Check Attachment is on AuditControlItem
        item = AuditControlItem.query.get(item_id)
        assert item.attachments.count() == 1
        att = item.attachments.first()
        assert att.filename == 'evidence_document.pdf'
        assert att.linkable_type == 'AuditControlItem'
        
        # Check AuditControlLink exists
        assert item.linked_objects.count() == 1
        link = item.linked_objects.first()
        assert link.linkable_type == 'Asset'
        assert link.linkable_id == asset2_id
        
        # Verify: Original Framework Control has NO links (evidence is audit-only)
        original_control = FrameworkControl.query.get(control_id)
        assert original_control.compliance_links.count() == 0, \
            "Evidence was incorrectly added to Framework instead of Audit!"


def test_audit_deletion(auth_client, app):
    """
    Test 4: Borrado en Cascada
    Verifica que al borrar la auditoría se eliminan items, links y attachments,
    pero NO el Framework ni los Assets vinculados.
    """
    with app.app_context():
        # Setup: Create Framework
        fw = Framework(name='Deletion Test Framework', is_custom=True)
        control = FrameworkControl(control_id='DEL.1', name='Delete Test Control')
        fw.framework_controls.append(control)
        db.session.add(fw)
        db.session.commit()
        fw_id = fw.id
        control_id = control.id
        
        # Create Asset
        asset = Asset(name='Linked Asset', serial_number='DEL-001')
        db.session.add(asset)
        db.session.commit()
        asset_id = asset.id
        
        # Create Internal Lead
        lead = User.query.first()
        lead_id = lead.id

    # Action: Create Audit with Items, Links, and Attachments
    with app.app_context():
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw_id,
            name='Deletion Test Audit',
            auditor_contact_id=None,
            internal_lead_id=lead_id,
            copy_links=False
        )
        audit_id = audit.id
        item = audit.audit_items.first()
        item_id = item.id
        
        # Add Attachment
        attachment = Attachment(
            filename='to_be_deleted.pdf',
            secure_filename='delete_12345.pdf',
            linkable_type='AuditControlItem',
            linkable_id=item_id
        )
        db.session.add(attachment)
        db.session.commit()
        attachment_id = attachment.id
        
        # Add AuditControlLink
        audit_link = AuditControlLink(
            audit_item_id=item_id,
            linkable_type='Asset',
            linkable_id=asset_id,
            description='Link to be cascade deleted'
        )
        db.session.add(audit_link)
        db.session.commit()
        audit_link_id = audit_link.id

    # Pre-deletion verification
    with app.app_context():
        assert ComplianceAudit.query.get(audit_id) is not None
        assert AuditControlItem.query.get(item_id) is not None
        assert AuditControlLink.query.get(audit_link_id) is not None
        assert Attachment.query.get(attachment_id) is not None

    # Action: Delete the Audit
    with app.app_context():
        audit = ComplianceAudit.query.get(audit_id)
        db.session.delete(audit)
        db.session.commit()

    # Verification: Cascade deletion
    with app.app_context():
        # Audit and its children should be deleted
        assert ComplianceAudit.query.get(audit_id) is None, "Audit was not deleted"
        assert AuditControlItem.query.get(item_id) is None, "AuditControlItem was not cascade deleted"
        assert AuditControlLink.query.get(audit_link_id) is None, "AuditControlLink was not cascade deleted"
        # Note: Attachments cascade depends on model config - checking it was deleted with item
        assert Attachment.query.get(attachment_id) is None, "Attachment was not cascade deleted"
        
        # Framework and Asset should STILL EXIST
        fw = Framework.query.get(fw_id)
        assert fw is not None, "Framework was incorrectly deleted!"
        assert fw.name == 'Deletion Test Framework'
        
        control = FrameworkControl.query.get(control_id)
        assert control is not None, "FrameworkControl was incorrectly deleted!"
        
        asset = Asset.query.get(asset_id)
        assert asset is not None, "Asset was incorrectly deleted!"
        assert asset.name == 'Linked Asset'
