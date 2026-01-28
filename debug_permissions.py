from src import create_app
from src.extensions import db
from src.models import User, Module, Permission, Group

app = create_app()

with app.app_context():
    print("--- MODULES ---")
    modules = Module.query.all()
    for m in modules:
        print(f"ID: {m.id}, Name: {m.name}, Slug: {m.slug}")

    print("\n--- USERS ---")
    users = User.query.filter(User.email != 'admin@example.com').all() # Skip default admin
    for u in users:
        print(f"User: {u.name} ({u.email}), Role: {u.role}")
        print("  Direct Permissions:")
        perms = Permission.query.filter_by(user_id=u.id).all()
        for p in perms:
            print(f"    - Module: {p.module.slug}, Level: {p.access_level.value}")
            
    print("\n--- GROUPS ---")
    groups = Group.query.all()
    for g in groups:
        print(f"Group: {g.name}")
        for p in g.permissions:
             print(f"    - Module: {p.module.slug}, Level: {p.access_level.value}")
