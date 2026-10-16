"""Po zápisu závěru komise (T-209) jde nový záznam MDT vyhledat a citovat (ARCH §4.5)."""
import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from services.fhir import client, writeback
from services.iris import indexing
from services.iris import vector_store as vs

PRAGUE = ZoneInfo('Europe/Prague')


def _decision() -> dict:
    for parent in Path(__file__).resolve().parents:
        fixture = parent / 'data' / 'fixtures' / 'decision_P03.json'
        if fixture.is_file():
            return json.loads(fixture.read_text(encoding='utf-8'))
    pytest.skip('chybí data/fixtures/decision_P03.json')


@pytest.fixture
def iris(fake_fhir_dataset, fake_iris):
    client.put({'resourceType': 'Device', 'id': 'mdt-copilot',
                'deviceName': [{'name': 'MDT Copilot', 'type': 'user-friendly-name'}]})
    vs.ensure_schema()
    indexing.index_patient('P03')
    return fake_iris


def _confirm() -> dict:
    return writeback.confirm_decision(
        _decision(), patient_id='P03', service_request_id='P03-zad01',
        mdt_date=datetime(2026, 10, 21, 14, 0, tzinfo=PRAGUE), confirmed_by={'user_id': '1', 'name': 'Předseda'},
        red_flags={}, now=datetime(2026, 10, 21, 15, 0, tzinfo=PRAGUE),
    )


def test_confirmed_record_is_indexed(iris):
    before = {r['EvidenceId'] for r in iris.rows('MDT.EvidenceChunk')}
    assert not any(e.startswith('P03-mdt02#') for e in before)
    assert _confirm()['composition'] == 'P03-mdt02'
    after = {r['EvidenceId'] for r in iris.rows('MDT.EvidenceChunk')}
    assert 'P03-mdt02#1' in after and before < after
    assert {r['PatientId'] for r in iris.rows('MDT.EvidenceChunk')} == {'P03'}


def test_reindex_failure_does_not_block_confirmation(iris, monkeypatch, caplog):
    def broken(patient_id, resources=None, provider=None):
        raise RuntimeError('IRIS SQL nedostupný')
    monkeypatch.setattr(indexing, 'index_patient', broken)
    with caplog.at_level(logging.WARNING, logger='services.fhir.writeback'):
        ids = _confirm()
    assert ids['composition'] == 'P03-mdt02' and client.read('Composition', 'P03-mdt02')
    assert 'Reindex vektorů P03' in caplog.text
