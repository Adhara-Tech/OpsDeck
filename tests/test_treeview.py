"""
Tests for src/routes/treeview.py
Covers: tree_view with locations, users, suppliers roots
"""
import pytest
from datetime import date, timedelta
from src import db
from src.models import (
    Location, User, Asset, Peripheral, License, Supplier, Subscription, Purchase
)

@pytest.fixture
def treeview_data(app):
    """Creates sample data for treeview testing using get_or_create pattern."""
    with app.app_context():
        # 1. Location
        location = Location.query.filter_by(name="Tree HQ").first()
        if not location:
            location = Location(name="Tree HQ")
            db.session.add(location)
            db.session.commit()

        # 2. Supplier
        supplier = Supplier.query.filter_by(email="tree_supplier@test.com").first()
        if not supplier:
            supplier = Supplier(name="Tree Supplier", email="tree_supplier@test.com")
            db.session.add(supplier)
            db.session.commit()

        # 3. User
        user = User.query.filter_by(email="tree_user@test.com").first()
        if not user:
            user = User(name="Tree User", email="tree_user@test.com", role="user")
            user.set_password("password")
            db.session.add(user)
            db.session.commit()

        # 4. Asset (Linked to Location, Supplier, User)
        asset = Asset.query.filter_by(name="Tree Asset").first()
        if not asset:
            asset = Asset(
                name="Tree Asset",
                status="In Use",
                location_id=location.id,
                supplier_id=supplier.id,
                user_id=user.id
            )
            db.session.add(asset)
            db.session.commit()
        else:
            # Ensure links exist if asset was already there (though unlikely in test env unless shared)
            asset.location_id = location.id
            asset.supplier_id = supplier.id
            asset.user_id = user.id
            db.session.commit()

        # 5. Peripheral (Linked to User)
        peri = Peripheral.query.filter_by(name="Tree Peripheral").first()
        if not peri:
            peri = Peripheral(
                name="Tree Peripheral",
                user_id=user.id
            )
            db.session.add(peri)
            db.session.commit()

        # 6. License (Linked to User)
        lic = License.query.filter_by(license_key="TREE-KEY-001").first()
        if not lic:
            lic = License(
                name="Tree License",
                license_key="TREE-KEY-001",
                user_id=user.id
            )
            db.session.add(lic)
            db.session.commit()

        # 7. Subscription (Linked to Supplier)
        sub = Subscription.query.filter_by(name="Tree Subscription").first()
        if not sub:
            sub = Subscription(
                name="Tree Subscription",
                subscription_type="SaaS",
                supplier_id=supplier.id,
                cost=100.0,
                renewal_date=date.today() + timedelta(days=30),
                renewal_period_type="monthly"
            )
            db.session.add(sub)
            db.session.commit()

        yield {
            'location_id': location.id,
            'user_id': user.id,
            'supplier_id': supplier.id
        }


def test_treeview_locations_root(auth_client, treeview_data):
    """Test treeview with locations root."""
    response = auth_client.get('/tree-view/?root=locations')
    assert response.status_code == 200
    # Should see Location Name
    assert b'Tree HQ' in response.data
    # Should see Asset linked to it
    assert b'Tree Asset' in response.data


def test_treeview_users_root(auth_client, treeview_data):
    """Test treeview with users root."""
    response = auth_client.get('/tree-view/?root=users')
    assert response.status_code == 200
    # Should see User Name (User is Tree User)
    assert b'Tree User' in response.data
    # Should see Asset linked to User
    assert b'Tree Asset' in response.data
    # Should see Peripheral linked to User
    assert b'Tree Peripheral' in response.data
    # Should see License linked to User
    assert b'Tree License' in response.data


def test_treeview_suppliers_root(auth_client, treeview_data):
    """Test treeview with suppliers root."""
    response = auth_client.get('/tree-view/?root=suppliers')
    assert response.status_code == 200
    assert b'Tree Supplier' in response.data
    # Should see Asset linked to Supplier
    assert b'Tree Asset' in response.data
    # Should see Subscription linked to Supplier
    assert b'Tree Subscription' in response.data
