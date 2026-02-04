from src.models import db, User, Group, Module, Permission
from src.services.permissions_service import get_user_modules, update_permission_matrix

def test_permissions(app, init_database):
    """
    Test permissions resolution using the standard app fixture to ensure
    the database is properly initialized (tables created).
    """
    with app.app_context():
        # Setup: Ensure we have a module to test with
        test_module = Module.query.first()
        if not test_module:
            # Create a dummy module if none exists (e.g. in CI/clean DB)
            test_module = Module(
                name="Test Module",
                slug="test-module",
                description="A module for testing permissions"
            )
            db.session.add(test_module)
            db.session.commit()

        # Setup: Create a test user and group
        # We check for existence just in case, though init_database should give us a clean slate
        test_user = User.query.filter_by(email='test_perm@example.com').first()
        if not test_user:
            test_user = User(name='Test Perm User', email='test_perm@example.com', role='user')
            db.session.add(test_user)
        
        test_group = Group.query.filter_by(name='Test Perm Group').first()
        if not test_group:
            test_group = Group(name='Test Perm Group')
            db.session.add(test_group)
            
        db.session.commit()
        
        # Test 1: No permissions
        print(f"Testing user: {test_user.name}")
        modules = get_user_modules(test_user.id)
        print(f"Initial modules: {[m.name for m in modules]}")
        assert len(modules) == 0
        
        # Test 2: Direct permission
        update_permission_matrix('user', test_user.id, [{'module_id': test_module.id, 'access_level': 'WRITE'}])
        modules = get_user_modules(test_user.id)
        print(f"Modules after direct permission: {[m.name for m in modules]}")
        assert test_module.id in [m.id for m in modules]
        
        # Test 3: Group permission
        update_permission_matrix('user', test_user.id, []) # Clear direct
        test_user.groups.append(test_group)
        db.session.commit()
        
        update_permission_matrix('group', test_group.id, [{'module_id': test_module.id, 'access_level': 'WRITE'}])
        modules = get_user_modules(test_user.id)
        print(f"Modules after group permission: {[m.name for m in modules]}")
        assert test_module.id in [m.id for m in modules]
        
        # Test 4: Combined permission
        update_permission_matrix('user', test_user.id, [{'module_id': test_module.id, 'access_level': 'WRITE'}])
        modules = get_user_modules(test_user.id)
        print(f"Modules after combined permissions: {[m.name for m in modules]}")
        assert len(modules) == 1 # Deduplicated
        
        # Cleanup (not strictly necessary with init_database fixture, but good for hygiene)
        db.session.delete(test_user)
        db.session.delete(test_group)
        Permission.query.filter_by(module_id=test_module.id, user_id=test_user.id).delete()
        Permission.query.filter_by(module_id=test_module.id, group_id=test_group.id).delete()
        # If we created the module, we might leave it or delete it. Leaving it is fine for the session scope if needed, 
        # but init_database cleans up per function usually if scoped that way. 
        # Checking conftest, init_database is function-scoped and does db.drop_all/create_all.
        # So manual cleanup is redundant but harmless.
        db.session.commit()
        print("✓ All tests passed successfully.")
