from django.urls import path

from . import twofa
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
    # T-383: dvoufázové přihlášení (TOTP)
    path('2fa/', twofa.twofa_status, name='auth-2fa'),
    path('2fa/setup/', twofa.twofa_setup, name='auth-2fa-setup'),
    path('2fa/confirm/', twofa.twofa_confirm, name='auth-2fa-confirm'),
    path('2fa/disable/', twofa.twofa_disable, name='auth-2fa-disable'),
]

