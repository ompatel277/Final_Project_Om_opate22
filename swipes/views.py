from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.utils import timezone
from dishes.models import Dish, Restaurant
from .models import SwipeAction, Favorite, FavoriteRestaurant, Blacklist, SwipeSession
import random


@login_required
def swipe_feed_view(request):
    """Main swipe interface"""
    # Get user's blacklisted items
    blacklist = Blacklist.objects.filter(user=request.user)
    blacklisted_dish_ids = blacklist.filter(blacklist_type='dish', dish__isnull=False).values_list('dish_id', flat=True)
    blacklisted_ingredients = blacklist.filter(blacklist_type='ingredient').values_list('item_name', flat=True)

    # Get dishes user hasn't swiped on yet
    swiped_dish_ids = SwipeAction.objects.filter(user=request.user).values_list('dish_id', flat=True)

    # Build query
    available_dishes = Dish.objects.filter(
        is_active=True
    ).exclude(
        id__in=swiped_dish_ids
    ).exclude(
        id__in=blacklisted_dish_ids
    )

    # Apply user preferences from profile
    profile = request.user.profile

    # Filter by dietary preferences
    if profile.diet_type == 'vegetarian':
        available_dishes = available_dishes.filter(is_vegetarian=True)
    elif profile.diet_type == 'vegan':
        available_dishes = available_dishes.filter(is_vegan=True)

    # Filter by allergies
    if profile.allergies:
        allergies = profile.get_allergies_list()
        for allergy in allergies:
            available_dishes = available_dishes.exclude(
                ingredients__name__icontains=allergy,
                ingredients__is_allergen=True
            )

    # Get random dish
    dish = None
    if available_dishes.exists():
        # Get random dish
        count = available_dishes.count()
        random_index = random.randint(0, count - 1)
        dish = available_dishes[random_index]

    context = {
        'dish': dish,
        'total_available': available_dishes.count() if available_dishes else 0,
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

        # If right swipe, optionally auto-add to favorites
        if direction == 'right':
            Favorite.objects.get_or_create(user=request.user, dish=dish)

        return JsonResponse({
            'status': 'success',
            'direction': direction,
            'dish_name': dish.name
        })

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def favorites_view(request):
    """View all favorite dishes"""
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