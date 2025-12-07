from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'cuisines', api_views.CuisineViewSet)
router.register(r'dishes', api_views.DishViewSet)
router.register(r'restaurants', api_views.RestaurantViewSet)

app_name = 'dishes_api'

urlpatterns = [
    path('', include(router.urls)),
    path('dishes/<int:dish_id>/restaurants/', api_views.DishRestaurantsView.as_view(), name='dish-restaurants'),
]
