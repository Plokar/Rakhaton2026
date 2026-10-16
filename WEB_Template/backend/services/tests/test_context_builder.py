"""Testy context builderu (T-105): dataset → evidence list, guidelines, studie, IRIS přes podvržené klienty."""
import sys
import types
from contextlib import contextmanager

import pytest

from services.ai import context_builder, guidelines
from services.ai.context_builder import context_from_resources
from services.ai.guidelines import GuidelinePassage, GuidelinesUnavailable, parse_guidelines
from services.rules.guideline_sets import guideline_sets_for, trial_is_relevant
from services.tests.dataset import load_guideline_markdowns, load_patient, load_studies

# Počty resources v bundlech (DATASET §2)
RESOURCE_COUNTS = {"P01": 164, "P02": 212, "P03": 171, "P04": 142, "P05": 179, "P06": 215}


@pytest.fixture(scope="module")
def all_guidelines():
    return [p for md in load_guideline_markdowns().values() for p in parse_guidelines(md)]


@pytest.fixture(scope="module")
def studies():
    return load_studies()


def make_context(patient_id, all_guidelines, studies, **kwargs):
    return context_from_resources(patient_id, load_patient(patient_id), studies=studies,
                                  guidelines=all_guidelines, **kwargs)


@pytest.fixture(scope="module")
def p03(all_guidelines, studies):
    return make_context("P03", all_guidelines, studies)


# ── Guidelines a výběr sad ────────────────────────────────────────────────────
class TestGuidelines:
    def test_parse_all_42(self, all_guidelines):
        ids = [p.evidence_id for p in all_guidelines]
        assert len(ids) == 42 and len(set(ids)) == 42
        counts = {s: sum(1 for p in all_guidelines if p.guideline_set == s) for s in ("KRC", "PRS", "PLI", "OBC")}
        assert counts == {"KRC": 9, "PRS": 14, "PLI": 10, "OBC": 9}

    def test_multiline_passage(self, all_guidelines):
        passage = next(p for p in all_guidelines if p.evidence_id == "KRC-2.1")
        assert passage.title == "Posouzení resekability"
        assert "≥ 40 % po intenzivní chemoterapii" in passage.text and "\n" not in passage.text

    @pytest.mark.parametrize("codes, expected", [
        (["C18.7", "C78.7"], ["KRC", "OBC"]),
        (["C50.4", "C78.0", "D41.0"], ["PRS", "OBC"]),
        (["C34.1", "C77.1"], ["PLI", "OBC"]),
        (["C20"], ["KRC", "OBC"]),
        ([], ["OBC"]),
    ])
    def test_guideline_sets_for(self, codes, expected):
        assert guideline_sets_for(codes) == expected

    def test_trial_relevance(self):
        assert trial_is_relevant(["Kolorektální karcinom s jaterními metastázami"], ["KRC", "OBC"])
        assert not trial_is_relevant(["Karcinom prsu, HER2+, metastatický"], ["KRC", "OBC"])
        assert trial_is_relevant(["Solidní nádory"], ["OBC"])


class FakeCursor:
    def __init__(self, rows, error=None):
        self.rows, self.error, self.executed = rows, error, []

    def execute(self, sql, params):
        if self.error:
            raise self.error
        self.executed.append((sql, params))

    def fetchall(self):
        return self.rows

    def close(self):
        pass


@pytest.fixture
def fake_iris(monkeypatch):
    """`services.iris.db` bez skutečného IRIS (modul `iris` nemusí být nainstalovaný)."""
    if "iris" not in sys.modules:
        try:
            import iris  # noqa: F401
        except ImportError:
            monkeypatch.setitem(sys.modules, "iris", types.ModuleType("iris"))
    import services.iris.db as db

    state = {"closed": 0}

    def install(rows=(), error=None):
        cursor = FakeCursor(list(rows), error)

        @contextmanager
        def connect(namespace=None):
            try:
                yield types.SimpleNamespace(cursor=lambda: cursor)
            finally:
                state["closed"] += 1

        monkeypatch.setattr(db, "connect", connect)
        return cursor

    install.state = state
    return install


class TestLoadGuidelines:
    def test_sql_params_and_sorting(self, fake_iris):
        cursor = fake_iris(rows=[("OBC-1.3", "OBC", "ECOG", "text"), ("KRC-2.4", "KRC", "Restaging", "t"),
                                 ("KRC-1.1", "KRC", "Biomarkery", "t"), ("OBC-1.10", "OBC", "X", "t")])
        passages = guidelines.load_guidelines(["KRC", "OBC"])
        assert [p.evidence_id for p in passages] == ["KRC-1.1", "KRC-2.4", "OBC-1.3", "OBC-1.10"]
        sql, params = cursor.executed[0]
        assert "MDT.GuidelineChunk" in sql and "IN (?, ?)" in sql and params == ["KRC", "OBC"]
        assert fake_iris.state["closed"] == 1

    def test_missing_set_is_error(self, fake_iris):
        fake_iris(rows=[("OBC-1.1", "OBC", "Nominace", "t")])
        with pytest.raises(GuidelinesUnavailable, match="KRC"):
            guidelines.load_guidelines(["KRC", "OBC"])

    def test_missing_table_is_error(self, fake_iris):
        fake_iris(error=RuntimeError("Table 'MDT.GuidelineChunk' not found"))
        with pytest.raises(GuidelinesUnavailable, match="T-203"):
            guidelines.load_guidelines(["OBC"])
        assert fake_iris.state["closed"] == 1


# ── Kontext P03 ───────────────────────────────────────────────────────────────
class TestP03Context:
    def test_all_resources_as_lines(self, p03):
        bundle_ids = {r["id"] for r in load_patient("P03")}
        assert len(p03.resource_ids) == 171
        assert set(p03.resource_ids) == bundle_ids

    @pytest.mark.parametrize("line", [
        "[P03] Pacient: muž, 67 let (věk k datu MDT)",
        "[P03-lab06-cea] 2026-10-05 CEA: 13,9 µg/l (ref 0–5) H",
        "[P03-ecog03] 2026-10-05 ECOG – hodnoceno lékařem: 0 · hodnotil: LEK-P03-01 · zdroj: P03-doc07",
        "[P03-bm04] 2026-05-12 Biomarker / molekulární patologie – MMR / MSI: nevyšetřeno · zdroj: P03-pat02",
        "[P03-neuro01] 2026-10-05 Toxicita léčby – Periferní neuropatie (CTCAE) – hodnocení lékařem: grade 1"
        " · zdroj: P03-doc07",
        "[P03-img03#4] 2026-09-21 Závěr: Parciální odpověď dle RECIST 1.1 – součet cílových lézí 50 mm"
        " (pokles o 40 %). Bez nových ložisek.",
        "[P03-zad01-task] 2026-10-06 Stav nominace P03-zad01: Naplánovaná · termín zasedání MDT: 2026-10-21 14:00",
        "[LEK-P03-05] Lékař: chirurg – hepatobiliární chirurgie",
        "[RKT-03/V3] vyřazení: Periferní neuropatie ≥ G2",
    ])
    def test_rendered_lines(self, p03, line):
        assert line in p03.render().splitlines()

    def test_proms_line(self, p03):
        line = next(x for x in p03.render().splitlines() if x.startswith("[P03-prom02]"))
        assert "samostatnost (ECOG podle pacienta): 1 – Těžší fyzickou práci" in line
        assert "brnění 6/10" in line and "padají mi věci z ruky" in line
        assert "místo bolesti: bez odpovědi" in line       # prázdný string odstraněn sanitizací

    def test_no_pii(self, p03):
        text = p03.render()
        assert "Pacient P03 (fiktivní)" not in text      # Patient.name
        assert "fiktivní lékař" not in text              # Practitioner.name
        assert "1959" not in text                        # birthDate
        assert p03.pseudonymized == 0

    def test_guidelines_trials_and_allowed_ids(self, p03):
        assert p03.guideline_sets == ["KRC", "OBC"]
        assert [p.evidence_id for p in p03.guidelines][:2] == ["KRC-1.1", "KRC-1.2"]
        assert len(p03.guidelines) == 18
        assert [t.study_id for t in p03.trials] == ["RKT-03", "RKT-05", "RKT-06"]
        assert {"P03-img03#4", "P03-zad01#1", "KRC-2.4", "OBC-1.3", "RKT-03", "RKT-03/V3"} <= p03.allowed_ids
        assert "PRS-1.1" not in p03.allowed_ids and "RKT-01/Z1" not in p03.allowed_ids

    def test_facts(self, p03):
        facts = p03.facts
        assert (facts["sex"], facts["age"], facts["mdt_date"]) == ("male", 67, "2026-10-21")
        assert facts["service_request_id"] == "P03-zad01"
        assert facts["mdt_question"].startswith("Jsou jaterní metastázy po 8 cyklech")
        assert [d["icd10"] for d in facts["diagnoses"]] == ["C18.7", "C78.7"]

    def test_source_text(self, p03):
        assert "50 mm" in p03.source_text("P03-img03")              # resource = řádek + odstavce
        assert p03.source_text("P03-img03#4").startswith("Závěr:")
        assert "4–6 týdnů" in p03.source_text("KRC-2.4")
        assert p03.source_text("RKT-03/V3") == "Periferní neuropatie ≥ G2"
        assert p03.source_text("P99-neexistuje") is None

    def test_group_order_and_highlight(self, p03):
        lines = p03.render(highlight=["P03-img03#4", "neznámé-id"]).splitlines()
        assert lines[3:5] == ["## Nejrelevantnější odstavce", p03.evidence[[e.id for e in p03.evidence].index(
            "P03-img03#4")].render()]
        headers = [line for line in lines if line.startswith("## ")]
        assert headers[1] == "## Pacient, nominace a termín MDT"
        assert headers[-2:] == ["## Doporučené postupy (KRC, OBC)", "## Klinické studie"]
        diagnosis = lines.index("## Diagnózy a komorbidity")
        assert lines[diagnosis + 1].startswith("[P03-dg1]")     # nádory před komorbiditami

    def test_rule_results(self, all_guidelines, studies):
        ctx = make_context("P03", all_guidelines, studies, rule_results=["RF-ECOG: ECOG 0 vs. 1 [P03-ecog03]"])
        assert ctx.render().rstrip().endswith("- RF-ECOG: ECOG 0 vs. 1 [P03-ecog03]")


# ── Všichni pacienti ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("patient_id", sorted(RESOURCE_COUNTS))
def test_every_patient(patient_id, all_guidelines, studies):
    ctx = make_context(patient_id, all_guidelines, studies)
    assert len(ctx.resource_ids) == RESOURCE_COUNTS[patient_id]
    ids = [line.id for line in ctx.evidence]
    assert len(ids) == len(set(ids))
    assert not [i for i in ids if "_" in i]          # sanitizovaná ID (P01-lab01-hb-f)
    assert ctx.pseudonymized == 0                    # žádné falešné náhrady na datech bez PII
    assert ctx.facts["mdt_date"] and ctx.facts["mdt_question"]
    assert len(ctx.render()) < 120_000               # vejde se do jednoho callu (D-010)


def test_sanitized_hb_ids(all_guidelines, studies):
    ctx = make_context("P01", all_guidelines, studies)
    assert "P01-lab01-hb-f" in ctx.allowed_ids
    report = next(line for line in ctx.evidence if line.id == "P01-lab01")
    assert report.group == "lab"


@pytest.mark.parametrize("patient_id, sets, trials", [
    ("P01", ["PRS", "OBC"], ["RKT-01", "RKT-02", "RKT-05", "RKT-06"]),
    ("P04", ["PLI", "OBC"], ["RKT-04", "RKT-05", "RKT-06"]),
    ("P06", ["PRS", "OBC"], ["RKT-01", "RKT-02", "RKT-05", "RKT-06"]),
])
def test_sets_and_trials_by_diagnosis(patient_id, sets, trials, all_guidelines, studies):
    ctx = make_context(patient_id, all_guidelines, studies)
    assert ctx.guideline_sets == sets
    assert [t.study_id for t in ctx.trials] == trials


def test_rkt06_protocol_rules(all_guidelines, studies):
    ctx = make_context("P05", all_guidelines, studies)
    rkt06 = next(t for t in ctx.trials if t.study_id == "RKT-06")
    assert "Anémie G3 při nejnižší dávce (200 mg 2× denně) → ukončení" in rkt06.protocol
    assert "Z1:" not in rkt06.protocol


# ── build_context nad IRIS (podvržený FHIR klient) ────────────────────────────
def test_build_context_reads_fhir(monkeypatch, all_guidelines, studies):
    from services.fhir import client as fhir

    resources = load_patient("P03")
    others = [r for p in ("P01", "P02") for r in load_patient(p) if r["resourceType"] == "Practitioner"]
    by_type = {}
    for r in resources:
        if r["resourceType"] not in ("Practitioner", "Organization"):
            by_type.setdefault(r["resourceType"], []).append(r)
    searches = []

    def search(rtype, **params):
        searches.append((rtype, params))
        if rtype == "Practitioner":     # IRIS neznámý parametr ignoruje → vrátí i cizí lékaře
            return [r for r in resources if r["resourceType"] == "Practitioner"] + others
        if rtype == "Organization":
            return [r for r in resources if r["resourceType"] == "Organization"]
        return [s for s in studies if s["resourceType"] == rtype]

    monkeypatch.setattr(fhir, "patient_everything", lambda pid: by_type)
    monkeypatch.setattr(fhir, "search", search)
    loaded = []
    monkeypatch.setattr(context_builder, "load_guidelines",
                        lambda sets: loaded.append(sets) or [p for p in all_guidelines if p.guideline_set in sets])

    ctx = context_builder.build_context("P03")
    assert len(ctx.resource_ids) == 171
    assert not [i for i in ctx.resource_ids if i.startswith("LEK-P01") or i.startswith("LEK-P02")]
    assert loaded == [["KRC", "OBC"]]
    practitioner_search = next(p for t, p in searches if t == "Practitioner")
    assert practitioner_search["_id"].split(",") == [f"LEK-P03-0{i}" for i in range(1, 9)]


def test_build_context_with_given_guidelines(monkeypatch):
    from services.fhir import client as fhir

    monkeypatch.setattr(fhir, "patient_everything", lambda pid: {"Patient": [{"resourceType": "Patient", "id": pid}]})
    monkeypatch.setattr(fhir, "search", lambda rtype, **params: [])
    passage = GuidelinePassage("OBC-1.1", "OBC", "Nominace", "text")
    ctx = context_builder.build_context("P99", guidelines=[passage])
    assert ctx.guidelines == [passage] and ctx.resource_ids == ["P99"]
    assert "[P99] Pacient: neuvedeno, věk neuveden" in ctx.render()
