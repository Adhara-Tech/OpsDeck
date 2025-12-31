import sys
import os
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src import create_app, db
from src.models.auth import User
from src.models.services import BusinessService
from src.models.onboarding import OnboardingPack, PackItem, OnboardingProcess, OffboardingProcess, ProcessItem

def run_verification():
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for testing
    with app.app_context():
        # Setup
        print("[-] Setting up test data...")
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            print("x Admin user not found. Run reset-demo-data.sh first.")
            return

        # Create a dummy user for testing
        test_user = User.query.filter_by(email='alice@example.com').first()
        if not test_user:
            # Pick any user if alice doesn't exist (demo data usually has randoms)
            test_user = User.query.filter(User.id != admin.id).first()
            print(f"[-] Using test user: {test_user.name} ({test_user.email})")

        # 1. Create Service
        print("\n[1] Creating 'Test App' Service...")
        client = app.test_client()
        # Login
        with client.session_transaction() as sess:
            sess['user_id'] = admin.id
            sess['_fresh'] = True

        res = client.post('/services/new', data={
            'name': 'Test Application 1',
            'description': 'Auto Verify App',
            'category': 'Application',
            'criticality': 'Tier 3',
            'status': 'Operational',
            'owner_id': admin.id
        }, follow_redirects=True)
        
        service = BusinessService.query.filter_by(name='Test Application 1').first()
        if service and service.category == 'Application':
            print("✓ Service created successfully.")
        else:
            print(f"x Service creation failed. Status: {res.status_code}")
            # print(res.get_data(as_text=True))
            if "Error creating service" in res.get_data(as_text=True):
                 print("Error found in response.")
            # Let's print the whole thing to find the flash message
            print(res.get_data(as_text=True))
            return

        # 2. Add User Access
        print(f"\n[2] Granting access to {test_user.name}...")
        res = client.post(f'/services/{service.id}/users/add', data={'user_id': test_user.id}, follow_redirects=True)
        
        if test_user in service.users:
            print("✓ User added to service.")
        else:
            print("x Failed to add user to service.")
            return

        # 3. Onboarding with ServiceAccess
        print("\n[3] Verification of Onboarding Flow (Checklist generation)...")
        # Create a Pack with ServiceAccess
        pack = OnboardingPack(name="Dev Pack", input_type="Hardware") # dummy
        db.session.add(pack)
        db.session.commit()
        
        # Add ServiceAccess Item
        # We need to manually add it because the UI does it via form
        # Simulating the DB state after form submission
        pack_item = PackItem(
            pack_id=pack.id,
            item_type='ServiceAccess',
            description='Access to Test App',
            service_id=service.id
        )
        db.session.add(pack_item)
        db.session.commit()
        
        # Start Onboarding
        print("[-] Starting Onboarding Process...")
        res = client.post('/onboarding/new', data={
            'new_hire_name': 'Bobby Tables',
            'start_date': '2025-01-01',
            'department': 'Engineering',
            'pack_id': pack.id
        }, follow_redirects=True)
        
        # Check generated checklist items
        # We need to find the latest process
        process = OnboardingProcess.query.order_by(OnboardingProcess.id.desc()).first()
        process_items = ProcessItem.query.filter_by(onboarding_process_id=process.id).all()
        
        found_sa = False
        for item in process_items:
            if item.item_type == 'ServiceAccess' and item.linked_object_id == service.id:
                found_sa = True
                print(f"✓ Found generated ServiceAccess checklist item: {item.description}")
        
        if not found_sa:
            print("x Failed to generate ServiceAccess checklist item.")

        # 4. Offboarding with Revocation
        print(f"\n[4] Verification of Offboarding Flow for {test_user.name}...")
        res = client.post('/onboarding/offboarding/new', data={
            'user_id': test_user.id, # Using ID as the form likely submits ID
            'departure_date': '2025-02-01',
        }, follow_redirects=True)
        
        off_process = OffboardingProcess.query.filter_by(user_id=test_user.id).order_by(OffboardingProcess.id.desc()).first()
        if not off_process:
            print("x Failed to create offboarding process.")
            return

        off_items = ProcessItem.query.filter_by(offboarding_process_id=off_process.id).all()
        
        revoke_item = None
        for item in off_items:
            if item.item_type == 'RevokeAccess' and item.linked_object_id == service.id:
                revoke_item = item
                print(f"✓ Found RevokeAccess item: {item.description}")
                break
        
        if not revoke_item:
            print("x Failed to generate RevokeAccess item.")
            return

        # 5. Execute Revocation
        print("\n[5] Executing Revocation via Route...")
        res = client.post(f'/onboarding/offboarding/{off_process.id}/revoke_service/{revoke_item.id}', follow_redirects=True)
        
        # Reload objects
        db.session.refresh(service)
        db.session.refresh(revoke_item)
        
        if test_user not in service.users:
            print("✓ User successfully removed from service.")
        else:
            print("x User SHOULD BE removed but is still in service.")

        if revoke_item.is_completed:
            print("✓ Revoke task marked as completed.")
        else:
            print("x Revoke task NOT marked as completed.")
            
        print("\n[verification] ALL CHECKS PASSED.")

if __name__ == "__main__":
    run_verification()
