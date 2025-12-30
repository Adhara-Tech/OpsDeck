"""
Tests for src/routes/subscriptions.py
Covers: list_subscriptions, detail, new, edit, delete, archive/unarchive, calendar
"""
import pytest
from datetime import date, timedelta
from src import db
from src.models import (
    Subscription, Supplier, PaymentMethod, Contact, 
    Budget, Software
)

@pytest.fixture
def subscriptions_data(app):
    """Creates sample data for subscription testing using get_or_create pattern."""
    with app.app_context():
        # 1. Supplier
        supplier = Supplier.query.filter_by(email="sub_supplier@test.com").first()
        if not supplier:
            supplier = Supplier(name="SaaS Supplier", email="sub_supplier@test.com")
            db.session.add(supplier)
            db.session.commit()

        # 2. Contact
        contact = Contact.query.filter_by(email="sales@saas.com").first()
        if not contact:
            contact = Contact(name="Sales Rep", email="sales@saas.com", supplier_id=supplier.id)
            db.session.add(contact)
            db.session.commit()

        # 3. Payment Method
        payment = PaymentMethod.query.filter_by(name="Corp Card Sub").first()
        if not payment:
            payment = PaymentMethod(name="Corp Card Sub", method_type="Credit Card")
            db.session.add(payment)
            db.session.commit()

        # 4. Budget
        budget = Budget.query.filter_by(name="Sub Budget").first()
        if not budget:
            budget = Budget(
                name="Sub Budget",
                amount=20000.0,
                valid_from=date.today().replace(month=1, day=1),
                valid_until=date.today().replace(month=12, day=31)
            )
            db.session.add(budget)
            db.session.commit()

        # 5. Software (Optional link)
        software = Software.query.filter_by(name="Linked Software").first()
        if not software:
            software = Software(
                name="Linked Software", 
                category="SaaS",
                supplier_id=supplier.id
            )
            db.session.add(software)
            db.session.commit()

        # 6. Subscription
        sub = Subscription.query.filter_by(name="Test Subscription").first()
        if not sub:
            sub = Subscription(
                name="Test Subscription",
                subscription_type="Cloud Service",
                supplier_id=supplier.id,
                cost=500.0,
                currency="EUR",
                renewal_date=date.today() + timedelta(days=90),
                renewal_period_type="monthly",
                renewal_period_value=1,
                monthly_renewal_day="1",
                budget_id=budget.id
            )
            sub.payment_methods.append(payment)
            sub.contacts.append(contact)
            db.session.add(sub)
            db.session.commit()

        # 7. Archived Subscription
        archived = Subscription.query.filter_by(name="Old Subscription").first()
        if not archived:
            archived = Subscription(
                name="Old Subscription",
                subscription_type="Support",
                supplier_id=supplier.id,
                cost=100.0,
                renewal_date=date.today(),
                renewal_period_type="yearly",
                is_archived=True
            )
            db.session.add(archived)
            db.session.commit()

        yield {
            'subscription_id': sub.id,
            'archived_id': archived.id,
            'supplier_id': supplier.id,
            'contact_id': contact.id,
            'payment_id': payment.id,
            'budget_id': budget.id,
            'software_id': software.id
        }


def test_subscriptions_list_loads(auth_client, subscriptions_data):
    """Test subscription list loads."""
    response = auth_client.get('/subscriptions/')
    assert response.status_code == 200


def test_subscriptions_list_hides_archived(auth_client, subscriptions_data):
    """Test list hides archived items by default."""
    response = auth_client.get('/subscriptions/')
    assert b'Old Subscription' not in response.data


def test_subscription_detail_loads(auth_client, subscriptions_data):
    """Test detail page using ID."""
    response = auth_client.get(f'/subscriptions/{subscriptions_data["subscription_id"]}')
    assert response.status_code == 200
    assert b'Test Subscription' in response.data


def test_new_subscription_post_success(auth_client, subscriptions_data, app):
    """Test creating new subscription."""
    unique_name = "New Created Sub"
    # Cleanup check
    with app.app_context():
        exist = Subscription.query.filter_by(name=unique_name).first()
        if exist: db.session.delete(exist); db.session.commit()

    response = auth_client.post('/subscriptions/new', data={
        'name': unique_name,
        'subscription_type': 'SaaS',
        'supplier_id': subscriptions_data['supplier_id'],
        'cost': '150',
        'currency': 'USD',
        'renewal_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
        'renewal_period_type': 'yearly',
        'renewal_period_value': '1'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Subscription created successfully' in response.data or unique_name.encode() in response.data


def test_edit_subscription_post_success(auth_client, subscriptions_data, app):
    """Test updating subscription."""
    response = auth_client.post(f'/subscriptions/{subscriptions_data["subscription_id"]}/edit', data={
        'name': 'Updated Sub Name',
        'subscription_type': 'Cloud Service',
        'supplier_id': subscriptions_data['supplier_id'],
        'cost': '550',
        'currency': 'EUR',
        'renewal_date': (date.today() + timedelta(days=90)).strftime('%Y-%m-%d'),
        'renewal_period_type': 'monthly',
        'renewal_period_value': '1'
    }, follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        s = db.session.get(Subscription, subscriptions_data['subscription_id'])
        assert s.cost == 550.0
        assert s.name == 'Updated Sub Name'


def test_archive_subscription(auth_client, subscriptions_data, app):
    """Test archiving."""
    response = auth_client.post(f'/subscriptions/{subscriptions_data["subscription_id"]}/archive', follow_redirects=True)
    assert response.status_code == 200
    
    with app.app_context():
        s = db.session.get(Subscription, subscriptions_data['subscription_id'])
        assert s.is_archived


def test_calendar_loads(auth_client):
    """Test calendar page."""
    response = auth_client.get('/subscriptions/calendar')
    assert response.status_code == 200
