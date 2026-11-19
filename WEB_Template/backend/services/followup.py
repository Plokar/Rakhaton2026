"""Sledování po zasedání a připomínky (T-384): co komu poslat. Odesílá `manage.py mdt_reminders` (cron).

Nic se tu nerozhoduje ani nezakládá v záznamu: re-MDT se jen připomene zadávajícímu lékaři, pacienta na
zasedání zařazuje lékař (zlaté pravidlo: oficiální je jen to, co potvrdí lékař).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

RE_MDT_AHEAD_DAYS = 30


def re_mdt_due(user=None, today: date | None = None) -> list[dict]:
    """Potvrzené závěry s plánovaným re-MDT do 30 dní (i prošlé), kde pacient ještě není na budoucím zasedání.
    `user` = jen případy, kde je zadávající nebo přizvaný (předseda vidí vše)."""
    from apps.mdt import roles
    from apps.mdt.models import Decision, MdtCase

    today = today or timezone.localdate()
    future = set(MdtCase.objects.filter(session__date__date__gte=today).exclude(session__status='closed')
                 .values_list('patient_fhir_id', flat=True))
    out = []
    decisions = Decision.objects.filter(status='confirmed').select_related('case__session', 'case__created_by')
    if user is not None and roles.role(user) != roles.ADMIN:
        from django.db.models import Q
        decisions = decisions.filter(Q(case__created_by=user) | Q(case__collaborators=user)).distinct()
    for d in decisions:
        re_mdt = (d.content.get('sections') or {}).get('re_mdt') or {}
        try:
            due = date.fromisoformat(str(re_mdt.get('date'))[:10])
        except ValueError:
            continue
        if due > today + timedelta(days=RE_MDT_AHEAD_DAYS) or d.case.patient_fhir_id in future:
            continue
        c = d.case
        out.append({'case_id': c.pk, 'patient_id': c.patient_fhir_id, 'date': due.isoformat(), 'overdue': due < today,
                    'reason': re_mdt.get('reason', ''), 'session': {'id': c.session_id, 'title': c.session.title},
                    'committee_id': c.session.committee_id,
                    'requester': c.created_by and {'user_id': c.created_by_id, 'name': roles.display_name(c.created_by)}})
    return sorted(out, key=lambda x: x['date'])


def day_before(today: date | None = None) -> dict[int, list[str]]:
    """Zítřejší zasedání: zadávajícímu lékaři co u jeho pacientů chybí (připravenost) a co je nového (T-349)."""
    from apps.mdt.models import MdtCase
    from services import patients
    from services.fhir.client import FhirError
    from services.rules import readiness, review

    today = today or timezone.localdate()
    lines: dict[int, list[str]] = defaultdict(list)
    for c in (MdtCase.objects.filter(session__date__date=today + timedelta(days=1), session__status='planned')
              .exclude(created_by=None).select_related('session')):
        try:
            resources = patients.load_patient(c.patient_fhir_id)
        except FhirError:
            continue
        ready = readiness.evaluate_readiness(resources, c.skipped_fields)
        missing = [f.get('label') or f['id'] for f in ready['unresolved']]
        state = review.review_state(resources, service_request_id=c.service_request_fhir_id,
                                    meeting=timezone.localtime(c.session.date), now=timezone.now(),
                                    created=c.created_at, checked_at=c.checked_at, session_status=c.session.status)
        parts = []
        if missing:
            parts.append(f'chybí: {", ".join(missing[:6])}{"…" if len(missing) > 6 else ""}')
        if state['unseen_count']:
            parts.append(f'nových výsledků ke kontrole: {state["unseen_count"]}')
        if parts:
            lines[c.created_by_id].append(f'{c.patient_fhir_id} ({c.session.title}): {"; ".join(parts)}')
    return lines


def overdue_tasks(today: date | None = None) -> dict[int, list[str]]:
    """Úkoly po zasedání po termínu → vlastníkovi (účet propojený s lékařem v IRIS, T-328)."""
    from apps.mdt.models import UserProfile
    from services import tasks

    today = today or timezone.localdate()
    owners = dict(UserProfile.objects.exclude(practitioner_fhir_id='').values_list('practitioner_fhir_id', 'user_id'))
    lines: dict[int, list[str]] = defaultdict(list)
    for t in tasks.list_tasks():
        if t['status'] == 'completed' or not t.get('due_date') or date.fromisoformat(t['due_date'][:10]) >= today:
            continue
        uid = owners.get((t.get('owner') or {}).get('id'))
        if uid:
            lines[uid].append(f'{t["patient_id"]}: {t["description"]} (termín {t["due_date"][:10]})')
    return lines


def new_results(today: date | None = None, *, record: bool = True) -> dict[int, list[str]]:
    """Pacienti na zasedáních v příštích 7 dnech s novými výsledky od posledního upozornění (T-349)."""
    from apps.mdt.models import MdtCase
    from services import patients
    from services.fhir.client import FhirError
    from services.rules import review

    today = today or timezone.localdate()
    lines: dict[int, list[str]] = defaultdict(list)
    for c in (MdtCase.objects.filter(session__date__date__gte=today, session__date__date__lte=today + timedelta(days=7))
              .exclude(session__status='closed').exclude(created_by=None).select_related('session')):
        try:
            resources = patients.load_patient(c.patient_fhir_id)
        except FhirError:
            continue
        state = review.review_state(resources, service_request_id=c.service_request_fhir_id,
                                    meeting=timezone.localtime(c.session.date), now=timezone.now(),
                                    created=c.created_at, checked_at=c.checked_at, session_status=c.session.status)
        count = len(state['new_results'])
        if count > c.results_notified:
            fresh = state['new_results'][c.results_notified:]
            labels = ', '.join(r.get('label', '') for r in fresh[:4])
            lines[c.created_by_id].append(f'{c.patient_fhir_id} ({c.session.title}): {len(fresh)} nové: {labels}')
            if record:
                MdtCase.objects.filter(pk=c.pk).update(results_notified=count)
    return lines


def users(ids) -> dict[int, object]:
    return {u.pk: u for u in get_user_model().objects.filter(pk__in=list(ids), is_active=True)}
