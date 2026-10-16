from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """Root API endpoint s informacemi o dostupných endpointech"""
    return Response({
        "message": "Hackathon Web Template API",
        "version": "2.0.0",
        "docs": "/api/docs/",  # Swagger UI (odkomentovat pokud nainstalován drf-spectacular)
        "endpoints": {
            "auth": {
                "register": "/api/auth/register/",
                "login": "/api/auth/token/",
                "refresh": "/api/auth/token/refresh/",
                "verify": "/api/auth/token/verify/",
                "logout": "/api/auth/logout/",
                "me": "/api/auth/me/",
                "change_password": "/api/auth/change-password/",
                "status": "/api/auth/status/",
            },
            "items": "/api/items/",
            "admin": "/admin/",
            "websockets": {
                "echo": "ws://host/ws/echo/",
                "room": "ws://host/ws/room/<room_name>/",
            }
        }
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint pro Docker healthcheck a monitoring."""
    from django.db import connection
    from django.core.cache import cache

    checks = {}

    # Database check
    try:
        connection.ensure_connection()
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'

    # Cache/Redis check
    try:
        cache.set('health_check', 'ok', 10)
        checks['cache'] = 'ok' if cache.get('health_check') == 'ok' else 'error'
    except Exception as e:
        checks['cache'] = f'error: {str(e)}'

    # Storage check
    try:
        import tempfile
        from django.conf import settings
        test_file = os.path.join(settings.MEDIA_ROOT, '.health_check')
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        with open(test_file, 'w') as f:
            f.write('ok')
        os.remove(test_file)
        checks['storage'] = 'ok'
    except Exception as e:
        checks['storage'] = f'error: {str(e)}'

    all_ok = all(v == 'ok' for v in checks.values())

    return Response(
        {
            'status': 'healthy' if all_ok else 'degraded',
            'version': '2.0.0',
            'checks': checks
        },
        status=200 if all_ok else 503
    )


import os
from django.conf import settings
from django.conf.urls.static import static
from apps.projects.ai_views import ai_generate, ai_providers_list

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', api_root, name='api-root'),
    path('api/health/', health_check, name='health-check'),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/items/', include('apps.items.urls')),

    # API Documentation (Swagger & ReDoc)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Hackathon OS Core Domain
    path('api/', include('apps.projects.urls')),
    path('api/ai/generate/', ai_generate, name='ai-generate'),
    path('api/ai/providers/', ai_providers_list, name='ai-providers'),
]

# Media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

