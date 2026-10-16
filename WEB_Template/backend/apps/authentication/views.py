"""
JWT Authentication – Views
Náhrada session auth za stateless JWT tokeny.
Endpoints:
  POST /api/auth/register/       – Registrace, vrátí JWT
  POST /api/auth/token/          – Login (obtain JWT pair)
  POST /api/auth/token/refresh/  – Refresh access tokenu
  POST /api/auth/token/verify/   – Ověření access tokenu
  POST /api/auth/logout/         – Blacklist refresh tokenu
  GET  /api/auth/me/             – Profil přihlášeného uživatele
  PUT  /api/auth/me/             – Aktualizace profilu
  POST /api/auth/change-password/ – Změna hesla
"""
import logging
from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .serializers import (
    RegisterSerializer,
    UserSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
)

logger = logging.getLogger(__name__)

# ── Konstanty pro cookie nastavení ────────────────────────────────────────────
COOKIE_SETTINGS = {
    'httponly': settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True),
    'secure': settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
    'samesite': settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
    'path': settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
}


def set_jwt_cookies(response: Response, refresh_token) -> Response:
    """Nastaví JWT tokeny jako httpOnly cookies."""
    access_token = str(refresh_token.access_token)
    refresh_str = str(refresh_token)

    response.set_cookie(
        key=settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'),
        value=access_token,
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        **COOKIE_SETTINGS,
    )
    response.set_cookie(
        key=settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token'),
        value=refresh_str,
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        **COOKIE_SETTINGS,
    )
    return response


def clear_jwt_cookies(response: Response) -> Response:
    """Smaže JWT cookies (logout)."""
    response.delete_cookie(settings.SIMPLE_JWT.get('AUTH_COOKIE', 'access_token'))
    response.delete_cookie(settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token'))
    return response


class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Registrace nového uživatele – vrátí JWT tokeny.
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        response = Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'message': 'Registrace proběhla úspěšně.',
        }, status=status.HTTP_201_CREATED)

        set_jwt_cookies(response, refresh)
        logger.info(f"New user registered: {user.username} ({user.email})")
        return response


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/auth/token/
    Login – vrátí JWT access + refresh token (v body i cookies).
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        data = serializer.validated_data
        user = User.objects.get(username=request.data.get('username'))
        refresh = RefreshToken.for_user(user)

        response_data = {
            'user': UserSerializer(user).data,
            'access': data['access'],
            'refresh': data['refresh'],
        }
        response = Response(response_data, status=status.HTTP_200_OK)
        set_jwt_cookies(response, refresh)

        logger.info(f"User logged in: {user.username}")
        return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    POST /api/auth/token/refresh/
    Refresh access tokenu – přijme refresh z body nebo cookie.
    """
    def post(self, request, *args, **kwargs):
        # Pokud není refresh v body, zkusit cookie
        refresh_token = request.COOKIES.get(
            settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token')
        )
        if refresh_token and 'refresh' not in request.data:
            request.data._mutable = True if hasattr(request.data, '_mutable') else None
            data = request.data.copy()
            data['refresh'] = refresh_token
            request._data = data

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            refresh = RefreshToken(response.data.get('refresh', refresh_token))
            set_jwt_cookies(response, refresh)

        return response


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blacklistuje refresh token a smaže cookies.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = (
                request.data.get('refresh')
                or request.COOKIES.get(settings.SIMPLE_JWT.get('AUTH_COOKIE_REFRESH', 'refresh_token'))
            )
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info(f"User logged out: {request.user.username}")

            response = Response({'message': 'Odhlášení proběhlo úspěšně.'})
            clear_jwt_cookies(response)
            return response

        except TokenError:
            response = Response({'message': 'Odhlášeno (token již byl invalidován).'})
            clear_jwt_cookies(response)
            return response


class UserProfileView(APIView):
    """
    GET  /api/auth/me/  – Profil přihlášeného uživatele
    PUT  /api/auth/me/  – Aktualizace profilu
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Změna hesla – invaliduje všechny refresh tokeny uživatele.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Invalidovat všechny refresh tokeny uživatele
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            tokens = OutstandingToken.objects.filter(user=request.user)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)
        except Exception:
            pass  # Token blacklist nemusí být nainstalován

        response = Response({'message': 'Heslo bylo úspěšně změněno. Přihlaste se znovu.'})
        clear_jwt_cookies(response)
        return response


@api_view(['GET'])
@permission_classes([AllowAny])
def check_auth_status(request):
    """
    GET /api/auth/status/
    Kontrola stavu autentizace (pro client-side auth check).
    """
    if request.user.is_authenticated:
        return Response({
            'authenticated': True,
            'user': UserSerializer(request.user).data,
        })
    return Response({'authenticated': False, 'user': None})


class ForgotPasswordView(APIView):
    """
    POST /api/auth/forgot-password/
    Zašle e-mail s resetovacím odkazem do Mailhogu.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response({'error': 'Email je povinný.'}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(email=email)
        if users.exists():
            user = users.first()
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            from services.email_service import send_hackathon_email

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"http://localhost:3000/reset-password?uid={uid}&token={token}"

            subject = "Obnova hesla – Hackathon Template"
            body = f"Ahoj {user.username},\n\npro obnovu hesla klikni na odkaz:\n{reset_url}\n\nOdkaz je platný 24 hodin."
            html_body = f"""
            <div style="font-family: sans-serif; padding: 20px;">
              <h2>Obnova hesla</h2>
              <p>Ahoj <b>{user.username}</b>,</p>
              <p>obdrželi jsme žádost o obnovu tvého hesla v Hackathon OS.</p>
              <p><a href="{reset_url}" style="background: #4f46e5; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none;">Nastavit nové heslo</a></p>
              <p style="color: #6b7280; font-size: 12px; margin-top: 20px;">Pokud jsi o změnu nežádal/a, tento email ignoruj.</p>
            </div>
            """
            send_hackathon_email(to=email, subject=subject, body=body, html_body=html_body)

        return Response({
            'message': 'Pokud je zadaný e-mail v systému, byl odeslán odkaz pro obnovu hesla (zkontroluj Mailhog na :8025).'
        })


class ResetPasswordView(APIView):
    """
    POST /api/auth/reset-password/
    Nastaví nové heslo na základě tokenu.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        new_password2 = request.data.get('new_password2')

        if not all([uidb64, token, new_password]):
            return Response({'error': 'Chybí povinné parametry (uid, token, new_password).'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != new_password2:
            return Response({'error': 'Hesla se neshodují.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'error': 'Heslo musí mít alespoň 8 znaků.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_decode
            from django.utils.encoding import force_str

            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Neplatný uživatel nebo token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Token je neplatný nebo již expiroval.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Heslo bylo úspěšně nastaveno. Nyní se můžete přihlásit.'})

