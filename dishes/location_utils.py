"""
Location utility functions for distance calculations and filtering
"""
from math import radians, cos, sin, asin, sqrt
from django.db.models import F, FloatField
from django.db.models.functions import ACos, Cos, Radians, Sin


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    Returns distance in miles
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    # Radius of earth in miles
    miles = 3959 * c
    return miles


DEFAULT_MAX_DISTANCE_MILES = 10


def filter_nearby_restaurants(restaurants_queryset, user_lat, user_lng, max_distance_miles=DEFAULT_MAX_DISTANCE_MILES):
    """
    Filter restaurants within max_distance_miles of user location
    Returns queryset with annotated 'distance' field
    """
    from dishes.models import Restaurant

    nearby_restaurants = []
    for restaurant in restaurants_queryset:
        if restaurant.latitude and restaurant.longitude:
            distance = haversine_distance(
                user_lat, user_lng,
                restaurant.latitude, restaurant.longitude
            )
            if distance <= max_distance_miles:
                restaurant.distance = distance
                nearby_restaurants.append(restaurant)

    # Sort by distance
    nearby_restaurants.sort(key=lambda x: x.distance)
    return nearby_restaurants


def get_dishes_from_nearby_restaurants(user_lat, user_lng, max_distance_miles=DEFAULT_MAX_DISTANCE_MILES):
    """
    Get all dishes available at nearby restaurants
    Returns list of dish IDs
    """
    from dishes.models import Restaurant, RestaurantDish

    # Get nearby restaurants
    all_restaurants = Restaurant.objects.filter(
        is_active=True,
        latitude__isnull=False,
        longitude__isnull=False
    )

    nearby_restaurants = []
    for restaurant in all_restaurants:
        distance = haversine_distance(
            user_lat, user_lng,
            restaurant.latitude, restaurant.longitude
        )
        if distance <= max_distance_miles:
            nearby_restaurants.append(restaurant.id)

    # Get dishes from these restaurants
    dish_ids = RestaurantDish.objects.filter(
        restaurant_id__in=nearby_restaurants,
        is_available=True
    ).values_list('dish_id', flat=True).distinct()

    return list(dish_ids)


def get_user_location_from_request(request):
    """
    Get user location from session
    Returns dict with latitude, longitude, city, or None
    """
    location = request.session.get('user_location')
    if location and location.get('latitude') and location.get('longitude'):
        return location
    return None


def set_user_location_in_session(request, latitude, longitude, city=None):
    """
    Store user location in session
    """
    request.session['user_location'] = {
        'latitude': float(latitude),
        'longitude': float(longitude),
        'city': city or 'Unknown'
    }
    request.session.modified = True
