"""
Time utilities for Manila timezone and human-readable formatting.
Uses Asia/Manila (PHT) consistently across the application.
"""
from datetime import datetime, timedelta, timezone

# Manila timezone is UTC+8 fixed offset
MANILA_TZ = timezone(timedelta(hours=8))


def get_manila_now():
    """Get current time in Manila timezone."""
    return datetime.now(MANILA_TZ)


def to_manila_time(dt):
    """Convert UTC or naive datetime to Manila timezone."""
    if dt is None:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(MANILA_TZ)


def format_checkin_time(dt):
    """
    Format check-in time as HH:MM AM/PM (Manila time).
    Example: 02:23 PM
    """
    if dt is None:
        return "N/A"

    manila_dt = to_manila_time(dt)
    return manila_dt.strftime("%I:%M %p")


def format_checkout_time(dt):
    """
    Format check-out time as HH:MM AM/PM (Manila time).
    Example: 02:28 PM
    Returns 'N/A' if dt is None.
    """
    if dt is None:
        return "N/A"

    manila_dt = to_manila_time(dt)
    return manila_dt.strftime("%I:%M %p")


def format_date(dt):
    """
    Format date as 'Mon DD, YYYY' (Manila time).
    Example: May 29, 2026
    """
    if dt is None:
        return "N/A"

    manila_dt = to_manila_time(dt)
    return manila_dt.strftime("%b %d, %Y")


def decimal_hours_to_readable(decimal_hours):
    """
    Convert decimal hours to a human-readable format.

    Examples:
    - 0.08 hours (4.8 minutes) -> "5 mins"
    - 1.5 hours -> "1 hr 30 mins"
    - 0.5 hours -> "30 mins"
    - 2.0 hours -> "2 hrs"
    - 0.0 hours -> "0 mins"
    """
    if decimal_hours is None or decimal_hours < 0:
        return "0 mins"

    if decimal_hours == 0:
        return "0 mins"

    total_seconds = int(decimal_hours * 3600)
    hours = total_seconds // 3600
    remaining_seconds = total_seconds % 3600
    minutes = remaining_seconds // 60

    if hours == 0:
        return f"{minutes} min" if minutes == 1 else f"{minutes} mins"
    elif minutes == 0:
        return f"{hours} hr" if hours == 1 else f"{hours} hrs"
    else:
        hrs_label = "hr" if hours == 1 else "hrs"
        mins_label = "min" if minutes == 1 else "mins"
        return f"{hours} {hrs_label} {minutes} {mins_label}"
