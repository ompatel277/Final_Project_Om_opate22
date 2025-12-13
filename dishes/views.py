from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import JsonResponse
from swipes.models import Favorite
from .models import Dish, Restaurant, Cuisine, RestaurantDish
from .location_utils import (
    DEFAULT_MAX_DISTANCE_MILES,
    filter_nearby_restaurants,
    get_user_location_from_request,
    set_user_location_in_session,
    haversine_distance,
)
from .maps_service import GoogleMapsService
from .time_utils import get_current_meal_type


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


def dish_detail_view(request, dish_id):
    """View detailed dish information and where to find it."""
    dish = get_object_or_404(Dish, id=dish_id, is_active=True)
    user_location = get_user_location_from_request(request)

    restaurant_qs = Restaurant.objects.filter(
        restaurant_dishes__dish=dish,
        restaurant_dishes__is_available=True
    ).distinct().select_related('cuisine_type')

    restaurants = []
    if user_location:
        for restaurant in restaurant_qs:
            if restaurant.latitude and restaurant.longitude:
                restaurant.distance = haversine_distance(
                    user_location['latitude'],
                    user_location['longitude'],
                    restaurant.latitude,
                    restaurant.longitude
                )
            restaurants.append(restaurant)
        restaurants.sort(key=lambda r: r.distance if hasattr(r, 'distance') and r.distance is not None else float('inf'))
    else:
        restaurants = list(restaurant_qs)

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, dish=dish).exists()

    context = {
        'dish': dish,
        'restaurants': restaurants,
        'user_location': user_location,
        'is_favorite': is_favorite,
    }
    return render(request, 'dishes/dish_detail.html', context)


def restaurant_list_view(request):
    """Browse restaurants with optional filters and sorting."""
    user_location = get_user_location_from_request(request)

    query = request.GET.get('q', '')
    price_filter = request.GET.get('price')
    rating_filter = request.GET.get('rating')
    sort = request.GET.get('sort', 'name')

    restaurants_qs = Restaurant.objects.filter(is_active=True)

    if query:
        restaurants_qs = restaurants_qs.filter(
            Q(name__icontains=query) | Q(address__icontains=query) | Q(city__icontains=query)
        )

    if price_filter:
        restaurants_qs = restaurants_qs.filter(price_range=price_filter)

    if rating_filter:
        try:
            restaurants_qs = restaurants_qs.filter(rating__gte=float(rating_filter))
        except (ValueError, TypeError):
            pass

    restaurants = list(restaurants_qs)

    if user_location and sort == 'distance':
        for restaurant in restaurants:
            if restaurant.latitude and restaurant.longitude:
                restaurant.distance = haversine_distance(
                    user_location['latitude'],
                    user_location['longitude'],
                    restaurant.latitude,
                    restaurant.longitude
                )
        restaurants = [r for r in restaurants if hasattr(r, 'distance')]
        restaurants.sort(key=lambda r: r.distance)
    else:
        if sort == 'rating':
            restaurants_qs = restaurants_qs.order_by('-rating')
        elif sort == 'name':
            restaurants_qs = restaurants_qs.order_by('name')
        restaurants = list(restaurants_qs)

    restaurant_count = len(restaurants)

    context = {
        'restaurants': restaurants,
        'restaurant_count': restaurant_count,
        'user_location': user_location,
        'query': query,
        'selected_price': price_filter,
        'selected_rating': rating_filter,
        'sort': sort,
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
    current_meal_type = get_current_meal_type()

    # Get filters
    distance_filter = str(DEFAULT_MAX_DISTANCE_MILES)
    price_filter = request.GET.get('price')
    rating_filter = request.GET.get('rating')
    max_distance = DEFAULT_MAX_DISTANCE_MILES
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
                related_dishes = db_restaurant.restaurant_dishes.all()
                if related_dishes.exists():
                    if not related_dishes.filter(dish__meal_type=current_meal_type, is_available=True).exists():
                        continue

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


def geocode_location_view(request):
    """AJAX endpoint to geocode a city name or ZIP code using Google Maps"""
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()

        if not query:
            return JsonResponse({
                'status': 'error',
                'message': 'Please enter a city or ZIP code'
            }, status=400)

        try:
            from serpapi import GoogleSearch
            from django.conf import settings

            api_key = settings.SERPAPI_KEY
            if not api_key:
                # Fallback to Nominatim if no SerpApi key
                import urllib.request
                import json

                url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(query)}&limit=1"
                req = urllib.request.Request(url, headers={'User-Agent': 'SwipeBite/1.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())

                if data:
                    result = data[0]
                    lat = float(result['lat'])
                    lng = float(result['lon'])
                    # Extract city name
                    display_parts = result.get('display_name', '').split(',')
                    city = display_parts[0].strip() if display_parts else query

                    return JsonResponse({
                        'status': 'success',
                        'latitude': lat,
                        'longitude': lng,
                        'city': city
                    })
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Location not found'
                    }, status=404)

            # Use Google Maps via SerpApi
            params = {
                "engine": "google_maps",
                "q": query,
                "type": "search",
                "api_key": api_key
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            # Try to get location from place_results or local_results
            place_results = results.get('place_results', {})
            local_results = results.get('local_results', [])

            lat = None
            lng = None
            city = query

            # First check place_results
            if place_results:
                gps = place_results.get('gps_coordinates', {})
                lat = gps.get('latitude')
                lng = gps.get('longitude')
                city = place_results.get('title', query)

            # If not found, try local_results
            if (lat is None or lng is None) and local_results:
                first_result = local_results[0]
                gps = first_result.get('gps_coordinates', {})
                lat = gps.get('latitude')
                lng = gps.get('longitude')
                city = first_result.get('title', query).split(' - ')[0]

            # If still not found, try the search_information
            if lat is None or lng is None:
                search_info = results.get('search_information', {})
                if 'location' in search_info:
                    # Make another search specifically for the location
                    location_params = {
                        "engine": "google_maps",
                        "q": f"{query} city",
                        "type": "search",
                        "api_key": api_key
                    }
                    location_search = GoogleSearch(location_params)
                    location_results = location_search.get_dict()

                    local = location_results.get('local_results', [])
                    if local:
                        gps = local[0].get('gps_coordinates', {})
                        lat = gps.get('latitude')
                        lng = gps.get('longitude')

            if lat is not None and lng is not None:
                return JsonResponse({
                    'status': 'success',
                    'latitude': lat,
                    'longitude': lng,
                    'city': city
                })
            else:
                # Fallback to Nominatim
                import urllib.request
                import urllib.parse
                import json

                url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(query)}&limit=1"
                req = urllib.request.Request(url, headers={'User-Agent': 'SwipeBite/1.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())

                if data:
                    result = data[0]
                    return JsonResponse({
                        'status': 'success',
                        'latitude': float(result['lat']),
                        'longitude': float(result['lon']),
                        'city': result.get('display_name', '').split(',')[0].strip()
                    })

                return JsonResponse({
                    'status': 'error',
                    'message': 'Location not found. Please try a different search.'
                }, status=404)

        except Exception as e:
            # Final fallback to Nominatim
            try:
                import urllib.request
                import urllib.parse
                import json

                url = f"https://nominatim.openstreetmap.org/search?format=json&q={urllib.parse.quote(query)}&limit=1"
                req = urllib.request.Request(url, headers={'User-Agent': 'SwipeBite/1.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())

                if data:
                    result = data[0]
                    return JsonResponse({
                        'status': 'success',
                        'latitude': float(result['lat']),
                        'longitude': float(result['lon']),
                        'city': result.get('display_name', '').split(',')[0].strip()
                    })
            except:
                pass

            return JsonResponse({
                'status': 'error',
                'message': f'Error finding location: {str(e)}'
            }, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
