from ..models import db, User, Group, Permission, Module
from .permissions_cache import permissions_cache

def get_user_modules(user_id):
    """
    Resolves the list of modules a user has access to.
    Logic: User has access if they have a direct permission OR 
    if they belong to a group that has the permission.
    """
    user = User.query.get(user_id)
    if not user:
        return []
    
    # Try cache first
    cached_slugs = permissions_cache.get(user_id)
    if cached_slugs is not None:
        if not cached_slugs:
            return []
        return Module.query.filter(Module.slug.in_(cached_slugs)).all()
    
    # 1. Get direct module permissions
    direct_module_ids = db.session.query(Permission.module_id).filter_by(user_id=user_id).all()
    direct_module_ids = [m[0] for m in direct_module_ids]
    
    # 2. Get permissions inherited from groups
    group_ids = [g.id for g in user.groups]
    group_module_ids = []
    if group_ids:
        group_module_ids = db.session.query(Permission.module_id).filter(Permission.group_id.in_(group_ids)).all()
        group_module_ids = [m[0] for m in group_module_ids]
        
    # 3. Combine and deduplicate
    all_module_ids = list(set(direct_module_ids + group_module_ids))
    
    # 4. Fetch module objects
    if not all_module_ids:
        permissions_cache.set(user_id, [])
        return []
        
    modules = Module.query.filter(Module.id.in_(all_module_ids)).all()
    
    # Update cache
    permissions_cache.set(user_id, [m.slug for m in modules])
    
    return modules

def update_permission_matrix(target_type, target_id, module_ids):
    """
    Bulk updates permissions for a user or group.
    target_type: 'user' or 'group'
    target_id: ID of the user or group
    module_ids: List of module IDs to grant access to
    """
    # 1. Clear existing permissions
    if target_type == 'user':
        Permission.query.filter_by(user_id=target_id).delete()
    elif target_type == 'group':
        Permission.query.filter_by(group_id=target_id).delete()
    else:
        raise ValueError("Invalid target_type. Must be 'user' or 'group'.")
        
    # 2. Insert new permissions
    for m_id in module_ids:
        perm = Permission(module_id=m_id)
        if target_type == 'user':
            perm.user_id = target_id
        else:
            perm.group_id = target_id
        db.session.add(perm)
        
    db.session.commit()

    # Invalidate cache
    if target_type == 'user':
        permissions_cache.invalidate(target_id)
    else:
        # If it's a group, invalidate all to be safe (could be optimized later)
        permissions_cache.invalidate()
