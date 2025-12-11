from datetime import timedelta
import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.shortcuts import redirect, render
from django.utils import timezone

from community.models import Review
from swipes.models import Favorite, SwipeAction

from .forms import UserProfileForm, UserRegistrationForm, UserUpdateForm
from .models import UserProfile


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
    user = request.user
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

    # Build swipe activity for the last 7 days
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

    context = {
        'user': user,
        'profile': profile,
        'total_swipes': total_swipes,
        'total_matches': total_matches,
        'total_favorites': total_favorites,
        'total_reviews': total_reviews,
        'recent_swipes': recent_swipes,
        'recent_favorites': recent_favorites,
        'profile_completion': profile_completion,
        'swipe_chart_data': json.dumps(
            {
                'labels': chart_labels,
                'right_swipes': chart_right,
                'left_swipes': chart_left,
            }
        ),
    }

    return render(request, 'accounts/dashboard.html', context)