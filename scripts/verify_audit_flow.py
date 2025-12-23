import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Starting script...")
from src import create_app
from src.extensions import db
from src.models.audits import ComplianceAudit, AuditControlItem, AuditControlLink
from src.models.security import Framework, FrameworkControl, ComplianceLink
from src.models.assets import Asset
from src.models.crm import Contact
from src.models.auth import User

def verify_audit_flow():
    app = create_app()
    with app.app_context():
        print("1. Setup Test Data...")
        # Create dependencies
        user = User.query.first()
        if not user:
            user = User(name="Test User", email="test@example.com")
            db.session.add(user)
        
        contact = Contact.query.first()
        if not contact:
            contact = Contact(first_name="Auditor", last_name="External", email="auditor@example.com")
            db.session.add(contact)
            
        asset = Asset.query.first()
        if not asset:
            asset = Asset(name="Test Asset", asset_tag="TAG-001", status="Active")
            db.session.add(asset)
            
        db.session.commit()

        # Create Framework & Control
        fw = Framework(name="Test Framework v1", description="Test", is_active=True)
        db.session.add(fw)
        db.session.flush()
        
        ctrl = FrameworkControl(framework_id=fw.id, control_id="T.1.1", name="Test Control", description="Must have asset")
        db.session.add(ctrl)
        db.session.flush()
        
        # Link Asset to Control (ComplianceLink)
        link = ComplianceLink(
            framework_control_id=ctrl.id,
            linkable_type='Asset',
            linkable_id=asset.id,
            description="Evidence for control"
        )
        db.session.add(link)
        db.session.commit()
        
        print(f"   Framework {fw.id} created with Control {ctrl.id} linked to Asset {asset.id}")

        print("\n2. Execute create_snapshot (copy_links=True)...")
        audit = ComplianceAudit.create_snapshot(
            framework_id=fw.id,
            name="Test Audit 2025",
            auditor_contact_id=contact.id,
            internal_lead_id=user.id,
            copy_links=True
        )
        
        print(f"   Audit {audit.id} created.")

        print("\n3. Verifications...")
        
        # Verify Audit
        assert audit.name == "Test Audit 2025"
        assert audit.status == "Planned"
        assert audit.auditor_id == contact.id
        assert audit.internal_lead_id == user.id
        print("   [PASS] Audit basic fields")
        
        # Verify Items
        items = audit.audit_items.all()
        assert len(items) == 1
        item = items[0]
        assert item.control_code == "T.1.1"
        assert item.control_title == "Test Control"
        assert item.status == "Compliant"
        print("   [PASS] Audit Item snapshot")
        
        # Verify Links
        links = item.linked_objects.all()
        assert len(links) == 1
        audit_link = links[0]
        assert audit_link.linkable_type == 'Asset'
        assert audit_link.linkable_id == asset.id
        assert audit_link.linked_object.id == asset.id
        print("   [PASS] Audit Link snapshot")
        
        # Verify Participants
        audit.participants.append(user)
        db.session.commit()
        assert user in audit.participants
        print("   [PASS] Participants relationship")

        print("\nSUCCESS: Audit Flow Verified!")

if __name__ == "__main__":
    verify_audit_flow()
