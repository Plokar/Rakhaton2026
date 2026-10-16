"""Znalostní báze onkologie `data/onko/` (T-315): integrita, soulad se semaforem aplikace (T-503) a barvy dema."""
import importlib.util
from pathlib import Path

import pytest
import yaml

from services.rules.compatibility import DEFAULT_RULES_FILE


def _load_q():
    for parent in Path(__file__).resolve().parents:
        script = parent / 'data' / 'onko' / 'q.py'
        if script.is_file():
            spec = importlib.util.spec_from_file_location('onko_q', script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    return None


@pytest.fixture(scope='module')
def q():
    module = _load_q()
    if module is None:
        pytest.skip('data/onko nenalezen (v kontejneru není připojený)')
    return module


@pytest.fixture(scope='module')
def app_catalog():
    return yaml.safe_load(DEFAULT_RULES_FILE.read_text(encoding='utf-8'))


def _lights(q, pid, facts):
    out = q.evaluate_postup(pid, facts)
    return out['light'], {r['id']: r['light'] for r in out['pravidla']}


def test_integrity(q):
    assert q.check() == []


def test_every_app_rule_is_in_kb_with_same_source(q, app_catalog):
    kb = {r['id']: r for r in q.kb()['kriteria']}
    for rid, rule in app_catalog['rules'].items():
        assert rid in kb, f'{rid} chybí v data/onko/kriteria.tsv'
        assert rule['source'] in kb[rid]['zdroj'].split(','), f'{rid}: zdroj {rule["source"]} vs {kb[rid]["zdroj"]}'


def test_kb_tags_cover_every_app_procedure(q, app_catalog):
    for proc in app_catalog['procedures']:
        applicable = {r['id'] for r in q.applicable_rules(q.postup(proc['id']), {})}
        assert set(proc['rules']) <= applicable, f'{proc["id"]}: chybí {set(proc["rules"]) - applicable}'


def test_p03_colors_match_pozadavky(q):
    light, rules = _lights(q, 'krc-resekce-jater', {
        'liver.flr': 38, 'staging.liver_complete': 'ne', 'liver.bilobar': 'ano', 'treatment.bev_days': 45,
        'card.mi_days': 2500, 'card.stent_days': 2500, 'wt.loss6m': 7, 'ecog.diff': 1})
    assert light == 'orange'
    assert {k: rules[k] for k in ('VS-KRC-01', 'VS-KRC-02', 'VS-KRC-03', 'VS-OBC-04', 'VS-OBC-02')} == dict.fromkeys(
        ('VS-KRC-01', 'VS-KRC-02', 'VS-KRC-03', 'VS-OBC-04', 'VS-OBC-02'), 'orange')
    assert rules['VS-CHIR-01'] == rules['VS-CHIR-03'] == 'green'
    assert _lights(q, 'krc-anti-egfr', {'bm.ras': 'mut'})[1]['VS-KRC-06'] == 'red'
    assert _lights(q, 'krc-imunoterapie', {'bm.mmr': 'nezn'})[1]['VS-KRC-07'] == 'grey'


def test_p04_chrt_durvalumab_is_orange(q):
    light, rules = _lights(q, 'pli-chrt-durvalumab', {
        'bm.pdl1': 60, 'bm.egfr_alk': 'nezn', 'lesion.unverified': 'ano', 'wt.loss6m': 9, 'lab.crcl': 76,
        'tox.neuropathy': 0, 'tox.hearing': 0, 'ecog.physician': 1, 'card.nyha': 1})
    assert light == 'orange'
    assert rules['VS-PLI-07'] == rules['VS-PLI-11'] == 'green'
    assert rules['VS-PLI-06'] == rules['VS-PLI-04'] == 'orange'
    assert rules['VS-PLI-10'] == 'grey'


def test_reirradiation_depends_on_interval_and_intent(q):
    _, curative = _lights(q, 'pli-sbrt', {'intent': 'C', 'rt.prior_same_area': 'ano', 'rt.prior_months': 3})
    assert curative['VS-RT-01'] == 'orange' and curative['VS-RT-02'] == 'red'
    _, palliative = _lights(q, 'met-kost-rt', {'intent': 'P', 'rt.prior_same_area': 'ano', 'rt.prior_months': 2})
    assert palliative['VS-RT-03'] == 'green' and 'VS-RT-02' not in palliative
    _, never = _lights(q, 'pli-sbrt', {'intent': 'C', 'rt.prior_same_area': 'ne', 'rt.prior_months': 'ne'})
    assert never['VS-RT-01'] == never['VS-RT-02'] == 'green'


def test_unknown_biomarker_is_not_a_negative(q):
    trial = q.screen_trial('RKT-03', {'bm.mmr': 'nezn'})
    assert next(c for c in trial['kriteria'] if c['id'] == 'RKT-03/V2')['status'] == 'chybí údaj'
    assert _lights(q, 'pli-m-io-mono', {'bm.pdl1': 30})[1]['VS-BM-01'] == 'red'
