import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src import create_app
from src.extensions import db
from src.models.auth import User, Group
from src.models.communications import Campaign

def reproduce_issues():
    app = create_app()
    with app.app_context():
        # Setup data
        print("Setting up test data...")
        user1 = User.query.filter_by(email='repro_user@example.com').first()
        if not user1:
            user1 = User(name='Repro User', email='repro_user@example.com')
            db.session.add(user1)
        
        group1 = Group.query.filter_by(name='Repro Group').first()
        if not group1:
            group1 = Group(name='Repro Group')
            db.session.add(group1)
            
        if user1 not in group1.users:
            group1.users.append(user1)
            
        db.session.commit()
        
        # Test Case 1: Duplicate Recipients
        print("\n--- Testing Duplicate Recipients ---")
        campaign = Campaign(title='Repro Campaign', subject='Subj', body_html='Body')
        # Add user explicitly AND via group
        campaign.target_users.append(user1)
        campaign.target_groups.append(group1)
        db.session.add(campaign)
        db.session.commit()
        
        audience = campaign.get_resolved_audience()
        print(f"Audience count: {len(audience)}")
        user_ids = [u.id for u in audience]
        print(f"User IDs: {user_ids}")
        
        if len(audience) != 1: 
             # Check if it's actually the same user object or different instances
             unique_ids = set(u.id for u in audience)
             if len(unique_ids) == 1 and len(audience) > 1:
                 print("FAIL: Duplicate objects for same user ID found (Python object identity issue).")
             elif len(unique_ids) > 1:
                 print("FAIL: Different users found.")
        else:
            print("PASS: Only 1 unique user found.")

        # Test Case 2: Zero Count in Draft
        print("\n--- Testing Zero Count in Draft ---")
        stats = campaign.get_communications_stats()
        print(f"Stats for Draft Campaign: {stats}")
        
        if stats['total'] == 0:
            print("FAIL: Total count is 0 for Draft campaign (Expected > 0 based on audience).")
        else:
            print(f"PASS: Total count is {stats['total']}.")
            
        # Clean up
        db.session.delete(campaign)
        # Keep user/group for manual insp if needed, or delete.
        db.session.commit()

if __name__ == '__main__':
    reproduce_issues()
