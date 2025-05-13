# src/utils/date_utils.py
from datetime import datetime, timedelta

def calculate_target_saturday():
    """
    Calculate the target Saturday date that is at least 8 days in the future.
    Returns date in YYYY-MM-DD format.
    """
    today = datetime.now()
    
    # Calculate days until next Saturday (weekday 5)
    days_until_saturday = (5 - today.weekday()) % 7
    
    # If today is Saturday, we want next Saturday
    if days_until_saturday == 0:
        days_until_saturday = 7
    
    # Add days to get to next Saturday
    next_saturday = today + timedelta(days=days_until_saturday)
    
    # Ensure we're looking at least 8 days ahead
    if (next_saturday - today).days < 8:
        next_saturday = next_saturday + timedelta(days=7)
    
    # Format date as YYYY-MM-DD
    return next_saturday.strftime("%Y-%m-%d")

def calculate_dates_range(days_ahead=8, num_days=1):
    """
    Calculate a range of dates starting from X days ahead.
    Returns a list of dates in YYYY-MM-DD format.
    """
    today = datetime.now()
    start_date = today + timedelta(days=days_ahead)
    
    dates = []
    for i in range(num_days):
        date = start_date + timedelta(days=i)
        dates.append(date.strftime("%Y-%m-%d"))
    
    return dates