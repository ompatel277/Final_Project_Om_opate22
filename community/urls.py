from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    # Community Home
    path('', views.community_home_view, name='community_home'),

    # Trending & Rankings
    path('trending/', views.trending_view, name='trending'),
    path('rankings/', views.weekly_rankings_view, name='weekly_rankings'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),

    # Reviews
    path('dish/<int:dish_id>/reviews/', views.dish_reviews_view, name='dish_reviews'),
    path('dish/<int:dish_id>/review/add/', views.add_review_view, name='add_review'),
    path('review/<int:review_id>/helpful/', views.mark_helpful_view, name='mark_helpful'),

    # Challenges
    path('challenges/', views.challenges_view, name='challenges'),
    path('challenge/<int:challenge_id>/join/', views.join_challenge_view, name='join_challenge'),

    # Badges
    path('badges/', views.my_badges_view, name='my_badges'),
]