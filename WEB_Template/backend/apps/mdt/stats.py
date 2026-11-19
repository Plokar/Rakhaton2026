"""Statistiky komise (T-384): kolik případů, jak rychle od zařazení k potvrzení, soulad s guidelines, vrácení
k doplnění a souhlas přítomných. Jen předseda a správce MDT; pacienti se nevypisují, jen počty."""
from collections import Counter, defaultdict
from statistics import median

from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import roles
from .models import Decision, DecisionVote, MdtCase


def _range(request):
    out = {}
    for param in ('from', 'to'):
        raw = request.query_params.get(param)
        if raw:
            day = parse_date(raw)
            if day is None:
                raise ValidationError({param: 'Datum YYYY-MM-DD.'})
            out[param] = day
    return out.get('from'), out.get('to')


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def committee_stats(request):
    """`?from=&to=` (YYYY-MM-DD, termín zasedání). Celkem a po komisích (`committee` nebo název boardu)."""
    if not (roles.role(request.user) == roles.ADMIN or roles.is_manager(request.user)):
        raise PermissionDenied('Statistiky vidí předseda a správce MDT.')
    start, end = _range(request)
    cases = MdtCase.objects.select_related('session__committee')
    if start:
        cases = cases.filter(session__date__date__gte=start)
    if end:
        cases = cases.filter(session__date__date__lte=end)
    cases = list(cases)
    decisions = {d.case_id: d for d in Decision.objects.filter(case__in=cases)}
    votes = Counter(DecisionVote.objects.filter(case__in=cases).values_list('vote', flat=True))

    def summarize(items: list[MdtCase]) -> dict:
        status = Counter(c.status for c in items)
        days, compliance = [], Counter()
        for c in items:
            d = decisions.get(c.pk)
            if d and d.status == 'confirmed' and d.confirmed_at:
                days.append((d.confirmed_at - c.created_at).total_seconds() / 86400)
            gc = ((d.content.get('sections') or {}).get('guideline_compliance') if d else None)
            if d and d.status == 'confirmed':
                compliance['compliant' if gc and gc.get('compliant') else 'deviation' if gc else 'unknown'] += 1
        return {'cases': len(items), 'sessions': len({c.session_id for c in items}), 'by_status': dict(status),
                'confirmed': status.get('confirmed', 0), 'returned': status.get('returned', 0),
                'median_days_to_confirm': round(median(days), 1) if days else None,
                'guideline_compliance': {k: compliance.get(k, 0) for k in ('compliant', 'deviation', 'unknown')}}

    groups = defaultdict(list)
    for c in cases:
        groups[c.session.committee.name if c.session.committee_id else c.session.title].append(c)
    months = Counter(timezone.localtime(c.session.date).strftime('%Y-%m') for c in cases)
    return Response({'from': start.isoformat() if start else None, 'to': end.isoformat() if end else None,
                     'total': summarize(cases), 'votes': {'agree': votes.get('agree', 0), 'disagree': votes.get('disagree', 0)},
                     'by_committee': sorted(({'name': name, **summarize(items)} for name, items in groups.items()),
                                            key=lambda x: -x['cases']),
                     'by_month': [{'month': m, 'cases': n} for m, n in sorted(months.items())]})


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def re_mdt_list(request):
    """Plánovaná re-MDT do 30 dní (i prošlá) bez zařazení na budoucí zasedání (T-384). Předseda vidí všechny,
    lékař své (zadávající nebo přizvaný). Zařazuje lékař sám („Zařadit“), nic se neděje automaticky."""
    from services.followup import re_mdt_due
    return Response(re_mdt_due(request.user))
