from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from .views import (
    RegisterView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    LogoutView,
    UserProfileView,
    ChangePasswordView,
    check_auth_status,
    ForgotPasswordView,
    ResetPasswordView,
)

urlpatterns = [
    # Registrace
    path('register/', RegisterView.as_view(), name='auth-register'),

    # JWT token management
    path('token/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token-verify'),

    # Logout (blacklist)
    path('logout/', LogoutView.as_view(), name='auth-logout'),

    # Profil
    path('me/', UserProfileView.as_view(), name='auth-me'),

    # Změna a obnova hesla
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='auth-forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='auth-reset-password'),

    # Status check (zpětná kompatibilita)
    path('status/', check_auth_status, name='auth-status'),
]

