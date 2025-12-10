from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    # Existing URLs
    path('', views.community_home_view, name='home'),
    path('trending/', views.trending_view, name='trending'),
    path('rankings/', views.weekly_rankings_view, name='rankings'),
    path('dish/<int:dish_id>/reviews/', views.dish_reviews_view, name='dish_reviews'),
    path('dish/<int:dish_id>/review/add/', views.add_review_view, name='add_review'),
    path('review/<int:review_id>/helpful/', views.mark_helpful_view, name='mark_helpful'),
    path('challenges/', views.challenges_view, name='challenges'),
    path('challenge/<int:challenge_id>/join/', views.join_challenge_view, name='join_challenge'),
    path('badges/', views.my_badges_view, name='my_badges'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),

    # NEW URLs
    path('restaurant/<int:restaurant_id>/reviews/', views.restaurant_reviews_view, name='restaurant_reviews'),
    path('restaurant/<int:restaurant_id>/review/add/', views.add_restaurant_review, name='add_restaurant_review'),
    path('search/', views.search_community, name='search'),
    path('ai-chat/', views.ai_chatbot, name='ai_chat'),
]
