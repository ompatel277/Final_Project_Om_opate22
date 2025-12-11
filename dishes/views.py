from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import JsonResponse
from .models import Dish, Restaurant, Cuisine, RestaurantDish
from .location_utils import filter_nearby_restaurants, get_user_location_from_request, set_user_location_in_session, \
    haversine_distance
from .maps_service import GoogleMapsService


def dish_list_view(request):
    """
        Browse restaurants - HYBRID APPROACH
        Fetches from Google Maps API and saves to database for full functionality
        """
    user_location = get_user_location_from_request(request)
    has_location = user_location is not None
    restaurants = []

    # Get filters
    cuisine_filter = request.GET.get('cuisine')
    price_filter = request.GET.get('price')
    if has_location:
        maps_service = GoogleMapsService()

        # Build search query based on filters

        query = "restaurants"
        if cuisine_filter:
            try:
                cuisine = Cuisine.objects.get(id=cuisine_filter)
                query = f"{cuisine.name} restaurants"
            except Cuisine.DoesNotExist:
                pass

        # Fetch real restaurants from Google Maps
        api_restaurants = maps_service.search_restaurants(
            query=query,
            latitude=user_location['latitude'],
            longitude=user_location['longitude'],
            zoom=14,
            num_results=30
        )

        # HYBRID: Save API restaurants to database and collect database objects
        for restaurant_data in api_restaurants:

            # Save to database (returns database object with ID)
            db_restaurant = maps_service.save_restaurant_to_db(restaurant_data)
            if db_restaurant:

                # Apply price filter if specified
                if price_filter and db_restaurant.price_range != price_filter:
                    continue

                # Add distance calculation
                if db_restaurant.latitude and db_restaurant.longitude:
                    db_restaurant.distance = haversine_distance(
                        user_location['latitude'],
                        user_location['longitude'],
                        db_restaurant.latitude,
                        db_restaurant.longitude
                    )
                else:
                    db_restaurant.distance = None
                restaurants.append(db_restaurant)

        # Sort by distance
        restaurants = sorted(
            [r for r in restaurants if r.distance is not None],
            key=lambda x: x.distance
        )
    else:
        # No location - show database restaurants
        db_restaurants = Restaurant.objects.filter(is_active=True)
        if cuisine_filter:
            db_restaurants = db_restaurants.filter(cuisine_type__id=cuisine_filter)
        if price_filter:
            db_restaurants = db_restaurants.filter(price_range=price_filter)
        restaurants = list(db_restaurants)

    # Get filter options
    cuisines = Cuisine.objects.all()
    context = {
        'restaurants': restaurants,
        'cuisines': cuisines,
        'has_location': has_location,
        'user_location': user_location,
    }
    return render(request, 'dishes/restaurant_list.html', context)


def restaurant_detail_view(request, restaurant_id):
    """View single restaurant details"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)

    user_location = get_user_location_from_request(request)
    if user_location and restaurant.latitude and restaurant.longitude:
        restaurant.distance = haversine_distance(
            user_location['latitude'],
            user_location['longitude'],
            restaurant.latitude,
            restaurant.longitude
        )

    # Get dishes available at this restaurant
    restaurant_dishes = RestaurantDish.objects.filter(
        restaurant=restaurant,
        is_available=True
    ).select_related('dish').order_by('dish__name')

    context = {
        'restaurant': restaurant,
        'restaurant_dishes': restaurant_dishes,
        'has_location': user_location is not None,
    }
    return render(request, 'dishes/restaurant_detail.html', context)


def cuisine_view(request, cuisine_id):
    """View all dishes from a specific cuisine"""
    cuisine = get_object_or_404(Cuisine, id=cuisine_id)
    dishes = Dish.objects.filter(cuisine=cuisine, is_active=True)

    context = {
        'cuisine': cuisine,
        'dishes': dishes,
    }
    return render(request, 'dishes/cuisine_dishes.html', context)


def search_view(request):
    """Search for dishes and restaurants"""
    query = request.GET.get('q', '')

    dishes = Dish.objects.none()
    restaurants = Restaurant.objects.none()

    if query:
        dishes = Dish.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True
        )

        restaurants = Restaurant.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True
        )

    context = {
        'query': query,
        'dishes': dishes,
        'restaurants': restaurants,
    }
    return render(request, 'dishes/search_results.html', context)


def nearby_restaurants(request):
    """

        Display nearby restaurants - HYBRID APPROACH
        Fetches from Google Maps API and saves to database
        """
    user_location = get_user_location_from_request(request)
    has_location = user_location is not None
    restaurants = []

    # Get filters
    distance_filter = request.GET.get('distance', '10')
    price_filter = request.GET.get('price')
    rating_filter = request.GET.get('rating')
    try:
        max_distance = float(distance_filter)
    except (ValueError, TypeError):
        max_distance = 10
    if has_location:
        maps_service = GoogleMapsService()

        # Fetch real restaurants from Google Maps
        api_restaurants = maps_service.search_restaurants(
            query="restaurants",
            latitude=user_location['latitude'],
            longitude=user_location['longitude'],
            zoom=14,
            num_results=40
        )

        # HYBRID: Save API restaurants to database and collect database objects
        for restaurant_data in api_restaurants:
            db_restaurant = maps_service.save_restaurant_to_db(restaurant_data)
            if db_restaurant:

                # Calculate distance
                if db_restaurant.latitude and db_restaurant.longitude:
                    db_restaurant.distance = haversine_distance(
                        user_location['latitude'],
                        user_location['longitude'],
                        db_restaurant.latitude,
                        db_restaurant.longitude
                    )

                    # Apply distance filter
                    if db_restaurant.distance > max_distance:
                        continue
                else:
                    continue

                # Apply price filter
                if price_filter and db_restaurant.price_range != price_filter:
                    continue

                # Apply rating filter
                if rating_filter:
                    try:
                        min_rating = float(rating_filter)
                        if db_restaurant.rating < min_rating:
                            continue
                    except (ValueError, TypeError):
                        pass
                restaurants.append(db_restaurant)

        # Sort by distance
        restaurants = sorted(restaurants, key=lambda x: x.distance)

    # Get favorite restaurant IDs for logged-in user
    favorite_ids = []
    if request.user.is_authenticated:
        from swipes.models import FavoriteRestaurant
        favorite_ids = list(
            FavoriteRestaurant.objects.filter(user=request.user)
            .values_list('restaurant_id', flat=True)
        )

    context = {
        'restaurants': restaurants,
        'has_location': has_location,
        'user_location': user_location,
        'selected_distance': distance_filter,
        'selected_price': price_filter,
        'selected_rating': rating_filter,
        'favorite_ids': favorite_ids,
    }
    return render(request, 'dishes/nearby_restaurants.html', context)


@login_required
def set_location_view(request):
    """AJAX endpoint to set user location in session"""
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            city = data.get('city', 'Unknown')

            if latitude and longitude:
                set_user_location_in_session(request, latitude, longitude, city)
                return JsonResponse({
                    'status': 'success',
                    'message': 'Location updated successfully',
                    'location': {
                        'latitude': latitude,
                        'longitude': longitude,
                        'city': city
                    }
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Missing latitude or longitude'
                }, status=400)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
