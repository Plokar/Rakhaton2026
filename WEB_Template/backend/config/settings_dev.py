"""Development settings"""
from .settings import *  # noqa

DEBUG = True

ALLOWED_HOSTS = ['*']

# Dev: přijmout všechny CORS origins
CORS_ALLOW_ALL_ORIGINS = True

# Dev: méně přísné rate limity
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {  # noqa
    'anon': '10000/hour',
    'user': '100000/hour',
}

# Dev: Django Debug Toolbar (odkomentovat pokud nainstalován)
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
# INTERNAL_IPS = ['127.0.0.1']

# Dev: JWT tokeny platné déle (pro pohodlí)
from datetime import timedelta
SIMPLE_JWT = {
    **SIMPLE_JWT,  # noqa
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),   # Delší platnost v dev
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'AUTH_COOKIE_SECURE': False,
}

# Dev: E-maily posílat do Mailhogu
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mailhog'
EMAIL_PORT = 1025
EMAIL_USE_TLS = False

# Dev: SQL query logging (zakomentovat pro čistší výstup)
# LOGGING['loggers']['django.db.backends'] = {
#     'handlers': ['console'],
#     'level': 'DEBUG',
#     'propagate': False,
# }
