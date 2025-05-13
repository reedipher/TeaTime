# src/utils/date_utils.py
from datetime import datetime, timedelta
import logging

# Set up logger
logger = logging.getLogger("teatime")

def calculate_next_available_date(target_weekday, max_days_ahead=7):
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

def calculate_target_saturday(max_days_ahead=7):
    """
    Calculate the next Saturday within the booking window
    Returns date in YYYY-MM-DD format or None if not available
    """
    # Saturday is weekday 5 (0=Monday, 6=Sunday)
    return calculate_next_available_date(5, max_days_ahead)

def calculate_target_sunday(max_days_ahead=7):
    """
    Calculate the next Sunday within the booking window
    Returns date in YYYY-MM-DD format or None if not available
    """
    # Sunday is weekday 6 (0=Monday, 6=Sunday)
    return calculate_next_available_date(6, max_days_ahead)

def calculate_available_dates(max_days_ahead=7):
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