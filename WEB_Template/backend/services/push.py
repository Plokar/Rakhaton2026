"""Push oznámení na mobil (T-383, Web Push s klíči VAPID).

Bez `VAPID_PUBLIC_KEY` a `VAPID_PRIVATE_KEY` je vypnuté (`enabled() == False`), nic se neposílá. Klíče vytvoří
`manage.py vapid_keys`. Obsah oznámení je šifrovaný pro zařízení (push služba prohlížeče ho nepřečte) a pacient
v něm je jen jako `Pxx` (D-018). Odesílá se ve vlákně, požadavek předsedy na odeslání nečeká.
"""
from __future__ import annotations

import json
import logging
import os
import threading

from django.core.cache import cache
from django.db import close_old_connections

log = logging.getLogger(__name__)
DEDUP_SECONDS = 6 * 3600


def enabled() -> bool:
    return bool(os.environ.get('VAPID_PUBLIC_KEY') and os.environ.get('VAPID_PRIVATE_KEY'))


def public_key() -> str | None:
    return os.environ.get('VAPID_PUBLIC_KEY') or None


def _send_one(sub, payload: dict) -> bool:
    """Jedno zařízení; zaniklý odběr (404/410) smaže. Vrací True, když push služba zprávu přijala."""
    from pywebpush import WebPushException, webpush

    try:
        webpush(subscription_info={'endpoint': sub.endpoint, 'keys': {'p256dh': sub.p256dh, 'auth': sub.auth}},
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=os.environ['VAPID_PRIVATE_KEY'],
                vapid_claims={'sub': os.environ.get('VAPID_SUBJECT', 'mailto:mdt@localhost')}, ttl=600)
        return True
    except WebPushException as e:
        status = getattr(e.response, 'status_code', None)
        if status in (404, 410):
            sub.delete()
        else:
            log.warning('T-383: push na %s selhal (%s)', sub.endpoint[:60], status or e)
        return False


def send(user_ids: list[int], payload: dict, *, dedup_key: str | None = None, background: bool = True) -> None:
    """Pošle `{title, body, url, tag}` všem zařízením lékařů. `dedup_key` = stejné oznámení jen jednou za 6 h."""
    if not enabled() or not user_ids:
        return
    from apps.mdt.models import PushSubscription

    targets = []
    for uid in user_ids:
        if dedup_key and not cache.add(f'push:{dedup_key}:{uid}', 1, DEDUP_SECONDS):
            continue
        targets.append(uid)
    if not targets:
        return

    def run():
        for sub in PushSubscription.objects.select_related('user').filter(user_id__in=targets):
            _send_one(sub, payload)

    def in_thread():
        try:
            run()
        finally:
            close_old_connections()                # vlastní spojení vlákna do DB

    if background:
        threading.Thread(target=in_thread, name='mdt-push', daemon=True).start()
    else:
        run()


def notify_live(session, live: dict, *, background: bool = True) -> None:
    """Živé zasedání (T-380/T-383): zadávajícímu a přizvanému lékaři „váš pacient je další / na projektoru“."""
    if not enabled() or live.get('status') != 'in_progress':
        return
    from apps.mdt.models import MdtCase

    url = f'/dashboard/live?zasedani={session.pk}'
    for kind, item, text in (('now', live.get('case'), 'je na projektoru'), ('next', live.get('next'), 'jde na řadu jako další')):
        if not item:
            continue
        case = MdtCase.objects.filter(pk=item['id']).prefetch_related('collaborators').first()
        if case is None:
            continue
        users = {u.pk for u in case.collaborators.all()} | ({case.created_by_id} if case.created_by_id else set())
        send(sorted(users), {'title': f'Váš pacient {case.patient_fhir_id} {text}', 'body': session.title,
                             'url': url, 'tag': f'mdt-{session.pk}-{kind}'},
             dedup_key=f'{session.pk}:{kind}:{case.pk}', background=background)
