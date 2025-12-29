"""
Tests for model functionality - Software, License, CostCenter, Subscription, 
BusinessService, ServiceComponent.
Migrated from test_missing_coverage.py
"""
import pytest
from datetime import date, timedelta
from src.models import (
    Software, License, CostCenter, Subscription, Supplier,
    BusinessService, ServiceComponent, Asset, User
)


def test_software_and_license_creation(init_database):
    """Test Software and License model creation and relationships."""
    db = init_database
    
    # Create Owner (User)
    user = User(name="Software Owner", email="owner@test.com", role="admin")
    db.session.add(user)
    db.session.commit()
    
    # Create Software
    software = Software(
        name="Test Software Suite",
        category="Productivity",
        description="A test suite",
        owner_id=user.id,
        owner_type="user"
    )
    db.session.add(software)
    db.session.commit()
    
    assert software.id is not None
    assert software.owner == user
    
    # Create License
    lic = License(
        name="Test License Key",
        license_key="XXXX-YYYY-ZZZZ",
        cost=100.0,
        currency="USD",
        purchase_date=date.today(),
        expiry_date=date.today() + timedelta(days=365),
        software_id=software.id,
        user_id=user.id
    )
    db.session.add(lic)
    db.session.commit()
    
    assert lic.id is not None
    assert lic.software == software
    assert lic.status == "Expired" if lic.expiry_date < date.today() else "In use"


def test_cost_center_creation(init_database):
    """Test CostCenter model creation and repr."""
    db = init_database
    cc = CostCenter(code="CC-001", name="Engineering", description="Engineering Dept")
    db.session.add(cc)
    db.session.commit()
    
    assert cc.id is not None
    assert repr(cc) == "<CostCenter CC-001>"


def test_subscription_creation_and_renewal(init_database):
    """Test Subscription model creation and renewal date calculation."""
    db = init_database
    
    supplier = Supplier(name="SaaS Provider", email="sales@saas.com")
    db.session.add(supplier)
    db.session.commit()
    
    sub = Subscription(
        name="Monthly SaaS",
        subscription_type="Cloud",
        supplier_id=supplier.id,
        cost=50.0,
        currency="EUR",
        renewal_date=date.today() - timedelta(days=1),
        renewal_period_type="monthly",
        renewal_period_value=1,
        monthly_renewal_day="15"
    )
    db.session.add(sub)
    db.session.commit()
    
    assert sub.id is not None
    assert sub.cost_eur == 50.0
    
    # Test renewal logic
    next_date = sub.next_renewal_date
    assert next_date > date.today()


def test_business_service_and_components(init_database):
    """Test BusinessService and ServiceComponent model creation."""
    db = init_database
    
    # Create Cost Center
    cc = CostCenter(code="IT-01", name="IT Services")
    db.session.add(cc)
    
    # Create Service
    service = BusinessService(
        name="Core Banking",
        criticality="Tier 1 - Critical",
        cost_center=cc
    )
    db.session.add(service)
    db.session.commit()
    
    # Create Asset to link
    asset = Asset(name="Server 01", status="In Use")
    db.session.add(asset)
    db.session.commit()
    
    # Link Asset as ServiceComponent
    comp = ServiceComponent(
        service_id=service.id,
        component_type="Asset",
        component_id=asset.id,
        notes="Primary Server"
    )
    db.session.add(comp)
    db.session.commit()
    
    assert comp.linked_object == asset
    assert service.components.count() == 1
    assert repr(service) == "<BusinessService Core Banking>"
