"""
Tests for Bug #7: Renewal date in the past causing CPU-intensive loops

Tests that the next_renewal_date property:
1. Handles dates far in the past efficiently (no excessive loops)
2. Calculates the correct next renewal date
3. Works for all renewal period types (monthly, yearly, custom)
"""
import pytest
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import time

from src.models.procurement import Subscription, Supplier
from src.extensions import db
from src.utils.timezone_helper import today


@pytest.fixture
def test_supplier(app):
    """Create a test supplier."""
    with app.app_context():
        supplier = Supplier(
            name='Test Supplier',
            website='https://test.com'
        )
        db.session.add(supplier)
        db.session.commit()
        yield supplier
        # Cleanup: delete subscriptions first (due to FK constraint)
        Subscription.query.filter_by(supplier_id=supplier.id).delete()
        db.session.delete(supplier)
        db.session.commit()


class TestRenewalDateOptimization:
    """Test suite for renewal date optimization (Bug #7)."""

    def test_monthly_renewal_far_in_past_performance(self, app, test_supplier):
        """Test that monthly renewals 5 years in the past calculate quickly."""
        with app.app_context():
            # Create subscription with renewal date 5 years ago
            five_years_ago = today() - relativedelta(years=5)

            subscription = Subscription(
                name='Old Monthly Subscription',
                subscription_type='SaaS',
                renewal_date=five_years_ago,
                renewal_period_type='monthly',
                renewal_period_value=1,
                auto_renew=True,  # Required for next_renewal_date calculation
                cost=100.0,
                currency='USD',
                supplier_id=test_supplier.id
            )
            db.session.add(subscription)
            db.session.commit()

            # Measure performance
            start_time = time.time()
            next_renewal = subscription.next_renewal_date
            elapsed_time = time.time() - start_time

            # Should complete in under 0.1 seconds (was taking seconds before optimization)
            assert elapsed_time < 0.1, f"Calculation took {elapsed_time:.3f}s - too slow!"

            # Verify the result is in the future
            assert next_renewal >= today(), "Next renewal should be today or in the future"

            # Verify it's within a reasonable range (within 2 months of today)
            max_expected = today() + relativedelta(months=2)
            assert next_renewal <= max_expected, f"Next renewal {next_renewal} is too far in future"

    def test_yearly_renewal_far_in_past_performance(self, app, test_supplier):
        """Test that yearly renewals 10 years in the past calculate quickly."""
        with app.app_context():
            # Create subscription with renewal date 10 years ago
            ten_years_ago = today() - relativedelta(years=10)

            subscription = Subscription(
                name='Old Yearly Subscription',
                subscription_type='License',
                renewal_date=ten_years_ago,
                renewal_period_type='yearly',
                renewal_period_value=1,
                auto_renew=True,  # Required for next_renewal_date calculation
                cost=1000.0,
                currency='USD',
                supplier_id=test_supplier.id
            )
            db.session.add(subscription)
            db.session.commit()

            # Measure performance
            start_time = time.time()
            next_renewal = subscription.next_renewal_date
            elapsed_time = time.time() - start_time

            # Should complete in under 0.1 seconds
            assert elapsed_time < 0.1, f"Calculation took {elapsed_time:.3f}s - too slow!"

            # Verify the result is in the future
            assert next_renewal >= today(), "Next renewal should be today or in the future"

            # Verify it's within a reasonable range (within 2 years of today)
            max_expected = today() + relativedelta(years=2)
            assert next_renewal <= max_expected, f"Next renewal {next_renewal} is too far in future"

    def test_custom_days_renewal_far_in_past_performance(self, app, test_supplier):
        """Test that custom (daily) renewals 2 years in the past calculate quickly."""
        with app.app_context():
            # Create subscription with renewal date 2 years ago, renewing every 90 days
            two_years_ago = today() - relativedelta(years=2)

            subscription = Subscription(
                name='Old Custom Period Subscription',
                subscription_type='Service',
                renewal_date=two_years_ago,
                renewal_period_type='custom',
                renewal_period_value=90,
                auto_renew=True,  # Required for next_renewal_date calculation
                cost=250.0,
                currency='USD',
                supplier_id=test_supplier.id
            )
            db.session.add(subscription)
            db.session.commit()

            # Measure performance
            start_time = time.time()
            next_renewal = subscription.next_renewal_date
            elapsed_time = time.time() - start_time

            # Should complete in under 0.1 seconds
            assert elapsed_time < 0.1, f"Calculation took {elapsed_time:.3f}s - too slow!"

            # Verify the result is in the future
            assert next_renewal >= today(), "Next renewal should be today or in the future"

            # Verify it's within a reasonable range (within 180 days of today)
            max_expected = today() + timedelta(days=180)
            assert next_renewal <= max_expected, f"Next renewal {next_renewal} is too far in future"

    def test_monthly_renewal_with_specific_day_far_in_past(self, app, test_supplier):
        """Test monthly renewals with specific day (e.g., 15th) when far in the past."""
        with app.app_context():
            # Create subscription with renewal date 3 years ago, renewing on 15th
            three_years_ago = today() - relativedelta(years=3)

            subscription = Subscription(
                name='Old Monthly Specific Day Subscription',
                subscription_type='SaaS',
                renewal_date=three_years_ago,
                renewal_period_type='monthly',
                renewal_period_value=1,
                monthly_renewal_day='15',
                auto_renew=True,  # Required for next_renewal_date calculation
                cost=150.0,
                currency='USD',
                supplier_id=test_supplier.id
            )
            db.session.add(subscription)
            db.session.commit()

            # Measure performance
            start_time = time.time()
            next_renewal = subscription.next_renewal_date
            elapsed_time = time.time() - start_time

            # Should complete quickly
            assert elapsed_time < 0.1, f"Calculation took {elapsed_time:.3f}s - too slow!"

            # Verify the result is in the future
            assert next_renewal >= today(), "Next renewal should be today or in the future"

    def test_renewal_date_in_future_returns_immediately(self, app, test_supplier):
        """Test that renewal dates already in the future are returned immediately."""
        with app.app_context():
            # Create subscription with renewal date in the future
            future_date = today() + timedelta(days=30)

            subscription = Subscription(
                name='Future Renewal Subscription',
                subscription_type='SaaS',
                renewal_date=future_date,
                renewal_period_type='monthly',
                renewal_period_value=1,
                auto_renew=True,  # Required for next_renewal_date calculation
                cost=100.0,
                currency='USD',
                supplier_id=test_supplier.id
            )
            db.session.add(subscription)
            db.session.commit()

            # Should return the same date
            assert subscription.next_renewal_date == future_date

    def test_renewal_date_today_returns_today(self, app, test_supplier):
        """Test that renewal date set to today returns today."""
        with app.app_context():
            subscription = Subscription(
                name='Today Renewal Subscription',
                subscription_type='SaaS',
                renewal_date=today(),
                renewal_period_type='monthly',
                renewal_period_value=1,
                auto_renew=True,  # Required for next_renewal_date calculation
                cost=100.0,
                currency='USD',
                supplier_id=test_supplier.id
            )
            db.session.add(subscription)
            db.session.commit()

            # Should return today
            assert subscription.next_renewal_date == today()

    def test_quarterly_renewal_far_in_past(self, app, test_supplier):
        """Test quarterly (every 3 months) renewals when far in the past."""
        with app.app_context():
            # Create subscription with renewal date 4 years ago
            four_years_ago = today() - relativedelta(years=4)

            subscription = Subscription(
                name='Old Quarterly Subscription',
                subscription_type='Support',
                renewal_date=four_years_ago,
                renewal_period_type='monthly',
                renewal_period_value=3,  # Quarterly
                auto_renew=True,  # Required for next_renewal_date calculation
                cost=500.0,
                currency='USD',
                supplier_id=test_supplier.id
            )
            db.session.add(subscription)
            db.session.commit()

            # Measure performance
            start_time = time.time()
            next_renewal = subscription.next_renewal_date
            elapsed_time = time.time() - start_time

            # Should complete quickly
            assert elapsed_time < 0.1, f"Calculation took {elapsed_time:.3f}s - too slow!"

            # Verify the result is in the future
            assert next_renewal >= today(), "Next renewal should be today or in the future"

            # Verify it's within a reasonable range (within 6 months of today)
            max_expected = today() + relativedelta(months=6)
            assert next_renewal <= max_expected, f"Next renewal {next_renewal} is too far in future"
