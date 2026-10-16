"""
Django ASGI configuration for WebSocket + HTTP routing.
Hackathon Web Template – supports both HTTP and WebSocket connections.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to populate AppRegistry
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from apps.ws.middleware import JWTAuthMiddlewareStack
from apps.ws import routing as ws_routing

application = ProtocolTypeRouter({
    # HTTP requests → standard Django ASGI handler
    "http": django_asgi_app,

    # WebSocket requests → channels URL router
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(
                ws_routing.websocket_urlpatterns
            )
        )
    ),
})
