from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from dishes.models import Dish, Restaurant, Cuisine
from dishes.location_utils import (
    DEFAULT_MAX_DISTANCE_MILES,
    get_dishes_from_nearby_restaurants,
    get_user_location_from_request,
    haversine_distance,
)
from dishes.maps_service import GoogleMapsService
from dishes.ai_service import AIService, DeliveryAppService
from dishes.time_utils import get_current_meal_type
from .models import Review, ReviewHelpful


def community_home_view(request):
    """Community homepage with rankings and trending - personalized for each user"""
    current_meal_type = get_current_meal_type()

    # ✅ LOCATION FILTER - Get location-based dishes
    user_location = get_user_location_from_request(request)
    location_dish_ids = None
    has_location = False

    if user_location and request.user.is_authenticated:
        has_location = True
        max_distance = DEFAULT_MAX_DISTANCE_MILES
        location_dish_ids = get_dishes_from_nearby_restaurants(
            user_location['latitude'],
            user_location['longitude'],
            max_distance
        )

    # ✅ PERSONALIZED TRENDING DISHES - Tailored to user profile
    trending_query = Dish.objects.filter(is_active=True, meal_type=current_meal_type).select_related('cuisine')

    # Filter by user preferences if authenticated
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile

        # Filter by diet type
        if profile.diet_type == 'vegetarian':
            trending_query = trending_query.filter(is_vegetarian=True)
        elif profile.diet_type == 'vegan':
            trending_query = trending_query.filter(is_vegan=True)

        # Filter by favorite cuisines if set
        favorite_cuisines = profile.get_favorite_cuisines_list()
        if favorite_cuisines:
            # Get cuisine objects matching the favorite cuisine names
            cuisine_ids = Cuisine.objects.filter(
                name__in=favorite_cuisines
            ).values_list('id', flat=True)
            if cuisine_ids:
                trending_query = trending_query.filter(cuisine_id__in=cuisine_ids)

    # Apply location filter
    if location_dish_ids is not None:
        trending_query = trending_query.filter(id__in=location_dish_ids)

    # Get trending dishes - prioritize by swipes, ratings, and recency
    trending_dishes = trending_query.annotate(
        review_count=Count('reviews'),
        avg_rating=Avg('reviews__rating')
    ).filter(
        total_swipes__gte=1  # Must have at least 1 swipe
    ).order_by(
        '-total_right_swipes',  # Most right swipes first
        '-average_rating',  # Then by rating
        '-review_count',  # Then by reviews
        '-created_at'  # Then by newest
    )[:5]  # TOP 5

    # Get TOP 5 trending restaurants based on existing ratings
    trending_restaurants = Restaurant.objects.filter(
        total_reviews__gte=1,
        is_active=True
    ).order_by('-rating', '-total_reviews')[:5]  # TOP 5

    # Calculate distance for restaurants if location available
    if user_location:
        filtered_restaurants = []
        for restaurant in trending_restaurants:
            if restaurant.latitude and restaurant.longitude:
                restaurant.distance = haversine_distance(
                    user_location['latitude'],
                    user_location['longitude'],
                    restaurant.latitude,
                    restaurant.longitude
                )
                if restaurant.distance <= DEFAULT_MAX_DISTANCE_MILES:
                    filtered_restaurants.append(restaurant)
        trending_restaurants = filtered_restaurants

    # Get recent reviews (filtered by location if available)
    recent_reviews = Review.objects.select_related('user', 'dish').order_by('-created_at')
    if location_dish_ids is not None:
        recent_reviews = recent_reviews.filter(dish_id__in=location_dish_ids)
    recent_reviews = recent_reviews[:5]

    # Calculate personalization indicator
    is_personalized = request.user.is_authenticated and hasattr(request.user, 'profile')

    context = {
        'trending_dishes': trending_dishes,
        'trending_restaurants': trending_restaurants,
        'recent_reviews': recent_reviews,
        'has_location': has_location,
        'user_location': user_location,
        'is_personalized': is_personalized,  # Indicate if results are personalized
    }
    return render(request, 'community/community_home.html', context)


def trending_view(request):
    """View all trending dishes - personalized and location-aware"""
    current_meal_type = get_current_meal_type()

    # ✅ LOCATION FILTER
    user_location = get_user_location_from_request(request)
    location_dish_ids = None
    has_location = False

    if user_location and request.user.is_authenticated:
        has_location = True
        max_distance = DEFAULT_MAX_DISTANCE_MILES
        location_dish_ids = get_dishes_from_nearby_restaurants(
            user_location['latitude'],
            user_location['longitude'],
            max_distance
        )

    # ✅ PERSONALIZED TRENDING DISHES
    trending_query = Dish.objects.filter(is_active=True, meal_type=current_meal_type).select_related('cuisine')

    # Filter by user preferences if authenticated
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        profile = request.user.profile

        # Filter by diet type
        if profile.diet_type == 'vegetarian':
            trending_query = trending_query.filter(is_vegetarian=True)
        elif profile.diet_type == 'vegan':
            trending_query = trending_query.filter(is_vegan=True)

        # Filter by favorite cuisines if set
        favorite_cuisines = profile.get_favorite_cuisines_list()
        if favorite_cuisines:
            cuisine_ids = Cuisine.objects.filter(
                name__in=favorite_cuisines
            ).values_list('id', flat=True)
            if cuisine_ids:
                trending_query = trending_query.filter(cuisine_id__in=cuisine_ids)

    # Apply location filter
    if location_dish_ids is not None:
        trending_query = trending_query.filter(id__in=location_dish_ids)

    # Get ALL trending dishes for this page
    trending_dishes = trending_query.annotate(
        review_count=Count('reviews'),
        avg_rating=Avg('reviews__rating')
    ).filter(
        total_swipes__gte=1
    ).order_by(
        '-total_right_swipes',
        '-average_rating',
        '-review_count',
        '-created_at'
    )[:20]  # Show top 20 on full trending page

    is_personalized = request.user.is_authenticated and hasattr(request.user, 'profile')

    context = {
        'trending_dishes': trending_dishes,
        'has_location': has_location,
        'user_location': user_location,
        'is_personalized': is_personalized,
    }
    return render(request, 'community/trending.html', context)


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
    """View REAL Google reviews for a restaurant using Google Maps API"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    # Initialize Google Maps service
    maps_service = GoogleMapsService()

    # Get real reviews from Google if we have google_place_id
    google_reviews = []
    place_details = None

    if restaurant.google_place_id:
        # Try to get place details first
        place_details = maps_service.get_place_details(restaurant.google_place_id)

        # Get Google reviews
        google_reviews = maps_service.get_place_reviews(
            restaurant.google_place_id,
            num_reviews=20
        )

    # Calculate stats from Google reviews
    total_reviews = len(google_reviews)
    avg_rating = 0
    rating_distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}

    if google_reviews:
        ratings = [review.get('rating', 0) for review in google_reviews]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0

        for review in google_reviews:
            rating = review.get('rating', 0)
            if rating in rating_distribution:
                rating_distribution[rating] += 1
    else:
        # Fallback to restaurant's own rating
        avg_rating = restaurant.rating
        total_reviews = restaurant.total_reviews

    # Filter by rating if requested
    rating_filter = request.GET.get('rating')
    if rating_filter and google_reviews:
        rating_value = int(rating_filter)
        google_reviews = [r for r in google_reviews if r.get('rating') == rating_value]

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

    # Get dishes available at this restaurant
    restaurant_dishes = restaurant.restaurant_dishes.select_related('dish').all()[:10]

    context = {
        'restaurant': restaurant,
        'google_reviews': google_reviews,  # Real Google reviews
        'place_details': place_details,  # Extra place info from Google
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 1),
        'rating_distribution': rating_distribution,
        'delivery_links': delivery_links,
        'has_location': user_location is not None,
        'restaurant_dishes': restaurant_dishes,
    }
    return render(request, 'community/restaurant_reviews.html', context)


@login_required
def add_restaurant_review(request, restaurant_id):
    """Add a review for a dish at a restaurant - redirects to dish review form"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    # Get the first dish from this restaurant or show selection
    restaurant_dishes = restaurant.restaurant_dishes.all()

    if request.method == 'POST':
        dish_id = request.POST.get('dish_id')
        if dish_id:
            return redirect('community:add_review', dish_id=dish_id)

        return JsonResponse({
            'status': 'error',
            'message': 'Please select a dish to review'
        }, status=400)

    # Show dish selection page
    context = {
        'restaurant': restaurant,
        'dishes': restaurant_dishes
    }
    return render(request, 'community/select_dish_for_review.html', context)


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


def search_community(request):
    """Search for dishes and restaurants"""
    query = request.GET.get('q', '')
    current_meal_type = get_current_meal_type()

    if not query:
        return JsonResponse({'dishes': [], 'restaurants': []})

    # Get user location for filtering
    user_location = get_user_location_from_request(request)
    location_dish_ids = None

    if user_location and request.user.is_authenticated:
        max_distance = DEFAULT_MAX_DISTANCE_MILES
        location_dish_ids = get_dishes_from_nearby_restaurants(
            user_location['latitude'],
            user_location['longitude'],
            max_distance
        )

    # Search dishes
    dishes = Dish.objects.filter(
        Q(name__icontains=query) | Q(description__icontains=query),
        is_active=True,
        meal_type=current_meal_type
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )

    if location_dish_ids is not None:
        dishes = dishes.filter(id__in=location_dish_ids)

    dishes = dishes[:10]

    # Search restaurants - use existing rating and total_reviews fields
    restaurants = Restaurant.objects.filter(
        Q(name__icontains=query) | Q(address__icontains=query),
        is_active=True
    ).order_by('-rating', '-total_reviews')[:10]

    if user_location:
        filtered_restaurants = []
        for restaurant in restaurants:
            if restaurant.latitude and restaurant.longitude:
                distance = haversine_distance(
                    user_location['latitude'],
                    user_location['longitude'],
                    restaurant.latitude,
                    restaurant.longitude
                )
                if distance <= DEFAULT_MAX_DISTANCE_MILES:
                    restaurant.distance = distance
                    filtered_restaurants.append(restaurant)
        restaurants = filtered_restaurants

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
        'avg_rating': round(r.rating, 1),
        'review_count': r.total_reviews
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
