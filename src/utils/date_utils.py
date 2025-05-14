# src/utils/date_utils.py
from datetime import datetime, timedelta
import logging

# Import the config loader
from src.utils.config_loader import get_value

# Set up logger
logger = logging.getLogger("teatime")

# Get the target day from configuration (default to Sunday if not set)
TARGET_DAY = get_value("booking", "target_day", "Sunday")

# Mapping of day names to weekday numbers (0=Monday, 6=Sunday)
DAY_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

def calculate_next_available_date(target_weekday, max_days_ahead=None):
    # Get booking window days from config or use default
    if max_days_ahead is None:
        from src.utils.config_loader import get_value
        max_days_ahead = get_value("system", "booking_window_days", 7)
    """
    Calculate the next date that falls on the target weekday and is within the
    booking window (not more than max_days_ahead days out)
    
    Args:
        target_weekday: Day of week (0=Monday, 6=Sunday)
        max_days_ahead: Maximum days in the future to look
        
    Returns:
        Date in YYYY-MM-DD format
    """
    today = datetime.now()
    
    # Calculate days until the next occurrence of target_weekday
    days_until_target = (target_weekday - today.weekday()) % 7
    
    # If days_until_target is 0, it means today is the target weekday
    # In that case, we're looking at the occurrence 7 days from now
    if days_until_target == 0:
        days_until_target = 7
    
    # Calculate the next target date
    next_target_date = today + timedelta(days=days_until_target)
    
    # Check if this date is within our booking window
    days_ahead = (next_target_date - today).days
    
    if days_ahead > max_days_ahead:
        logger.info(f"Next {target_weekday} is {days_ahead} days ahead, which exceeds the {max_days_ahead}-day booking window")
        return None
    
    logger.info(f"Calculated target date: {next_target_date.strftime('%Y-%m-%d')} ({days_ahead} days from today)")
    return next_target_date.strftime("%Y-%m-%d")

def calculate_target_day(day=None, max_days_ahead=None):
    """
    Calculate the next occurrence of the specified day within the booking window
    
    Args:
        day: Day name (e.g., "Sunday", "Monday") or None to use TARGET_DAY from config
        max_days_ahead: Maximum days in the future to look
        
    Returns:
        Date in YYYY-MM-DD format or None if not available
    """
    # If max_days_ahead is not specified, get from config
    if max_days_ahead is None:
        from src.utils.config_loader import get_value
        max_days_ahead = get_value("system", "booking_window_days", 7)
    
    # If no day specified, use the configured TARGET_DAY
    target_day = day if day else TARGET_DAY
    
    # Convert day name to weekday number
    if target_day in DAY_MAP:
        target_weekday = DAY_MAP[target_day]
        logger.info(f"Calculating next {target_day} within {max_days_ahead} days")
        return calculate_next_available_date(target_weekday, max_days_ahead)
    else:
        logger.error(f"Invalid day name: {target_day}. Must be one of {list(DAY_MAP.keys())}")
        # Default to Sunday if invalid day specified
        return calculate_next_available_date(6, max_days_ahead)

# Keep these for backward compatibility
def calculate_target_saturday(max_days_ahead=None):
    """
    Calculate the next Saturday within the booking window
    Returns date in YYYY-MM-DD format or None if not available
    """
    return calculate_target_day("Saturday", max_days_ahead)

def calculate_target_sunday(max_days_ahead=None):
    """
    Calculate the next Sunday within the booking window
    Returns date in YYYY-MM-DD format or None if not available
    """
    return calculate_target_day("Sunday", max_days_ahead)

def calculate_available_dates(max_days_ahead=None):
    # Get booking window days from config if not specified
    if max_days_ahead is None:
        from src.utils.config_loader import get_value
        max_days_ahead = get_value("system", "booking_window_days", 7)
    """
    Calculate all available dates within the booking window
    Returns a list of dates in YYYY-MM-DD format
    """
    today = datetime.now()
    dates = []
    
    for i in range(max_days_ahead + 1):
        date = today + timedelta(days=i)
        dates.append({
            'date': date.strftime("%Y-%m-%d"),
            'weekday': date.strftime("%A"),
            'days_ahead': i
        })
    
    return dates