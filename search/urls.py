from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.global_search_view, name='global_search'),
    path('advanced/', views.advanced_search_view, name='advanced_search'),
    path('autocomplete/', views.autocomplete_view, name='autocomplete'),
]