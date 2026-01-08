# src/routes/finance.py
"""
Finance routes for exchange rate management.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..models import db
from ..models.finance import FinanceSettings, ExchangeRate
from ..services.finance_service import update_exchange_rates
from .main import login_required
from .admin import admin_required

finance_bp = Blueprint('finance', __name__)


@finance_bp.route('/exchange-rates', methods=['GET', 'POST'])
@login_required
@admin_required
def exchange_rates():
    """Exchange rates configuration and history visualization."""
    settings = FinanceSettings.get_settings()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'sync':
            # Manual sync button pressed
            success = update_exchange_rates()
            if success:
                flash('Exchange rates synchronized successfully!', 'success')
            else:
                flash('Failed to sync exchange rates. Check logs for details.', 'danger')
            return redirect(url_for('finance.exchange_rates'))
        
        elif action == 'save':
            # Save settings
            settings.api_endpoint = request.form.get('api_endpoint', settings.api_endpoint)
            settings.base_currency = request.form.get('base_currency', settings.base_currency)
            settings.api_key = request.form.get('api_key') or None
            db.session.commit()
            flash('Settings saved successfully!', 'success')
            return redirect(url_for('finance.exchange_rates'))
    
    # Get historical data for chart (last 30 entries per major currency)
    currencies_to_show = ['USD', 'GBP', 'CHF', 'JPY']
    chart_data = {}
    
    for currency in currencies_to_show:
        rates = ExchangeRate.query.filter_by(currency_code=currency)\
            .order_by(ExchangeRate.fetched_at.desc())\
            .limit(30).all()
        
        if rates:
            # Reverse to get chronological order
            rates = rates[::-1]
            chart_data[currency] = {
                'labels': [r.fetched_at.strftime('%Y-%m-%d') for r in rates],
                'values': [round(r.rate, 4) for r in rates]
            }
    
    # Get all current rates (latest only)
    latest_rates = db.session.query(ExchangeRate)\
        .distinct(ExchangeRate.currency_code)\
        .order_by(ExchangeRate.currency_code, ExchangeRate.fetched_at.desc())\
        .all()
    
    # SQLite workaround - get latest for each currency
    current_rates = {}
    all_currencies = db.session.query(ExchangeRate.currency_code).distinct().all()
    for (currency,) in all_currencies:
        rate = ExchangeRate.get_latest_rate(currency)
        if rate:
            current_rates[currency] = rate.rate
    
    return render_template('finance/exchange_rates.html',
                           settings=settings,
                           chart_data=chart_data,
                           current_rates=current_rates)
