"""
Tests for the seeder functionality.
Migrated from test_missing_coverage.py
"""
import pytest
from src.models import User, Supplier, Asset


def test_seeder_execution(init_database, app):
    """Test the entire seed_data function and its idempotency."""
    from src.seeder import seed_data
    
    seed_data()
    
    # Verify some data exists
    assert User.query.filter_by(email="alice.j@example.com").first() is not None
    assert Supplier.query.count() >= 14
    assert Asset.query.count() > 0
    
    # Run it again to test idempotency (should abort)
    seed_data()
    # Count should be same (no duplicates if idempotency works)
    assert User.query.filter_by(email="alice.j@example.com").count() == 1
