"""
Kontrola výběru guidelines podle MKN-10 na celé cestě generátoru podkladu (bez Dockeru, IRIS a Gemini).

Pustí skutečný `services.ai.brief.generate_brief` pro P01–P06 z datasetu a P07–P12 z `data/dataset_test`.
Podvržené jsou jen vnější služby:
- IRIS FHIR: `services.fhir.client.request` odpovídá z bundlů po sanitizaci ingestem (`ingest.load_patient`);
- IRIS SQL: `services.iris.db.connect` vrací pasáže `MDT.GuidelineChunk` z `guidelines/*.md` datasetu;
- Gemini: `MockAIProvider`, který si zapíše každý prompt, aby šlo ověřit, co AI opravdu dostala.

Potřebuje jen `pydantic` a `PyYAML`:

    python data/dataset_test/run_checks.py            # všechno
    python data/dataset_test/run_checks.py P08 P12    # vybraní pacienti
"""
from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import sys
import threading
import types
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BACKEND = ROOT / "WEB_Template" / "backend"
DATASET = ROOT / "Dataset_MDT_Copilot_v1.1_pre_timy" / "Dataset_MDT_Copilot_v1.1"

sys.path.insert(0, str(BACKEND))
os.environ["AI_PROVIDER"] = "mock"
os.environ.setdefault("ONKO_KB_DIR", str(ROOT / "data" / "onko"))
sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.ERROR)

# ── Falešné IRIS SQL (modul services.iris.db potřebuje driver `iris`, ten tu není) ──
GUIDELINE_TABLE: list = []
SQL_LOG: list[list[str]] = []
fake_db = types.ModuleType("services.iris.db")


class _Cursor:
    def execute(self, sql, params=()):
        assert "MDT.GuidelineChunk" in sql, sql
        SQL_LOG.append(list(params))
        self._rows = [(p.evidence_id, p.guideline_set, p.title, p.text) for p in GUIDELINE_TABLE
                      if p.guideline_set in params]

    def fetchall(self):
        return self._rows

    def close(self):
        pass


class _Conn:
    def cursor(self):
        return _Cursor()


@contextlib.contextmanager
def _connect():
    yield _Conn()


fake_db.connect = _connect
sys.modules["services.iris.db"] = fake_db

from services.ai import brief as brief_mod  # noqa: E402
from services.ai.guidelines import parse_guidelines  # noqa: E402
from services.ai_service import MockAIProvider  # noqa: E402
from services.fhir import client as fhir_client  # noqa: E402
from services.fhir import ingest  # noqa: E402
from services.rules.guideline_sets import guideline_sets_for  # noqa: E402

ALL_PASSAGES = [p for f in sorted((DATASET / "guidelines").glob("*.md"))
                for p in parse_guidelines(f.read_text(encoding="utf-8"))]
PER_SET = {s: sum(1 for p in ALL_PASSAGES if p.guideline_set == s) for s in ("KRC", "PRS", "PLI", "OBC")}
STUDIES = ingest.load_studies(DATASET)


# ── Falešný IRIS FHIR server ──────────────────────────────────────────────────
class FakeFhir:
    def __init__(self):
        self.store: dict[tuple[str, str], dict] = {}

    def load(self, resources):
        for r in resources:
            self.store[(r["resourceType"], r["id"])] = r

    def request(self, method, path="", body=None, params=None):
        assert method == "GET", method
        params = dict(params or {})
        rtype, _, rid = path.partition("/")
        if rid:
            return self.store[(rtype, rid)]
        items = [r for (t, _), r in self.store.items() if t == rtype]
        if "patient" in params:
            needle = f'"Patient/{params["patient"]}"'
            items = [r for r in items if needle in json.dumps(r)]
        if "_id" in params:
            ids = set(params["_id"].split(","))
            items = [r for r in items if r["id"] in ids]
        return {"resourceType": "Bundle", "entry": [{"resource": r} for r in items]}


class RecordingMock(MockAIProvider):
    """Mock bez sítě, který si pamatuje (schéma, system prompt, prompt) každého volání."""

    def __init__(self):
        super().__init__()
        self.calls: list[tuple[str, str, str]] = []
        self._lock = threading.Lock()

    def generate(self, prompt, system_prompt="", **kwargs):
        schema = kwargs.get("response_schema")
        with self._lock:
            self.calls.append((schema.__name__ if schema else "-", system_prompt, prompt))
        return super().generate(prompt, system_prompt=system_prompt, **kwargs)


GUIDE_ID = re.compile(r"^\[((KRC|PRS|PLI|OBC)-\d+\.\d+)\]", re.MULTILINE)
TRIAL_HEAD = re.compile(r"^\[(RKT-\d\d)\] ", re.MULTILINE)
HEADING = re.compile(r"^## Doporučené postupy \(([^)]*)\)", re.MULTILINE)


def run_patient(fake: FakeFhir, pid: str, table: list) -> dict:
    GUIDELINE_TABLE[:] = table
    SQL_LOG.clear()
    provider = RecordingMock()
    case = SimpleNamespace(patient_fhir_id=pid, pk=1, skipped_fields=[], intent=None)
    brief = brief_mod.generate_brief(case, {}, lambda _: None, provider=provider, log_call=lambda *a: None)

    summary_prompt = next(p for name, _, p in provider.calls if name == "SummaryOutput")
    every_prompt = "\n".join(s + "\n" + p for _, s, p in provider.calls)
    heading = HEADING.search(summary_prompt)
    in_prompt = sorted(set(m[0] for m in GUIDE_ID.findall(summary_prompt)))
    role_systems = [s for _, s, _ in provider.calls if "Tvoje role:" in s]
    return {
        "loaded_sets": SQL_LOG[0] if SQL_LOG else [],
        "heading_sets": [s.strip() for s in heading[1].split(",")] if heading else [],
        "prompt_sets": sorted({i.split("-")[0] for i in in_prompt}, key=["KRC", "PRS", "PLI", "OBC"].index),
        "prompt_passages": len(in_prompt),
        "foreign_ids": sorted({m[0] for m in GUIDE_ID.findall(every_prompt)} - set(in_prompt)),
        "trials": sorted(set(TRIAL_HEAD.findall(summary_prompt))),
        "role_questions": sum("Otázka posouzení:" in s for s in role_systems),
        "roles": len(role_systems),
        "llm_calls": len(provider.calls),
        "options": len((brief.get("decision_support") or {}).get("treatment_options") or []),
        "option_titles": [o.get("title", "") for o in (brief.get("decision_support") or {}).get("treatment_options") or []],
        "header_dx": (brief["header"].get("diagnosis") or {}).get("icd10") or "",
        "red_flags": len(brief["red_flags"]),
        "sections": len(brief["sections"]),
        "mentions_missing_guidelines": bool(re.search(r"guidelin\w* (nejsou|chybí|nedostupn)|bez guidelines",
                                                      json.dumps(brief, ensure_ascii=False), re.IGNORECASE)),
    }


def check(pid: str, got: dict, exp: dict) -> list[tuple[str, bool, str]]:
    sets = exp["sets"]
    n = sum(PER_SET[s] for s in sets)
    titles = got["option_titles"]
    extra = [(f"semafor nabízí „{t}“", any(t in title for title in titles), "ano" if any(t in title for title in titles)
              else "ne") for t in exp.get("options_include", [])]
    extra += [(f"semafor nenabízí „{t}“", not any(t in title for title in titles),
               next((title for title in titles if t in title), "ok")) for t in exp.get("options_exclude", [])]
    if exp.get("header_dx"):
        extra.append(("diagnóza v hlavičce", got["header_dx"] == exp["header_dx"],
                      f"„{got['header_dx']}“ (čekám {exp['header_dx']})"))
    return [
        ("sady stažené z IRIS", got["loaded_sets"] == sets, f"{got['loaded_sets']} (čekám {sets})"),
        ("nadpis v promptu", got["heading_sets"] == sets, f"{got['heading_sets']}"),
        ("pasáže v promptu", got["prompt_sets"] == sets and got["prompt_passages"] == n,
         f"{got['prompt_sets']}, {got['prompt_passages']} pasáží (čekám {n})"),
        ("nic z cizích sad v žádném promptu", not got["foreign_ids"], ", ".join(got["foreign_ids"]) or "ok"),
        ("studie v kontextu", got["trials"] == exp["trials"], f"{got['trials']} (čekám {exp['trials']})"),
        ("otázka posouzení pro role", (got["role_questions"] > 0) == exp["role_question"],
         f"{got['role_questions']}/{got['roles']} rolí"),
    ] + extra


def dataset_expectations() -> dict:
    breast = {"sets": ["PRS", "OBC"], "trials": ["RKT-01", "RKT-02", "RKT-05", "RKT-06"], "role_question": True}
    return {
        "P01": breast, "P02": breast, "P05": breast, "P06": breast,
        "P03": {"sets": ["KRC", "OBC"], "trials": ["RKT-03", "RKT-05", "RKT-06"], "role_question": True},
        "P04": {"sets": ["PLI", "OBC"], "trials": ["RKT-04", "RKT-05", "RKT-06"], "role_question": True},
    }


def unit_map_checks() -> list[tuple[str, bool, str]]:
    cases = [(["C18.7"], ["KRC", "OBC"]), (["C19"], ["KRC", "OBC"]), (["C20"], ["KRC", "OBC"]),
             ([" c18.7 "], ["KRC", "OBC"]), (["C187"], ["KRC", "OBC"]), (["C21.1"], ["OBC"]),
             (["C50.4", "C34.1"], ["PRS", "PLI", "OBC"]), (["C61"], ["OBC"]), (["D05.1"], ["OBC"]),
             (["C78.7", "C79.5"], ["OBC"]), (["", None], ["OBC"]), ([], ["OBC"])]
    out = []
    for codes, exp in cases:
        try:
            got = guideline_sets_for(codes)
        except Exception as exc:          # noqa: BLE001 – chci vidět i pád
            got = f"výjimka {type(exc).__name__}: {exc}"
        out.append((f"guideline_sets_for({codes!r})", got == exp, f"{got}"))
    return out


def main(selected: list[str]) -> int:
    fake = FakeFhir()
    fhir_client.request = fake.request
    expectations = dataset_expectations()
    test_exp = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
    expectations.update(test_exp)
    roots = {pid: DATASET for pid in ingest.patient_ids(DATASET)}
    roots.update({pid: HERE for pid in ingest.patient_ids(HERE)})
    for pid, root in roots.items():
        fake.load(ingest.load_patient(root, pid))
    fake.load(STUDIES)

    failures, gaps = 0, []
    print("=== Jednotkové kontroly mapy guideline_sets_for")
    for name, ok, detail in unit_map_checks():
        failures += not ok
        print(f"  {'OK ' if ok else 'CHYBA'}  {name} → {detail}")

    for pid in [p for p in roots if not selected or p in selected]:
        exp = expectations[pid]
        print(f"\n=== {pid}  ({'dataset' if roots[pid] == DATASET else 'testovací'})"
              + (f"  {', '.join(exp['dx'])}" if "dx" in exp else ""))
        if exp.get("tests"):
            print(f"  Testuje: {exp['tests']}")
        try:
            got = run_patient(fake, pid, ALL_PASSAGES)
        except Exception as exc:          # noqa: BLE001
            failures += 1
            print(f"  CHYBA  generování podkladu spadlo: {type(exc).__name__}: {exc}")
            continue
        for name, ok, detail in check(pid, got, exp):
            failures += not ok
            print(f"  {'OK ' if ok else 'CHYBA'}  {name}: {detail}")
        print(f"  info   podklad: {got['sections']} sekcí, {got['red_flags']} red flags, "
              f"{got['options']} léčebných možností v semaforu, {got['llm_calls']} volání AI")
        if roots[pid] != DATASET:
            print(f"  info   semafor: {'; '.join(got['option_titles']) or '—'}")
        if exp.get("gap"):
            gaps.append(f"{pid}: {exp['gap']}")

    if not selected or "P03" in selected:
        print("\n=== Scénář: IRIS bez guidelines (ingest s --skip-vectors), pacient P03")
        got = run_patient(fake, "P03", [])
        ok_gen = got["sections"] > 0
        print(f"  {'OK ' if ok_gen else 'CHYBA'}  podklad se vygeneroval: {got['sections']} sekcí")
        print(f"  info   pasáží guidelines v promptu: {got['prompt_passages']}, nadpis: {got['heading_sets'] or '—'}")
        print(f"  {'OK ' if got['mentions_missing_guidelines'] else 'MEZERA'}  podklad upozorní, že guidelines "
              f"chyběly: {'ano' if got['mentions_missing_guidelines'] else 'ne, nikde v podkladu to není vidět'}")
        failures += not ok_gen
        if not got["mentions_missing_guidelines"]:
            gaps.append("IRIS bez guidelines: podklad vznikne bez nich a v UI to není poznat.")

    print("\n=== Výsledek")
    print(f"  {'Všechny kontroly prošly.' if not failures else f'{failures} kontrol selhalo.'}")
    for g in gaps:
        print(f"  známá mezera  {g}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
