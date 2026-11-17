"""Hlášení chyb (T-377): bez DSN nic, s DSN událost bez těla, cookies, hlaviček, query a uživatele."""
import sys

from core import monitoring


def test_without_dsn_nothing_is_imported(monkeypatch):
    monkeypatch.delenv('SENTRY_DSN', raising=False)
    monkeypatch.delitem(sys.modules, 'sentry_sdk', raising=False)
    assert monitoring.init_sentry() is False
    assert 'sentry_sdk' not in sys.modules


def test_scrub_keeps_only_path_and_method():
    event = {
        'request': {'url': 'https://api.example.cz/api/patients/search/?q=7501011234', 'method': 'POST',
                    'data': {'q': 'Novák'}, 'cookies': {'access_token': 'x'}, 'headers': {'Authorization': 'Bearer y'},
                    'query_string': 'q=7501011234', 'env': {'REMOTE_ADDR': '10.0.0.1'}},
        'user': {'id': 1, 'username': 'predseda', 'ip_address': '10.0.0.1'},
        'breadcrumbs': {'values': [{'category': 'query', 'message': "SELECT … WHERE rc = '7501011234'"},
                                   {'category': 'httplib', 'data': {'url': 'http://iris/fhir?name=Novák', 'method': 'GET',
                                                                    'status_code': 200}}]},
        'exception': {'values': [{'stacktrace': {'frames': [{'function': 'f', 'vars': {'patient': {'name': 'Novák'}}}]}}]},
    }
    out = monitoring.scrub(event)
    assert out['request'] == {'url': 'https://api.example.cz/api/patients/search/', 'method': 'POST'}
    assert 'user' not in out
    text = repr(out)
    assert '7501011234' not in text and 'Novák' not in text and 'Bearer' not in text and 'access_token' not in text
