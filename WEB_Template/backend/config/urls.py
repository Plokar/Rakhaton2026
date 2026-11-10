import os

from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    """Root API endpoint s informacemi o dostupných endpointech"""
    return Response({
        "message": "MDTcore API",
        "version": os.environ.get("APP_VERSION", "dev"),
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


def _iris_checks() -> dict:
    """IRIS FHIR (`GET metadata`) a IRIS SQL (`SELECT 1`), jen s `IRIS_HOST`; výsledek v cache 20 s (T-369).

    Monitoring à 30 s nesmí vyčerpat limit spojení Community Edition; spojení se vždy zavírá (`db.connect`).
    """
    if not os.environ.get('IRIS_HOST'):
        return {'iris_fhir': 'skipped', 'iris_sql': 'skipped'}
    from django.core.cache import cache

    try:
        cached = cache.get('health_iris')
    except Exception:
        cached = None
    if cached:
        return cached
    from services.fhir import client
    from services.iris import db

    checks = {}
    try:
        client.request('GET', 'metadata', timeout=3)
        checks['iris_fhir'] = 'ok'
    except Exception as e:
        checks['iris_fhir'] = f'error: {type(e).__name__}'
    try:
        with db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.fetchone()
        checks['iris_sql'] = 'ok'
    except Exception as e:
        checks['iris_sql'] = f'error: {type(e).__name__}'
    try:
        cache.set('health_iris', checks, 20)
    except Exception:
        pass
    return checks


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([])  # Docker healthcheck každých 30 s nesmí narazit na anon limit (T-353)
def health_check(request):
    """Health check pro Docker a monitoring (T-369, ARCH §6.3).

    Postgres, Redis nebo disk dole → 503 vždy. IRIS dole → `degraded`, ale 200 (Docker nesmí kvůli IRIS
    restartovat backend); `?strict=1` vrátí při `degraded` 503 (externí monitoring pilotu).
    """
    from django.db import connection
    from django.core.cache import cache

    checks = {}
    try:
        connection.ensure_connection()
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {type(e).__name__}'
    try:
        cache.set('health_check', 'ok', 10)
        checks['cache'] = 'ok' if cache.get('health_check') == 'ok' else 'error'
    except Exception as e:
        checks['cache'] = f'error: {type(e).__name__}'
    try:
        test_file = os.path.join(settings.MEDIA_ROOT, '.health_check')
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        with open(test_file, 'w') as f:
            f.write('ok')
        os.remove(test_file)
        checks['storage'] = 'ok'
    except Exception as e:
        checks['storage'] = f'error: {type(e).__name__}'
    core_ok = all(v == 'ok' for v in checks.values())
    checks.update(_iris_checks())
    all_ok = all(v in ('ok', 'skipped') for v in checks.values())
    strict = request.query_params.get('strict') in ('1', 'true')
    return Response(
        {'status': 'healthy' if all_ok else 'degraded', 'version': os.environ.get('APP_VERSION', 'dev'), 'checks': checks},
        status=200 if core_ok and (all_ok or not strict) else 503,
    )


from django.conf.urls.static import static
from apps.projects.ai_views import ai_generate, ai_providers_list
from apps.patients import views as patient_views
from apps.copilot import views as copilot_views

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
    path('api/patients/', include('apps.patients.urls')),
    path('api/evidence/', patient_views.evidence_source, name='evidence-source'),
    path('api/mdt/', include('apps.mdt.urls')),
    path('api/jobs/<int:jid>/', copilot_views.job_status, name='job-status'),
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

