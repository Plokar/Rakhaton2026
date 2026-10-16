"""DoD T-101 proti skutečnému IRIS (dev compose, po iris_init). Bez IRIS se přeskočí.

    docker compose -f docker-compose.dev.yml exec backend pytest -m integration services/fhir
"""
import pytest

from services.fhir import client, ingest


def _iris_up():
    try:
        client.request('GET', 'metadata')
        return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _iris_up(), reason='IRIS FHIR nedostupný (dev.ps1 up + iris_init)'),
]


def test_full_ingest_twice_without_duplicates(dataset_root):
    """Všech 1 091 resources v IRIS, počty sedí s DATASET §2, 2. běh bez duplikátů."""
    for _ in range(2):
        report = ingest.ingest(dataset_root)
        assert report.errors == []
        assert report.unique_resources == ingest.EXPECTED_TOTAL
    assert client.count('Observation', patient='P03') >= 85
    assert client.count('Observation', _id='P01-lab01-hb-f') == 1
    assert client.count('Patient', _tag='https://rakathon.example.org/fhir/tag|fiktivni-data') >= 6
