from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from . import api_views

router = DefaultRouter()
router.register(r'profile', api_views.UserProfileViewSet, basename='profile')

app_name = 'accounts_api'

urlpatterns = [
    # JWT Authentication
    path('token/', api_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Registration
    path('register/', api_views.UserRegistrationView.as_view(), name='register'),

    # User Management
    path('user/', api_views.CurrentUserView.as_view(), name='current_user'),
    path('user/update/', api_views.UserUpdateView.as_view(), name='user_update'),
    path('user/change-password/', api_views.ChangePasswordView.as_view(), name='change_password'),

    # Profile routes
    path('', include(router.urls)),
]
