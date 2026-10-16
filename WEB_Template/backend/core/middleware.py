"""
Custom middleware pro bezpečnost a rate limiting
"""
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
import time


class RateLimitMiddleware:
    """
    Simple rate limiting middleware pro ochranu API endpointů
    V produkci doporučuji použít django-ratelimit nebo Redis
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Rate limits: (requests, seconds)
        self.limits = {
            '/api/auth/login/': (5, 300),  # 5 pokusů za 5 minut
            '/api/auth/register/': (3, 3600),  # 3 registrace za hodinu
            'default': (100, 60),  # 100 requestů za minutu pro ostatní
        }

    def __call__(self, request):
        if not settings.DEBUG:  # Rate limiting pouze v produkci
            # Získání IP adresy
            ip = self.get_client_ip(request)
            path = request.path
            
            # Kontrola rate limitu
            if not self.check_rate_limit(ip, path):
                return JsonResponse({
                    'error': 'Příliš mnoho požadavků. Zkuste to prosím později.'
                }, status=429)
        
        response = self.get_response(request)
        return response

    def get_client_ip(self, request):
        """Získání IP adresy klienta (i za proxy)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def check_rate_limit(self, ip, path):
        """Kontrola, zda IP nepřekročila rate limit"""
        # Najdi vhodný limit
        limit_key = path if path in self.limits else 'default'
        max_requests, time_window = self.limits.get(limit_key, self.limits['default'])
        
        # Cache key
        cache_key = f'rate_limit:{ip}:{path}'
        
        # Získej aktuální počet requestů
        requests = cache.get(cache_key, [])
        now = time.time()
        
        # Odstraň staré requesty mimo time window
        requests = [req_time for req_time in requests if now - req_time < time_window]
        
        # Kontrola limitu
        if len(requests) >= max_requests:
            return False
        
        # Přidej nový request
        requests.append(now)
        cache.set(cache_key, requests, time_window)
        
        return True


class SecurityHeadersMiddleware:
    """
    Middleware pro přidání dalších security headers
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Content Security Policy
        if not settings.DEBUG:
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' " + ' '.join(settings.CORS_ALLOWED_ORIGINS) + "; "
                "frame-ancestors 'none';"
            )
        
        # Permissions Policy (dříve Feature-Policy)
        response['Permissions-Policy'] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
