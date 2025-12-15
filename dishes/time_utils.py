from django.utils import timezone
import pytz
from datetime import datetime


def get_current_meal_type(user_timezone=None):
    """Return the current meal type based on the user's local time.

    Time ranges:
    - Breakfast: 6:00 AM - 10:00 AM
    - Lunch: 10:30 AM - 4:30 PM
    - Dinner: 5:00 PM - 11:30 PM
    - Outside these hours: defaults to the nearest meal

    Args:
        user_timezone: User's timezone string (e.g., 'America/New_York').
                      If None, uses server's local time.
    """
    # Get current time in user's timezone
    if user_timezone:
        try:
            tz = pytz.timezone(user_timezone)
            current_time = datetime.now(tz)
        except Exception:
            # Fall back to server time if timezone is invalid
            current_time = timezone.localtime(timezone.now())
    else:
        current_time = timezone.localtime(timezone.now())

    hour = current_time.hour
    minute = current_time.minute

    # Convert to total minutes for easier comparison
    total_minutes = hour * 60 + minute

    # Breakfast: 6:00 AM (360) - 10:00 AM (600)
    breakfast_start = 6 * 60  # 360
    breakfast_end = 10 * 60  # 600

    # Lunch: 10:30 AM (630) - 4:30 PM (990)
    lunch_start = 10 * 60 + 30  # 630
    lunch_end = 16 * 60 + 30  # 990

    # Dinner: 5:00 PM (1020) - 11:30 PM (1410)
    dinner_start = 17 * 60  # 1020
    dinner_end = 23 * 60 + 30  # 1410

    if breakfast_start <= total_minutes <= breakfast_end:
        return 'breakfast'
    elif lunch_start <= total_minutes <= lunch_end:
        return 'lunch'
    elif dinner_start <= total_minutes <= dinner_end:
        return 'dinner'
    else:
        # Outside defined meal times, default based on time of day
        if total_minutes < breakfast_start:
            # Before 6 AM - show breakfast (early morning)
            return 'breakfast'
        elif breakfast_end < total_minutes < lunch_start:
            # Between 10:00 AM and 10:30 AM - show breakfast (closer to breakfast)
            return 'breakfast'
        elif lunch_end < total_minutes < dinner_start:
            # Between 4:30 PM and 5:00 PM - show dinner (closer to dinner)
            return 'dinner'
        else:
            # After 11:30 PM - show dinner (late night)
            return 'dinner'


def get_current_meal_window(user_timezone=None):
    """Return the start of the current eating hour and its meal type.

    Args:
        user_timezone: User's timezone string (e.g., 'America/New_York').
                      If None, uses server's local time.
    """
    # Get current time in user's timezone
    if user_timezone:
        try:
            tz = pytz.timezone(user_timezone)
            current_time = datetime.now(tz)
        except Exception:
            current_time = timezone.localtime(timezone.now())
    else:
        current_time = timezone.localtime(timezone.now())

    window_start = current_time.replace(minute=0, second=0, microsecond=0)
    return window_start, get_current_meal_type(user_timezone)
