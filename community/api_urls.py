from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'reviews', api_views.ReviewViewSet, basename='reviews')

app_name = 'community_api'

urlpatterns = [
    path('', include(router.urls)),
    path('trending/', api_views.TrendingDishView.as_view(), name='trending'),
]
