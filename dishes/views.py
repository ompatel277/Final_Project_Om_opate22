from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.http import JsonResponse
from .models import Dish, Restaurant, Cuisine, RestaurantDish
from .location_utils import filter_nearby_restaurants, get_user_location_from_request, set_user_location_in_session


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
    """View single dish details"""
    dish = get_object_or_404(Dish, id=dish_id, is_active=True)

    # Get restaurants serving this dish
    restaurant_dishes = RestaurantDish.objects.filter(
        dish=dish,
        is_available=True,
        restaurant__is_active=True
    ).select_related('restaurant').order_by('price')

    # ✅ LOCATION FILTER - Sort by distance if user has location
    user_location = get_user_location_from_request(request)
    if user_location and request.user.is_authenticated:
        max_distance = request.user.profile.max_distance_miles or 50
        restaurants = [rd.restaurant for rd in restaurant_dishes]
        nearby_restaurants = filter_nearby_restaurants(
            Restaurant.objects.filter(id__in=[r.id for r in restaurants]),
            user_location['latitude'],
            user_location['longitude'],
            max_distance
        )
        # Map distances back to restaurant_dishes
        distance_map = {r.id: r.distance for r in nearby_restaurants}
        for rd in restaurant_dishes:
            rd.distance = distance_map.get(rd.restaurant.id, 999)
        restaurant_dishes = sorted(restaurant_dishes, key=lambda x: x.distance)

    # Get ingredients
    ingredients = dish.ingredients.all()
    allergens = ingredients.filter(is_allergen=True)

    context = {
        'dish': dish,
        'restaurant_dishes': restaurant_dishes,
        'ingredients': ingredients,
        'allergens': allergens,
        'has_location': user_location is not None,
    }
    return render(request, 'dishes/dish_detail.html', context)


def restaurant_list_view(request):
    """Browse all restaurants - location-aware"""
    restaurants = Restaurant.objects.filter(is_active=True)

    # Filters
    city_filter = request.GET.get('city')
    cuisine_filter = request.GET.get('cuisine')
    price_filter = request.GET.get('price')

    if city_filter:
        restaurants = restaurants.filter(city__icontains=city_filter)

    if cuisine_filter:
        restaurants = restaurants.filter(cuisine_type__id=cuisine_filter)

    if price_filter:
        restaurants = restaurants.filter(price_range=price_filter)

    # ✅ LOCATION FILTER - Filter and sort by distance
    user_location = get_user_location_from_request(request)
    nearby_restaurants = []
    has_location = False

    if user_location and request.user.is_authenticated:
        has_location = True
        max_distance = request.user.profile.max_distance_miles or 50
        nearby_restaurants = filter_nearby_restaurants(
            restaurants,
            user_location['latitude'],
            user_location['longitude'],
            max_distance
        )
    else:
        # No location - show all restaurants (not filtered by distance)
        nearby_restaurants = list(restaurants)

    # Get unique cities
    cities = Restaurant.objects.filter(is_active=True).values_list('city', flat=True).distinct()
    cuisines = Cuisine.objects.all()

    context = {
        'restaurants': nearby_restaurants,
        'cities': cities,
        'cuisines': cuisines,
        'has_location': has_location,
    }
    return render(request, 'dishes/restaurant_list.html', context)


def restaurant_detail_view(request, restaurant_id):
    """View single restaurant details"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)

    # ✅ Calculate distance if user has location
    user_location = get_user_location_from_request(request)
    if user_location and restaurant.latitude and restaurant.longitude:
        from .location_utils import haversine_distance
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
        # Search dishes
        dishes = Dish.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            is_active=True
        )

        # Search restaurants
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
