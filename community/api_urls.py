from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'reviews', api_views.ReviewViewSet, basename='reviews')
router.register(r'challenges', api_views.CommunityChallengeViewSet, basename='challenges')
router.register(r'badges', api_views.UserBadgeViewSet, basename='badges')

app_name = 'community_api'

urlpatterns = [
    path('', include(router.urls)),
    path('rankings/weekly/', api_views.WeeklyRankingView.as_view(), name='weekly-rankings'),
    path('trending/', api_views.TrendingDishView.as_view(), name='trending'),
]
