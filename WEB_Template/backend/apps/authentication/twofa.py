"""Dvoufázové přihlášení (T-383): TOTP z aplikace v telefonu (Google / Microsoft Authenticator).

- Každý lékař si ho může zapnout; pro správce MDT (`mdt_manager`) je povinné, když `MDT_REQUIRE_2FA_MANAGER`
  (v produkci výchozí True). Správce bez něj se přihlásí, ale API mu do nastavení vrací 403 `twofa_setup_required`.
- Přihlášení: s 2FA `POST /api/auth/token/` bez `otp` vrátí 401 `{otp_required: true}`, s `otp` normálně tokeny.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import authenticate
from django.http import JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core import totp


def _profile(user):
    from apps.mdt.models import UserProfile
    return UserProfile.objects.get_or_create(user=user)[0]


def required_for(user) -> bool:
    from apps.mdt import roles
    return bool(getattr(settings, 'MDT_REQUIRE_2FA_MANAGER', False)) and roles.is_manager(user)


def enabled_for(user) -> bool:
    from apps.mdt.models import UserProfile
    return UserProfile.objects.filter(user=user, totp_enabled=True).exists()


def check_login_code(user, code: str | None) -> bool | None:
    """Pro přihlášení: `None` = 2FA vypnuté, `True` = kód platí (a zapíše se, aby nešel použít znovu), `False` = ne."""
    if not enabled_for(user):
        return None
    profile = _profile(user)
    step = totp.verify(profile.totp_secret, code or '', last_step=profile.totp_last_step)
    if step is None:
        return False
    profile.totp_last_step = step
    profile.save(update_fields=['totp_last_step'])
    return True


def _state(user) -> dict:
    return {'enabled': enabled_for(user), 'required': required_for(user)}


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def twofa_status(request):
    """`{enabled, required}`."""
    return Response(_state(request.user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def twofa_setup(request):
    """Nové tajemství (zatím nepotvrzené) → `{secret, otpauth_uri}`; aplikace ho ukáže jako QR kód. Zapnuté 2FA
    se tím nezmění, dokud ho lékař nepotvrdí kódem (`confirm`)."""
    profile = _profile(request.user)
    if profile.totp_enabled:
        return Response({'detail': 'Dvoufázové přihlášení už je zapnuté.'}, status=409)
    profile.totp_secret = totp.new_secret()
    profile.totp_last_step = None
    profile.save(update_fields=['totp_secret', 'totp_last_step'])
    account = request.user.email or request.user.username
    return Response({'secret': profile.totp_secret, 'otpauth_uri': totp.otpauth_uri(profile.totp_secret, account)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def twofa_confirm(request):
    """`{code}` z aplikace → zapne 2FA."""
    profile = _profile(request.user)
    if profile.totp_enabled:
        return Response(_state(request.user))
    step = totp.verify(profile.totp_secret, str(request.data.get('code') or ''))
    if not profile.totp_secret or step is None:
        raise ValidationError({'code': 'Kód nesedí. Zkontrolujte čas v telefonu a zkuste aktuální kód.'})
    profile.totp_enabled, profile.totp_last_step = True, step
    profile.save(update_fields=['totp_enabled', 'totp_last_step'])
    return Response(_state(request.user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def twofa_disable(request):
    """`{password, code}` → vypne 2FA. Správce s povinným 2FA ho vypnout nemůže (409)."""
    if required_for(request.user):
        return Response({'detail': 'Správce MDT má dvoufázové přihlášení povinné.'}, status=409)
    if authenticate(username=request.user.username, password=str(request.data.get('password') or '')) is None:
        raise ValidationError({'password': 'Heslo nesedí.'})
    if check_login_code(request.user, str(request.data.get('code') or '')) is False:
        raise ValidationError({'code': 'Kód nesedí.'})
    profile = _profile(request.user)
    profile.totp_enabled, profile.totp_secret, profile.totp_last_step = False, '', None
    profile.save(update_fields=['totp_enabled', 'totp_secret', 'totp_last_step'])
    return Response(_state(request.user), status=status.HTTP_200_OK)


ALLOWED_WITHOUT_2FA = ('/api/auth/', '/api/mdt/me/', '/api/health/')


class RequireManager2FAMiddleware:
    """Správce MDT s povinným 2FA, který ho ještě nemá, dostane na API 403 `twofa_setup_required` (kromě přihlášení,
    nastavení 2FA a `me`). Frontend ho pošle do nastavení."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if (path.startswith('/api/') and not path.startswith(ALLOWED_WITHOUT_2FA)
                and getattr(settings, 'MDT_REQUIRE_2FA_MANAGER', False)):
            from apps.mdt.scope import _api_user
            user = _api_user(request)
            if user is not None and required_for(user) and not enabled_for(user):
                return JsonResponse({'detail': 'Nejdřív si nastavte dvoufázové přihlášení (Nastavení → Zabezpečení).',
                                     'twofa_setup_required': True}, status=403)
        return self.get_response(request)
