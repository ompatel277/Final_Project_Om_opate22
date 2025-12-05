from django.urls import path
from . import views

app_name = 'dishes'

urlpatterns = [
    # Dishes
    path('', views.dish_list_view, name='dish_list'),
    path('dish/<int:dish_id>/', views.dish_detail_view, name='dish_detail'),
    path('cuisine/<int:cuisine_id>/', views.cuisine_view, name='cuisine_dishes'),

    # Restaurants
    path('restaurants/', views.restaurant_list_view, name='restaurant_list'),
    path('restaurant/<int:restaurant_id>/', views.restaurant_detail_view, name='restaurant_detail'),

    # Search
    path('search/', views.search_view, name='search'),
]