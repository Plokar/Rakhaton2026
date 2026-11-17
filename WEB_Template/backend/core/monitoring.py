"""Hlášení chyb do Sentry (T-377), jen když je nastavené `SENTRY_DSN`.

Bez DSN se `sentry_sdk` ani neimportuje a nic neodchází ven. S DSN se posílají jen výjimky (žádné trasování,
`send_default_pii=False`) a `scrub` z události odstraní tělo požadavku, cookies, hlavičky, query string
i uživatele: v adrese zůstane jen cesta (obsahuje nejvýš Pxx a čísla případů, žádná jména ani RČ).
"""
from __future__ import annotations

import os

KEEP_REQUEST = ('url', 'method')


def scrub(event: dict, hint: dict | None = None) -> dict:
    """`before_send` / `before_send_transaction`: z události nesmí odejít nic o pacientovi ani o uživateli."""
    request = event.get('request')
    if isinstance(request, dict):
        url = str(request.get('url') or '').split('?', 1)[0]
        event['request'] = {k: v for k, v in request.items() if k in KEEP_REQUEST} | ({'url': url} if url else {})
    event.pop('user', None)
    for crumb in (event.get('breadcrumbs') or {}).get('values', []) if isinstance(event.get('breadcrumbs'), dict) else []:
        data = crumb.get('data')
        if isinstance(data, dict):
            crumb['data'] = {k: v for k, v in data.items() if k in ('method', 'status_code')}
        if crumb.get('category') in ('query', 'django.db', 'sql'):
            crumb['message'] = '[SQL skryto]'
    for frame_list in _frames(event):
        for frame in frame_list:
            frame.pop('vars', None)                  # lokální proměnné mohou nést data pacienta
    return event


def _frames(event: dict):
    for exc in (event.get('exception') or {}).get('values', []) or []:
        frames = (exc.get('stacktrace') or {}).get('frames')
        if frames:
            yield frames
    for thread in (event.get('threads') or {}).get('values', []) or []:
        frames = (thread.get('stacktrace') or {}).get('frames')
        if frames:
            yield frames


def init_sentry() -> bool:
    """Zapne Sentry, když je `SENTRY_DSN`; vrací, zda se zapnulo."""
    dsn = os.environ.get('SENTRY_DSN', '').strip()
    if not dsn:
        return False
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0,
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size='never',
        environment=os.environ.get('SENTRY_ENVIRONMENT', 'pilot'),
        release=os.environ.get('APP_VERSION') or None,
        before_send=scrub,
        before_send_transaction=scrub,
    )
    return True
