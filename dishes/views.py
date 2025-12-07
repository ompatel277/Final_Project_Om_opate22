from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from .models import Dish, Restaurant, Cuisine, RestaurantDish


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

    # Get ingredients
    ingredients = dish.ingredients.all()
    allergens = ingredients.filter(is_allergen=True)

    context = {
        'dish': dish,
        'restaurant_dishes': restaurant_dishes,
        'ingredients': ingredients,
        'allergens': allergens,
    }
    return render(request, 'dishes/dish_detail.html', context)


def restaurant_list_view(request):
    """Browse all restaurants"""
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

    # Get unique cities
    cities = Restaurant.objects.filter(is_active=True).values_list('city', flat=True).distinct()
    cuisines = Cuisine.objects.all()

    context = {
        'restaurants': restaurants,
        'cities': cities,
        'cuisines': cuisines,
    }
    return render(request, 'dishes/restaurant_list.html', context)


def restaurant_detail_view(request, restaurant_id):
    """View single restaurant details"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)

    # Get dishes available at this restaurant
    restaurant_dishes = RestaurantDish.objects.filter(
        restaurant=restaurant,
        is_available=True
    ).select_related('dish').order_by('dish__name')

    context = {
        'restaurant': restaurant,
        'restaurant_dishes': restaurant_dishes,
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
