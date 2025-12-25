from src import create_app, db
from src.models.services import BusinessService, ServiceComponent
from src.models.auth import User

app = create_app()

with app.app_context():
    print("Starting Verification...")
    
    # 1. Clean up previous test data if any
    try:
        BusinessService.query.filter(BusinessService.name.like('Test Service%')).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Cleanup warning: {e}")

    # 2. Create Services
    s1 = BusinessService(name="Test Service Core", description="Core System", status="Operational")
    s2 = BusinessService(name="Test Service Frontend", description="Web UI", status="Operational")
    
    # Mock user if needed, but owner_id is optional.
    admin = User.query.first()
    if admin:
        s1.owner_id = admin.id
    
    db.session.add(s1)
    db.session.add(s2)
    db.session.commit()
    print(f"Created Services: {s1.id}, {s2.id}")
    
    # 3. Add Dependency: Frontend depends on Core (Frontend -> Core)
    # s2 (Frontend) depends on s1 (Core)
    # So s1 is in s2.upstream_dependencies
    
    # Refresh instances
    s1 = BusinessService.query.get(s1.id)
    s2 = BusinessService.query.get(s2.id)
    
    s2.upstream_dependencies.append(s1)
    db.session.commit()
    
    # Verify dependency
    assert s1 in s2.upstream_dependencies
    assert s2 in s1.downstream_dependencies
    print("Dependency Verified: Frontend -> Core")
    
    # 4. Add Component
    c1 = ServiceComponent(service_id=s1.id, component_type="Asset", component_id=999, notes="Dummy Asset")
    db.session.add(c1)
    db.session.commit()
    
    assert c1 in s1.components
    print("Component Verified: Linked Asset 999 to Core")
    
    print("ALL MODEL CHECKS PASSED")
