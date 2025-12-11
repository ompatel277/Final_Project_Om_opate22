from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dishes.models import Dish, Cuisine
from swipes.models import SwipeAction, Favorite
from accounts.models import UserProfile
import json
import random


@login_required
def recommender_home_view(request):
    """AI Recommender homepage"""
    profile = request.user.profile

    # Get user preferences
    favorite_dishes = Favorite.objects.filter(user=request.user).select_related('dish')[:5]
    recent_swipes = SwipeAction.objects.filter(
        user=request.user,
        direction='right'
    ).select_related('dish').order_by('-created_at')[:10]

    context = {
        'profile': profile,
        'favorite_dishes': favorite_dishes,
        'recent_swipes': recent_swipes,
    }
    return render(request, 'recommender/recommender_home.html', context)


@login_required
def ai_chat_view(request):
    """AI Chat Interface"""
    return render(request, 'recommender/ai_chat.html')


@login_required
def get_recommendations_view(request):
    """Get personalized dish recommendations"""
    profile = request.user.profile

    # Build recommendation logic based on user preferences
    recommendations = Dish.objects.filter(is_active=True)

    # Filter by dietary preferences
    if profile.diet_type == 'vegetarian':
        recommendations = recommendations.filter(is_vegetarian=True)
    elif profile.diet_type == 'vegan':
        recommendations = recommendations.filter(is_vegan=True)

    # Filter by allergies
    if profile.allergies:
        allergies = profile.get_allergies_list()
        for allergy in allergies:
            recommendations = recommendations.exclude(
                ingredients__name__icontains=allergy,
                ingredients__is_allergen=True
            )

    # Get user's favorite cuisines
    favorite_cuisines = []
    if profile.favorite_cuisines:
        favorite_cuisines = profile.get_favorite_cuisines_list()
        if favorite_cuisines:
            recommendations = recommendations.filter(
                cuisine__name__in=favorite_cuisines
            )

    # Filter by calorie goals
    if profile.daily_calorie_goal:
        max_calories = profile.daily_calorie_goal / 3  # Rough estimate per meal
        recommendations = recommendations.filter(calories__lte=max_calories)

    # Exclude already swiped dishes
    swiped_dish_ids = SwipeAction.objects.filter(
        user=request.user
    ).values_list('dish_id', flat=True)
    recommendations = recommendations.exclude(id__in=swiped_dish_ids)

    # Get top 10 recommendations
    recommendations = recommendations.select_related('cuisine').order_by('?')[:10]

    context = {
        'recommendations': recommendations,
        'profile': profile,
    }
    return render(request, 'recommender/recommendations.html', context)


@login_required
def similar_dishes_view(request, dish_id):
    """Find similar dishes based on a given dish"""
    from django.shortcuts import get_object_or_404

    dish = get_object_or_404(Dish, id=dish_id)

    # Find similar dishes based on:
    # 1. Same cuisine
    # 2. Similar calories (±200)
    # 3. Same meal type
    similar = Dish.objects.filter(
        is_active=True,
        cuisine=dish.cuisine,
        meal_type=dish.meal_type
    ).exclude(id=dish.id)

    # Filter by similar calories
    if dish.calories:
        similar = similar.filter(
            calories__gte=dish.calories - 200,
            calories__lte=dish.calories + 200
        )

    # Get top 6 similar dishes
    similar = similar.select_related('cuisine')[:6]

    context = {
        'dish': dish,
        'similar_dishes': similar,
    }
    return render(request, 'recommender/similar_dishes.html', context)


@login_required
def surprise_me_view(request):
    """Random dish recommendation - "I can't decide" mode"""
    profile = request.user.profile

    # Get random dish based on preferences
    dishes = Dish.objects.filter(is_active=True)

    # Apply dietary filters
    if profile.diet_type == 'vegetarian':
        dishes = dishes.filter(is_vegetarian=True)
    elif profile.diet_type == 'vegan':
        dishes = dishes.filter(is_vegan=True)

    # Get random dish
    dish = dishes.order_by('?').first()

    if dish:
        context = {'dish': dish}
        return render(request, 'recommender/surprise_dish.html', context)
    else:
        return redirect('recommender:recommender_home')


@login_required
@csrf_exempt
def ai_assistant_api(request):
    """API endpoint for AI chat assistant (mock implementation)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').lower()

            # Simple rule-based responses (you can replace with actual AI API)
            response = generate_mock_ai_response(user_message, request.user)

            return JsonResponse({
                'status': 'success',
                'response': response
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


def generate_mock_ai_response(message, user):
    """Generate mock AI responses based on keywords"""
    profile = user.profile

    # Keyword-based responses
    if 'recommend' in message or 'suggest' in message:
        cuisines = ['Italian', 'Mexican', 'Chinese', 'Japanese', 'Indian']
        cuisine = random.choice(cuisines)
        return f"Based on your preferences, I'd recommend trying some {cuisine} cuisine! How about checking out our top-rated {cuisine} dishes?"

    elif 'calorie' in message or 'calories' in message:
        if profile.daily_calorie_goal:
            per_meal = profile.daily_calorie_goal / 3
            return f"Based on your daily goal of {profile.daily_calorie_goal} calories, aim for around {int(per_meal)} calories per meal. Would you like me to find some dishes in that range?"
        else:
            return "I'd be happy to help with calorie information! What's your target calorie range for this meal?"

    elif 'protein' in message:
        if profile.protein_goal:
            return f"Your protein goal is {profile.protein_goal}g per day. I can help you find high-protein dishes if you'd like!"
        else:
            return "Looking for high-protein options? I can show you dishes with 30g+ of protein per serving!"

    elif 'allerg' in message:
        if profile.allergies:
            allergies = profile.get_allergies_list()
            return f"I see you're allergic to: {', '.join(allergies)}. I'll make sure to filter those out from your recommendations!"
        else:
            return "Do you have any food allergies I should know about? I can help you avoid specific ingredients."

    elif 'spicy' in message or 'hot' in message:
        return "Love spicy food? I can filter dishes by spice level! We have options from mild (🌶️) to very spicy (🌶️🌶️🌶️🌶️🌶️)."

    elif 'vegetarian' in message or 'vegan' in message:
        return "Looking for plant-based options? I can show you delicious vegetarian and vegan dishes that are packed with flavor!"

    elif 'cheap' in message or 'budget' in message or 'affordable' in message:
        return "I can help you find great dishes on a budget! Would you like me to show you our most affordable options ($-$$)?"

    elif 'healthy' in message or 'light' in message:
        return "Looking for healthier options? I can recommend dishes under 500 calories with good protein content!"

    elif 'dessert' in message or 'sweet' in message:
        return "Got a sweet tooth? Check out our dessert section for some amazing treats! 🍰🍨"

    elif any(word in message for word in ['hi', 'hello', 'hey']):
        return f"Hi {user.first_name}! I'm your AI food assistant. I can help you find the perfect dish based on your preferences, dietary needs, and cravings. What are you in the mood for?"

    elif 'thank' in message:
        return "You're welcome! Enjoy your meal! 🍽️"

    else:
        return "I'm here to help you find amazing food! You can ask me about:\n• Dish recommendations\n• Nutrition info\n• Dietary restrictions\n• Cuisine types\n• Or just tell me what you're craving!"


@login_required
def macro_calculator_view(request):
    """Macro and nutrition calculator"""
    profile = request.user.profile

    context = {
        'profile': profile,
    }
    return render(request, 'recommender/macro_calculator.html', context)

