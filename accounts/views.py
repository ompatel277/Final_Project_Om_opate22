from datetime import timedelta
import csv
import io
import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from community.models import Review
from swipes.models import Favorite, SwipeAction

from .forms import UserProfileForm, UserRegistrationForm, UserUpdateForm
from .models import UserProfile


def _build_dashboard_payload(user):
    """Gather dashboard metrics for reuse across multiple responses."""
    profile = user.profile

    total_swipes = SwipeAction.objects.filter(user=user).count()
    total_matches = SwipeAction.objects.filter(user=user, direction='right').count()
    total_favorites = Favorite.objects.filter(user=user).count()
    total_reviews = Review.objects.filter(user=user).count()

    recent_swipes = (
        SwipeAction.objects.filter(user=user)
        .select_related('dish')
        .order_by('-created_at')[:5]
    )
    recent_favorites = (
        Favorite.objects.filter(user=user)
        .select_related('dish')
        .order_by('-created_at')[:5]
    )

    start_date = timezone.now().date() - timedelta(days=6)
    swipe_activity = {start_date + timedelta(days=i): {'right': 0, 'left': 0} for i in range(7)}

    aggregated_swipes = (
        SwipeAction.objects.filter(user=user, created_at__date__gte=start_date)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(
            right_count=Count('id', filter=Q(direction='right')),
            left_count=Count('id', filter=Q(direction='left')),
        )
    )

    for entry in aggregated_swipes:
        day = entry['day']
        swipe_activity[day]['right'] = entry['right_count']
        swipe_activity[day]['left'] = entry['left_count']

    chart_labels = [day.strftime('%b %d') for day in swipe_activity.keys()]
    chart_right = [counts['right'] for counts in swipe_activity.values()]
    chart_left = [counts['left'] for counts in swipe_activity.values()]

    profile_completion_fields = [
        bool(profile.city),
        bool(profile.bio),
        bool(profile.favorite_cuisines),
        bool(profile.allergies),
        bool(profile.profile_picture),
    ]
    profile_completion = int((sum(profile_completion_fields) / len(profile_completion_fields)) * 100)

    return {
        'user': user,
        'profile': profile,
        'recent_swipes_qs': recent_swipes,
        'recent_favorites_qs': recent_favorites,
        'totals': {
            'swipes': total_swipes,
            'matches': total_matches,
            'favorites': total_favorites,
            'reviews': total_reviews,
        },
        'recent_swipes': [
            {
                'dish': swipe.dish.name,
                'image': swipe.dish.display_image,
                'direction': swipe.direction,
                'created_at': swipe.created_at.isoformat(),
            }
            for swipe in recent_swipes
        ],
        'recent_favorites': [
            {
                'dish': favorite.dish.name,
                'image': favorite.dish.display_image,
                'created_at': favorite.created_at.isoformat(),
            }
            for favorite in recent_favorites
        ],
        'chart': {
            'labels': chart_labels,
            'right_swipes': chart_right,
            'left_swipes': chart_left,
        },
        'profile_completion': profile_completion,
        'swipe_activity': swipe_activity,
    }


def register_view(request):
    """Handle user registration"""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            # Auto login after registration
            login(request, user)
            return redirect('accounts:profile_setup')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                next_url = request.GET.get('next', 'accounts:dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def profile_view(request):
    """Display user profile"""
    profile = request.user.profile
    context = {
        'profile': profile,
        'user': request.user,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit_view(request):
    """Edit user profile"""
    profile = request.user.profile

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'accounts/profile_edit.html', context)


@login_required
def profile_setup_view(request):
    """Initial profile setup after registration"""
    profile = request.user.profile

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()

            # Save location to session if provided
            latitude = request.POST.get('latitude')
            longitude = request.POST.get('longitude')
            city = request.POST.get('city', profile.city or 'Unknown')

            if latitude and longitude:
                try:
                    from dishes.location_utils import set_user_location_in_session
                    set_user_location_in_session(
                        request,
                        float(latitude),
                        float(longitude),
                        city
                    )
                except (ValueError, TypeError):
                    pass  # Invalid lat/lng, skip setting location

            messages.success(request, 'Profile setup complete! Start swiping!')
            return redirect('accounts:dashboard')
    else:
        form = UserProfileForm(instance=profile)

    context = {
        'form': form,
        'is_setup': True,
    }
    return render(request, 'accounts/profile_setup.html', context)


@login_required
def dashboard_view(request):
    """User dashboard with stats and overview"""
    dashboard_payload = _build_dashboard_payload(request.user)

    context = {
        'user': dashboard_payload['user'],
        'profile': dashboard_payload['profile'],
        'total_swipes': dashboard_payload['totals']['swipes'],
        'total_matches': dashboard_payload['totals']['matches'],
        'total_favorites': dashboard_payload['totals']['favorites'],
        'total_reviews': dashboard_payload['totals']['reviews'],
        'recent_swipes': dashboard_payload['recent_swipes_qs'],
        'recent_favorites': dashboard_payload['recent_favorites_qs'],
        'profile_completion': dashboard_payload['profile_completion'],
        'swipe_chart_data': json.dumps(dashboard_payload['chart']),
    }

    return render(request, 'accounts/dashboard.html', context)


@login_required
def dashboard_data_json(request):
    """Expose dashboard metrics as a JSON API."""
    dashboard_payload = _build_dashboard_payload(request.user)

    return JsonResponse(
        {
            'totals': dashboard_payload['totals'],
            'chart': dashboard_payload['chart'],
            'recent_swipes': dashboard_payload['recent_swipes'],
            'recent_favorites': dashboard_payload['recent_favorites'],
            'profile_completion': dashboard_payload['profile_completion'],
        }
    )


@login_required
def dashboard_data_csv(request):
    """Download swipe activity in CSV format for external analysis."""
    dashboard_payload = _build_dashboard_payload(request.user)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Date', 'Right Swipes', 'Left Swipes'])

    for label, right, left in zip(
            dashboard_payload['chart']['labels'],
            dashboard_payload['chart']['right_swipes'],
            dashboard_payload['chart']['left_swipes'],
    ):
        writer.writerow([label, right, left])

    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="swipe_activity.csv"'
    return response
