from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Profile
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/setup/', views.profile_setup_view, name='profile_setup'),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/data/json/', views.dashboard_data_json, name='dashboard_data_json'),
    path('dashboard/data/csv/', views.dashboard_data_csv, name='dashboard_data_csv'),
]