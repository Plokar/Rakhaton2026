"""Provoz (T-383): dvoufázové přihlášení (TOTP) a povinné 2FA pro správce MDT."""
import time

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.mdt import roles
from core import totp

pytestmark = pytest.mark.django_db
PASSWORD = 'demo123456'


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')
    cache.clear()


def login(username, otp=None):
    body = {'username': username, 'password': PASSWORD, **({'otp': otp} if otp else {})}
    return APIClient().post('/api/auth/token/', body, format='json')


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


def test_totp_rfc6238_vector_and_replay():
    secret = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'                      # RFC 6238, ASCII „12345678901234567890“
    assert totp.code_at(secret, 59 // 30) == '287082'                # posledních 6 číslic z 94287082
    step = totp.verify(secret, '287082', now=59)
    assert step == 1 and totp.verify(secret, '287082', last_step=step, now=59) is None     # podruhé ne
    assert totp.verify(secret, '000000', now=59) is None and totp.verify(secret, 'abc', now=59) is None
    assert totp.otpauth_uri(secret, 'doc@x.cz').startswith('otpauth://totp/MDTcore:doc%40x.cz?secret=')


def test_enable_2fa_then_login_needs_code(seeded):
    client = as_user('onkolog')
    secret = client.post('/api/auth/2fa/setup/').json()['secret']
    assert client.post('/api/auth/2fa/confirm/', {'code': '000000'}, format='json').status_code == 400
    assert client.post('/api/auth/2fa/confirm/', {'code': totp.code_at(secret, int(time.time() // 30))},
                       format='json').json()['enabled'] is True

    first = login('onkolog')
    assert first.status_code == 401 and first.json()['otp_required'] is True and 'access' not in first.json()
    assert login('onkolog', '123456').status_code == 401
    code = totp.code_at(secret, int(time.time() // 30) + 1)            # kód z dalšího kroku (okno ±1)
    ok = login('onkolog', code)
    assert ok.status_code == 200 and ok.json()['access'] and 'access_token' in ok.cookies
    assert login('onkolog', code).status_code == 401                  # stejný kód podruhé ne
    assert login('pneumolog').status_code == 200                      # bez 2FA beze změny


def test_manager_must_set_up_2fa(seeded, settings):
    settings.MDT_REQUIRE_2FA_MANAGER = True
    user = get_user_model().objects.get(username='predseda')
    roles.set_manager(user, True)
    access = login('predseda').json()['access']
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
    blocked = client.get('/api/mdt/sessions/')
    assert blocked.status_code == 403 and blocked.json()['twofa_setup_required'] is True
    assert client.get('/api/mdt/me/').status_code == 200 and client.get('/api/auth/2fa/').json() == {
        'enabled': False, 'required': True}
    secret = client.post('/api/auth/2fa/setup/').json()['secret']
    client.post('/api/auth/2fa/confirm/', {'code': totp.code_at(secret, int(time.time() // 30))}, format='json')
    assert client.get('/api/mdt/sessions/').status_code == 200
    assert client.post('/api/auth/2fa/disable/', {'password': PASSWORD}, format='json').status_code == 409


# ── fronta jobů v Redisu ──────────────────────────────────────────────────────
def test_redis_job_queue(seeded, monkeypatch, settings):
    """`MDT_JOB_BACKEND=redis`: start() job jen zařadí, worker ho vezme a spustí (test bez skutečného Redisu)."""
    from apps.copilot import jobs
    from apps.copilot.models import GenerationJob
    from apps.mdt.models import MdtCase

    class FakeRedis:
        def __init__(self):
            self.items = []

        def lpush(self, key, value):
            self.items.insert(0, value)

        def brpop(self, key, timeout=0):
            return (key, str(self.items.pop()).encode()) if self.items else None

    fake = FakeRedis()
    ran = []
    settings.MDT_JOBS_SYNC = False
    monkeypatch.setenv('MDT_JOB_BACKEND', 'redis')
    monkeypatch.setattr(jobs, '_redis', lambda: fake)
    monkeypatch.setattr(jobs, 'run', ran.append)
    monkeypatch.setattr(jobs, 'connection', type('C', (), {'close': staticmethod(lambda: None)}))
    case = MdtCase.objects.first()
    job = GenerationJob.objects.create(case=case, kind='brief', params={})
    jobs.start(job)
    assert fake.items == [job.pk] and ran == []                  # backend nic nespouští
    calls = iter([False, False, True])
    assert jobs.work_forever(lambda: next(calls), timeout=0) == 1 and ran == [job.pk]


# ── push oznámení ─────────────────────────────────────────────────────────────
@pytest.fixture
def vapid(monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid01, b64urlencode

    v = Vapid01()
    v.generate_keys()
    monkeypatch.setenv('VAPID_PUBLIC_KEY', b64urlencode(v.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)))
    monkeypatch.setenv('VAPID_PRIVATE_KEY', b64urlencode(v.private_key.private_bytes(
        serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())))


SUB = {'endpoint': 'https://push.example.org/abc', 'keys': {'p256dh': 'BKey', 'auth': 'secret'}}


def test_push_disabled_without_keys(seeded, monkeypatch):
    monkeypatch.delenv('VAPID_PUBLIC_KEY', raising=False)
    assert as_user('onkolog').get('/api/mdt/push/key/').json() == {'enabled': False}
    assert as_user('onkolog').post('/api/mdt/push/subscriptions/', SUB, format='json').status_code == 409


def test_subscribe_and_notify_requester_once(seeded, vapid, monkeypatch, settings):
    from apps.mdt.models import MdtSession, PushSubscription
    from services import push

    settings.CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
    sent = []
    monkeypatch.setattr(push, '_send_one', lambda sub, payload: sent.append((sub.user.username, payload)) or True)
    assert as_user('onkolog').get('/api/mdt/push/key/').json()['enabled'] is True
    assert as_user('onkolog').post('/api/mdt/push/subscriptions/', {**SUB, 'endpoint': 'http://x'},
                                   format='json').status_code == 400
    assert as_user('onkolog').post('/api/mdt/push/subscriptions/', SUB, format='json').status_code == 201

    s = MdtSession.objects.get(title='Mamární komise')
    MdtSession.objects.filter(pk=s.pk).update(status='in_progress')
    s.refresh_from_db()
    first = s.cases.first()
    assert first.created_by.username == 'onkolog'
    live = as_user('predseda').get(f'/api/mdt/sessions/{s.pk}/live/').json()
    push.notify_live(s, live, background=False)                       # na řadě je jako další P01 onkologa
    push.notify_live(s, live, background=False)                       # podruhé stejné oznámení ne
    assert [(u, p['title']) for u, p in sent] == [('onkolog', f'Váš pacient {first.patient_fhir_id} jde na řadu jako další')]
    assert sent[0][1]['url'] == f'/dashboard/live?zasedani={s.pk}'

    assert as_user('onkolog').delete('/api/mdt/push/subscriptions/', {'endpoint': SUB['endpoint']},
                                     format='json').status_code == 204
    assert not PushSubscription.objects.exists()


def test_gone_subscription_is_removed(seeded, vapid, monkeypatch):
    from types import SimpleNamespace

    import pywebpush

    from apps.mdt.models import PushSubscription
    from services import push

    user = get_user_model().objects.get(username='onkolog')
    sub = PushSubscription.objects.create(user=user, endpoint=SUB['endpoint'], p256dh='k', auth='a')

    def gone(**kwargs):
        raise pywebpush.WebPushException('gone', response=SimpleNamespace(status_code=410))

    monkeypatch.setattr(pywebpush, 'webpush', gone)
    assert push._send_one(sub, {'title': 'x'}) is False and not PushSubscription.objects.exists()
