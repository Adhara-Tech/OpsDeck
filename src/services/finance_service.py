# src/services/finance_service.py
"""
Finance service for managing exchange rates.
"""
import logging
from datetime import datetime
import requests

from ..extensions import db
from ..models.finance import FinanceSettings, ExchangeRate
from ..models.core import CURRENCY_RATES

logger = logging.getLogger(__name__)


def update_exchange_rates():
    """
    Fetch exchange rates from the configured API provider and store them.
    Uses Frankfurter API by default (free, no API key required, ECB data).
    """
    settings = FinanceSettings.get_settings()
    
    try:
        # Build the API URL
        url = f"{settings.api_endpoint}?from={settings.base_currency}"
        
        logger.info(f"Fetching exchange rates from {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        rates = data.get('rates', {})
        
        if not rates:
            logger.warning("No rates returned from API")
            return False
        
        # Store each rate
        fetched_at = datetime.utcnow()
        for currency_code, rate in rates.items():
            # Store as rate to convert TO base currency (inverse of API response)
            # API gives: 1 EUR = X USD, we want conversion rate TO EUR
            conversion_rate = 1.0 / rate if rate != 0 else 1.0
            
            new_rate = ExchangeRate(
                currency_code=currency_code,
                rate=conversion_rate,
                fetched_at=fetched_at
            )
            db.session.add(new_rate)
        
        # Also add the base currency with rate 1.0
        base_rate = ExchangeRate(
            currency_code=settings.base_currency,
            rate=1.0,
            fetched_at=fetched_at
        )
        db.session.add(base_rate)
        
        # Update last sync time
        settings.last_sync_at = fetched_at
        db.session.commit()
        
        logger.info(f"Successfully updated {len(rates) + 1} exchange rates")
        return True
        
    except requests.RequestException as e:
        logger.error(f"Error fetching exchange rates: {e}")
        db.session.rollback()
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating exchange rates: {e}")
        db.session.rollback()
        return False


def get_conversion_rate(currency_code):
    """
    Get the conversion rate to EUR for a currency.
    Falls back to hardcoded rates if DB lookup fails.
    
    Args:
        currency_code: The currency code (e.g., 'USD', 'GBP')
        
    Returns:
        float: The conversion rate to EUR (multiply amount by this to get EUR)
    """
    if not currency_code:
        return 1.0
    
    currency_code = currency_code.upper()
    
    # 1. Try to get the most recent rate from the database
    try:
        latest_rate = ExchangeRate.get_latest_rate(currency_code)
        if latest_rate:
            return latest_rate.rate
    except Exception as e:
        logger.warning(f"Error looking up rate for {currency_code}: {e}")
    
    # 2. Fallback to hardcoded rates
    return CURRENCY_RATES.get(currency_code, 1.0)
