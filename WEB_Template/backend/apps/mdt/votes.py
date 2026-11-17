"""Souhlas přítomných s návrhem závěru (T-381, ARCH §6.3).

Během jednání předseda nebo zadávající lékař píše návrh závěru; ostatní členové komise z mobilu nebo webu dají
„souhlasím“ nebo „nesouhlasím“ s krátkým důvodem. Předseda to vidí v editoru závěru a při potvrzení se stav zapíše
do záznamu MDT (`sections.votes`, Composition v IRIS i PDF). Hlas nic nerozhoduje: závěr potvrzuje předseda.
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import roles
from .models import Decision, DecisionVote, MdtCase


def _vote(v: DecisionVote) -> dict:
    return {'user_id': v.user_id, 'name': roles.display_name(v.user), 'specialty': roles.specialty(v.user),
            'vote': v.vote, 'comment': v.comment, 'updated_at': timezone.localtime(v.updated_at).isoformat()}


def _state(case: MdtCase, user) -> dict:
    """`DecisionVotes` (ARCH §8.6): hlasy, součty, jestli jde hlasovat a můj hlas."""
    decision = Decision.objects.filter(case=case).first()
    votes = list(case.votes.select_related('user__mdt_profile'))
    is_open = bool(decision and decision.status == 'draft' and case.session.status != 'closed')
    return {'case_id': case.pk, 'open': is_open, 'decision': decision.status if decision else None,
            'agree': sum(v.vote == 'agree' for v in votes), 'disagree': sum(v.vote == 'disagree' for v in votes),
            'votes': [_vote(v) for v in votes], 'mine': next((_vote(v) for v in votes if v.user_id == user.pk), None)}


def snapshot(case: MdtCase) -> list[dict]:
    """Hlasy pro záznam při potvrzení (`DecisionVoteRecord`)."""
    return [{'member': roles.display_name(v.user), 'role': roles.specialty(v.user), 'vote': v.vote,
             'comment': v.comment, 'at': timezone.localtime(v.updated_at).isoformat()}
            for v in case.votes.select_related('user__mdt_profile')]


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def case_votes(request, cid):
    """GET: `DecisionVotes`. PUT `{vote: "agree" | "disagree", comment?}`: můj hlas (nesouhlas chce důvod), jen
    u návrhu závěru na neuzavřeném zasedání, jinak 409. DELETE: stáhnout můj hlas."""
    case = get_object_or_404(MdtCase.objects.select_related('session'), pk=cid)
    if request.method == 'GET':
        return Response(_state(case, request.user))
    state = _state(case, request.user)
    if not state['open']:
        detail = ('Závěr je potvrzený, hlasovat už nejde.' if state['decision'] == 'confirmed'
                  else 'Návrh závěru zatím není.' if state['decision'] is None else 'Zasedání je ukončené.')
        return Response({'detail': detail}, status=409)
    if request.method == 'DELETE':
        DecisionVote.objects.filter(case=case, user=request.user).delete()
        return Response(_state(case, request.user))
    vote = request.data.get('vote')
    if vote not in ('agree', 'disagree'):
        raise ValidationError({'vote': 'Jen "agree" nebo "disagree".'})
    comment = str(request.data.get('comment') or '').strip()
    if vote == 'disagree' and not comment:
        raise ValidationError({'comment': 'U nesouhlasu napište krátce proč (zapíše se do záznamu MDT).'})
    if len(comment) > DecisionVote.MAX_COMMENT:
        raise ValidationError({'comment': f'Nejvýš {DecisionVote.MAX_COMMENT} znaků.'})
    from services.ai.pseudonymize import PERSONAL_DATA_LABELS, personal_data_kinds
    if kinds := personal_data_kinds(comment):
        found = ', '.join(PERSONAL_DATA_LABELS[k] for k in kinds)
        raise ValidationError({'comment': f'Důvod obsahuje osobní údaj ({found}). Pacienta označte jen jako Pxx.'})
    DecisionVote.objects.update_or_create(case=case, user=request.user, defaults={'vote': vote, 'comment': comment})
    return Response(_state(case, request.user))
