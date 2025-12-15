from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from dishes.models import Dish, Restaurant, Cuisine
from dishes.location_utils import (
    DEFAULT_MAX_DISTANCE_MILES,
    get_dishes_from_nearby_restaurants,
    get_user_location_from_request,
    get_user_timezone_from_request,
    haversine_distance,
)
from dishes.maps_service import GoogleMapsService
from dishes.time_utils import get_current_meal_type, get_current_meal_window
from .models import SwipeAction, Favorite, FavoriteRestaurant, Blacklist, SwipeSession
import random


@login_required
def swipe_feed_view(request):
    """Main swipe interface - shows dishes based on location and preferences"""
    user_location = get_user_location_from_request(request)
    user_timezone = get_user_timezone_from_request(request)
    current_meal_type = get_current_meal_type(user_timezone)

    # Get user's blacklisted items
    blacklist = Blacklist.objects.filter(user=request.user)
    blacklisted_dish_ids = blacklist.filter(blacklist_type='dish', dish__isnull=False).values_list('dish_id', flat=True)

    # Only exclude RIGHT swipes and blacklisted dishes (left swipes can come back)
    right_swiped_dish_ids = SwipeAction.objects.filter(
        user=request.user,
        direction='right'
    ).values_list('dish_id', flat=True)

    # Get filter parameters from request
    cuisine_filter = request.GET.get('cuisine')
    dietary_filter = request.GET.get('dietary')
    meal_filter = request.GET.get('meal')  # Allow user to filter by meal type

    # Apply user preferences from profile
    profile = request.user.profile

    # Start with ALL active dishes, then apply filters progressively
    available_dishes = Dish.objects.filter(is_active=True).exclude(
        id__in=right_swiped_dish_ids
    ).exclude(
        id__in=blacklisted_dish_ids
    )

    # Determine which meal filter to use and what to show as selected
    if meal_filter and meal_filter != 'all':
        # User explicitly selected a meal type
        available_dishes = available_dishes.filter(meal_type=meal_filter)
        selected_meal = meal_filter
    elif meal_filter == 'all':
        # User explicitly selected "All Meals"
        selected_meal = 'all'
        # Don't filter by meal type - show all
    else:
        # No filter specified - default to current meal type based on time
        current_meal_dishes = available_dishes.filter(meal_type=current_meal_type)
        if current_meal_dishes.exists():
            available_dishes = current_meal_dishes
            selected_meal = current_meal_type  # Show current meal as selected
        else:
            # No dishes for current meal type, show all
            selected_meal = 'all'

    # Filter by dietary preferences (profile default or user filter)
    if dietary_filter and dietary_filter != 'all':
        if dietary_filter == 'vegetarian':
            available_dishes = available_dishes.filter(is_vegetarian=True)
        elif dietary_filter == 'vegan':
            available_dishes = available_dishes.filter(is_vegan=True)
        elif dietary_filter == 'non_veg':
            available_dishes = available_dishes.filter(is_vegetarian=False, is_vegan=False)
    elif profile.diet_type == 'vegetarian':
        available_dishes = available_dishes.filter(is_vegetarian=True)
    elif profile.diet_type == 'vegan':
        available_dishes = available_dishes.filter(is_vegan=True)

    # Filter by allergies from profile
    if profile.allergies:
        allergies = profile.get_allergies_list()
        for allergy in allergies:
            available_dishes = available_dishes.exclude(
                ingredients__name__icontains=allergy,
                ingredients__is_allergen=True
            )

    # Apply cuisine filter if selected
    if cuisine_filter and cuisine_filter != 'all':
        try:
            selected_cuisine = Cuisine.objects.get(id=cuisine_filter)
            available_dishes = available_dishes.filter(cuisine=selected_cuisine)
        except Cuisine.DoesNotExist:
            pass

    # Location-based filtering (OPTIONAL - only if we get results)
    relevant_cuisines = []
    if user_location:
        # Try to get dishes from nearby restaurants in our database first
        nearby_dish_ids = get_dishes_from_nearby_restaurants(
            user_location['latitude'],
            user_location['longitude'],
            DEFAULT_MAX_DISTANCE_MILES
        )

        if nearby_dish_ids:
            # Check if filtering by nearby dishes would give us results
            nearby_dishes = available_dishes.filter(id__in=nearby_dish_ids)
            if nearby_dishes.exists():
                available_dishes = nearby_dishes

        # Try Google Maps API for cuisine relevance (but don't require it)
        if not cuisine_filter or cuisine_filter == 'all':
            try:
                maps_service = GoogleMapsService()
                local_restaurants = maps_service.search_restaurants(
                    query="restaurants",
                    latitude=user_location['latitude'],
                    longitude=user_location['longitude'],
                    zoom=14,
                    num_results=30
                )

                # Extract cuisine keywords from local restaurants
                cuisine_keywords = set()
                for restaurant_data in local_restaurants:
                    rest_type = restaurant_data.get('type', '').lower()
                    rest_name = restaurant_data.get('title', '').lower()

                    cuisine_words = [
                        'italian', 'pizza', 'mexican', 'chinese', 'japanese', 'sushi',
                        'indian', 'thai', 'vietnamese', 'korean', 'american', 'burger',
                        'french', 'mediterranean', 'greek', 'spanish', 'bbq', 'steakhouse',
                        'seafood', 'asian', 'latin', 'middle eastern', 'ethiopian', 'caribbean',
                        'fast food', 'cafe', 'diner', 'grill', 'bakery', 'deli'
                    ]

                    for word in cuisine_words:
                        if word in rest_type or word in rest_name:
                            cuisine_keywords.add(word)

                # Map keywords to our Cuisine objects
                if cuisine_keywords:
                    for keyword in cuisine_keywords:
                        matching_cuisines = Cuisine.objects.filter(Q(name__icontains=keyword))
                        relevant_cuisines.extend(matching_cuisines)
                    relevant_cuisines = list(set(relevant_cuisines))

            except Exception as e:
                # If Google Maps fails, continue without location-based cuisine filtering
                print(f"Google Maps search error (continuing anyway): {e}")

    # Get random dish from available dishes
    dish = None
    total_available = available_dishes.count()

    if total_available > 0:
        random_index = random.randint(0, total_available - 1)
        dish = available_dishes[random_index]

    # Get all cuisines for filter dropdown
    if relevant_cuisines:
        available_cuisines = relevant_cuisines
    else:
        available_cuisines = list(Cuisine.objects.all())

    context = {
        'dish': dish,
        'total_available': total_available,
        'has_location': user_location is not None,
        'user_location': user_location,
        'relevant_cuisines': relevant_cuisines,
        'available_cuisines': available_cuisines,
        'selected_cuisine': cuisine_filter or 'all',
        'selected_dietary': dietary_filter or 'all',
        'selected_meal': selected_meal,
        'current_meal_type': current_meal_type,
    }

    return render(request, 'swipes/swipe_feed.html', context)


@login_required
def swipe_action_view(request, dish_id):
    """Handle swipe action (AJAX)"""
    if request.method == 'POST':
        dish = get_object_or_404(Dish, id=dish_id)
        direction = request.POST.get('direction')  # 'right' or 'left'

        # Create or update swipe action
        swipe, created = SwipeAction.objects.get_or_create(
            user=request.user,
            dish=dish,
            defaults={'direction': direction}
        )

        if not created:
            swipe.direction = direction
            swipe.save()

        # Update dish stats
        dish.total_swipes += 1
        if direction == 'right':
            dish.total_right_swipes += 1
        dish.save()

        return JsonResponse({
            'status': 'success',
            'direction': direction,
            'dish_name': dish.name
        })

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def block_dish_view(request, dish_id):
    """Block a dish from ever showing again (AJAX)"""
    if request.method == 'POST':
        dish = get_object_or_404(Dish, id=dish_id)

        # Add to blacklist
        blacklist_item, created = Blacklist.objects.get_or_create(
            user=request.user,
            dish=dish,
            blacklist_type='dish',
            item_name=dish.name,
            defaults={'reason': 'Blocked from swipe feed'}
        )

        return JsonResponse({
            'status': 'success',
            'message': f'Blocked {dish.name}'
        })

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def matches_view(request):
    """View matches (right swipes) - restaurants loaded on demand"""
    user_timezone = get_user_timezone_from_request(request)
    meal_window_start, current_meal_type = get_current_meal_window(user_timezone)

    # Get filter parameters
    cuisine_filter = request.GET.get('cuisine')
    dietary_filter = request.GET.get('dietary')

    # Get all right swipes (not limited to current meal window for better UX)
    right_swipes = SwipeAction.objects.filter(
        user=request.user,
        direction='right'
    ).select_related('dish', 'dish__cuisine').order_by('-created_at')

    user_location = get_user_location_from_request(request)

    # Don't filter matches by location - show all matches
    # Location filtering was too restrictive

    # Convert to list of dishes and apply filters
    matches = []
    for swipe in right_swipes:
        if swipe.dish and swipe.dish.is_active:
            dish = swipe.dish

            # Apply cuisine filter
            if cuisine_filter and cuisine_filter != 'all':
                try:
                    if str(dish.cuisine_id) != cuisine_filter:
                        continue
                except (ValueError, AttributeError):
                    continue

            # Apply dietary filter
            if dietary_filter and dietary_filter != 'all':
                if dietary_filter == 'vegetarian' and not dish.is_vegetarian:
                    continue
                elif dietary_filter == 'vegan' and not dish.is_vegan:
                    continue
                elif dietary_filter == 'non_veg' and (dish.is_vegetarian or dish.is_vegan):
                    continue

            matches.append(dish)

    # Get AI recommendations
    profile = request.user.profile
    ai_recommendations = []

    if matches:
        liked_cuisine_ids = [dish.cuisine_id for dish in matches if dish.cuisine_id]

        if liked_cuisine_ids:
            swiped_dish_ids = SwipeAction.objects.filter(user=request.user).values_list('dish_id', flat=True)

            potential_dishes = Dish.objects.filter(
                is_active=True,
                cuisine_id__in=liked_cuisine_ids
            ).exclude(
                id__in=swiped_dish_ids
            )

            if profile.diet_type == 'vegetarian':
                potential_dishes = potential_dishes.filter(is_vegetarian=True)
            elif profile.diet_type == 'vegan':
                potential_dishes = potential_dishes.filter(is_vegan=True)

            ai_recommendations = list(potential_dishes.order_by('-average_rating', '-total_right_swipes')[:10])

    # Get all cuisines from matched dishes for filter dropdown
    matched_cuisine_ids = set(dish.cuisine_id for dish in matches if dish.cuisine_id)
    available_cuisines = list(Cuisine.objects.filter(id__in=matched_cuisine_ids).order_by('name'))

    context = {
        'matches': matches,
        'ai_recommendations': ai_recommendations,
        'total_matches': len(matches),
        'has_location': user_location is not None,
        'user_location': user_location,
        'total_right_swipes': right_swipes.count(),
        'available_cuisines': available_cuisines,
        'selected_cuisine': cuisine_filter or 'all',
        'selected_dietary': dietary_filter or 'all',
    }
    return render(request, 'swipes/matches.html', context)


@login_required
def delete_match_view(request, dish_id):
    """Allow a user to remove a matched dish (delete the right swipe)."""
    swipe = SwipeAction.objects.filter(
        user=request.user,
        dish_id=dish_id,
        direction='right'
    ).first()

    if swipe:
        dish_name = swipe.dish.name
        swipe.delete()
        messages.success(request, f"Removed {dish_name} from your matches.")
    else:
        messages.info(request, "Match not found or already removed.")

    return redirect('swipes:matches')


@login_required
def get_dish_restaurants_view(request, dish_id):
    """AJAX endpoint to get restaurants for a specific dish"""
    if request.method != 'GET':
        return JsonResponse({'status': 'error'}, status=400)

    dish = get_object_or_404(Dish, id=dish_id)
    user_location = get_user_location_from_request(request)

    if not user_location:
        return JsonResponse({
            'status': 'error',
            'message': 'Location not set'
        }, status=400)

    maps_service = GoogleMapsService()

    # Fetch local restaurants serving this dish
    try:
        restaurants_data = maps_service.search_restaurants_by_dish(
            dish_name=dish.name,
            latitude=user_location['latitude'],
            longitude=user_location['longitude'],
            zoom=14,
            num_results=5
        )
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Error searching restaurants: {str(e)}'
        }, status=500)

    # Parse and calculate distances
    local_restaurants = []
    for restaurant_data in restaurants_data:
        parsed = maps_service.parse_restaurant_data(restaurant_data)

        if parsed['latitude'] and parsed['longitude']:
            parsed['distance'] = haversine_distance(
                user_location['latitude'],
                user_location['longitude'],
                parsed['latitude'],
                parsed['longitude']
            )
            if parsed['distance'] <= DEFAULT_MAX_DISTANCE_MILES:
                local_restaurants.append(parsed)

    # Sort by distance
    local_restaurants.sort(key=lambda x: x.get('distance', 999))

    return JsonResponse({
        'status': 'success',
        'restaurants': local_restaurants[:5]
    })


@login_required
def favorites_view(request):
    """View explicitly favorited dishes only"""
    favorite_dishes = Favorite.objects.filter(user=request.user).select_related('dish')
    favorite_restaurants = FavoriteRestaurant.objects.filter(user=request.user).select_related('restaurant')

    context = {
        'favorite_dishes': favorite_dishes,
        'favorite_restaurants': favorite_restaurants,
    }
    return render(request, 'swipes/favorites.html', context)


@login_required
def add_favorite_view(request, dish_id):
    """Add dish to favorites"""
    dish = get_object_or_404(Dish, id=dish_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, dish=dish)

    if created:
        messages.success(request, f'Added {dish.name} to your favorites!')
    else:
        messages.info(request, f'{dish.name} is already in your favorites.')

    return redirect('dishes:dish_detail', dish_id=dish.id)


@login_required
def remove_favorite_view(request, favorite_id):
    """Remove dish from favorites"""
    favorite = get_object_or_404(Favorite, id=favorite_id, user=request.user)
    dish_name = favorite.dish.name
    favorite.delete()

    messages.success(request, f'Removed {dish_name} from your favorites.')
    return redirect('swipes:favorites')


@login_required
def add_favorite_restaurant_view(request, restaurant_id):
    """Add restaurant to favorites"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    favorite, created = FavoriteRestaurant.objects.get_or_create(user=request.user, restaurant=restaurant)

    if created:
        messages.success(request, f'Added {restaurant.name} to your favorites!')
    else:
        messages.info(request, f'{restaurant.name} is already in your favorites.')

    return redirect('dishes:restaurant_detail', restaurant_id=restaurant.id)


@login_required
def remove_favorite_restaurant_view(request, favorite_id):
    """Remove restaurant from favorites"""
    favorite = get_object_or_404(FavoriteRestaurant, id=favorite_id, user=request.user)
    restaurant_name = favorite.restaurant.name
    favorite.delete()

    messages.success(request, f'Removed {restaurant_name} from your favorites.')
    return redirect('swipes:favorites')


@login_required
def remove_favorite_restaurant_by_id_view(request, restaurant_id):
    """Remove restaurant from favorites by restaurant ID (not favorite ID)"""
    favorite = FavoriteRestaurant.objects.filter(user=request.user, restaurant_id=restaurant_id).first()

    if favorite:
        restaurant_name = favorite.restaurant.name
        favorite.delete()
        messages.success(request, f'Removed {restaurant_name} from your favorites.')
    else:
        messages.info(request, 'Restaurant was not in your favorites.')

    # Redirect back to the referring page, or to nearby restaurants
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('dishes:nearby_restaurants')


@login_required
def blacklist_view(request):
    """View and manage blacklist"""
    blacklist_items = Blacklist.objects.filter(user=request.user)

    if request.method == 'POST':
        item_name = request.POST.get('item_name')
        blacklist_type = request.POST.get('blacklist_type')
        reason = request.POST.get('reason', '')

        Blacklist.objects.create(
            user=request.user,
            item_name=item_name,
            blacklist_type=blacklist_type,
            reason=reason
        )

        messages.success(request, f'Added {item_name} to your blacklist.')
        return redirect('swipes:blacklist')

    context = {
        'blacklist_items': blacklist_items,
    }
    return render(request, 'swipes/blacklist.html', context)


@login_required
def remove_blacklist_view(request, blacklist_id):
    """Remove item from blacklist"""
    item = get_object_or_404(Blacklist, id=blacklist_id, user=request.user)
    item_name = item.item_name
    item.delete()

    messages.success(request, f'Removed {item_name} from your blacklist.')
    return redirect('swipes:blacklist')


@login_required
def add_dish_to_blacklist_view(request, dish_id):
    """Add specific dish to blacklist"""
    dish = get_object_or_404(Dish, id=dish_id)

    blacklist_item, created = Blacklist.objects.get_or_create(
        user=request.user,
        dish=dish,
        blacklist_type='dish',
        item_name=dish.name
    )

    if created:
        messages.success(request, f'Added {dish.name} to your blacklist.')
    else:
        messages.info(request, f'{dish.name} is already in your blacklist.')

    return redirect('swipes:swipe_feed')


@login_required
def swipe_history_view(request):
    """View swipe history"""
    swipe_actions = SwipeAction.objects.filter(user=request.user).select_related('dish')

    # Filter by direction
    direction_filter = request.GET.get('direction')
    if direction_filter:
        swipe_actions = swipe_actions.filter(direction=direction_filter)

    # Stats
    total_swipes = swipe_actions.count()
    right_swipes = swipe_actions.filter(direction='right').count()
    left_swipes = swipe_actions.filter(direction='left').count()

    context = {
        'swipe_actions': swipe_actions,
        'total_swipes': total_swipes,
        'right_swipes': right_swipes,
        'left_swipes': left_swipes,
    }
    return render(request, 'swipes/swipe_history.html', context)
