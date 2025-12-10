from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from dishes.models import Dish, Restaurant
from dishes.location_utils import get_dishes_from_nearby_restaurants, get_user_location_from_request, haversine_distance
from dishes.maps_service import GoogleMapsService
from dishes.ai_service import AIService, DeliveryAppService
from .models import (
    Review, ReviewHelpful, WeeklyRanking, TrendingDish,
    CommunityChallenge, ChallengeParticipation, UserBadge
)


def community_home_view(request):
    """Community homepage with rankings and trending - location-aware with AI enhancements"""

    # ✅ LOCATION FILTER - Get location-based dishes
    user_location = get_user_location_from_request(request)
    location_dish_ids = None
    has_location = False

    if user_location and request.user.is_authenticated:
        has_location = True
        max_distance = request.user.profile.max_distance_miles or 50
        location_dish_ids = get_dishes_from_nearby_restaurants(
            user_location['latitude'],
            user_location['longitude'],
            max_distance
        )

    # Get trending dishes (filtered by location if available)
    trending_dishes = TrendingDish.objects.select_related('dish').order_by('-trending_score')
    if location_dish_ids is not None:
        trending_dishes = trending_dishes.filter(dish_id__in=location_dish_ids)
    trending_dishes = trending_dishes[:10]

    # Get trending restaurants based on reviews and ratings
    trending_restaurants = Restaurant.objects.annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).filter(
        review_count__gte=1
    ).order_by('-avg_rating', '-review_count')[:10]

    # Calculate distance for restaurants if location available
    if user_location:
        for restaurant in trending_restaurants:
            if restaurant.latitude and restaurant.longitude:
                restaurant.distance = haversine_distance(
                    user_location['latitude'],
                    user_location['longitude'],
                    restaurant.latitude,
                    restaurant.longitude
                )

    # Get current week rankings (filtered by location if available)
    today = timezone.now().date()
    current_week_rankings = WeeklyRanking.objects.filter(
        week_start__lte=today,
        week_end__gte=today
    ).select_related('dish').order_by('rank')
    if location_dish_ids is not None:
        current_week_rankings = current_week_rankings.filter(dish_id__in=location_dish_ids)
    current_week_rankings = current_week_rankings[:10]

    # Get active challenges
    active_challenges = CommunityChallenge.objects.filter(status='active')

    # Get recent reviews (filtered by location if available)
    recent_reviews = Review.objects.select_related('user', 'dish').order_by('-created_at')
    if location_dish_ids is not None:
        recent_reviews = recent_reviews.filter(dish_id__in=location_dish_ids)
    recent_reviews = recent_reviews[:5]

    context = {
        'trending_dishes': trending_dishes,
        'trending_restaurants': trending_restaurants,
        'current_week_rankings': current_week_rankings,
        'active_challenges': active_challenges,
        'recent_reviews': recent_reviews,
        'has_location': has_location,
        'user_location': user_location,
    }
    return render(request, 'community/community_home.html', context)


def trending_view(request):
    """View all trending dishes - location-aware"""

    # ✅ LOCATION FILTER
    user_location = get_user_location_from_request(request)
    location_dish_ids = None
    has_location = False

    if user_location and request.user.is_authenticated:
        has_location = True
        max_distance = request.user.profile.max_distance_miles or 50
        location_dish_ids = get_dishes_from_nearby_restaurants(
            user_location['latitude'],
            user_location['longitude'],
            max_distance
        )

    trending_dishes = TrendingDish.objects.select_related('dish').order_by('-trending_score')
    if location_dish_ids is not None:
        trending_dishes = trending_dishes.filter(dish_id__in=location_dish_ids)

    context = {
        'trending_dishes': trending_dishes,
        'has_location': has_location,
        'user_location': user_location,
    }
    return render(request, 'community/trending.html', context)


def weekly_rankings_view(request):
    """View weekly rankings - location-aware"""
    today = timezone.now().date()

    # ✅ LOCATION FILTER
    user_location = get_user_location_from_request(request)
    location_dish_ids = None
    has_location = False

    if user_location and request.user.is_authenticated:
        has_location = True
        max_distance = request.user.profile.max_distance_miles or 50
        location_dish_ids = get_dishes_from_nearby_restaurants(
            user_location['latitude'],
            user_location['longitude'],
            max_distance
        )

    # Current week
    current_week_rankings = WeeklyRanking.objects.filter(
        week_start__lte=today,
        week_end__gte=today
    ).select_related('dish').order_by('rank')
    if location_dish_ids is not None:
        current_week_rankings = current_week_rankings.filter(dish_id__in=location_dish_ids)

    # Previous weeks
    previous_weeks = WeeklyRanking.objects.filter(
        week_end__lt=today
    ).values('week_start', 'week_end').distinct().order_by('-week_start')[:4]

    context = {
        'current_week_rankings': current_week_rankings,
        'previous_weeks': previous_weeks,
        'has_location': has_location,
        'user_location': user_location,
    }
    return render(request, 'community/weekly_rankings.html', context)


@login_required
def add_review_view(request, dish_id):
    """Add review for a dish with AI-enhanced descriptions"""
    dish = get_object_or_404(Dish, id=dish_id)

    # Enhance dish description with AI if needed
    if not dish.description or len(dish.description) < 100:
        ai_service = AIService()
        ai_description = ai_service.get_dish_description(
            dish.name,
            dish.cuisine.name if dish.cuisine else None
        )
        if ai_description:
            dish.ai_description = ai_description
        else:
            dish.ai_description = dish.description
    else:
        dish.ai_description = dish.description

    # Check if user already reviewed
    existing_review = Review.objects.filter(user=request.user, dish=dish).first()

    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        title = request.POST.get('title')
        content = request.POST.get('content')
        image = request.FILES.get('image')

        if existing_review:
            # Update existing review
            existing_review.rating = rating
            existing_review.title = title
            existing_review.content = content
            if image:
                existing_review.image = image
            existing_review.save()
            messages.success(request, 'Review updated successfully!')
        else:
            # Create new review
            Review.objects.create(
                user=request.user,
                dish=dish,
                rating=rating,
                title=title,
                content=content,
                image=image
            )
            messages.success(request, 'Review posted successfully!')

        # Update dish rating
        avg_rating = Review.objects.filter(dish=dish).aggregate(Avg('rating'))['rating__avg']
        dish.average_rating = avg_rating or 0
        dish.total_ratings = Review.objects.filter(dish=dish).count()
        dish.save()

        return redirect('dishes:dish_detail', dish_id=dish.id)

    context = {
        'dish': dish,
        'existing_review': existing_review,
    }
    return render(request, 'community/add_review.html', context)


def dish_reviews_view(request, dish_id):
    """View all reviews for a dish with delivery app integration"""
    dish = get_object_or_404(Dish, id=dish_id)
    reviews = Review.objects.filter(dish=dish).select_related('user').order_by('-created_at')

    # Filter by rating
    rating_filter = request.GET.get('rating')
    if rating_filter:
        reviews = reviews.filter(rating=int(rating_filter))

    # Stats
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    rating_distribution = {
        5: reviews.filter(rating=5).count(),
        4: reviews.filter(rating=4).count(),
        3: reviews.filter(rating=3).count(),
        2: reviews.filter(rating=2).count(),
        1: reviews.filter(rating=1).count(),
    }

    # Get user location and delivery links
    user_location = get_user_location_from_request(request)
    delivery_links = {}
    if user_location:
        delivery_service = DeliveryAppService()
        delivery_links = delivery_service.get_delivery_links(
            dish.name,
            user_location.get('city', '')
        )

    context = {
        'dish': dish,
        'reviews': reviews,
        'total_reviews': total_reviews,
        'avg_rating': avg_rating,
        'rating_distribution': rating_distribution,
        'delivery_links': delivery_links,
        'has_location': user_location is not None,
    }
    return render(request, 'community/dish_reviews.html', context)


def restaurant_reviews_view(request, restaurant_id):
    """View all reviews for a specific restaurant"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    reviews = Review.objects.filter(restaurant=restaurant).select_related('user').order_by('-created_at')

    # Filter by rating
    rating_filter = request.GET.get('rating')
    if rating_filter:
        reviews = reviews.filter(rating=int(rating_filter))

    # Stats
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    rating_distribution = {
        5: reviews.filter(rating=5).count(),
        4: reviews.filter(rating=4).count(),
        3: reviews.filter(rating=3).count(),
        2: reviews.filter(rating=2).count(),
        1: reviews.filter(rating=1).count(),
    }

    # Get delivery links
    delivery_service = DeliveryAppService()
    delivery_links = delivery_service.get_delivery_links(
        restaurant.name,
        restaurant.address or ""
    )

    # Calculate distance if user has location
    user_location = get_user_location_from_request(request)
    if user_location and restaurant.latitude and restaurant.longitude:
        restaurant.distance = haversine_distance(
            user_location['latitude'],
            user_location['longitude'],
            restaurant.latitude,
            restaurant.longitude
        )

    context = {
        'restaurant': restaurant,
        'reviews': reviews,
        'total_reviews': total_reviews,
        'avg_rating': avg_rating,
        'rating_distribution': rating_distribution,
        'delivery_links': delivery_links,
        'has_location': user_location is not None,
    }
    return render(request, 'community/restaurant_reviews.html', context)


@login_required
def add_restaurant_review(request, restaurant_id):
    """Add or update a restaurant review"""
    if request.method == 'POST':
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        rating = int(request.POST.get('rating'))
        title = request.POST.get('title', '')
        content = request.POST.get('content', '')

        review, created = Review.objects.update_or_create(
            user=request.user,
            restaurant=restaurant,
            defaults={
                'rating': rating,
                'title': title,
                'content': content
            }
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Review posted!' if created else 'Review updated!'
        })

    return JsonResponse({'status': 'error'}, status=400)


@login_required
def mark_helpful_view(request, review_id):
    """Mark review as helpful"""
    review = get_object_or_404(Review, id=review_id)

    helpful, created = ReviewHelpful.objects.get_or_create(user=request.user, review=review)

    if created:
        review.helpful_count += 1
        review.save()
        messages.success(request, 'Marked as helpful!')
    else:
        helpful.delete()
        review.helpful_count -= 1
        review.save()
        messages.info(request, 'Removed helpful mark.')

    return redirect('community:dish_reviews', dish_id=review.dish.id)


def challenges_view(request):
    """View all community challenges"""
    active_challenges = CommunityChallenge.objects.filter(status='active')
    upcoming_challenges = CommunityChallenge.objects.filter(status='upcoming').order_by('start_date')
    completed_challenges = CommunityChallenge.objects.filter(status='completed').order_by('-end_date')[:5]

    context = {
        'active_challenges': active_challenges,
        'upcoming_challenges': upcoming_challenges,
        'completed_challenges': completed_challenges,
    }
    return render(request, 'community/challenges.html', context)


@login_required
def join_challenge_view(request, challenge_id):
    """Join a community challenge"""
    challenge = get_object_or_404(CommunityChallenge, id=challenge_id)

    participation, created = ChallengeParticipation.objects.get_or_create(
        user=request.user,
        challenge=challenge
    )

    if created:
        messages.success(request, f'You joined {challenge.title}!')
    else:
        messages.info(request, 'You are already participating in this challenge.')

    return redirect('community:challenges')


@login_required
def my_badges_view(request):
    """View user's badges and achievements"""
    badges = UserBadge.objects.filter(user=request.user).order_by('-earned_at')

    # Stats for badge eligibility
    from swipes.models import SwipeAction
    total_swipes = SwipeAction.objects.filter(user=request.user).count()
    total_reviews = Review.objects.filter(user=request.user).count()

    context = {
        'badges': badges,
        'total_swipes': total_swipes,
        'total_reviews': total_reviews,
    }
    return render(request, 'community/my_badges.html', context)


def leaderboard_view(request):
    """Community leaderboard"""
    from django.contrib.auth.models import User
    from swipes.models import SwipeAction

    # Top reviewers
    top_reviewers = User.objects.annotate(
        review_count=Count('reviews')
    ).filter(review_count__gt=0).order_by('-review_count')[:10]

    # Top swipers
    top_swipers = User.objects.annotate(
        swipe_count=Count('swipes')
    ).filter(swipe_count__gt=0).order_by('-swipe_count')[:10]

    # Most badges
    top_badge_earners = User.objects.annotate(
        badge_count=Count('badges')
    ).filter(badge_count__gt=0).order_by('-badge_count')[:10]

    context = {
        'top_reviewers': top_reviewers,
        'top_swipers': top_swipers,
        'top_badge_earners': top_badge_earners,
    }
    return render(request, 'community/leaderboard.html', context)


def search_community(request):
    """Search for dishes and restaurants"""
    query = request.GET.get('q', '')

    if not query:
        return JsonResponse({'dishes': [], 'restaurants': []})

    # Get user location for filtering
    user_location = get_user_location_from_request(request)
    location_dish_ids = None

    if user_location and request.user.is_authenticated:
        max_distance = request.user.profile.max_distance_miles or 50
        location_dish_ids = get_dishes_from_nearby_restaurants(
            user_location['latitude'],
            user_location['longitude'],
            max_distance
        )

    # Search dishes
    dishes = Dish.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_active=True
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )

    if location_dish_ids is not None:
        dishes = dishes.filter(id__in=location_dish_ids)

    dishes = dishes[:10]

    # Search restaurants
    restaurants = Restaurant.objects.filter(
        Q(name__icontains=query) | Q(address__icontains=query)
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )[:10]

    dishes_data = [{
        'id': d.id,
        'name': d.name,
        'cuisine': d.cuisine.name if d.cuisine else '',
        'avg_rating': round(d.avg_rating, 1) if d.avg_rating else 0,
        'review_count': d.review_count,
        'image': d.display_image
    } for d in dishes]

    restaurants_data = [{
        'id': r.id,
        'name': r.name,
        'address': r.address,
        'avg_rating': round(r.avg_rating, 1) if r.avg_rating else 0,
        'review_count': r.review_count
    } for r in restaurants]

    return JsonResponse({
        'dishes': dishes_data,
        'restaurants': restaurants_data
    })


@login_required
def ai_chatbot(request):
    """AI chatbot endpoint"""
    if request.method == 'POST':
        user_message = request.POST.get('message', '')
        context = request.POST.get('context', '')

        # Add user context about location and preferences
        user_context = ""
        if request.user.profile:
            profile = request.user.profile
            user_context = f"User preferences: diet={profile.diet_type}, allergies={profile.allergies}. "

        user_location = get_user_location_from_request(request)
        if user_location:
            user_context += f"User is in {user_location.get('city', 'unknown location')}. "

        full_context = user_context + context

        ai_service = AIService()
        response = ai_service.chat_response(user_message, full_context)

        return JsonResponse({
            'status': 'success',
            'response': response
        })

    return JsonResponse({'status': 'error'}, status=400)
