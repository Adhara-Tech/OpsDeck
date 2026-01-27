class PermissionsCache:
    """
    A simple in-memory singleton cache for user permissions.
    Stores user_id -> {module_slug: access_level_name}.
    """
    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PermissionsCache, cls).__new__(cls)
        return cls._instance

    def get(self, user_id):
        """Returns the mapping of module slugs to access levels for a user if cached, else None."""
        return self._cache.get(user_id)

    def set(self, user_id, permissions):
        """Caches the mapping of module slugs to access levels for a user."""
        self._cache[user_id] = permissions

    def invalidate(self, user_id=None):
        """
        Clears the cache for a specific user, or all users if user_id is None.
        """
        if user_id:
            if user_id in self._cache:
                del self._cache[user_id]
        else:
            self._cache.clear()

# Global instance
permissions_cache = PermissionsCache()
