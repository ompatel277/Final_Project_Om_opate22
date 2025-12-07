from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'swipes', api_views.SwipeActionViewSet, basename='swipes')
router.register(r'favorites', api_views.FavoriteViewSet, basename='favorites')
router.register(r'favorite-restaurants', api_views.FavoriteRestaurantViewSet, basename='favorite-restaurants')
router.register(r'blacklist', api_views.BlacklistViewSet, basename='blacklist')
router.register(r'sessions', api_views.SwipeSessionViewSet, basename='sessions')

app_name = 'swipes_api'

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', api_views.SwipeStatsView.as_view(), name='stats'),
]
