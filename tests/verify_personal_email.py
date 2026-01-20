from datetime import date
from src import create_app, db
from src.models import User, OnboardingProcess, OnboardingPack, PackCommunication, EmailTemplate, ScheduledCommunication
from src.utils.communications_manager import trigger_workflow_communications

def test_personal_email_flow():
    app = create_app()
    with app.app_context():
        print("1. Verifying User Model...")
        # Check if personal_email column exists (implicit by setting it)
        try:
            user = User(name="Test User", email="test@example.com", personal_email="personal@gmail.com")
            user.set_password("password")
            db.session.add(user)
            db.session.commit()
            print("   SUCCESS: User created with personal_email.")
        except Exception as e:
            print(f"   FAILURE: {e}")
            return

        print("2. Verifying Onboarding Process & Comms...")
        # Create Template
        tpl = EmailTemplate(name="Test Tpl", subject="Hello", body_html="<p>Hi {{ user.name }}, email: {{ user.personal_email }}</p>")
        db.session.add(tpl)
        db.session.commit()

        # Create Pack with Personal Email rule
        pack = OnboardingPack(name="Test Pack")
        db.session.add(pack)
        db.session.commit()
        
        comm_rule = PackCommunication(pack_id=pack.id, template_id=tpl.id, offset_days=0, recipient_type='personal_email')
        db.session.add(comm_rule)
        db.session.commit()

        # Create Onboarding Process
        process = OnboardingProcess(
            new_hire_name="New Hire",
            personal_email="hire@personal.com",
            start_date=date.today(),
            pack_id=pack.id
        )
        db.session.add(process)
        db.session.commit()

        # Trigger Communications
        count = trigger_workflow_communications(process, pack)
        print(f"   Communications triggered: {count}")
        
        # Verify Scheduled Communication
        sc = ScheduledCommunication.query.filter_by(target_id=process.id, recipient_type='personal_email').first()
        if sc and sc.recipient_email == "hire@personal.com":
            print("   SUCCESS: ScheduledCommunication created for personal_email.")
        else:
            print(f"   FAILURE: ScheduledCommunication missing or incorrect email. Found: {sc}")

        print("3. Verifying User Creation Logic (Simulated)...")
        # Simulate create_user_account logic
        try:
            new_user = User(
                name=process.new_hire_name,
                email="corporate@example.com",
                role='user',
                personal_email=process.personal_email
            )
            db.session.add(new_user)
            db.session.commit()
            
            saved_user = User.query.get(new_user.id)
            if saved_user.personal_email == "hire@personal.com":
                 print("   SUCCESS: User created with correct personal_email.")
            else:
                 print(f"   FAILURE: User created but personal_email mismatch: {saved_user.personal_email}")
        except Exception as e:
            print(f"   FAILURE: {e}")

        # Cleanup
        db.session.delete(sc)
        db.session.delete(process)
        db.session.delete(comm_rule)
        db.session.delete(pack)
        db.session.delete(tpl)
        db.session.delete(new_user)
        db.session.delete(user)
        db.session.commit()

if __name__ == "__main__":
    test_personal_email_flow()
