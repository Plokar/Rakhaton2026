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


TEMPLATES = {'P01': 'sab-prs-hr', 'P02': 'sab-prs-her2', 'P03': 'sab-krc-jatra', 'P04': 'sab-pli-radikalni',
             'P05': 'sab-prs-hr', 'P06': 'sab-duplicita'}


def _warnings(q, pid):
    dg, facts, docs, mdt, _ = q._source(pid, {})
    return {i['warning']['id']: i for i in q.recommend(dg, facts, docs, mdt) if 'warning' in i}


@pytest.fixture(scope='module')
def dataset_ok(q):
    if not (q.DATASET_DIR / 'pacienti' / 'P01').is_dir():
        pytest.skip('dataset není v checkoutu')


@pytest.mark.parametrize('pid', sorted(TEMPLATES))
def test_projector_template_per_patient(q, dataset_ok, pid):
    dg, facts, _, _, _ = q._source(pid, {})
    assert q.pick_template(dg, facts)['sablona'] == TEMPLATES[pid]


def test_templates_are_valid_brief_configs(q):
    pytest.importorskip('django')
    from apps.mdt.config import ROLE_IDS, SECTION_ORDER
    for t in q.kb()['sablony']:
        config = q.template_config(t)
        assert [s['id'] for s in sorted(config['sections'], key=lambda s: s['order'])] != []
        assert {s['id'] for s in config['sections']} == set(SECTION_ORDER), t['sablona']
        assert set(config['roles_present']) <= ROLE_IDS, t['sablona']


def test_recommended_data_match_pozadavky_dataset_findings(q, dataset_ok):
    """docs/POZADAVKY_LEKARE.md §4: co v podkladech chybí (sloupec Dataset)."""
    p03, p04 = _warnings(q, 'P03'), _warnings(q, 'P04')
    assert p03['CHYBI:krc.mmr']['status'] == 'mention'                  # MMR nevyšetřeno
    assert p03['CHYBI:krc.restaging']['status'] == 'stale'              # CT hrudníku jen ze stagingu
    assert 'CHYBI:krc.dpd' in p03 and 'CHYBI:krc.her2' not in p03       # KRAS G12D → HER2 netřeba
    assert {'CHYBI:obc.g8', 'CHYBI:pli.siadh', 'CHYBI:pli.egfr'} <= set(p04)
    assert 'P04-doc06' in p04['CHYBI:pli.vo2max']['ids']                # „doporučena spiroergometrie“ = jen zmínka
    assert 'CHYBI:obc.kortikoidy' in _warnings(q, 'P02')                # dexametazon bez plánu
    assert 'CHYBI:obc.g8' in _warnings(q, 'P06')
    assert _warnings(q, 'P01')['CHYBI:obc.zobrazeni']['age'] == 50     # staging 50 dní
    assert 'CHYBI:prs.esr1' not in _warnings(q, 'P02')                  # ESR1 jen u HR+/HER2−
    assert all(w['warning']['severity'] == 'low' for k, w in p04.items() if k.startswith('DOP:'))


def test_role_view_puts_specialty_first(q, dataset_ok):
    dg, facts, docs, mdt, _ = q._source('P03', {})
    view = q.role_view('surgeon', dg, facts, q.recommend(dg, facts, docs, mdt))
    assert view['sekce'][:2] == ['summary', 'role_views']
    assert view['udaje'][0]['udaj'] == 'krc.flr'
    assert view['postupy'][0]['postup'] == 'krc-resekce-jater'


def test_unknown_biomarker_is_not_a_negative(q):
    trial = q.screen_trial('RKT-03', {'bm.mmr': 'nezn'})
    assert next(c for c in trial['kriteria'] if c['id'] == 'RKT-03/V2')['status'] == 'chybí údaj'
    assert _lights(q, 'pli-m-io-mono', {'bm.pdl1': 30})[1]['VS-BM-01'] == 'red'
