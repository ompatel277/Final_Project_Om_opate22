from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views, views

router = DefaultRouter()
router.register(r"cuisines", api_views.CuisineViewSet)
router.register(r"dishes", api_views.DishViewSet)
router.register(r"restaurants", api_views.RestaurantViewSet)

app_name = "dishes_api"

urlpatterns = [
    # REST API - ViewSets
    path("", include(router.urls)),

    # REST API - Custom Endpoints
    path("dishes/<int:dish_id>/restaurants/", api_views.DishRestaurantsView.as_view(), name="dish-restaurants"),
    path("restaurants/nearby/", api_views.find_nearby_restaurants, name="nearby-restaurants"),
    path("dishes/<int:dish_id>/restaurants/nearby/", api_views.find_restaurants_for_dish, name="dish-restaurants-nearby"),

    # Google Maps / SerpApi helpers
    path("places/details/", api_views.get_place_details, name="place-details"),
    path("places/reviews/", api_views.get_place_reviews, name="place-reviews"),
    path("directions/", api_views.get_directions, name="directions"),

    # Session location (this is in views.py, not api_views.py)
    path("set-location/", views.set_location_view, name="set-location"),
]
