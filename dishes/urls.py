from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, api_views

# Router for REST API ViewSets
router = DefaultRouter()
router.register(r'cuisines', api_views.CuisineViewSet)
router.register(r'dishes', api_views.DishViewSet)
router.register(r'restaurants', api_views.RestaurantViewSet)

app_name = 'dishes'

urlpatterns = [
    # Web Pages - Dishes
    path('', views.dish_list_view, name='dish_list'),
    path('dish/<int:dish_id>/', views.dish_detail_view, name='dish_detail'),
    path('cuisine/<int:cuisine_id>/', views.cuisine_view, name='cuisine_dishes'),

    # Web Pages - Restaurants
    path('restaurants/', views.restaurant_list_view, name='restaurant_list'),
    path('restaurant/<int:restaurant_id>/', views.restaurant_detail_view, name='restaurant_detail'),

    # Web Pages - Search
    path('search/', views.search_view, name='search'),

    # Web Pages - Nearby Restaurants (NEW)
    path('nearby/', views.nearby_restaurants, name='nearby_restaurants'),

    # REST API - ViewSets
    path('api/', include(router.urls)),

    # REST API - Custom Endpoints (NEW)
    path('api/dishes/<int:dish_id>/restaurants/', api_views.DishRestaurantsView.as_view(),
         name='api_dish_restaurants_detail'),

    # REST API - Location Management (NEW)
    path('api/set-location/', views.set_location_view, name='set_location'),

    # REST API - Google Maps Integration (NEW)
    path('api/restaurants/nearby/', api_views.find_nearby_restaurants, name='api_nearby_restaurants'),
    path('api/dishes/<int:dish_id>/restaurants/nearby/', api_views.find_restaurants_for_dish,
         name='api_dish_restaurants'),
    path('api/places/details/', api_views.get_place_details, name='api_place_details'),
    path('api/places/reviews/', api_views.get_place_reviews, name='api_place_reviews'),
    path('api/directions/', api_views.get_directions, name='api_directions'),
    path('api/set-location/', views.set_location_view, name='set_location'),

]
