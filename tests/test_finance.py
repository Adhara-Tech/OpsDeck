from datetime import date, datetime, timedelta
import pytest
from src import db
from src.models import Budget, Subscription, Supplier
from src.utils.timezone_helper import today

def test_purchase_cost_calculation(auth_client, app):
    """
    Test 12: Prueba que la propiedad @total_cost de una Compra (Purchase)
    se calcula correctamente sumando sus activos y periféricos.
    """
    # --- 1. Setup ---
    # (auth_client ya ha creado un Admin (ID 1) y un User (ID 2))
    
    # Crear una Compra (ID 1)
    auth_client.post('/purchases/new', data={
        'description': 'Compra de Portátiles Q4',
        'purchase_date': '2025-11-14'
    }, follow_redirects=True)
    
    # Crear un Activo (cost=1000) y un Periférico (cost=150)
    # y enlazarlos a la Compra (ID 1)
    auth_client.post('/assets/new', data={
        'name': 'Laptop A',
        'status': 'Stored',
        'cost': 1000,
        'purchase_id': 1
    }, follow_redirects=True)
    
    auth_client.post('/peripherals/new', data={
        'name': 'Monitor A',
        'status': 'Stored',
        'cost': 150,
        'purchase_id': 1
    }, follow_redirects=True)

    # --- 2. Acción ---
    # Acceder a la página de detalles de la Compra
    response = auth_client.get('/purchases/1')
    
    # --- 3. Verify ---
    assert response.status_code == 200
    # Asumimos que la plantilla formatea el coste total como 1150.00
    assert b'1150.00' in response.data

def test_budget_remaining_calculation(auth_client, app):
    """
    Test 13: Prueba que la propiedad @remaining de un Presupuesto (Budget)
    se calcula correctamente restando el coste de las compras asociadas.
    """
    # --- 1. Setup ---
    
    # Crear un Presupuesto (ID 1) con 5000
    auth_client.post('/budgets/new', data={
        'name': 'Presupuesto IT 2025',
        'amount': 5000,
        'valid_from': '2025-01-01',
        'valid_until': '2025-12-31'
    }, follow_redirects=True)
    
    # Crear una Compra (ID 1) enlazada al Presupuesto 1
    auth_client.post('/purchases/new', data={
        'description': 'Compra de Servidor',
        'purchase_date': '2025-11-14',
        'budget_id': 1
    }, follow_redirects=True)
    
    # Crear un Activo (cost=3000) enlazado a la Compra 1
    auth_client.post('/assets/new', data={
        'name': 'Servidor R740',
        'status': 'Stored',
        'cost': 3000,
        'purchase_id': 1
    }, follow_redirects=True)

    with app.app_context():
        budget = db.session.get(Budget, 1)
        assert budget is not None
        # 5000 (Presupuesto) - 3000 (Coste Activo) = 2000 (Restante)
        assert budget.remaining == 2000.00


def test_budget_is_active_within_period(app):
    """
    Test that Budget.is_active() returns True for dates within the validity period.
    """
    with app.app_context():
        budget = Budget(
            name='Test Budget',
            amount=1000,
            valid_from=date(2024, 1, 1),
            valid_until=date(2024, 12, 31)
        )
        db.session.add(budget)
        db.session.commit()

        # Date in the middle of the period should be active
        assert budget.is_active(date(2024, 6, 15)) is True


def test_budget_is_active_on_first_day(app):
    """
    Test that Budget.is_active() returns True on valid_from date (inclusive).
    """
    with app.app_context():
        budget = Budget(
            name='Test Budget',
            amount=1000,
            valid_from=date(2024, 1, 1),
            valid_until=date(2024, 12, 31)
        )
        db.session.add(budget)
        db.session.commit()

        # First day should be active (inclusive)
        assert budget.is_active(date(2024, 1, 1)) is True


def test_budget_is_active_on_last_day(app):
    """
    Test that Budget.is_active() returns True on valid_until date (inclusive).
    This is the main edge case mentioned in bug #6.
    """
    with app.app_context():
        budget = Budget(
            name='Test Budget',
            amount=1000,
            valid_from=date(2024, 1, 1),
            valid_until=date(2024, 12, 31)
        )
        db.session.add(budget)
        db.session.commit()

        # Last day should be active (inclusive)
        assert budget.is_active(date(2024, 12, 31)) is True


def test_budget_is_active_before_period(app):
    """
    Test that Budget.is_active() returns False for dates before valid_from.
    """
    with app.app_context():
        budget = Budget(
            name='Test Budget',
            amount=1000,
            valid_from=date(2024, 1, 1),
            valid_until=date(2024, 12, 31)
        )
        db.session.add(budget)
        db.session.commit()

        # Date before period should be inactive
        assert budget.is_active(date(2023, 12, 31)) is False


def test_budget_is_active_after_period(app):
    """
    Test that Budget.is_active() returns False for dates after valid_until.
    """
    with app.app_context():
        budget = Budget(
            name='Test Budget',
            amount=1000,
            valid_from=date(2024, 1, 1),
            valid_until=date(2024, 12, 31)
        )
        db.session.add(budget)
        db.session.commit()

        # Date after period should be inactive
        assert budget.is_active(date(2025, 1, 1)) is False


def test_budget_is_active_with_datetime_object(app):
    """
    Test that Budget.is_active() correctly handles datetime objects by converting to date.
    """
    with app.app_context():
        budget = Budget(
            name='Test Budget',
            amount=1000,
            valid_from=date(2024, 1, 1),
            valid_until=date(2024, 12, 31)
        )
        db.session.add(budget)
        db.session.commit()

        # Datetime object should be converted to date (time component ignored)
        test_datetime = datetime(2024, 6, 15, 14, 30, 0)
        assert budget.is_active(test_datetime) is True

        # Edge case: datetime on last day with late hour should still be valid
        # because it's the same DATE as valid_until
        last_day_evening = datetime(2024, 12, 31, 23, 59, 59)
        assert budget.is_active(last_day_evening) is True


def test_budget_is_active_defaults_to_today(app):
    """
    Test that Budget.is_active() defaults to today's date when no parameter is provided.
    """
    with app.app_context():
        current_date = today()

        # Create budget that includes today
        budget = Budget(
            name='Test Budget',
            amount=1000,
            valid_from=current_date - timedelta(days=30),
            valid_until=current_date + timedelta(days=30)
        )
        db.session.add(budget)
        db.session.commit()

        # No parameter should default to today and be active
        assert budget.is_active() is True

        # Create budget that expired yesterday
        expired_budget = Budget(
            name='Expired Budget',
            amount=1000,
            valid_from=current_date - timedelta(days=60),
            valid_until=current_date - timedelta(days=1)
        )
        db.session.add(expired_budget)
        db.session.commit()

        # Should be inactive when checking with default (today)
        assert expired_budget.is_active() is False


def test_budget_negative_amount_validation(app):
    """
    Test that Budget.amount validates against negative values (Bug #7).
    """
    with app.app_context():
        with pytest.raises(ValueError, match="must be greater than 0"):
            budget = Budget(
                name='Invalid Budget',
                amount=-1000,  # Negative amount should raise ValueError
                valid_from=date(2024, 1, 1),
                valid_until=date(2024, 12, 31)
            )
            db.session.add(budget)
            db.session.flush()  # Force validation


def test_budget_zero_amount_validation(app):
    """
    Test that Budget.amount validates against zero value (Bug #7).
    """
    with app.app_context():
        with pytest.raises(ValueError, match="must be greater than 0"):
            budget = Budget(
                name='Invalid Budget',
                amount=0,  # Zero amount should raise ValueError
                valid_from=date(2024, 1, 1),
                valid_until=date(2024, 12, 31)
            )
            db.session.add(budget)
            db.session.flush()  # Force validation


def test_budget_positive_amount_validation(app):
    """
    Test that Budget.amount accepts positive values.
    """
    with app.app_context():
        budget = Budget(
            name='Valid Budget',
            amount=1000,  # Positive amount should be accepted
            valid_from=date(2024, 1, 1),
            valid_until=date(2024, 12, 31)
        )
        db.session.add(budget)
        db.session.commit()

        assert budget.amount == 1000


def test_subscription_negative_cost_validation(app):
    """
    Test that Subscription.cost validates against negative values (Bug #8).
    """
    with app.app_context():
        # Create a supplier first (required FK)
        supplier = Supplier(name='Test Supplier')
        db.session.add(supplier)
        db.session.commit()

        with pytest.raises(ValueError, match="must be greater than 0"):
            subscription = Subscription(
                name='Invalid Subscription',
                subscription_type='SaaS',
                renewal_date=date(2024, 6, 15),
                renewal_period_type='monthly',
                cost=-100,  # Negative cost should raise ValueError
                supplier_id=supplier.id
            )
            db.session.add(subscription)
            db.session.flush()  # Force validation


def test_subscription_zero_cost_validation(app):
    """
    Test that Subscription.cost validates against zero value (Bug #8).
    """
    with app.app_context():
        # Create a supplier first (required FK)
        supplier = Supplier(name='Test Supplier')
        db.session.add(supplier)
        db.session.commit()

        with pytest.raises(ValueError, match="must be greater than 0"):
            subscription = Subscription(
                name='Invalid Subscription',
                subscription_type='SaaS',
                renewal_date=date(2024, 6, 15),
                renewal_period_type='monthly',
                cost=0,  # Zero cost should raise ValueError
                supplier_id=supplier.id
            )
            db.session.add(subscription)
            db.session.flush()  # Force validation


def test_subscription_positive_cost_validation(app):
    """
    Test that Subscription.cost accepts positive values.
    """
    with app.app_context():
        # Create a supplier first (required FK)
        supplier = Supplier(name='Test Supplier')
        db.session.add(supplier)
        db.session.commit()

        subscription = Subscription(
            name='Valid Subscription',
            subscription_type='SaaS',
            renewal_date=date(2024, 6, 15),
            renewal_period_type='monthly',
            cost=99.99,  # Positive cost should be accepted
            supplier_id=supplier.id
        )
        db.session.add(subscription)
        db.session.commit()

        assert subscription.cost == 99.99