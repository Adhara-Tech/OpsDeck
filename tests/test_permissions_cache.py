import unittest
from src.services.permissions_cache import permissions_cache

class TestPermissionsCache(unittest.TestCase):
    def setUp(self):
        permissions_cache.invalidate()

    def test_set_and_get(self):
        user_id = 999
        slugs = ['finance', 'procurement']
        permissions_cache.set(user_id, slugs)
        self.assertEqual(permissions_cache.get(user_id), slugs)

    def test_get_non_existent(self):
        self.assertIsNone(permissions_cache.get(12345))

    def test_invalidate_user(self):
        user_id = 1
        permissions_cache.set(user_id, ['module1'])
        permissions_cache.invalidate(user_id)
        self.assertIsNone(permissions_cache.get(user_id))

    def test_invalidate_all(self):
        permissions_cache.set(1, ['m1'])
        permissions_cache.set(2, ['m2'])
        permissions_cache.invalidate()
        self.assertIsNone(permissions_cache.get(1))
        self.assertIsNone(permissions_cache.get(2))

    def test_singleton(self):
        from src.services.permissions_cache import PermissionsCache
        cache1 = PermissionsCache()
        cache2 = PermissionsCache()
        self.assertIs(cache1, cache2)
        self.assertIs(cache1, permissions_cache)

if __name__ == '__main__':
    unittest.main()
