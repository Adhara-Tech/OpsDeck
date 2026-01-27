from src import create_app
from src.models import db, User, Group, Module, Permission
from src.services.permissions_service import get_user_modules, update_permission_matrix

def test_permissions():
    app = create_app()
    with app.app_context():
        # Setup: Create a test user, group, and module
        test_user = User.query.filter_by(email='test_perm@example.com').first()
        if not test_user:
            test_user = User(name='Test Perm User', email='test_perm@example.com', role='user')
            db.session.add(test_user)
        
        test_group = Group.query.filter_by(name='Test Perm Group').first()
        if not test_group:
            test_group = Group(name='Test Perm Group')
            db.session.add(test_group)
            
        test_module = Module.query.first()
        if not test_module:
            print("✗ No modules found in DB. Run seed-db-prod first.")
            return

        db.session.commit()
        
        # Test 1: No permissions
        print(f"Testing user: {test_user.name}")
        modules = get_user_modules(test_user.id)
        print(f"Initial modules: {[m.name for m in modules]}")
        assert len(modules) == 0
        
        # Test 2: Direct permission
        update_permission_matrix('user', test_user.id, [test_module.id])
        modules = get_user_modules(test_user.id)
        print(f"Modules after direct permission: {[m.name for m in modules]}")
        assert test_module.id in [m.id for m in modules]
        
        # Test 3: Group permission
        update_permission_matrix('user', test_user.id, []) # Clear direct
        test_user.groups.append(test_group)
        db.session.commit()
        
        update_permission_matrix('group', test_group.id, [test_module.id])
        modules = get_user_modules(test_user.id)
        print(f"Modules after group permission: {[m.name for m in modules]}")
        assert test_module.id in [m.id for m in modules]
        
        # Test 4: Combined permission
        update_permission_matrix('user', test_user.id, [test_module.id])
        modules = get_user_modules(test_user.id)
        print(f"Modules after combined permissions: {[m.name for m in modules]}")
        assert len(modules) == 1 # Deduplicated
        
        # Cleanup
        db.session.delete(test_user)
        db.session.delete(test_group)
        Permission.query.filter_by(module_id=test_module.id, user_id=test_user.id).delete()
        Permission.query.filter_by(module_id=test_module.id, group_id=test_group.id).delete()
        db.session.commit()
        print("✓ All tests passed successfully.")

if __name__ == "__main__":
    test_permissions()
