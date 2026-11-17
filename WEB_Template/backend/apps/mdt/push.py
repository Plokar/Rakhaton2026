"""Odběr push oznámení zařízení (T-383): klíč VAPID pro prohlížeč a uložení / zrušení odběru."""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from services import push

from .models import PushSubscription


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def push_key(request):
    """`{enabled, public_key?}`: bez klíčů VAPID na serveru jsou oznámení vypnutá."""
    return Response({'enabled': True, 'public_key': push.public_key()} if push.enabled() else {'enabled': False})


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def push_subscriptions(request):
    """POST `PushSubscription.toJSON()` z prohlížeče (`{endpoint, keys: {p256dh, auth}}`) → uloží pro mě;
    DELETE `{endpoint}` → zruší (odhlášení na zařízení)."""
    endpoint = str(request.data.get('endpoint') or '')
    if not endpoint.startswith('https://') or len(endpoint) > 1000:
        raise ValidationError({'endpoint': 'Adresa push služby (https://…).'})
    if request.method == 'DELETE':
        PushSubscription.objects.filter(endpoint=endpoint, user=request.user).delete()
        return Response(status=204)
    if not push.enabled():
        return Response({'detail': 'Push oznámení nejsou na serveru zapnutá.'}, status=409)
    keys = request.data.get('keys') or {}
    if not isinstance(keys, dict) or not keys.get('p256dh') or not keys.get('auth'):
        raise ValidationError({'keys': 'Chybí p256dh a auth.'})
    PushSubscription.objects.update_or_create(endpoint=endpoint, defaults={
        'user': request.user, 'p256dh': str(keys['p256dh'])[:200], 'auth': str(keys['auth'])[:100]})
    return Response({'enabled': True}, status=201)
