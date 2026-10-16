"""Fixtures pro testy services/: dataset a in-memory FHIR server (bez IRIS)."""
import os
from pathlib import Path

import pytest

from services.fhir import client
from services.fhir.testing import FakeFhirServer


def _repo_dataset() -> Path | None:
    """Dataset v checkoutu repa (lokálně, CI). V kontejneru nastavuje DATASET_DIR docker-compose.dev.yml."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / 'Dataset_MDT_Copilot_v1.1_pre_timy' / 'Dataset_MDT_Copilot_v1.1'
        if candidate.is_dir():
            return candidate
    return None


@pytest.fixture(scope='session')
def dataset_root() -> Path:
    raw = os.environ.get('DATASET_DIR') or _repo_dataset()
    if not raw or not (Path(raw) / 'pacienti').is_dir():
        pytest.skip(f'dataset není k dispozici ({raw}); nastav DATASET_DIR')
    return Path(raw)


@pytest.fixture
def fake_fhir(monkeypatch) -> FakeFhirServer:
    """Prázdný FHIR server místo IRIS: ``services.fhir.client`` volá jeho ``request``."""
    server = FakeFhirServer()
    monkeypatch.setattr(client, 'request', server.request)
    return server


@pytest.fixture
def fake_fhir_dataset(fake_fhir, dataset_root) -> FakeFhirServer:
    """FHIR server s celým sanitizovaným datasetem (1 091 resources), jako po ``ingest_dataset``."""
    return fake_fhir.load(dataset_root)
