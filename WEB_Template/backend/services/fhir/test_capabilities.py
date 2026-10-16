"""iris_check (T-313) proti fake FHIR serveru, který (jako IRIS) některé parametry tiše ignoruje."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from services.fhir import capabilities


def _by_name(checks):
    return {c.name: c for c in checks}


def test_detects_filtering_and_ignored_params(fake_fhir_dataset):
    checks = _by_name(capabilities.run_checks('P03'))
    assert checks['metadata'].status == 'ok'
    for rtype in ('Observation', 'Task', 'ImagingStudy', 'Composition', 'MedicationAdministration'):
        assert checks[f'{rtype}?patient'].status == 'ok', checks[f'{rtype}?patient'].detail
    assert checks['Observation?_id'].status == 'ok' and checks['_id=a,b (OR)'].status == 'ok'
    assert checks['Observation?code'].status == 'ok' and checks['Observation?subject'].status == 'ok'
    # fake server category/status/date/_tag/_sort neumí → musí se ukázat jako ignorované
    for name in ('Observation?category', 'Observation?status', 'Observation?date', 'Patient?_tag'):
        assert checks[name].status == 'fail' and checks[name].detail.startswith('IGNORUJE SE'), name
    assert checks['Observation?_sort=-date'].status == 'fail' and not checks['Observation?_sort=-date'].required
    assert checks['Patient/$everything'].detail.startswith('nepodporováno')
    assert checks['mCODE IG'].detail.startswith('nenahraný')
    assert checks['$validate'].detail.startswith('nepodporováno')


def test_empty_server_says_ingest_first(fake_fhir):
    check = capabilities._filters('Observation', 'patient', 'x', {'patient': 'P03'})
    assert check.status == 'fail' and 'ingest_dataset' in check.detail


def test_command_prints_markdown_table_and_fails_on_ignored_params(fake_fhir_dataset):
    out = StringIO()
    with pytest.raises(CommandError, match='Observation\\?category'):
        call_command('iris_check', stdout=out)
    assert out.getvalue().startswith('| Kontrola | Výsledek | Detail |')
    assert '| `Observation?patient` | ✓ ok |' in out.getvalue()
