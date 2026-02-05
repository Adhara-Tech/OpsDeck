"""
Timezone Helper Module

Provides timezone-aware datetime functions that respect the application's
configured timezone. Solves the DST (Daylight Saving Time) issues.

Usage:
    from src.utils.timezone_helper import now, today, current_time, to_local

    # Get current datetime in app's timezone
    current_dt = now()

    # Get current date in app's timezone
    current_date = today()

    # Get current time in app's timezone
    current_t = current_time()

    # Convert UTC datetime to local timezone
    local_dt = to_local(utc_datetime)
"""
import os
from datetime import datetime, date, time
import pytz
from typing import Optional


# Get configured timezone from environment
TIMEZONE = os.getenv('TIMEZONE', 'Europe/Madrid')

# Create timezone object
try:
    APP_TIMEZONE = pytz.timezone(TIMEZONE)
except pytz.exceptions.UnknownTimeZoneError:
    # Fallback to Europe/Madrid if invalid timezone configured
    APP_TIMEZONE = pytz.timezone('Europe/Madrid')


def now() -> datetime:
    """
    Get current datetime in the application's configured timezone.

    This is the primary function to use instead of datetime.now() or datetime.utcnow().
    It returns a timezone-aware datetime that automatically handles DST transitions.

    Returns:
        datetime: Current datetime with timezone info

    Example:
        >>> current_time = now()
        >>> print(current_time)
        2026-02-05 14:30:45.123456+01:00
    """
    return datetime.now(APP_TIMEZONE)


def today() -> date:
    """
    Get current date in the application's configured timezone.

    Use this instead of date.today() to ensure the date respects the
    application's timezone (important when app is hosted in a different timezone).

    Returns:
        date: Current date in app's timezone

    Example:
        >>> current_date = today()
        >>> print(current_date)
        2026-02-05
    """
    return now().date()


def current_time() -> time:
    """
    Get current time in the application's configured timezone.

    Returns:
        time: Current time in app's timezone

    Example:
        >>> current_t = current_time()
        >>> print(current_t)
        14:30:45.123456
    """
    return now().time()


def to_local(dt: Optional[datetime], from_tz: str = 'UTC') -> Optional[datetime]:
    """
    Convert a datetime from one timezone to the application's local timezone.

    Args:
        dt: Datetime to convert (can be naive or aware)
        from_tz: Source timezone if dt is naive (default: 'UTC')

    Returns:
        datetime: Timezone-aware datetime in app's timezone, or None if input is None

    Example:
        >>> utc_dt = datetime(2026, 2, 5, 13, 30)  # Naive UTC time
        >>> local_dt = to_local(utc_dt)
        >>> print(local_dt)
        2026-02-05 14:30:00+01:00  # In Europe/Madrid (UTC+1 in winter)

        >>> # With aware datetime
        >>> utc_aware = datetime(2026, 2, 5, 13, 30, tzinfo=pytz.UTC)
        >>> local_dt = to_local(utc_aware)
    """
    if dt is None:
        return None

    # If datetime is naive, assume it's in from_tz
    if dt.tzinfo is None:
        source_tz = pytz.timezone(from_tz)
        dt = source_tz.localize(dt)

    # Convert to app's timezone
    return dt.astimezone(APP_TIMEZONE)


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert a datetime to UTC timezone.

    Args:
        dt: Datetime to convert (can be naive or aware)

    Returns:
        datetime: Timezone-aware datetime in UTC, or None if input is None

    Example:
        >>> local_dt = now()  # 2026-02-05 14:30:00+01:00
        >>> utc_dt = to_utc(local_dt)
        >>> print(utc_dt)
        2026-02-05 13:30:00+00:00
    """
    if dt is None:
        return None

    # If datetime is naive, assume it's in app's timezone
    if dt.tzinfo is None:
        dt = APP_TIMEZONE.localize(dt)

    # Convert to UTC
    return dt.astimezone(pytz.UTC)


def naive_to_aware(dt: datetime, tz: Optional[str] = None) -> datetime:
    """
    Convert a naive datetime to timezone-aware datetime.

    Args:
        dt: Naive datetime to convert
        tz: Timezone to use (default: app's timezone)

    Returns:
        datetime: Timezone-aware datetime

    Example:
        >>> naive_dt = datetime(2026, 2, 5, 14, 30)
        >>> aware_dt = naive_to_aware(naive_dt)
        >>> print(aware_dt)
        2026-02-05 14:30:00+01:00
    """
    if dt.tzinfo is not None:
        return dt  # Already aware

    timezone = pytz.timezone(tz) if tz else APP_TIMEZONE
    return timezone.localize(dt)


def aware_to_naive(dt: datetime, tz: Optional[str] = None) -> datetime:
    """
    Convert a timezone-aware datetime to naive datetime in specified timezone.

    Args:
        dt: Aware datetime to convert
        tz: Target timezone (default: app's timezone)

    Returns:
        datetime: Naive datetime in specified timezone

    Example:
        >>> aware_dt = now()
        >>> naive_dt = aware_to_naive(aware_dt)
    """
    if dt.tzinfo is None:
        return dt  # Already naive

    timezone = pytz.timezone(tz) if tz else APP_TIMEZONE
    local_dt = dt.astimezone(timezone)
    return local_dt.replace(tzinfo=None)


def get_timezone_name() -> str:
    """
    Get the configured timezone name.

    Returns:
        str: Timezone name (e.g., 'Europe/Madrid')
    """
    return TIMEZONE


def get_timezone_offset() -> str:
    """
    Get the current timezone offset from UTC (respects DST).

    Returns:
        str: Offset string (e.g., '+01:00' or '+02:00' during DST)

    Example:
        >>> offset = get_timezone_offset()
        >>> print(offset)
        +01:00  # In winter for Europe/Madrid
        +02:00  # In summer for Europe/Madrid (DST)
    """
    current = now()
    offset = current.strftime('%z')
    # Format as +HH:MM
    return f"{offset[:3]}:{offset[3:]}"


def is_dst() -> bool:
    """
    Check if Daylight Saving Time is currently active.

    Returns:
        bool: True if DST is active, False otherwise

    Example:
        >>> if is_dst():
        ...     print("DST is active (summer time)")
        ... else:
        ...     print("Standard time (winter)")
    """
    current = now()
    return bool(current.dst())
