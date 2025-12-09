from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import JsonResponse
from .models import Dish, Restaurant, Cuisine, RestaurantDish
from .location_utils import filter_nearby_restaurants, get_user_location_from_request, set_user_location_in_session, \
    haversine_distance
from .maps_service import GoogleMapsService


def dish_list_view(request):
    """Browse all dishes"""
    dishes = Dish.objects.filter(is_active=True).select_related('cuisine')

    # Filters
    cuisine_filter = request.GET.get('cuisine')
    meal_type_filter = request.GET.get('meal_type')
    dietary_filter = request.GET.get('dietary')

    if cuisine_filter:
        dishes = dishes.filter(cuisine__id=cuisine_filter)

    if meal_type_filter:
        dishes = dishes.filter(meal_type=meal_type_filter)

    if dietary_filter:
        if dietary_filter == 'vegetarian':
            dishes = dishes.filter(is_vegetarian=True)
        elif dietary_filter == 'vegan':
            dishes = dishes.filter(is_vegan=True)
        elif dietary_filter == 'gluten_free':
            dishes = dishes.filter(is_gluten_free=True)

    cuisines = Cuisine.objects.all()

    context = {
        'dishes': dishes,
        'cuisines': cuisines,
    }
    return render(request, 'dishes/dish_list.html', context)


def dish_detail_view(request, dish_id):
    """View single dish details with LIVE local restaurants"""
    dish = get_object_or_404(Dish, id=dish_id, is_active=True)

    user_location = get_user_location_from_request(request)
    local_restaurants = []

    # ✅ FETCH REAL LOCAL RESTAURANTS SERVING THIS DISH
    if user_location:
        maps_service = GoogleMapsService()

        # Search for restaurants serving this specific dish
        restaurants_data = maps_service.search_restaurants_by_dish(
            dish_name=dish.name,
            latitude=user_location['latitude'],
            longitude=user_location['longitude'],
            zoom=14,
            num_results=20
        )

        # Parse and add distance
        for restaurant_data in restaurants_data:
            parsed = maps_service.parse_restaurant_data(restaurant_data)

            if parsed['latitude'] and parsed['longitude']:
                parsed['distance'] = haversine_distance(
                    user_location['latitude'],
                    user_location['longitude'],
                    parsed['latitude'],
                    parsed['longitude']
                )
                local_restaurants.append(parsed)

        # Sort by distance
        local_restaurants.sort(key=lambda x: x.get('distance', 999))

    # Get ingredients
    ingredients = dish.ingredients.all()
    allergens = ingredients.filter(is_allergen=True)

    # Check if user favorited this dish
    is_favorited = False
    if request.user.is_authenticated:
        from swipes.models import Favorite
        is_favorited = Favorite.objects.filter(user=request.user, dish=dish).exists()

    context = {
        'dish': dish,
        'local_restaurants': local_restaurants,  # LIVE API DATA
        'ingredients': ingredients,
        'allergens': allergens,
        'has_location': user_location is not None,
        'user_location': user_location,
        'is_favorited': is_favorited,
    }
    return render(request, 'dishes/dish_detail.html', context)


def restaurant_list_view(request):
    """Browse restaurants - LIVE API DATA from Google Maps"""
    user_location = get_user_location_from_request(request)
    has_location = user_location is not None

    restaurants = []
    api_restaurants = []

    # Get filters
    cuisine_filter = request.GET.get('cuisine')
    price_filter = request.GET.get('price')
    use_live_data = request.GET.get('live', 'true').lower() == 'true'

    if has_location and use_live_data:
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

        # Parse and filter API results
        for restaurant_data in api_restaurants:
            parsed = maps_service.parse_restaurant_data(restaurant_data)

            # Apply price filter if specified
            if price_filter and parsed['price_range'] != price_filter:
                continue

            # Add distance calculation
            if parsed['latitude'] and parsed['longitude']:
                parsed['distance'] = haversine_distance(
                    user_location['latitude'],
                    user_location['longitude'],
                    parsed['latitude'],
                    parsed['longitude']
                )
            else:
                parsed['distance'] = None

            restaurants.append(parsed)

        # Sort by distance
        restaurants = sorted(
            [r for r in restaurants if r['distance'] is not None],
            key=lambda x: x['distance']
        )
    else:
        # Fallback to database restaurants
        db_restaurants = Restaurant.objects.filter(is_active=True)

        if cuisine_filter:
            db_restaurants = db_restaurants.filter(cuisine_type__id=cuisine_filter)

        if price_filter:
            db_restaurants = db_restaurants.filter(price_range=price_filter)

        if user_location:
            max_distance = request.user.profile.max_distance_miles if request.user.is_authenticated else 50
            restaurants = filter_nearby_restaurants(
                db_restaurants,
                user_location['latitude'],
                user_location['longitude'],
                max_distance
            )
        else:
            restaurants = list(db_restaurants)

    # Get filter options
    cities = Restaurant.objects.filter(is_active=True).values_list('city', flat=True).distinct()
    cuisines = Cuisine.objects.all()

    context = {
        'restaurants': restaurants,
        'api_restaurants': api_restaurants,
        'cities': cities,
        'cuisines': cuisines,
        'has_location': has_location,
        'using_live_data': use_live_data and has_location,
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
    """Display page to find nearby restaurants"""
    return render(request, 'dishes/nearby_restaurants.html')


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
