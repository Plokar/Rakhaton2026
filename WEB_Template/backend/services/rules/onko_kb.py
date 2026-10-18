"""Znalostní báze onkologie `data/onko` (T-315) v semaforu souladu (T-316, ARCHITEKTURA §5.9).

Stávající katalog `compatibility_rules.yaml` a jeho kontrolní funkce zůstávají beze změny (barvy P03 / P04).
Báze přidá **další postupy pro diagnózu pacienta**, které katalog nemá (např. ablace, další linie, podpůrná
péče, jiné nádory), filtrované podle stadia (M1 vs. nemetastatické) a markeru (`KRAS=g12c` u G12D vypadne).
Barvu každého pravidla počítá referenční vyhodnocovač báze (`data/onko/q.py`, D-015) nad fakty z FHIR;
každý fakt nese citaci zdroje. Fakt, který z dat neumíme vytáhnout, je „chybí údaj“ (⚪), nic se neodhaduje.
"""
from __future__ import annotations

import importlib.util
import os
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from services.rules.compatibility import LIGHT_ORDER, Facts, lung_histology
from services.fhir.values import fhir_code
from services.rules.red_flags import SYMPTOMS, _date

MODALITY = (("CHIR", "chirurgie"), ("ABL", "chirurgie"), ("RT", "rt"), ("NUK", "rt"), ("CHT", "chemoterapie"),
            ("IO", "imunoterapie"), ("TT", "cilena"), ("ADC", "cilena"), ("HT", "hormonalni"), ("SYS", "jina-systemova"),
            ("SUP", "jina-systemova"), ("DG", "diagnostika"), ("SLED", "sledovani"))
OWNER = {"chirurgie": "surgeon", "rt": "radiation_oncologist", "diagnostika": "radiologist"}
GUIDELINE_ID = re.compile(r"^(KRC|PLI|PRS|OBC)-\d+\.\d+$")
LOINC_FACT = re.compile(r"LOINC (\d+-\d)")
ICD_FACT = re.compile(r"Condition(?: ICD)? ([A-Z]\d\d(?:\.\d)?(?:[–-][A-Z]\d\d)?(?:, [A-Z]\d\d(?:\.\d)?(?:[–-][A-Z]\d\d)?)*)")
ATC_FACT = re.compile(r"ATC ([A-Z]\d\d[A-Z]{0,2}\d{0,2}(?:, [A-Z]\d\d[A-Z]{0,2}\d{0,2})*)")
# mHSPC / mCRPC = metastatický karcinom prostaty (nmCRPC je M0, `\b` ho nechytí)
M1_CONTEXT = re.compile(r"\bM1\b|\bIV\b|metast|pokročil|\b[1-3]L\b|udržovac|oligometast|rozsáhlé|\bm(?:HSPC|CRPC)\b",
                        re.IGNORECASE)
CASTRATION_CONTEXT = re.compile(r"HSPC|CRPC")
CRPC_TEXT = re.compile(r"kastračn\w* rezistent|\bn?m?CRPC\b", re.IGNORECASE)
HSPC_TEXT = re.compile(r"(hormonálně|kastračně) senzitiv|\bm?HSPC\b", re.IGNORECASE)
MISSING = re.compile(r"nevyšetř|probíh|čeká|nestanov|nedostat", re.IGNORECASE)


# ── báze ──────────────────────────────────────────────────────────────────────
def kb_dir() -> Path | None:
    env = os.environ.get("ONKO_KB_DIR")
    if env and (Path(env) / "q.py").is_file():
        return Path(env)
    return next((p / "data" / "onko" for p in Path(__file__).resolve().parents if (p / "data" / "onko" / "q.py").is_file()),
                None)


@lru_cache(maxsize=1)
def q():
    """Referenční vyhodnocovač báze (`data/onko/q.py`, jen stdlib); bez báze `None` (semafor jede dál z katalogu)."""
    root = kb_dir()
    if root is None:
        return None
    spec = importlib.util.spec_from_file_location("onko_q", root / "q.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── fakta z FHIR (s citacemi) ─────────────────────────────────────────────────
def _icd_match(spec: str, code: str) -> bool:
    for part in spec.split(", "):
        lo, _, hi = part.partition("–") if "–" in part else part.partition("-")
        if hi:
            if lo[0] == hi[0] == code[:1] and int(lo[1:3]) <= int(code[1:3] or 0) <= int(hi[1:3]):
                return True
        elif code.startswith(lo):
            return True
    return False


def _biomarker(f: Facts, pattern: str):
    """Poslední **známá** hodnota biomarkeru; „nevyšetřeno“ jen když jiná není (P06: plicní biopsie bez materiálu)."""
    matches = [o for o in f.by_category("Biomarker") if re.search(pattern, o.text, re.IGNORECASE)]
    known = [o for o in matches if not MISSING.search(str(o.value or ""))]
    return (known or matches or [None])[-1]


def _marker(obs, mapping: Iterable[tuple[str, str]]) -> str | None:
    value = str(obs.value or "")
    if MISSING.search(value):
        return "nezn"
    for pattern, out in mapping:
        if re.search(pattern, value, re.IGNORECASE):
            return out
    return None


def patient_facts(resources: list[dict], comorbidities_confirmed: bool = False) -> tuple[dict, dict[str, list[str]]]:
    """Fakta ve slovníku báze (`fakta.tsv`) a jejich citace; co z dat nevyčteme, ve faktech není (= chybí údaj)."""
    f = Facts(resources, comorbidities_confirmed)
    facts: dict = {}
    cites: dict[str, list[str]] = {}

    def put(name, value, *citations):
        if value is not None:
            facts[name], cites[name] = value, [c for c in citations if c]

    primary = next((c for c in f.oncologic if not re.match(r"C7[789]|C80", fhir_code(c.get("code"), "icd-10"))), None)
    if primary:
        put("dg", fhir_code(primary.get("code"), "icd-10"), primary["id"])
    patient = (f.by_type.get("Patient") or [{}])[0]
    put("age", f.age, patient.get("id"))
    put("sex", {"male": "M", "female": "Z"}.get(patient.get("gender")), patient.get("id"))

    for row in q().kb()["fakta"]:                       # laboratoř a další LOINC: poslední hodnota
        m = LOINC_FACT.search(row["zdroj"])
        if m and not row["zdroj"].startswith("odvoz"):
            series = [o for o in f.observations if fhir_code(o.resource.get("code"), "loinc.org") == m[1]
                      and isinstance(o.value, (int, float))]
            if series:
                put(row["fakt"], series[-1].value, series[-1].id)
        m = ICD_FACT.search(row["zdroj"])
        if m and row["typ"] == "b":                     # komorbidity podle MKN-10
            hit = next((c for c in f.conditions if _icd_match(m[1], fhir_code(c.get("code"), "icd-10"))), None)
            put(row["fakt"], "ano" if hit else ("ne" if comorbidities_confirmed else None), hit and hit["id"])
        m = ATC_FACT.search(row["zdroj"])
        if m and row["typ"] == "b":                     # léky podle ATC
            prefixes = tuple(m[1].split(", "))
            meds = [r for t in ("MedicationRequest", "MedicationStatement", "MedicationAdministration")
                    for r in f.by_type.get(t, []) if fhir_code(r.get("medicationCodeableConcept"), "atc").startswith(prefixes)]
            put(row["fakt"], "ano" if meds else ("ne" if comorbidities_confirmed else None), meds and meds[-1]["id"])

    ecog = f.latest("ecog")
    if ecog:
        put("ecog.physician", ecog.value, ecog.id)
    if f.proms:
        last = f.proms[-1]
        selfcare = f.answers(last).get("samostatnost")
        if selfcare not in (None, ""):
            put("ecog.patient", float(selfcare), last["id"])
    if "ecog.physician" in facts and "ecog.patient" in facts:
        put("ecog.diff", abs(facts["ecog.patient"] - facts["ecog.physician"]), *cites["ecog.physician"], *cites["ecog.patient"])
    weight = f.by_loinc("weight")
    if weight:
        put("weight", weight[-1].value, weight[-1].id)
        start = [o for o in weight if o.date and weight[-1].date and (weight[-1].date - o.date).days <= 183]
        if len(start) > 1 and start[0].value:
            put("wt.loss6m", round((start[0].value - weight[-1].value) / start[0].value * 100, 1), start[0].id, weight[-1].id)
    crcl = f.crcl()
    if crcl:
        put("lab.crcl", round(crcl[0], 1), *crcl[1]["inputs"])
    for name, loinc in (("lab.bili_xuln", "14631-6"), ("lab.alt_xuln", "1742-6"), ("lab.alp_xuln", "6768-6")):
        series = [o for o in f.observations if fhir_code(o.resource.get("code"), "loinc.org") == loinc and isinstance(o.value, (int, float))]
        high = ((series[-1].resource.get("referenceRange") or [{}])[0].get("high") or {}).get("value") if series else None
        if series and high:
            put(name, round(series[-1].value / high, 2), series[-1].id)
    lvef = [o for o in f.observations if "lvef" in o.text.lower() and isinstance(o.value, (int, float))]
    if lvef:
        put("lvef", lvef[-1].value, lvef[-1].id)
        put("lvef.drop", max(o.value for o in lvef) - lvef[-1].value, *(o.id for o in lvef[-2:]))
    mdt = f.mdt_date or date.today()
    mi = next((c for c in f.conditions if re.match(r"I2[12]|I25\.2", fhir_code(c.get("code"), "icd-10"))), None)
    if mi and _date(mi.get("onsetDateTime")):
        put("card.mi_days", (mdt - _date(mi.get("onsetDateTime"))).days, mi["id"])
    pci = next((p for p in f.by_type.get("Procedure", []) if re.search(r"PCI|stent", _code_text(p), re.I)), None)
    if pci and _date(pci.get("performedDateTime")):
        put("card.stent_days", (mdt - _date(pci.get("performedDateTime"))).days, pci["id"])

    markers = (("bm.kras", r"\bKRAS", ((r"G12C", "g12c"), (r"mutac|varianta|G1[23]|Q61", "mut"), (r"wild|wt|neprokáz", "wt"))),
               ("bm.nras", r"\bNRAS", ((r"mutac|varianta", "mut"), (r"wild|wt|neprokáz", "wt"))),
               ("bm.braf", r"\bBRAF", ((r"neprokáz|wild|wt", "wt"), (r"V600E", "v600e"))),
               ("bm.mmr", r"MMR|MSI", ((r"dMMR|deficien|MSI-H", "dmmr"), (r"pMMR|zachov|MSS", "pmmr"))),
               ("bm.egfr", r"\bEGFR", ((r"wild|wt|neprokáz|negat", "wt"), (r"mutac|exon|L858R|del", "mut"))),
               ("bm.alk", r"\bALK", ((r"negat|neprokáz", "neg"), (r"pozit|přestavb", "pos"))),
               ("bm.ros1", r"ROS1", ((r"negat|neprokáz", "neg"), (r"pozit|přestavb", "pos"))),
               ("bm.brca", r"BRCA", ((r"patogen|mutac", "mut"), (r"wild|wt|neprokáz|negat", "wt"))),
               ("bm.her2", r"HER2", ((r"3\+|pozit|ampl", "pos"), (r"[12]\+|low", "low"), (r"\b0\b|negat", "0"))))
    for name, pattern, mapping in markers:
        obs = _biomarker(f, pattern)
        if obs:
            put(name, _marker(obs, mapping), obs.id)
    if "bm.kras" in facts or "bm.nras" in facts:
        values = {facts.get("bm.kras"), facts.get("bm.nras")}
        ras = "mut" if values & {"mut", "g12c"} else ("wt" if values <= {"wt"} else "nezn")
        put("bm.ras", ras, *cites.get("bm.kras", []), *cites.get("bm.nras", []))
    for name, pattern in (("bm.pdl1", r"PD-?L1"), ("bm.er_pct", r"\bER\b|Estrogen")):
        obs = _biomarker(f, pattern)
        number = re.search(r"(\d+(?:[.,]\d+)?)\s*%", str(obs.value or "")) if obs else None
        if number:
            put(name, float(number[1].replace(",", ".")), obs.id)
    hormone = [o for o in (_biomarker(f, r"\bER\b|Estrogen"), _biomarker(f, r"\bPR\b|Progesteron")) if o]
    known = [o for o in hormone if not MISSING.search(str(o.value or ""))]
    if hormone:
        positive = [o for o in known if re.search(r"pozit|\b[1-9]\d*\s*%", str(o.value or ""))]
        put("bm.hr", "pos" if positive else ("neg" if known else "nezn"), *(o.id for o in hormone))
    return {k: q().value(v) for k, v in facts.items()}, cites


def _code_text(resource: dict) -> str:
    return (resource.get("code") or {}).get("text", "")


# ── postupy ───────────────────────────────────────────────────────────────────
def _metastatic(f: Facts) -> bool:
    tnm = [o for o in f.observations if "tnm" in o.id.lower() and isinstance(o.value, str)]
    if tnm and re.search(r"\b[cpy]*M1|stadium IV", tnm[-1].value):
        return True
    # C78–C79 = vzdálené metastázy; C77 jsou regionální uzliny (P04 cN2 M0)
    return any(re.match(r"C7[89]", fhir_code(c.get("code"), "icd-10")) for c in f.oncologic)


def _castration(f: Facts) -> str | None:
    """Prostata: „CRPC“ / „HSPC“ podle výslovné zmínky v textech, jinak `None` (nefiltruje se, nehádá se).

    ponytail: jen ze zmínky v textu; strukturovaně (PSA progrese na ADT) až s fakty z LLM s citací.
    """
    texts = list(f.texts.values())
    if any(CRPC_TEXT.search(t) for t in texts):
        return "CRPC"
    return "HSPC" if any(HSPC_TEXT.search(t) for t in texts) else None


ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4}
STAGE_TOKEN = re.compile(r"\b(IV|I{1,3})[ABC]?\b(?:\s*[–-]\s*\b(IV|I{1,3})[ABC]?\b)?")


def _stage(f: Facts) -> int | None:
    """Stadium 1–4 z posledního TNM („stadium IIIA“)."""
    tnm = [o for o in f.observations if "tnm" in o.id.lower() and isinstance(o.value, str)]
    m = re.search(r"stadium\s+(IV|I{1,3})", tnm[-1].value) if tnm else None
    return ROMAN[m[1]] if m else None


def _stage_fits(context: str, stage: int | None) -> bool:
    """Kontext postupu („NSCLC I–II resekabilní“, „IB–IIIA“) proti stadiu pacienta; bez stadia nic nevyřadí."""
    allowed = set()
    for lo, hi in STAGE_TOKEN.findall(context):
        allowed |= set(range(ROMAN[lo], ROMAN[hi or lo] + 1))
    return stage is None or not allowed or stage in allowed


def _context_fits(context: str, facts: dict) -> bool:
    """Fenotyp v kontextu postupu („TNBC“, „HR+ HER2−“, „RAS wt“) proti známým biomarkerům; neznámé nevyřadí."""
    hr, her2, ras = facts.get("bm.hr"), facts.get("bm.her2"), facts.get("bm.ras")
    if "TNBC" in context and (hr == "pos" or her2 == "pos"):
        return False
    if re.search(r"HER2\+", context) and her2 in ("0", "low", "ultralow"):
        return False
    if re.search(r"HER2[−-]", context) and her2 == "pos":
        return False
    if re.search(r"HR\+", context) and hr == "neg":
        return False
    return not (re.search(r"RAS[^,;]*wt", context) and ras == "mut")


def _indicated(postup_id: str, facts: dict, f: Facts) -> bool:
    """Obecné postupy (`dg = *`) jen při splněné indikaci OBC-2.x; bez dat (VTE, G-CSF…) se nenabízejí.

    ponytail: jednoduché prahy z kontextu `postupy.tsv`; přesnější indikace až s fakty z textu (LLM s citací).
    """
    answers = f.answers(f.proms[-1]) if f.proms else {}
    symptom = max((v for k, v in answers.items() if k in SYMPTOMS and isinstance(v, (int, float))), default=0)
    flags = {fl.rule for fl in f.flags}
    return {
        "sup-paliativni": symptom >= 7 or (facts.get("ecog.physician") or 0) >= 2,
        "sup-nutrice": (facts.get("wt.loss6m") or 0) >= 5 or (facts.get("lab.alb") or 99) < 35,
        "sup-geriatr": (facts.get("age") or 0) >= 70,
        "sup-genetika": "RF-GENETIC" in flags,
        "sup-fertilita": (facts.get("age") or 99) < 45,
        "obc-biopsie": "RF-LESION" in flags,
    }.get(postup_id, False)


def _modality(tags: list[str]) -> str:
    return next((m for prefix, m in MODALITY for t in tags if t == prefix or t.startswith(prefix + ".")), "jina-systemova")


def kb_procedures(resources: list[dict], *, existing_ids: Iterable[str] = (), allowed_sources: Iterable[str] = (),
                  comorbidities_confirmed: bool = False) -> list[dict]:
    """Další postupy z báze pro diagnózu pacienta ve tvaru `ProcedureCompatibility` (§8.3)."""
    if q() is None:
        return []
    resources = list(resources)
    facts, cites = patient_facts(resources, comorbidities_confirmed)
    if "dg" not in facts:
        return []
    dg = str(facts["dg"]).upper()[:3]
    patient = Facts(resources, comorbidities_confirmed)
    metastatic, stage = _metastatic(patient), _stage(patient)
    histology = lung_histology(patient) if dg == "C34" else None
    castration = _castration(patient) if dg == "C61" else None
    allowed, existing = set(allowed_sources), set(existing_ids)
    out = []
    for p in q().kb()["postupy"]:
        tags = p["tagy"].split(",")
        if p["postup"] in existing or "STUDIE" in tags or not q().dg_match(p["dg"], [dg]):
            continue                                     # studie hodnotí screening RKT (B2), ne semafor
        if p["dg"] == "*" and not _indicated(p["postup"], facts, patient):
            continue                                     # podpůrná péče jen při indikaci (OBC-2.x)
        if p["dg"] != "*" and bool(M1_CONTEXT.search(p["kontext"])) != metastatic:
            continue                                     # stadium: M1 postupy jen u M1 a naopak
        if p["marker"] != "-" and q().marker_value(p, facts) == "ne":
            continue                                     # marker nesedí (např. KRAS G12C u G12D)
        if not _context_fits(p["kontext"], facts):
            continue
        if not _stage_fits(p["kontext"], stage):
            continue                                     # stadium I–IV podle kontextu
        if histology and p["kontext"].startswith("SCLC") != (histology == "SCLC"):
            continue                                     # histologie SCLC / NSCLC, jen když je v datech
        if castration and (m := CASTRATION_CONTEXT.search(p["kontext"])) and m[0] != castration:
            continue                                     # HSPC před kastrační rezistencí, CRPC až po ní
        result = q().evaluate_postup(p["postup"], facts)
        rules, unknown = [], []
        for r in result["pravidla"]:
            sources = [s for s in r["zdroj"].split(",") if s]
            rule_citation = next((s for s in sources if s in allowed), sources[0] if sources else None)
            patient_citations = list(dict.fromkeys(c for fact in r["fakta"] for c in cites.get(fact, [])))
            status = r["light"]
            # Červená jen s ověřeným zdrojem dodaných guidelines (ov = D) a faktem pacienta (§5.9); prahy báze
            # mimo dataset sestavil AI agent a nikdo je zatím neověřil (data/onko/README).
            if status == "red" and (r.get("ov") != "D" or rule_citation not in allowed or not patient_citations):
                status = "orange"
            shown = ", ".join(f"{k} = {_fmt(v)}" for k, v in r["fakta"].items())
            text = f"{r['kontrola']}: {r['proc']}" + (f" ({shown})" if shown else "")
            if r.get("ov") != "D":
                text += " · práh k ověření"
            if status == "grey":
                unknown.append((r, rule_citation))
                continue
            rules.append({"rule_id": r["id"], "status": status, "text": text,
                          "patient_citations": patient_citations, "rule_citation": rule_citation})
        if unknown:                                      # ⚪ pravidla shrnout do jednoho řádku (30 s orientace)
            missing = sorted({m for r, _ in unknown for m in r["chybi"]})
            rules.append({"rule_id": unknown[0][0]["id"] if len(unknown) == 1 else "KB-UNKNOWN", "status": "grey",
                          "text": f"{len(unknown)} pravidel nelze posoudit ({', '.join(r['kontrola'] for r, _ in unknown[:4])}"
                                  f"{' …' if len(unknown) > 4 else ''})" + (f"; chybí údaj: {', '.join(missing[:8])}" if missing else ""),
                          "patient_citations": [], "rule_citation": unknown[0][1]})
        modality = _modality(tags)
        out.append({
            "id": p["postup"], "title": p["nazev"],
            "guideline_citations": [s for s in p["zdroj"].split(",") if GUIDELINE_ID.match(s)],
            "compatibility": {
                "modality": modality, "owner_role": OWNER.get(modality, "oncologist"),
                "overall": min((r["status"] for r in rules), key=LIGHT_ORDER.get, default="grey"),
                "rules": rules, "patient_preferences": [],
            },
        })
    return out


@lru_cache(maxsize=1)
def ext_ids() -> frozenset[str]:
    """Evidence ID katalogu externích zdrojů (`services/iris/data/external_sources.json`, T-504)."""
    import json
    path = Path(__file__).resolve().parents[1] / "iris" / "data" / "external_sources.json"
    return frozenset(s["evidence_id"] for s in json.loads(path.read_text(encoding="utf-8"))["sources"])


def kb_for_patient(resources: list[dict], allowed_ids: Iterable[str] = (), comorbidities_confirmed: bool = False) -> list[dict]:
    """Postupy z báze mimo katalog `compatibility_rules.yaml` (jeho výběr postupů má přednost)."""
    from services.rules.compatibility import load_catalog
    catalog_ids = [p["id"] for p in load_catalog()["procedures"]]
    from services.rules.national_rules import attach
    return attach(kb_procedures(resources, existing_ids=catalog_ids, allowed_sources=set(allowed_ids) | ext_ids(),
                                comorbidities_confirmed=comorbidities_confirmed))


def _fmt(value) -> str:
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value).replace(".", ",")
    return str(value)
