"""
Cookie-based JWT Authentication Backend
Umožňuje autentizaci přes httpOnly cookies místo Authorization headeru.
"""
from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT autentizace z httpOnly cookie.
    Fallback na standardní Bearer token v Authorization headeru.
    """

    def authenticate(self, request):
        # 1. Zkusit cookie
        cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token')
        raw_token = request.COOKIES.get(cookie_name)

        if raw_token:
            try:
                validated_token = self.get_validated_token(raw_token)
                user = self.get_user(validated_token)
                return user, validated_token
            except (InvalidToken, TokenError):
                pass  # Token z cookie je neplatný, zkusit header

        # 2. Fallback na Authorization header
        return super().authenticate(request)
