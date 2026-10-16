"""
JWT WebSocket Middleware
Autentizuje WebSocket spojení přes JWT token z:
1. Cookie (access_token)
2. Query parametr (?token=<jwt>)
"""
import logging
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token_key: str):
    """Ověří JWT token a vrátí uživatele nebo AnonymousUser."""
    from django.contrib.auth.models import User
    try:
        token = AccessToken(token_key)
        user_id = token.get('user_id')
        if user_id is None:
            return AnonymousUser()
        return User.objects.get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    WebSocket middleware pro JWT autentizaci.
    Přidá `user` do scope před předáním do consumeru.
    """

    async def __call__(self, scope, receive, send):
        # 1. Zkusit cookie
        cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token')
        cookies = {}
        for header in scope.get('headers', []):
            if header[0] == b'cookie':
                cookie_str = header[1].decode()
                for part in cookie_str.split(';'):
                    if '=' in part:
                        k, v = part.strip().split('=', 1)
                        cookies[k.strip()] = v.strip()

        token = cookies.get(cookie_name)

        # 2. Fallback na query parametr
        if not token:
            query_string = scope.get('query_string', b'').decode()
            params = parse_qs(query_string)
            token_list = params.get('token', [])
            token = token_list[0] if token_list else None

        # 3. Získat uživatele
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Helper wrapper pro použití s ProtocolTypeRouter."""
    return JWTAuthMiddleware(inner)
