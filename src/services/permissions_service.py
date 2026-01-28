from flask import session, redirect, url_for, flash, request, abort
from functools import wraps
from ..models import db, User, Group, Permission, Module, AccessLevel
from .permissions_cache import permissions_cache

from src.utils.logger import log_audit
import logging
import sys

# Configure logger
logger = logging.getLogger(__name__)

def get_user_modules(user_id):
    """
    Resolves the list of modules a user has access to.
    Logic: User has access if they have a direct permission OR 
    if they belong to a group that has the permission.
    Returns modules with their access levels cached.
    """
    user = User.query.get(user_id)
    if not user:
        return []
    
    # Try cache first
    cached_perms = permissions_cache.get(user_id)
    if cached_perms is not None:
        if not cached_perms:
            return []
        return Module.query.filter(Module.slug.in_(cached_perms.keys())).all()
    
    # 1. Get direct module permissions
    direct_permissions = Permission.query.filter_by(user_id=user_id).all()
    logger.info(f"DEBUG: get_user_modules user_id={user_id} direct_perms_count={len(direct_permissions)}")

    
    # 2. Get permissions inherited from groups
    group_ids = [g.id for g in user.groups]
    group_permissions = []
    if group_ids:
        group_permissions = Permission.query.filter(Permission.group_id.in_(group_ids)).all()
    
    logger.info(f"DEBUG: group_ids={group_ids} group_perms_count={len(group_permissions)}")

        
    # 3. Combine and resolve access level (WRITE > READ_ONLY)
    # Mapping: module_id -> access_level
    resolved_permissions = {}
    
    for p in direct_permissions + group_permissions:
        m_id = p.module_id
        current_level = p.access_level.value # String value "WRITE" or "READ_ONLY"
        
        if m_id not in resolved_permissions or current_level == "WRITE":
            resolved_permissions[m_id] = current_level
    
    # 4. Fetch module objects and update cache with slugs
    if not resolved_permissions:
        permissions_cache.set(user_id, {})
        logger.info(f"DEBUG: No permissions resolved for user {user_id}")
        return []

        
    modules = Module.query.filter(Module.id.in_(resolved_permissions.keys())).all()
    
    # Map slugs to access levels for cache
    slug_permissions = {}
    for m in modules:
        slug_permissions[m.slug] = resolved_permissions[m.id]
        
    permissions_cache.set(user_id, slug_permissions)
    
    return modules

def update_permission_matrix(target_type, target_id, module_permissions):
    """
    Bulk updates permissions for a user or group.
    target_type: 'user' or 'group'
    target_id: ID of the user or group
    module_permissions: List of dictionaries or tuples [{'module_id': id, 'access_level': 'WRITE'}]
    """
    # 1. Clear existing permissions
    if target_type == 'user':
        Permission.query.filter_by(user_id=target_id).delete()
    elif target_type == 'group':
        Permission.query.filter_by(group_id=target_id).delete()
    else:
        raise ValueError("Invalid target_type. Must be 'user' or 'group'.")
        
    # 2. Insert new permissions
    for item in module_permissions:
        m_id = item.get('module_id')
        level_name = item.get('access_level', 'WRITE')
        
        # Validate access level name
        try:
            level = AccessLevel[level_name]
        except KeyError:
            level = AccessLevel.WRITE

        perm = Permission(module_id=m_id, access_level=level)
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

def requires_permission(module_slug, access_level='READ_ONLY'):
    """
    Decorator to enforce module-level permissions on routes.
    access_level can be 'READ_ONLY' or 'WRITE'.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                return redirect(url_for('main.login'))
            
            user = User.query.get(user_id)
            if not user:
                return redirect(url_for('main.login'))
                
            # Admin bypass
            if user.role == 'admin':
                return f(*args, **kwargs)
                
            # Check permissions
            perms = permissions_cache.get(user_id)
            if perms is None:
                # Refresh cache
                get_user_modules(user_id)
                perms = permissions_cache.get(user_id)
                
            if module_slug not in perms:
                flash(f"You don't have access to the {module_slug} module.", "danger")
                return redirect(url_for('main.dashboard'))
                
            if access_level == 'WRITE' and perms.get(module_slug) != 'WRITE':
                flash(f"You only have read-only access to the {module_slug} module.", "warning")
                # Try to redirect back, or to the module main page
                return redirect(request.referrer or url_for('main.dashboard'))
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def has_write_permission(module_slug):
    """
    Helper function to check if the current user has WRITE permission for a module.
    Returns True if user is admin or has WRITE access to the module.
    """
    user_id = session.get('user_id')
    if not user_id:
        return False
    
    user = User.query.get(user_id)
    if not user:
        return False
    
    # Admin bypass
    if user.role == 'admin':
        return True
    
    # Check permissions
    perms = permissions_cache.get(user_id)
    if perms is None:
        # Refresh cache
        get_user_modules(user_id)
        perms = permissions_cache.get(user_id)
    
    return perms.get(module_slug) == 'WRITE'
