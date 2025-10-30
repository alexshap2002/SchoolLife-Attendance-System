"""Timezone utilities for reliable UTC handling."""

from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
from typing import List

KYIV = ZoneInfo("Europe/Kyiv")


def to_utc(dt_local: datetime) -> datetime:
    """Convert local time to UTC."""
    if dt_local.tzinfo is None:
        dt_local = dt_local.replace(tzinfo=KYIV)
    return dt_local.astimezone(timezone.utc)


def from_utc_to_kyiv(dt_utc: datetime) -> datetime:
    """Convert UTC time to Kyiv local time."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(KYIV)


def next_n_weekly(local_weekday: int, local_hour: int, local_minute: int, n: int = 8, include_today: bool = True) -> List[datetime]:
    """Generate next N weekly occurrences in UTC.
    
    Args:
        local_weekday: 0=Monday, 1=Tuesday, ..., 6=Sunday
        local_hour: Hour in Kyiv time (0-23)
        local_minute: Minute (0-59)
        n: Number of occurrences to generate
        include_today: Include today if time hasn't passed yet
        
    Returns:
        List of datetime objects in UTC
    """
    import logging
    logger = logging.getLogger(__name__)
    
    now_local = datetime.now(KYIV)
    first_local = now_local.replace(hour=local_hour, minute=local_minute, second=0, microsecond=0)
    
    # Calculate days ahead to next occurrence
    days_ahead = (local_weekday - first_local.weekday()) % 7
    
    logger.info(f"next_n_weekly: target_weekday={local_weekday}, today={first_local.weekday()}, time={local_hour}:{local_minute}, now={now_local.strftime('%H:%M')}, days_ahead={days_ahead}")
    
    if days_ahead == 0:
        # Today is the target weekday
        if include_today and first_local > now_local:
            # Time hasn't passed yet - include today
            days_ahead = 0
            logger.info(f"Including today: time {local_hour}:{local_minute} > now {now_local.strftime('%H:%M')}")
        else:
            # Time already passed or not including today - next week
            days_ahead = 7
            logger.info(f"Skipping today: time {local_hour}:{local_minute} <= now {now_local.strftime('%H:%M')} or include_today={include_today}")
    
    first_local = first_local + timedelta(days=days_ahead)
    first_utc = first_local.astimezone(timezone.utc)
    
    logger.info(f"First occurrence: {first_local} (local) = {first_utc} (UTC)")
    
    return [first_utc + timedelta(days=7*i) for i in range(n)]


def now_utc() -> datetime:
    """Get current time in UTC."""
    return datetime.now(timezone.utc)


def parse_time_string(time_str: str) -> time:
    """Parse time string like '14:30' or '14:30:00'."""
    parts = time_str.split(':')
    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) > 2 else 0
    return time(hour, minute, second)


def combine_date_time_to_utc(date_obj, time_obj) -> datetime:
    """Combine date and time objects and convert to UTC."""
    local_dt = datetime.combine(date_obj, time_obj, tzinfo=KYIV)
    return local_dt.astimezone(timezone.utc)
