from django.utils import timezone


def get_current_meal_type(now=None):
    """Return the current meal type based on the local hour."""
    current_time = timezone.localtime(now or timezone.now())
    hour = current_time.hour

    if 5 <= hour < 11:
        return 'breakfast'
    if 11 <= hour < 16:
        return 'lunch'
    return 'dinner'


def get_current_meal_window(now=None):
    """Return the start of the current eating hour and its meal type."""
    current_time = timezone.localtime(now or timezone.now())
    window_start = current_time.replace(minute=0, second=0, microsecond=0)
    return window_start, get_current_meal_type(current_time)
