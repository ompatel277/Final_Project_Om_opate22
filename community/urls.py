from django.urls import path
from . import views

app_name = 'community'

urlpatterns = [
    # Existing URLs
    path('', views.community_home_view, name='community_home'),
    path('trending/', views.trending_view, name='trending'),
    path('dish/<int:dish_id>/reviews/', views.dish_reviews_view, name='dish_reviews'),
    path('dish/<int:dish_id>/review/add/', views.add_review_view, name='add_review'),
    path('review/<int:review_id>/helpful/', views.mark_helpful_view, name='mark_helpful'),

    # NEW URLs
    path('restaurant/<int:restaurant_id>/reviews/', views.restaurant_reviews_view, name='restaurant_reviews'),
    path('restaurant/<int:restaurant_id>/review/add/', views.add_restaurant_review, name='add_restaurant_review'),
    path('search/', views.search_community, name='search'),
    path('ai-chat/', views.ai_chatbot, name='ai_chat'),
]
