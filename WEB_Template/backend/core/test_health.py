"""Health check zná IRIS (T-369): `degraded` při výpadku IRIS, 503 jen se `?strict=1`."""
from contextlib import contextmanager

import pytest
from django.core.cache import cache

from services.fhir import client
from services.iris import db as iris_db


@pytest.fixture(autouse=True)
def no_cached_iris():
    cache.delete('health_iris')
    yield
    cache.delete('health_iris')


def test_without_iris_host_checks_are_skipped(api_client, db, monkeypatch):
    monkeypatch.delenv('IRIS_HOST', raising=False)
    monkeypatch.setenv('APP_VERSION', '1.2.3')
    r = api_client.get('/api/health/?strict=1')
    body = r.json()
    assert r.status_code == 200 and body['status'] == 'healthy' and body['version'] == '1.2.3'
    assert body['checks']['iris_fhir'] == body['checks']['iris_sql'] == 'skipped'


def test_iris_down_is_degraded_but_200_unless_strict(api_client, db, monkeypatch):
    monkeypatch.setenv('IRIS_HOST', 'iris')     # client.request a db.connect jsou v testech offline (conftest)
    r = api_client.get('/api/health/')
    assert r.status_code == 200 and r.json()['status'] == 'degraded'
    assert r.json()['checks']['iris_fhir'].startswith('error')
    cache.delete('health_iris')
    assert api_client.get('/api/health/?strict=1').status_code == 503


def test_iris_up_is_healthy_and_connection_closed(api_client, db, monkeypatch):
    monkeypatch.setenv('IRIS_HOST', 'iris')
    calls = {'timeout': None, 'closed': 0}

    def fake_request(method, path='', body=None, params=None, timeout=300):
        calls['timeout'] = timeout
        return {'resourceType': 'CapabilityStatement'}

    class Cursor:
        def execute(self, sql):
            assert sql == 'SELECT 1'

        def fetchone(self):
            return (1,)

    class Conn:
        def cursor(self):
            return Cursor()

    @contextmanager
    def fake_connect(*args, **kwargs):
        try:
            yield Conn()
        finally:
            calls['closed'] += 1

    monkeypatch.setattr(client, 'request', fake_request)
    monkeypatch.setattr(iris_db, 'connect', fake_connect)
    r = api_client.get('/api/health/?strict=1')
    assert r.status_code == 200 and r.json()['status'] == 'healthy'
    assert calls == {'timeout': 3, 'closed': 1}
    api_client.get('/api/health/')                # druhé volání do 20 s z cache, žádné nové spojení
    assert calls['closed'] == 1
