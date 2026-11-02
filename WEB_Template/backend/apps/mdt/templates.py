"""Šablony klíčových údajů lékaře a zakládání lékaře předsedou (T-338, docs/SABLONY_LEKARE.md, ARCH §6.3).

- `GET /api/mdt/templates/`: moje šablony po oblastech + presety (podle mé odbornosti nahoře).
- `PUT|DELETE /api/mdt/templates/{area}/`: uložit / zrušit (pak platí výchozí pořadí).
- `GET /api/mdt/templates/catalog/?area=PLI`: kategorie a údaje oblasti pro editor.
- `POST /api/mdt/users/`: předseda založí lékaře (profil + šablony v jednom kroku).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from services.rules import fact_templates as ft
from services.rules.fact_categories import AREAS

from . import roles
from .models import FactTemplate, UserProfile

TITLE_MAX = 40


def _template(t: FactTemplate | None, area: str) -> dict:
    return {'area': area, 'area_label': AREAS[area], 'layout': t.layout if t else None,
            'preset': t.preset if t else None, 'updated_at': t.updated_at.isoformat() if t else None}


def clean_templates(value) -> dict[str, dict]:
    """`{area: layout}` z požadavku (registrace, založení lékaře) → ověřené, jinak 400."""
    if value in (None, ''):
        return {}
    if not isinstance(value, dict) or set(value) - set(AREAS):
        raise ValidationError({'templates': f'Objekt {{oblast: rozložení}}, oblasti {", ".join(AREAS)}.'})
    out = {}
    for area, layout in value.items():
        try:
            out[area] = ft.validate_layout(layout)
        except ValueError as e:
            raise ValidationError({'templates': f'{area}: {e}'}) from None
    return out


def save_templates(user, templates: dict[str, dict], preset: str = '') -> None:
    for area, layout in templates.items():
        FactTemplate.objects.update_or_create(user=user, area=area, defaults={'layout': layout, 'preset': preset})


def clean_titles(data) -> dict[str, str]:
    out = {}
    for key in ('title_before', 'title_after'):
        if key in data:
            value = str(data.get(key) or '').strip()
            if len(value) > TITLE_MAX:
                raise ValidationError({key: f'Nejvýš {TITLE_MAX} znaků.'})
            out[key] = value
    return out


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def template_list(request):
    """Moje šablony po oblastech (`layout: null` = výchozí pořadí) a presety; presety mé odbornosti jsou první."""
    mine = {t.area: t for t in FactTemplate.objects.filter(user=request.user)}
    specialty = roles.specialty(request.user)
    presets = sorted(ft.presets(), key=lambda p: (specialty not in p['specialties'], p['id'] == 'vychozi'))
    return Response({
        'templates': [_template(mine.get(area), area) for area in AREAS],
        'presets': [{k: p[k] for k in ('id', 'name', 'note', 'specialties', 'area', 'layout')} for p in presets],
        'suggested': {area: ft.preset_for(specialty, area)['id'] for area in AREAS},
    })


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def template_detail(request, area):
    """PUT `{layout, preset?}` uloží mou šablonu oblasti; DELETE ji zruší (platí výchozí pořadí)."""
    if area not in AREAS:
        raise ValidationError({'area': f'Jen {", ".join(AREAS)}.'})
    if request.method == 'DELETE':
        FactTemplate.objects.filter(user=request.user, area=area).delete()
        return Response(_template(None, area))
    try:
        layout = ft.validate_layout(request.data.get('layout'))
    except ValueError as e:
        raise ValidationError({'layout': str(e)}) from None
    preset = str(request.data.get('preset') or '')[:40]
    t, _ = FactTemplate.objects.update_or_create(user=request.user, area=area,
                                                 defaults={'layout': layout, 'preset': preset})
    return Response(_template(t, area))


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([AllowAny])
def template_catalog(request):
    """Kategorie, údaje a presety oblasti (`?area=PLI`) pro editor šablony. Bez přihlášení (registrace):
    obsahuje jen názvy údajů a kategorií, žádná data pacientů."""
    area = request.query_params.get('area', 'OBC')
    try:
        catalog = ft.catalog(area)
    except ValueError as e:
        raise ValidationError({'area': str(e)}) from None
    presets = [{k: p[k] for k in ('id', 'name', 'note', 'specialties', 'area', 'layout')}
               for p in ft.presets() if p['area'] in (area, '*')]
    return Response({**catalog, 'presets': presets})


def create_user(request):
    """POST `/api/mdt/users/` (předseda): `{username, password, email?, first_name, last_name, title_before?,
    title_after?, specialty, role, templates?: {area: layout}, preset?}` → 201 `Me`."""
    data = request.data
    User = get_user_model()
    username = str(data.get('username') or '').strip()
    if not username or len(username) > 150:
        raise ValidationError({'username': 'Vyplňte uživatelské jméno.'})
    if User.objects.filter(username__iexact=username).exists():
        raise ValidationError({'username': 'Uživatel s tímto jménem už existuje.'})
    if not str(data.get('last_name') or '').strip():
        raise ValidationError({'last_name': 'Vyplňte příjmení.'})
    role = data.get('role') or roles.DOCTOR
    if role not in roles.ROLES:
        raise ValidationError({'role': f'Jen {", ".join(roles.ROLES)}.'})
    specialty = data.get('specialty')
    if specialty not in roles.SPECIALTIES:
        raise ValidationError({'specialty': 'Vyberte profesi (odbornost).'})
    password = str(data.get('password') or '')
    try:
        validate_password(password)
    except DjangoValidationError as e:
        raise ValidationError({'password': list(e.messages)}) from None
    titles = clean_titles(data)
    templates = clean_templates(data.get('templates'))
    with transaction.atomic():
        user = User.objects.create_user(username=username, password=password, email=str(data.get('email') or ''),
                                        first_name=str(data.get('first_name') or '').strip()[:150],
                                        last_name=str(data['last_name']).strip()[:150])
        roles.assign(user, role=role, specialty=specialty)
        UserProfile.objects.filter(user=user).update(**titles)
        save_templates(user, templates, str(data.get('preset') or '')[:40])
    try:
        roles.ensure_practitioner(user)              # lékař v IRIS pro výběr přítomných (T-328); bez IRIS jede dál
    except Exception:
        pass
    return User.objects.get(pk=user.pk)              # profil s tituly načtený znovu (ne z mezipaměti vztahu)
