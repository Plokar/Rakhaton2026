"""Fixtures pro testy services/: dataset a in-memory FHIR server (bez IRIS)."""
import os
from pathlib import Path

import pytest

from services.fhir import client, ingest
from services.fhir.testing import FakeFhirServer
from services.iris import db
from services.iris.testing import FakeIris


@pytest.fixture(scope='session')
def dataset_root() -> Path:
    raw = os.environ.get('DATASET_DIR') or ingest.repo_dataset()
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


@pytest.fixture
def fake_iris(monkeypatch) -> FakeIris:
    """IRIS SQL v paměti místo ``services.iris.db.connect`` (vektorové tabulky MDT.*).

    Vynutí ``AI_PROVIDER=mock``: embeddingy jsou deterministické a nic neodchází do Gemini.
    """
    monkeypatch.setenv('AI_PROVIDER', 'mock')
    server = FakeIris()
    monkeypatch.setattr(db, 'connect', server.connect)
    return server


@pytest.fixture
def grounding_vectors(fake_iris, dataset_root) -> FakeIris:
    """Vektory všech 6 pacientů, guidelines a kritérií studií v in-memory IRIS (grounding v2, T-213)."""
    from services.iris import indexing

    for patient_id in ('P01', 'P02', 'P03', 'P04', 'P05', 'P06'):
        indexing.index_patient(patient_id, ingest.load_patient(dataset_root, patient_id))
    indexing.index_guidelines(indexing.guideline_chunks(dataset_root))
    indexing.index_trials(indexing.trial_criteria(ingest.load_studies(dataset_root)))
    return fake_iris
