from django.urls import path
from . import views

app_name = 'swipes'

urlpatterns = [
    # Swipe Interface
    path('', views.swipe_feed_view, name='swipe_feed'),
    path('swipe/<int:dish_id>/', views.swipe_action_view, name='swipe_action'),
    path('history/', views.swipe_history_view, name='swipe_history'),

    # Favorites
    path('favorites/', views.favorites_view, name='favorites'),
    path('favorite/add/<int:dish_id>/', views.add_favorite_view, name='add_favorite'),
    path('favorite/remove/<int:favorite_id>/', views.remove_favorite_view, name='remove_favorite'),
    path('favorite/restaurant/add/<int:restaurant_id>/', views.add_favorite_restaurant_view,
         name='add_favorite_restaurant'),
    path('favorite/restaurant/remove/<int:favorite_id>/', views.remove_favorite_restaurant_view,
         name='remove_favorite_restaurant'),
    path('favorite/restaurant/remove-by-id/<int:restaurant_id>/', views.remove_favorite_restaurant_by_id_view,
         name='remove_favorite_restaurant_by_id'),

    # Blacklist
    path('blacklist/', views.blacklist_view, name='blacklist'),
    path('blacklist/remove/<int:blacklist_id>/', views.remove_blacklist_view, name='remove_blacklist'),
    path('blacklist/add/<int:dish_id>/', views.add_dish_to_blacklist_view, name='add_dish_to_blacklist'),
    path('matches/', views.matches_view, name='matches'),
    path('matches/<int:dish_id>/delete/', views.delete_match_view, name='delete_match'),
    path('block/<int:dish_id>/', views.block_dish_view, name='block_dish'),
    path('dish/<int:dish_id>/restaurants/', views.get_dish_restaurants_view, name='get_dish_restaurants'),
]
