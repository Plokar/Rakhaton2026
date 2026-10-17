"""
Screening klinických studií RKT-01…06 po kritériích (FR-D2, ARCHITEKTURA §5.5, T-204).

Deterministický vyhodnocovač: pro kritéria, která jdou ověřit z dat (ECOG, krevní obraz, MMR, neuropatie,
FLR, extrahepatální onemocnění, BRCA…), vrátí `met` / `not_met` / `unknown` s citací faktu pacienta.
Kritérium bez vyhodnocovače vrátí `None` a doplní ho LLM (s ověřenými citacemi), jinak zůstane `unknown`.

Sémantika (kontrakt §8.1 `Criterion`): u vylučujícího kritéria `met` znamená, že vylučující okolnost platí.
Celkový stav: nesplněné zařazovací nebo splněné vylučující kritérium → `not_eligible`; jinak jakékoli
`unknown` → `potentially_eligible`; jinak `eligible`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

from services.rules import red_flags as rf
from services.rules.compatibility import (
    FLR_VALUE, OXALIPLATIN_IRINOTECAN_ATC, PARPI_ATC, Facts, _her2_samples, _mutation_state, _percent,
)
from services.fhir.values import cc_text, fhir_code
from services.rules.red_flags import STALE_DAYS, _date


@dataclass
class CriterionResult:
    status: str                                 # met | not_met | unknown
    citations: list[str] = field(default_factory=list)
    missing: str | None = None


def _ecog(maximum: int) -> Callable[[Facts], CriterionResult]:
    def check(f: Facts) -> CriterionResult:
        last = f.latest("ecog")
        if last is None:
            return CriterionResult("unknown", missing="ECOG podle lékaře chybí")
        return CriterionResult("met" if last.value <= maximum else "not_met", [last.id])
    return check


def _blood_counts(f: Facts) -> CriterionResult:
    limits = (("hb", 90), ("neu", 1.5), ("plt", 100))
    values = [(f.latest(key), minimum) for key, minimum in limits]
    if any(obs is None for obs, _ in values):
        return CriterionResult("unknown", [o.id for o, _ in values if o], "Krevní obraz není kompletní")
    low = any(obs.value < minimum for obs, minimum in values)
    return CriterionResult("not_met" if low else "met", [o.id for o, _ in values])


def _mmr_high(f: Facts) -> CriterionResult:
    obs = f.biomarker(r"MMR|MSI")
    if obs is None or re.search(r"nevyšetřen|probíhá", str(obs.value), re.I):
        return CriterionResult("unknown", [obs.id] if obs else [], "Vyšetřit MMR/MSI")
    return CriterionResult("met" if re.search(r"dMMR|MSI-H|deficit", str(obs.value), re.I) else "not_met", [obs.id])


def _neuropathy_ge2(f: Facts) -> CriterionResult:
    found = f.neuropathy()
    if found is None:
        return CriterionResult("unknown", missing="Neuropatie podle lékaře chybí")
    obs, grade = found
    if grade >= 2:
        return CriterionResult("met", [obs.id])
    tox = [flag for flag in f.flags if flag.rule == "RF-TOX"]
    if tox:
        return CriterionResult("unknown", list(tox[0].citations),
                               "Lékař hodnotí G1, pacient popisuje omezení odpovídající G2: ověřit stupeň neuropatie")
    return CriterionResult("not_met", [obs.id])


def _flr_below_30(f: Facts) -> CriterionResult:
    found = f.text_value(FLR_VALUE, ("DiagnosticReport",))
    if found is None:
        return CriterionResult("unknown", missing="FLR v podkladech není")
    value, evidence = found
    return CriterionResult("met" if value < 30 else "not_met", [evidence])


def _other_metastases(f: Facts) -> list[dict]:
    return [c for c in f.oncologic if re.match(r"C7[89]", fhir_code(c.get("code"), "icd-10"))
            and not fhir_code(c.get("code"), "icd-10").startswith("C78.7")]


def _chest_staging(f: Facts) -> tuple[dict | None, int | None]:
    chest = [r for r in f.radiology() if "hrudník" in cc_text(r.get("code")).lower()]
    if not chest:
        return None, None
    return chest[-1], f.days_before_mdt(_date(chest[-1].get("effectiveDateTime")))


def _liver_only(f: Facts) -> CriterionResult:
    liver = [c["id"] for c in f.oncologic if fhir_code(c.get("code"), "icd-10").startswith("C78.7")]
    others = _other_metastases(f)
    if others:
        return CriterionResult("not_met", [c["id"] for c in others])
    chest, age = _chest_staging(f)
    if chest is None or age is None or age > STALE_DAYS:
        note = next((p for r in reversed(f.radiology()) if (p := f.paragraph_with(r["id"], re.compile(
            "hrudník nebyl", re.I)))), None)
        return CriterionResult("unknown", liver + ([note] if note else []) + ([chest["id"]] if chest else []),
                               "Chybí aktuální CT hrudníku (extrahepatální onemocnění nelze vyloučit)")
    return CriterionResult("met", liver + [chest["id"]])


def _extrahepatic(f: Facts) -> CriterionResult:
    result = _liver_only(f)
    flipped = {"met": "not_met", "not_met": "met", "unknown": "unknown"}[result.status]
    return CriterionResult(flipped, result.citations, result.missing)


def _response_after_cycles(f: Facts) -> CriterionResult:
    cycles = f.administrations(OXALIPLATIN_IRINOTECAN_ATC)
    if not cycles:
        return CriterionResult("not_met", missing="Indukční chemoterapie s oxaliplatinou nebo irinotekanem v datech není")
    response = next((p for r in reversed(f.radiology())
                     if (p := f.paragraph_with(r["id"], re.compile(r"odpověď|regres|stabiliz", re.I)))), None)
    dates = sorted({c.get("effectiveDateTime", "")[:10] for c in cycles})
    if len(dates) >= 6 and response:
        return CriterionResult("met", [cycles[-1]["id"], response])
    if len(dates) < 6:
        return CriterionResult("not_met", [cycles[-1]["id"]])
    return CriterionResult("unknown", [cycles[-1]["id"]], "Hodnocení odpovědi chybí")


# ── předchozí léčba (T-302): nominace „Předchozí onkologická léčba:“ je seznam „- [druh] N. linie: léky (od – do)“
HISTORY_HEAD = re.compile(r"^Předchozí onkologická léčba", re.I)
HISTORY_LINE = re.compile(r"^-\s*\[(?P<kind>[^\]]+)\]\s*(?P<text>.*)$", re.M)
LINE_NO = re.compile(r"\b(\d+)\.\s*linie", re.I)
AI_DRUGS = re.compile(r"letrozol|anastrozol|exemestan", re.I)
CDK46_DRUGS = re.compile(r"ribocikl|palbocikl|abemacikl", re.I)
TRASTUZUMAB = re.compile(r"trastuzumab(?! deruxtekan)", re.I)
TAXANES = re.compile(r"paklitaxel|docetaxel", re.I)
# `\bzvětš` nechytí „nezvětšené“; „bez progrese / nových ložisek“ odfiltruje `_affirmed`
PROGRESSION = re.compile(r"progres|\bnov[ěáéýí]\w*\b|\broste\b|\bzvětš\w*", re.I)


@dataclass
class TreatmentLine:
    kind: str                       # „chemoterapie“, „hormonální léčba“…
    text: str
    number: int | None              # „2. linie“ → 2 (léčba metastatického onemocnění); adjuvance bez čísla


def _treatment_history(f: Facts) -> tuple[str | None, list[TreatmentLine]]:
    """Odstavec nominace s předchozí onkologickou léčbou (citace) a jeho řádky."""
    request_id = f.request.get("id")
    evidence = f.paragraph_with(request_id, HISTORY_HEAD) if request_id else None
    if evidence is None:
        return None, []
    lines = [TreatmentLine(m["kind"].strip().lower(), m["text"].strip(),
                           int(n[1]) if (n := LINE_NO.search(m["text"])) else None)
             for m in HISTORY_LINE.finditer(f.paragraph_text(evidence))]
    return evidence, lines


def _affirmed(text: str, pattern: re.Pattern) -> bool:
    """Věta se vzorem, která ho nepopírá („bez nových ložisek“ ne)."""
    return any(pattern.search(s) and not NEGATION.search(s) for s in re.split(r"(?<=[.;])\s+", text))


def _drug_history(pattern: str, atc: tuple[str, ...] = ()) -> Callable[[Facts], CriterionResult]:
    """Předchozí léčba lékem: podání / předpis, nebo řádek historie léčby v nominaci. Lék, který v historii není,
    = `not_met` s citací historie (seznam linií je povinná část nominace, OBC-1.1); bez historie `unknown`."""
    rx = re.compile(pattern, re.I)

    def check(f: Facts) -> CriterionResult:
        items = [m for m in f.by_type.get("MedicationAdministration", []) + f.by_type.get("MedicationRequest", [])
                 if rx.search(cc_text(m.get("medicationCodeableConcept")))
                 or (atc and fhir_code(m.get("medicationCodeableConcept"), "atc").startswith(atc))]
        if items:
            return CriterionResult("met", [items[-1]["id"]])
        evidence, lines = _treatment_history(f)
        if evidence is None:
            return CriterionResult("unknown", missing="Předchozí onkologická léčba v nominaci není")
        return CriterionResult("met" if any(rx.search(line.text) for line in lines) else "not_met", [evidence])
    return check


def _progression_after(first: re.Pattern, second: re.Pattern, what: str) -> Callable[[Facts], CriterionResult]:
    """Progrese během nebo po léčbě kombinací `first` + `second` (řádek historie nebo podání).

    Progrese = další linie po této kombinaci v historii, nebo popis zobrazení (případně otázka nominace) s progresí
    či novými ložisky po jejím zahájení. Bez kombinace v historii `not_met`, bez doložené progrese `unknown`.
    """
    def check(f: Facts) -> CriterionResult:
        evidence, lines = _treatment_history(f)
        combo = next((line for line in lines if first.search(line.text) and second.search(line.text)), None)
        doses = sorted((m for m in f.by_type.get("MedicationAdministration", [])
                        if first.search(cc_text(m.get("medicationCodeableConcept")))),
                       key=lambda m: m.get("effectiveDateTime", ""))
        if combo is None and not doses:
            if evidence is None:
                return CriterionResult("unknown", missing="Předchozí onkologická léčba v nominaci není")
            return CriterionResult("not_met", [evidence])
        basis = [evidence] if combo else [doses[-1]["id"]]
        if combo and combo.number and any(line.number and line.number > combo.number for line in lines):
            return CriterionResult("met", basis)        # po kombinaci následovala další linie
        start = doses[0].get("effectiveDateTime", "")[:10] if doses else ""
        new_sites = [c["id"] for c in f.oncologic if re.match(r"C7[789]", fhir_code(c.get("code"), "icd-10"))
                     and start and (c.get("onsetDateTime") or "")[:10] > start]
        if new_sites:                                   # nové metastatické ložisko (diagnóza) až po zahájení léčby
            return CriterionResult("met", basis + new_sites[-1:])
        progression = [pid for r in f.radiology() if r.get("effectiveDateTime", "")[:10] >= start
                       for pid in f.find_paragraphs(PROGRESSION, ("DiagnosticReport",))
                       if pid.startswith(r["id"] + "#") and _affirmed(f.paragraph_text(pid), PROGRESSION)]
        if progression:
            return CriterionResult("met", basis + progression[-1:])
        return CriterionResult("unknown", basis, f"Progrese po {what} není v podkladech doložená")
    return check


def _chemo_lines_m1(maximum: int) -> Callable[[Facts], CriterionResult]:
    """Počet linií chemoterapie v metastatickém stadiu (číslované linie historie s druhem „chemoterapie“)."""
    def check(f: Facts) -> CriterionResult:
        evidence, lines = _treatment_history(f)
        if evidence is None:
            return CriterionResult("unknown", missing="Předchozí onkologická léčba v nominaci není")
        count = sum(1 for line in lines if "chemoterap" in line.kind and line.number)
        return CriterionResult("met" if count <= maximum else "not_met", [evidence])
    return check


def _mdt_decision(_: Facts) -> CriterionResult:
    return CriterionResult("unknown", missing="Rozhodne tato MDT")


def _weight_loss(f: Facts) -> CriterionResult:
    change = rf.weight_change(f)
    if change is None:
        return CriterionResult("unknown", missing="Trend hmotnosti chybí")
    peak, last, loss = change
    return CriterionResult("met" if loss >= 0.05 else "not_met", [last[2], peak[2]])


def _recent_treatment(f: Facts) -> list[dict]:
    return [m for m in f.recent_administrations(90)
            if fhir_code(m.get("medicationCodeableConcept"), "atc").startswith(("L01", "L02"))]


def _active_treatment(f: Facts) -> CriterionResult:
    recent = _recent_treatment(f)
    return CriterionResult("met", [recent[-1]["id"]]) if recent else \
        CriterionResult("unknown", missing="Probíhající ani plánovaná protinádorová léčba v datech není")


def _bsc_only(f: Facts) -> CriterionResult:
    recent = _recent_treatment(f)
    return CriterionResult("not_met", [recent[-1]["id"]]) if recent else \
        CriterionResult("unknown", missing="Ověřit, zda pacient nemá jen podpůrnou léčbu")


def _nutrition_support(f: Facts) -> CriterionResult:
    found = f.find_paragraphs(re.compile(r"enterál|parenterál|sondov", re.I))
    return CriterionResult("met", found[-1:]) if found else \
        CriterionResult("unknown", missing="Enterální nebo parenterální výživa v datech není uvedena")


def _unable_to_walk(f: Facts) -> CriterionResult:
    if not f.proms:
        return CriterionResult("unknown", missing="Dotazník pacienta chybí")
    qr = f.proms[-1]
    answers = f.answers(qr)
    unable = answers.get("chuze") == "byt" or str(answers.get("samostatnost", "0")) in ("3", "4")
    return CriterionResult("met" if unable else "not_met", [qr["id"]])


def _hrr_alteration(f: Facts) -> CriterionResult:
    markers = [o for o in f.by_category("Biomarker") if re.search(r"BRCA|HRR|PALB2|ATM", o.text, re.I)
               and not re.search(r"germin|zárodeč", o.text, re.I)]
    positive = [o for o in markers if _mutation_state(str(o.value)) == "positive"]
    if positive:
        return CriterionResult("met", [positive[-1].id])
    if markers and all(_mutation_state(str(o.value)) == "negative" for o in markers):
        return CriterionResult("not_met", [o.id for o in markers])
    return CriterionResult("unknown", [o.id for o in markers], "NGS nádoru na HRR geny chybí")


def _prior_systemic_line(f: Facts) -> CriterionResult:
    treatment = [m for m in f.by_type.get("MedicationAdministration", []) + f.by_type.get("MedicationRequest", [])
                 if fhir_code(m.get("medicationCodeableConcept"), "atc").startswith(("L01", "L02"))]
    return CriterionResult("met", [treatment[-1]["id"]]) if treatment else \
        CriterionResult("unknown", missing="Předchozí systémová léčba v datech není")


def _prior_parpi(f: Facts) -> CriterionResult:
    doses = f.administrations(PARPI_ATC)
    if not doses:
        return _drug_history(r"olaparib|niraparib|rukaparib|talazoparib|PARP", PARPI_ATC)(f)
    in_study = any("RKT-06" in n.get("text", "") for d in doses for n in d.get("note", []))
    if in_study:      # PARPi je léčba v této studii, ne předchozí léčba (pacientka je zařazená)
        return CriterionResult("not_met", [doses[-1]["id"]])
    return CriterionResult("met", [doses[-1]["id"]])


def _mds_aml(f: Facts) -> CriterionResult:
    found = f.conditions_icd(("D46", "C92"))
    if found:
        return CriterionResult("met", [c["id"] for c in found])
    if f.comorbidities_confirmed:
        return CriterionResult("not_met")
    return CriterionResult("unknown", missing="MDS ani AML v dokumentaci nejsou, lékař potvrdí úplnost anamnézy")


def _brain_mets(f: Facts) -> list[dict]:
    return f.conditions_icd(("C79.3",))


BRAIN_TREATMENT = re.compile(r"stereotak|\bSRS\b|radiochirurg|\bWBRT\b|celomozkov|ozáření mozku|kraniotom|"
                             r"resekce (mozkové )?metast", re.I)


def _untreated_brain_mets(f: Facts) -> CriterionResult:
    brain = _brain_mets(f)
    if not brain:
        return CriterionResult("not_met", [c["id"] for c in f.oncologic])
    evidence, lines = _treatment_history(f)
    procedures = [p for p in f.by_type.get("Procedure", []) if BRAIN_TREATMENT.search(cc_text(p.get("code")))]
    if procedures or any(BRAIN_TREATMENT.search(line.text) for line in lines):
        return CriterionResult("not_met", [c["id"] for c in brain] + ([procedures[-1]["id"]] if procedures else [evidence]))
    if evidence is None:
        return CriterionResult("unknown", [c["id"] for c in brain], "Ověřit, zda jsou mozkové metastázy léčené")
    # mozkové metastázy jsou a v historii léčby ani ve výkonech není jejich léčba (RT, SRS, operace)
    return CriterionResult("met", [c["id"] for c in brain] + [evidence])


def _brain_mets_allowed(f: Facts) -> CriterionResult:
    brain = _brain_mets(f)
    if not brain:
        return CriterionResult("met", [c["id"] for c in f.oncologic])
    dexamethasone = [m for m in f.active_medications()
                     if fhir_code(m.get("medicationCodeableConcept"), "atc").startswith("H02AB02")]
    dose = re.search(r"(\d+(?:[,.]\d+)?)\s*mg", (dexamethasone[-1].get("dosageInstruction") or [{}])[0].get("text", "")) \
        if dexamethasone else None
    if dose and float(dose.group(1).replace(",", ".")) > 2:
        return CriterionResult("not_met", [brain[0]["id"], dexamethasone[-1]["id"]])
    return CriterionResult("unknown", [c["id"] for c in brain], "Ověřit, zda jsou mozkové metastázy léčené a stabilní")


def _bilirubin_high(f: Facts) -> CriterionResult:
    bili = f.latest("bili")
    uln = (bili.resource.get("referenceRange") or [{}])[0].get("high", {}).get("value") if bili else None
    if bili is None or uln is None:
        return CriterionResult("unknown", missing="Bilirubin s referenční mezí chybí")
    return CriterionResult("met" if bili.value > 1.5 * uln else "not_met", [bili.id])


def _lvef_50(f: Facts) -> CriterionResult:
    series = [o for o in f.observations if "lvef" in o.text.lower() and isinstance(o.value, (int, float))]
    if not series:
        return CriterionResult("unknown", missing="LVEF chybí")
    return CriterionResult("met" if series[-1].value >= 50 else "not_met", [series[-1].id])


def _her2_positive(f: Facts) -> CriterionResult:
    samples = _her2_samples(f)
    if not samples:
        return CriterionResult("unknown", missing="HER2 chybí")
    positive = [o.id for o, state in samples if state == "positive"]
    return CriterionResult("met", positive) if positive else CriterionResult("not_met", [o.id for o, _ in samples])


def _er10_her2_negative(f: Facts) -> CriterionResult:
    er = [o for o in f.by_category("Biomarker") if re.match(r"(ER\b|Estrogen)", o.text)]
    samples = _her2_samples(f)
    if not er or not samples:
        return CriterionResult("unknown", [o.id for o in er], "ER nebo HER2 chybí")
    er_value = _percent(er[-1])
    if any(state == "positive" for _, state in samples):
        return CriterionResult("not_met", [o.id for o, s in samples if s == "positive"])
    if er_value is not None and er_value < 10:
        return CriterionResult("not_met", [er[-1].id])
    return CriterionResult("met", [er[-1].id] + [o.id for o, _ in samples])


def _esr1_ctdna(f: Facts) -> CriterionResult:
    obs = f.biomarker(r"ESR1")
    if obs is None or re.search(r"nevyšetřen|ctDNA nevyšetřena", str(obs.value), re.I):
        return CriterionResult("unknown", [obs.id] if obs else [], "ESR1 v ctDNA (ne starší než 3 měsíce) chybí")
    return CriterionResult("met" if _mutation_state(str(obs.value)) == "positive" else "not_met", [obs.id])


def _ild(f: Facts) -> CriterionResult:
    from services.rules.compatibility import ild_history
    result = ild_history(f, {})
    if result.status == "orange":
        return CriterionResult("met", result.patient_citations)
    negative = f.find_paragraphs(re.compile(r"bez (známek )?(pneumonitid|intersticiáln|ILD)", re.I), ("DiagnosticReport",))
    if negative:                    # CT plic výslovně bez pneumonitidy / intersticiálního postižení
        return CriterionResult("not_met", negative[-1:])
    return CriterionResult("not_met") if result.status == "green" else \
        CriterionResult("unknown", missing="ILD v dokumentaci není, lékař potvrdí úplnost anamnézy")


def _egfr_alk(positive: bool) -> Callable[[Facts], CriterionResult]:
    def check(f: Facts) -> CriterionResult:
        markers = {n: f.biomarker(rf"^{n}\b") for n in ("EGFR", "ALK")}
        states = {n: _mutation_state(str(o.value)) if o else "unknown" for n, o in markers.items()}
        cites = [o.id for o in markers.values() if o]
        if positive:     # V1: mutace EGFR nebo přestavba ALK
            if "positive" in states.values():
                return CriterionResult("met", cites)
            if all(s == "negative" for s in states.values()):
                return CriterionResult("not_met", cites)
            return CriterionResult("unknown", cites, "EGFR nebo ALK není známý")
        if all(s in ("negative", "positive") for s in states.values()):      # Z4: známý stav
            return CriterionResult("met", cites)
        unknown = ", ".join(n for n, s in states.items() if s == "unknown")
        return CriterionResult("unknown", cites, f"Doplnit {unknown}")
    return check


def _distant_metastases(f: Facts) -> CriterionResult:
    metastases = _other_metastases(f)
    metastatic_staging = [o for o in f.by_category("Staging")
                          if re.search(r"\bM1|stadium IV", str(o.value), re.I)]
    if metastases or metastatic_staging:
        return CriterionResult("met", [c["id"] for c in metastases] + [o.id for o in metastatic_staging])
    lesions = [flag for flag in f.flags if flag.rule == "RF-LESION"]
    if lesions:
        return CriterionResult("unknown", [c for flag in lesions for c in flag.citations if "#" in c],
                               "Nejasné ložisko měnící stadium je třeba ověřit (M kategorie nejde stanovit)")
    return CriterionResult("not_met", [o.id for o in f.by_category("Staging")][-1:])


def _ppo_40(f: Facts) -> CriterionResult:
    values = [o for o in f.by_category("plic") if re.search(r"ppoFEV1|ppoDLCO", o.text)]
    numbers = [(o, _percent(o)) for o in values if _percent(o) is not None]
    if len(numbers) < 2:
        return CriterionResult("unknown", [o.id for o, _ in numbers], "ppoFEV1 a ppoDLCO nejsou kompletní")
    if all(v >= 40 for _, v in numbers):
        return CriterionResult("met", [o.id for o, _ in numbers])
    return CriterionResult("not_met", [o.id for o, _ in numbers], "Bez vyhovujícího zátěžového testu")


def _resectable_stage(f: Facts) -> CriterionResult:
    tnm = [o for o in f.by_category("Staging") if re.search(r"stadium\s+(II|IIIA|IIIB)\b", str(o.value))]
    return CriterionResult("unknown", [o.id for o in tnm], "Resekabilitu potvrdí hrudní chirurg")


def _autoimmune(f: Facts) -> CriterionResult:
    found = f.conditions_icd(("M05", "M06", "M32", "K50", "K51", "L40", "E05.0", "E06.3"))
    return CriterionResult("met", [c["id"] for c in found]) if found else \
        CriterionResult("unknown", missing="Autoimunitní onemocnění v dokumentaci není, lékař potvrdí")


NEGATION = re.compile(r"\b(bez|není|nejsou|neprokáz\w*|nepatrn\w*|negativn\w*|nelze prokázat)\b", re.I)


def _leptomeningeal(f: Facts) -> CriterionResult:
    found = f.find_paragraphs(re.compile(r"leptomening", re.I), ("DiagnosticReport", "DocumentReference"))
    positive, negative = [], []
    for evidence_id in found:
        for sentence in re.split(r"(?<=[.;])\s+", f.paragraph_text(evidence_id)):
            if re.search(r"leptomening", sentence, re.I):
                (negative if NEGATION.search(sentence) else positive).append(evidence_id)
    if positive:
        return CriterionResult("met", positive[-1:])
    if negative:                    # popis výslovně uvádí, že postižení není
        return CriterionResult("not_met", negative[-1:])
    return CriterionResult("unknown", missing="Leptomeningeální postižení není v popisech uvedeno")


def _visceral_crisis(f: Facts) -> CriterionResult:
    bili = _bilirubin_high(f)
    if bili.status == "not_met":
        return CriterionResult("not_met", bili.citations)
    return CriterionResult("unknown", bili.citations, "Posoudit známky viscerální krize")


CRITERIA: dict[str, Callable[[Facts], CriterionResult]] = {
    "RKT-01/Z1": _er10_her2_negative, "RKT-01/Z2": _esr1_ctdna, "RKT-01/Z5": _ecog(1),
    "RKT-01/V1": _visceral_crisis, "RKT-01/V2": _untreated_brain_mets, "RKT-01/V3": _bilirubin_high,
    "RKT-01/Z3": _progression_after(AI_DRUGS, CDK46_DRUGS, "inhibitoru aromatázy + CDK4/6"),
    "RKT-01/Z4": _chemo_lines_m1(1),
    "RKT-01/V4": _drug_history(r"fulvestrant|elacestrant|camizestrant|\bSERD\b"),
    "RKT-02/Z1": _her2_positive, "RKT-02/Z2": _progression_after(TRASTUZUMAB, TAXANES, "trastuzumabu a taxanu"),
    "RKT-02/Z3": _brain_mets_allowed, "RKT-02/Z4": _ecog(1), "RKT-02/Z5": _lvef_50,
    "RKT-02/V1": _ild, "RKT-02/V2": _drug_history(r"deruxtekan"), "RKT-02/V3": _leptomeningeal,
    "RKT-03/Z1": _liver_only, "RKT-03/Z2": _response_after_cycles, "RKT-03/Z3": _ecog(1),
    "RKT-03/Z4": _mdt_decision, "RKT-03/V1": _extrahepatic, "RKT-03/V2": _mmr_high, "RKT-03/V3": _neuropathy_ge2,
    "RKT-03/V4": _flr_below_30,
    "RKT-04/Z1": _resectable_stage, "RKT-04/Z2": _ecog(1), "RKT-04/Z3": _ppo_40, "RKT-04/Z4": _egfr_alk(False),
    "RKT-04/V1": _egfr_alk(True), "RKT-04/V2": _autoimmune, "RKT-04/V3": _distant_metastases,
    "RKT-05/Z1": _active_treatment, "RKT-05/Z2": _weight_loss, "RKT-05/Z3": _ecog(2),
    "RKT-05/V1": _bsc_only, "RKT-05/V2": _nutrition_support, "RKT-05/V3": _unable_to_walk,
    "RKT-06/Z1": _hrr_alteration, "RKT-06/Z2": _prior_systemic_line, "RKT-06/Z3": _ecog(1),
    "RKT-06/Z4": _blood_counts, "RKT-06/V1": _prior_parpi, "RKT-06/V2": _mds_aml, "RKT-06/V3": _untreated_brain_mets,
}


def evaluate_criterion(criterion_id: str, facts: Facts) -> CriterionResult | None:
    check = CRITERIA.get(criterion_id)
    return check(facts) if check else None


def overall(criteria: list[dict]) -> str:
    for c in criteria:
        if (c.get("kind") == "inclusion" and c["status"] == "not_met") or \
                (c.get("kind") == "exclusion" and c["status"] == "met"):
            return "not_eligible"
    return "potentially_eligible" if any(c["status"] == "unknown" for c in criteria) else "eligible"
