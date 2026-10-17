"""T-333: okno pro projektor upravené zadávajícím lékařem (skryté a přeskládané karty a údaje)."""
import pytest

from apps.mdt.models import MdtCase
from apps.mdt.test_roles import as_user, seeded  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db

LAYOUT = {'blocks': {'order': ['facts', 'treatments', 'anamnesis'], 'hidden': ['anamnesis']},
          'facts': {'order': ['lab:2039-6', 'staging.tnm'], 'hidden': ['lab:6690-2']}}


def test_projector_layout_saved_by_case_editors(seeded):  # noqa: F811
    p04 = MdtCase.objects.get(patient_fhir_id='P04')       # zadal pneumolog
    url = f'/api/mdt/cases/{p04.pk}/'
    assert as_user('chirurg').patch(url, {'projector_layout': LAYOUT}, format='json').status_code == 403
    r = as_user('pneumolog').patch(url, {'projector_layout': LAYOUT}, format='json')
    assert r.status_code == 200, r.json()
    assert r.json()['projector_layout'] == LAYOUT
    agenda = as_user('chirurg').get(f'/api/mdt/sessions/{p04.session_id}/').json()
    assert next(c for c in agenda['cases'] if c['id'] == p04.pk)['projector_layout'] == LAYOUT
    assert as_user('predseda').patch(url, {'projector_layout': {}}, format='json').json()['projector_layout'] == {}


@pytest.mark.parametrize('bad', [
    [],                                                     # není objekt
    {'grid': {}},                                           # neznámý klíč
    {'blocks': {'order': ['map']}},                         # neznámá karta
    {'blocks': {'order': 'facts'}},                         # není seznam
    {'facts': {'hidden': [1, 2]}},                          # ID nejsou text
    {'facts': {'order': ['x'], 'sort': 'asc'}},             # neznámý klíč části
])
def test_projector_layout_validation(seeded, bad):  # noqa: F811
    p04 = MdtCase.objects.get(patient_fhir_id='P04')
    assert as_user('pneumolog').patch(f'/api/mdt/cases/{p04.pk}/', {'projector_layout': bad}, format='json').status_code == 400
