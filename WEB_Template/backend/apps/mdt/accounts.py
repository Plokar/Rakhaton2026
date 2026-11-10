"""Správce MDT: pozvánky, komise a pozvaní na zasedání (T-361, T-362, D-027, docs/UCTY_A_PVW.md §1–3, ARCH §6.3).

- `GET|POST /api/mdt/invitations/`, `POST …/{id}/revoke/`, `POST …/{id}/resend/`: jen správce (`mdt_manager`).
- `GET /api/mdt/invitations/public/{token}/`, `POST …/accept/`: bez přihlášení; odkaz platí jednou a do expirace.
- `GET|POST /api/mdt/committees/`, `PATCH|DELETE /api/mdt/committees/{id}/`: komise a stálí členové (správce).
- `GET|PUT /api/mdt/sessions/{sid}/invited/`: pozvaní na zasedání (komise, vyřazení, přizvaní; předseda nebo správce).
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import roles, scope
from .models import Committee, Invitation, MdtSession, UserProfile
from .templates import clean_titles

INVITE_DAYS = 7
MAX_DAYS = 30


def require_manager(request) -> None:
    if not roles.is_manager(request.user):
        raise PermissionDenied('Účty, pozvánky a komise spravuje správce MDT.')


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def frontend_url(request) -> str:
    """Adresa aplikace pro odkaz v e-mailu: `MDT_FRONTEND_URL`, jinak původ požadavku (správce v prohlížeči)."""
    configured = getattr(settings, 'MDT_FRONTEND_URL', '')
    return (configured or request.headers.get('Origin') or 'http://localhost:3000').rstrip('/')


def _status(inv: Invitation) -> str:
    if inv.revoked_at:
        return 'revoked'
    if inv.used_at:
        return 'used'
    return 'expired' if inv.expires_at <= timezone.now() else 'pending'


def _committee(c: Committee) -> dict:
    return {'id': c.pk, 'name': c.name}


def _invitation(inv: Invitation) -> dict:
    return {'id': inv.pk, 'email': inv.email, 'first_name': inv.first_name, 'last_name': inv.last_name,
            'title_before': inv.title_before, 'title_after': inv.title_after, 'specialty': inv.specialty,
            'role': inv.role, 'organization': inv.organization, 'is_external': inv.is_external,
            'committees': [_committee(c) for c in inv.committees.all()], 'status': _status(inv),
            'expires_at': inv.expires_at.isoformat(), 'used_at': inv.used_at.isoformat() if inv.used_at else None,
            'used_by': inv.used_by.username if inv.used_by else None,
            'created_by': roles.display_name(inv.created_by) if inv.created_by else None,
            'created_at': inv.created_at.isoformat()}


def _new_token(inv: Invitation, days: int) -> str:
    token = secrets.token_urlsafe(32)
    inv.token_hash = _hash(token)
    inv.expires_at = timezone.now() + timedelta(days=days)
    return token


def _send(request, inv: Invitation, link: str) -> bool:
    if not inv.email:
        return False
    from services.email_service import send_hackathon_email
    name = ' '.join(x for x in (inv.title_before, inv.first_name, inv.last_name) if x)
    body = (f'Dobrý den, {name},\n\nsprávce MDT vás zve do aplikace MDTcore. Účet si založíte přes odkaz:\n{link}\n\n'
            f'Odkaz platí do {timezone.localtime(inv.expires_at):%d. %m. %Y %H:%M} a jen jednou.')
    return send_hackathon_email(to=inv.email, subject='Pozvánka do MDTcore', body=body)


def _response(request, inv: Invitation, token: str, send: bool, status: int = 200) -> Response:
    link = f'{frontend_url(request)}/pozvanka/{token}'
    sent = _send(request, inv, link) if send else False
    return Response({**_invitation(inv), 'link': link, 'path': f'/pozvanka/{token}', 'email_sent': sent}, status=status)


def _committees(value) -> list[Committee]:
    if value in (None, ''):
        return []
    if not isinstance(value, list) or not all(isinstance(x, int) for x in value):
        raise ValidationError({'committees': 'Seznam ID komisí.'})
    found = list(Committee.objects.filter(pk__in=value))
    if len(found) != len(set(value)):
        raise ValidationError({'committees': 'Neznámá komise.'})
    return found


def _users(value, key: str) -> list:
    if not isinstance(value, list) or not all(isinstance(x, int) for x in value):
        raise ValidationError({key: 'Seznam ID uživatelů.'})
    found = list(get_user_model().objects.filter(pk__in=value))
    if len(found) != len(set(value)):
        raise ValidationError({key: 'Neznámý uživatel.'})
    return found


# ── pozvánky (správce) ───────────────────────────────────────────────────────
@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def invitation_list(request):
    """GET: všechny pozvánky (stav pending / used / expired / revoked). POST: nová pozvánka `{last_name, specialty,
    role?, email?, first_name?, title_before?, title_after?, organization?, is_external?, committees?: [id], days?,
    send_email?}` → 201 s jednorázovým odkazem (`link`, `path`); token je jen v této odpovědi."""
    require_manager(request)
    if request.method == 'GET':
        return Response([_invitation(i) for i in Invitation.objects.prefetch_related('committees')
                         .select_related('used_by', 'created_by')])
    data = request.data
    last_name = str(data.get('last_name') or '').strip()
    if not last_name:
        raise ValidationError({'last_name': 'Vyplňte příjmení.'})
    specialty = data.get('specialty')
    if specialty not in roles.SPECIALTIES:
        raise ValidationError({'specialty': 'Vyberte profesi (odbornost).'})
    is_external = bool(data.get('is_external'))
    organization = str(data.get('organization') or '').strip()[:200]
    if is_external and not organization:
        raise ValidationError({'organization': 'U lékaře z jiné nemocnice vyplňte nemocnici.'})
    role = roles.VIEWER if is_external else (data.get('role') or roles.DOCTOR)   # externí pacienty nezařazuje
    if role not in roles.ROLES:
        raise ValidationError({'role': f'Jen {", ".join(roles.ROLES)}.'})
    email = str(data.get('email') or '').strip()[:254]
    send = bool(data.get('send_email', True)) and bool(email)
    if email and '@' not in email:
        raise ValidationError({'email': 'Neplatný e-mail.'})
    try:
        days = int(data.get('days') or INVITE_DAYS)
    except (TypeError, ValueError):
        raise ValidationError({'days': 'Počet dní 1–30.'}) from None
    if not 1 <= days <= MAX_DAYS:
        raise ValidationError({'days': 'Počet dní 1–30.'})
    committees = _committees(data.get('committees'))
    titles = clean_titles(data)
    inv = Invitation(email=email, first_name=str(data.get('first_name') or '').strip()[:150], last_name=last_name[:150],
                     specialty=specialty, role=role, organization=organization, is_external=is_external,
                     created_by=request.user, **titles)
    token = _new_token(inv, days)
    inv.save()
    inv.committees.set(committees)
    return _response(request, inv, token, send, status=201)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invitation_revoke(request, iid):
    require_manager(request)
    inv = get_object_or_404(Invitation, pk=iid)
    if inv.used_at:
        return Response({'detail': 'Pozvánka už byla použita, účet spravujte v týmu.'}, status=409)
    inv.revoked_at = inv.revoked_at or timezone.now()
    inv.save(update_fields=['revoked_at'])
    return Response(_invitation(inv))


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invitation_resend(request, iid):
    """Nový odkaz (starý přestane platit) s novou platností; `{send_email?, days?}`."""
    require_manager(request)
    inv = get_object_or_404(Invitation, pk=iid)
    if inv.used_at:
        return Response({'detail': 'Pozvánka už byla použita.'}, status=409)
    token = _new_token(inv, INVITE_DAYS)
    inv.revoked_at = None
    inv.save()
    return _response(request, inv, token, bool(request.data.get('send_email', True)))


# ── pozvánka (lékař přes odkaz) ──────────────────────────────────────────────
class InvitationGone(APIException):
    status_code = 410
    default_detail = 'Pozvánka už neplatí.'


def _valid(token: str) -> Invitation:
    inv = Invitation.objects.filter(token_hash=_hash(token)).prefetch_related('committees').first()
    if inv is None:
        raise NotFound('Pozvánka neexistuje. Požádejte správce MDT o nový odkaz.')
    status = _status(inv)
    if status != 'pending':
        message = {'used': 'Pozvánka už byla použita. Přihlaste se.',
                   'expired': 'Platnost pozvánky vypršela. Požádejte správce MDT o nový odkaz.',
                   'revoked': 'Pozvánku správce zrušil.'}[status]
        raise InvitationGone({'detail': message, 'status': status})
    return inv


def _public(inv: Invitation) -> dict:
    keys = ('email', 'first_name', 'last_name', 'title_before', 'title_after', 'specialty', 'role', 'organization',
            'is_external', 'committees', 'expires_at')
    return {k: v for k, v in _invitation(inv).items() if k in keys}


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([AllowAny])
def invitation_public(request, token):
    """Údaje pozvánky pro stránku `/pozvanka/{token}` (jméno, profese, nemocnice, komise)."""
    return Response(_public(_valid(token)))


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([AllowAny])
def invitation_accept(request, token):
    """`{username, password, password2}` → účet z pozvánky, přihlášení (JWT cookies), 201. Pak průvodce nastavením."""
    from rest_framework_simplejwt.tokens import RefreshToken

    from apps.authentication.views import set_jwt_cookies
    inv = _valid(token)
    User = get_user_model()
    username = str(request.data.get('username') or '').strip()
    password = str(request.data.get('password') or '')
    if not username or len(username) > 150:
        raise ValidationError({'username': 'Vyplňte uživatelské jméno.'})
    if User.objects.filter(username__iexact=username).exists():
        raise ValidationError({'username': 'Uživatel s tímto jménem už existuje.'})
    if password != str(request.data.get('password2') or ''):
        raise ValidationError({'password2': 'Hesla se neshodují.'})
    try:
        validate_password(password)
    except DjangoValidationError as e:
        raise ValidationError({'password': list(e.messages)}) from None
    try:
        with transaction.atomic():
            locked = Invitation.objects.select_for_update().get(pk=inv.pk)
            if locked.used_at or locked.revoked_at:
                raise InvitationGone({'detail': 'Pozvánka už byla použita. Přihlaste se.', 'status': 'used'})
            user = User.objects.create_user(username=username, password=password, email=inv.email,
                                            first_name=inv.first_name, last_name=inv.last_name)
            roles.assign(user, role=inv.role, specialty=inv.specialty)
            UserProfile.objects.filter(user=user).update(
                title_before=inv.title_before, title_after=inv.title_after, organization=inv.organization,
                is_external=inv.is_external, onboarding_done=False)
            for committee in inv.committees.all():
                committee.members.add(user)
            locked.used_at, locked.used_by = timezone.now(), user
            locked.save(update_fields=['used_at', 'used_by'])
    except IntegrityError:
        raise ValidationError({'username': 'Uživatel s tímto jménem už existuje.'}) from None
    try:
        roles.ensure_practitioner(user)              # lékař v IRIS (+ nemocnice u externího); bez IRIS jede dál
    except Exception:
        pass
    from .views import _member
    response = Response(_member(User.objects.get(pk=user.pk)), status=201)
    set_jwt_cookies(response, RefreshToken.for_user(user))
    return response


# ── komise ───────────────────────────────────────────────────────────────────
def committee_out(c: Committee) -> dict:
    return {**_committee(c), 'members': [{'user_id': u.pk, 'name': roles.display_name(u)} for u in c.members.all()],
            'sessions': c.sessions.count()}


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def committee_list(request):
    """GET: komise se členy (externí lékař jen své). POST (správce): `{name, members?: [user_id]}`."""
    if request.method == 'GET':
        committees = Committee.objects.prefetch_related('members')
        if roles.is_external(request.user):
            committees = committees.filter(members=request.user)
        return Response([committee_out(c) for c in committees])
    require_manager(request)
    name = str(request.data.get('name') or '').strip()[:300]
    if not name:
        raise ValidationError({'name': 'Vyplňte název komise.'})
    if Committee.objects.filter(name__iexact=name).exists():
        raise ValidationError({'name': 'Komise s tímto názvem už existuje.'})
    members = _users(request.data.get('members') or [], 'members')
    c = Committee.objects.create(name=name)
    c.members.set(members)
    return Response(committee_out(c), status=201)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def committee_detail(request, committee_id):
    require_manager(request)
    c = get_object_or_404(Committee, pk=committee_id)
    if request.method == 'DELETE':
        c.delete()                                    # zasedání zůstanou, jen bez komise
        return Response(status=204)
    if 'name' in request.data:
        name = str(request.data.get('name') or '').strip()[:300]
        if not name:
            raise ValidationError({'name': 'Vyplňte název komise.'})
        if Committee.objects.filter(name__iexact=name).exclude(pk=c.pk).exists():
            raise ValidationError({'name': 'Komise s tímto názvem už existuje.'})
        c.name = name
        c.save(update_fields=['name'])
    if 'members' in request.data:
        c.members.set(_users(request.data.get('members'), 'members'))
    return Response(committee_out(c))


# ── pozvaní na zasedání ──────────────────────────────────────────────────────
def session_invited_out(s: MdtSession) -> dict:
    def people(users):
        return [{'user_id': u.pk, 'name': roles.display_name(u), 'specialty': roles.specialty(u),
                 'organization': getattr(getattr(u, 'mdt_profile', None), 'organization', '')} for u in users]
    members = list(s.committee.members.all()) if s.committee_id else []
    return {'session': s.pk, 'committee': _committee(s.committee) if s.committee_id else None,
            'members': people(members), 'excluded': people(s.excluded.all()), 'invited': people(s.invited.all()),
            'attendees': people(scope.invited_users(s))}


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def session_invited(request, sid):
    """GET: komise, její členové, vyřazení, přizvaní a výslední pozvaní. PUT (předseda nebo správce):
    `{committee_id?: id | null, invited?: [user_id], excluded?: [user_id]}`."""
    s = get_object_or_404(MdtSession.objects.select_related('committee'), pk=sid)
    if request.method == 'PUT':
        if not (roles.is_manager(request.user) or roles.role(request.user) == roles.ADMIN):
            raise PermissionDenied('Pozvané na zasedání mění předseda nebo správce MDT.')
        data = request.data
        if 'committee_id' in data:
            s.committee = None if data['committee_id'] is None else get_object_or_404(Committee, pk=data['committee_id'])
            s.save(update_fields=['committee'])
        if 'invited' in data:
            s.invited.set(_users(data['invited'], 'invited'))
        if 'excluded' in data:
            s.excluded.set(_users(data['excluded'], 'excluded'))
    return Response(session_invited_out(s))
