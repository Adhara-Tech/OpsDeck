from datetime import date
from src.models import db
from src.models.audits import ComplianceAudit, AuditControlLink
from src.models.security import Framework, FrameworkControl
from src.models.assets import Asset
from src.models.auth import User
from src.models.crm import Contact
from src.models.procurement import Supplier

def test_audit_cloning_logic(auth_client, app):
    """
    Test the Smart Audit Cloning (Rollover) logic.
    """
    with app.app_context():
        # --- SETUP ---
        # 1. Create Framework & Controls
        fw = Framework(name='ISO 27001:2022', is_custom=True)
        c1 = FrameworkControl(control_id='5.1', name='Policies for InfoSec')
        c2 = FrameworkControl(control_id='5.2', name='InfoSec Roles')
        fw.framework_controls.extend([c1, c2])
        db.session.add(fw)
        db.session.flush() # Flush to get ID
        
        # 2. Create Users/Contacts
        old_owner = User(name='Old Lead', email='old@test.com', role='admin')
        old_owner.set_password('pass')
        new_owner = User(name='New Lead', email='new@test.com', role='admin')
        new_owner.set_password('pass')
        
        # Create Supplier for Auditor
        supplier = Supplier(name='Audit Boss LLC')
        db.session.add(supplier)
        db.session.flush()

        auditor = Contact(name='Ext Auditor', email='audit@ext.com', supplier_id=supplier.id)
        db.session.add_all([old_owner, new_owner, auditor])
        db.session.commit()
        
        # Store IDs for later use to avoid DetachedInstanceError
        new_owner_id = new_owner.id
        
        # 3. Create Source Audit
        source_audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name='Audit 2024',
            auditor_contact_id=auditor.id,
            internal_lead_id=old_owner.id
        )
        
        # 4. Set up Source Audit State
        # Item 1: Applicable, Compliant, Evidence Links
        item1 = source_audit.audit_items.filter_by(control_code='5.1').first()
        item1.is_applicable = True
        item1.status = 'Compliant'
        item1.justification = 'Policy exists'
        item1.internal_comments = 'Reviewed by bob'
        
        # Link an asset
        asset = Asset(name='Security Policy', serial_number='DOC-001')
        db.session.add(asset)
        db.session.commit()
        asset_id = asset.id
        
        link = AuditControlLink(
            audit_item_id=item1.id,
            linkable_type='Asset',
            linkable_id=asset.id,
            description='Evidence 2024'
        )
        db.session.add(link)
        
        # Item 2: Not Applicable
        item2 = source_audit.audit_items.filter_by(control_code='5.2').first()
        item2.is_applicable = False
        item2.status = 'Not Applicable'
        item2.justification = 'Too small'
        
        db.session.commit()
        source_id = source_audit.id
        
    # --- ACTION: CLONE ---
    target_date = date(2025, 12, 31)
    
    with app.app_context():
        # Call the clone method
        new_audit = ComplianceAudit.clone(
            source_id=source_id,
            new_owner_id=new_owner_id,
            target_date=target_date
        )
        new_audit_id = new_audit.id

    # --- VERIFICATION ---
    with app.app_context():
        new_audit = db.session.get(ComplianceAudit, new_audit_id)
        source_audit = db.session.get(ComplianceAudit, source_id)
        
        # 1. Metadata Checks
        assert new_audit.name == 'Renewal 2025: Audit 2024'
        assert new_audit.internal_lead_id == new_owner_id
        assert new_audit.auditor_id is None, "Auditor should be reset"
        assert new_audit.start_date is None
        assert new_audit.end_date == target_date
        assert new_audit.status == 'Planned'
        
        # 2. Control Logic
        # Item 1 (Applicable)
        new_item1 = new_audit.audit_items.filter_by(control_code='5.1').first()
        assert new_item1.is_applicable is True
        assert new_item1.status == 'Pending', "Status should reset to Pending"
        assert new_item1.justification == 'Policy exists', "Justification should be preserved"
        assert new_item1.internal_comments == 'Reviewed by bob', "Comments should be preserved"
        
        # Verify Evidence Link Copy
        assert new_item1.linked_objects.count() == 1
        new_link = new_item1.linked_objects.first()
        assert new_link.linkable_type == 'Asset'
        assert new_link.linkable_id == asset_id
        assert new_link.description == 'Evidence 2024'
        
        # Item 2 (Not Applicable)
        new_item2 = new_audit.audit_items.filter_by(control_code='5.2').first()
        assert new_item2.is_applicable is False
        assert new_item2.status == 'Not Applicable', "Status should remain Not Applicable"
        assert new_item2.justification == 'Too small'

        # 3. Independence Check
        # Modify new audit item
        new_item1.justification = 'Changed in 2025'
        db.session.commit()
        
        # Old item should be unchanged
        old_item1 = source_audit.audit_items.filter_by(control_code='5.1').first()
        assert old_item1.justification == 'Policy exists'
