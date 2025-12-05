from django.shortcuts import render
from django.db.models import Q
from dishes.models import Dish, Restaurant, Cuisine
from community.models import Review


def global_search_view(request):
    """Global search across dishes, restaurants, and reviews"""
    query = request.GET.get('q', '').strip()

    results = {
        'dishes': [],
        'restaurants': [],
        'cuisines': [],
        'query': query,
    }

    if query:
        # Search dishes
        results['dishes'] = Dish.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(cuisine__name__icontains=query),
            is_active=True
        ).select_related('cuisine')[:20]

        # Search restaurants
        results['restaurants'] = Restaurant.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(city__icontains=query) |
            Q(cuisine_type__name__icontains=query),
            is_active=True
        ).select_related('cuisine_type')[:20]

        # Search cuisines
        results['cuisines'] = Cuisine.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )[:10]

    return render(request, 'search/search_results.html', results)


def advanced_search_view(request):
    """Advanced search with multiple filters"""
    dishes = Dish.objects.filter(is_active=True).select_related('cuisine')

    # Get filter parameters
    query = request.GET.get('q', '')
    cuisine_id = request.GET.get('cuisine')
    meal_type = request.GET.get('meal_type')
    max_calories = request.GET.get('max_calories')
    min_protein = request.GET.get('min_protein')
    diet_type = request.GET.get('diet_type')
    max_price = request.GET.get('max_price')

    # Apply filters
    if query:
        dishes = dishes.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    if cuisine_id:
        dishes = dishes.filter(cuisine_id=cuisine_id)

    if meal_type:
        dishes = dishes.filter(meal_type=meal_type)

    if max_calories:
        dishes = dishes.filter(calories__lte=int(max_calories))

    if min_protein:
        dishes = dishes.filter(protein__gte=int(min_protein))

    if diet_type:
        if diet_type == 'vegetarian':
            dishes = dishes.filter(is_vegetarian=True)
        elif diet_type == 'vegan':
            dishes = dishes.filter(is_vegan=True)
        elif diet_type == 'gluten_free':
            dishes = dishes.filter(is_gluten_free=True)

    # Get all cuisines for filter dropdown
    cuisines = Cuisine.objects.all()

    context = {
        'dishes': dishes,
        'cuisines': cuisines,
        'query': query,
        'selected_cuisine': cuisine_id,
        'selected_meal_type': meal_type,
        'max_calories': max_calories,
        'min_protein': min_protein,
        'diet_type': diet_type,
    }

    return render(request, 'search/advanced_search.html', context)


def autocomplete_view(request):
    """Autocomplete suggestions for search"""
    from django.http import JsonResponse

    query = request.GET.get('q', '').strip()
    suggestions = []

    if query and len(query) >= 2:
        # Get dish suggestions
        dishes = Dish.objects.filter(
            name__icontains=query,
            is_active=True
        ).values('id', 'name', 'cuisine__name')[:5]

        for dish in dishes:
            suggestions.append({
                'type': 'dish',
                'id': dish['id'],
                'name': dish['name'],
                'cuisine': dish['cuisine__name'],
            })

        # Get restaurant suggestions
        restaurants = Restaurant.objects.filter(
            name__icontains=query,
            is_active=True
        ).values('id', 'name', 'city')[:5]

        for restaurant in restaurants:
            suggestions.append({
                'type': 'restaurant',
                'id': restaurant['id'],
                'name': restaurant['name'],
                'city': restaurant['city'],
            })

    return JsonResponse({'suggestions': suggestions})