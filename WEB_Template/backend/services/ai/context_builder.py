"""
Context builder (ARCHITEKTURA §5.1 krok 2, §5.2; T-105).

IRIS FHIR → evidence list pro LLM:

- každý resource pacienta = jeden řádek `[ID] datum text` (např.
  `[P03-lab06-cea] 2026-10-05 CEA: 13,9 µg/l (ref 0–5) H`);
- texty (zprávy, popisy, záznamy MDT, nominace) navíc po odstavcích `[P03-img03#3] …`
  (číslování `services.ai.text`, stejné jako ve vektorech a v resolveru citací);
- sada guidelines podle MKN-10 (+ OBC vždy), relevantní studie s kritérii `RKT-03/Z1`
  a výsledky deterministických pravidel;
- pseudonymizace každého řádku před odesláním (§5.7).

LLM smí citovat jen ID z `PatientContext.allowed_ids`. Za běhu se čte jen z IRIS.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from services.ai.guidelines import GuidelinePassage, load_guidelines
from services.ai.pseudonymize import Pseudonymizer
from services.ai.text import resource_paragraphs
from services.rules.guideline_sets import guideline_sets_for, trial_is_relevant

LOINC_ECOG = "89247-1"

GROUPS = (
    ("patient", "Pacient, nominace a termín MDT"),
    ("diagnosis", "Diagnózy a komorbidity"),
    ("staging", "Staging, biomarkery, toxicita a funkční vyšetření"),
    ("performance", "ECOG, hmotnost a dotazníky pacienta (PROMs)"),
    ("lab", "Laboratoř"),
    ("treatment", "Léčba a medikace"),
    ("procedure", "Výkony"),
    ("imaging", "Zobrazovací vyšetření"),
    ("pathology", "Patologie"),
    ("document", "Lékařské zprávy"),
    ("mdt", "Předchozí MDT a rozhodnutí"),
    ("people", "Lékaři a pracoviště"),
)
_GROUP_ORDER = {key: i for i, (key, _) in enumerate(GROUPS)}
_PATIENT_GROUP_ORDER = {"Patient": 0, "ServiceRequest": 1, "Task": 2}

SEX_CS = {"male": "muž", "female": "žena", "other": "jiné", "unknown": "neuvedeno"}

PROMS_LABELS = {
    "bolest": "bolest", "bolest-misto": "místo bolesti", "unava": "únava", "nevolnost": "nevolnost",
    "dusnost": "dušnost", "chut": "chuť k jídlu", "brneni": "brnění", "prujem": "průjem",
    "psychika": "psychika", "spanek": "spánek", "samostatnost": "samostatnost (ECOG podle pacienta)",
    "chuze": "chůze", "hmotnost": "hmotnost", "hmotnost-zmena": "změna hmotnosti za 3 měsíce",
    "nove-obtize": "nové obtíže", "alergie": "alergie", "leky-mimo": "léky, doplňky a byliny navíc",
    "priorita": "priorita", "postoj": "co mají lékaři vědět", "podpora": "podpora doma",
}
PROMS_SYMPTOMS = {"bolest", "unava", "nevolnost", "dusnost", "chut", "brneni", "prujem", "psychika", "spanek"}
PROMS_UNITS = {"hmotnost": "kg", "hmotnost-zmena": "kg"}


# ── Datové typy ───────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class EvidenceLine:
    id: str                     # Evidence ID: "P03-lab06-cea" | "P03-img03#3"
    resource_type: str
    resource_id: str
    group: str
    date: str                   # ISO datum (může být částečné "2019-03"), nebo ""
    text: str
    paragraph: int | None = None

    def render(self) -> str:
        return f"[{self.id}] {self.date} {self.text}" if self.date else f"[{self.id}] {self.text}"


@dataclass(frozen=True)
class TrialCriterion:
    evidence_id: str            # "RKT-03/V3"
    kind: str                   # "inclusion" | "exclusion"
    text: str


@dataclass(frozen=True)
class Trial:
    study_id: str               # "RKT-03"
    title: str
    phase: str
    conditions: tuple[str, ...]
    arms: tuple[str, ...]
    protocol: str               # pravidla protokolu z popisu studie (RKT-06), jinak ""
    criteria: tuple[TrialCriterion, ...]

    def render(self) -> list[str]:
        head = _join([
            self.title,
            f"fáze {self.phase}" if self.phase else "",
            "diagnóza: " + "; ".join(self.conditions) if self.conditions else "",
            "ramena: " + "; ".join(self.arms) if self.arms else "",
            self.protocol,
        ])
        kinds = {"inclusion": "zařazení", "exclusion": "vyřazení"}
        return [f"[{self.study_id}] {head}"] + [
            f"[{c.evidence_id}] {kinds.get(c.kind, c.kind)}: {c.text}" for c in self.criteria
        ]


@dataclass
class PatientContext:
    patient_id: str
    evidence: list[EvidenceLine]
    guideline_sets: list[str]
    guidelines: list[GuidelinePassage]
    trials: list[Trial]
    facts: dict[str, Any]
    rule_results: list[str] = field(default_factory=list)
    pseudonymized: int = 0      # počet náhrad pseudonymizace (audit)

    @property
    def resource_ids(self) -> list[str]:
        return [line.id for line in self.evidence if line.paragraph is None]

    @property
    def allowed_ids(self) -> set[str]:
        ids = {line.id for line in self.evidence}
        ids |= {p.evidence_id for p in self.guidelines}
        for trial in self.trials:
            ids.add(trial.study_id)
            ids |= {c.evidence_id for c in trial.criteria}
        return ids

    def source_text(self, evidence_id: str) -> str | None:
        """Text citovaného zdroje pro grounding validátor (čísla, data). Resource = řádek + odstavce."""
        lines = [line for line in self.evidence if line.id == evidence_id or
                 ("#" not in evidence_id and line.resource_id == evidence_id)]
        if lines:
            return "\n".join(line.text for line in lines)
        for passage in self.guidelines:
            if passage.evidence_id == evidence_id:
                return f"{passage.title}. {passage.text}"
        for trial in self.trials:
            if trial.study_id == evidence_id:
                return "\n".join(trial.render())
            for criterion in trial.criteria:
                if criterion.evidence_id == evidence_id:
                    return criterion.text
        return None

    def render(self, highlight: Sequence[str] = ()) -> str:
        """Text kontextu pro LLM. `highlight` = ID odstavců seřazená vektorovým hledáním (T-102)."""
        out = [
            f"# Podklady pacienta {self.patient_id} k MDT {self.facts.get('mdt_date') or '(datum neuvedeno)'}",
            "Formát řádku: [ID zdroje] datum text. ID s „#n“ je n-tý odstavec textu daného zdroje.",
        ]
        by_id = {line.id: line for line in self.evidence}
        top = [by_id[i] for i in highlight if i in by_id]
        if top:
            out += ["", "## Nejrelevantnější odstavce"] + [line.render() for line in top]
        for key, title in GROUPS:
            lines = [line.render() for line in self.evidence if line.group == key]
            if lines:
                out += ["", f"## {title}"] + lines
        if self.guidelines:
            out += ["", f"## Doporučené postupy ({', '.join(self.guideline_sets)})"]
            out += [f"[{p.evidence_id}] {p.title}: {p.text}" for p in self.guidelines]
        if self.trials:
            out += ["", "## Klinické studie"]
            for trial in self.trials:
                out += trial.render()
        if self.rule_results:
            out += ["", "## Výsledky deterministických pravidel"] + [f"- {r}" for r in self.rule_results]
        return "\n".join(out) + "\n"


# ── Veřejné API ───────────────────────────────────────────────────────────────
def build_context(patient_id: str, *, guidelines: list[GuidelinePassage] | None = None,
                  rule_results: Iterable[str] = ()) -> PatientContext:
    """Kontext pacienta z IRIS (FHIR REST + `MDT.GuidelineChunk`)."""
    from services.fhir import client as fhir

    by_type = fhir.patient_everything(patient_id)
    resources = [r for items in by_type.values() for r in items]
    for rtype in ("Practitioner", "Organization"):
        resources += _fetch_referenced(fhir, resources, rtype)
    studies = fhir.search("ResearchStudy") + fhir.search("Group")
    if guidelines is None:
        guidelines = load_guidelines(guideline_sets_for(_diagnosis_codes(resources)))
    return context_from_resources(patient_id, resources, studies=studies, guidelines=guidelines,
                                  rule_results=rule_results)


def context_from_resources(patient_id: str, resources: Iterable[dict], *, studies: Iterable[dict] = (),
                           guidelines: Iterable[GuidelinePassage] = (),
                           rule_results: Iterable[str] = ()) -> PatientContext:
    """Čistá transformace FHIR resources → `PatientContext` (testovatelná bez IRIS)."""
    resources = _unique(resources)
    pseudo = Pseudonymizer()
    for r in resources:
        if r.get("resourceType") in ("Patient", "Practitioner"):
            for name in r.get("name", []):
                pseudo.add_name(name.get("text"), r["id"])
                pseudo.add_name(" ".join(name.get("given", []) + [name.get("family", "")]).strip(), r["id"])

    facts = _facts(patient_id, resources)
    sets = guideline_sets_for(_diagnosis_codes(resources))

    blocks = []
    for r in resources:
        formatter = _FORMATTERS.get(r.get("resourceType"), _generic)
        group, date, text = formatter(r, facts)
        lines = [EvidenceLine(r["id"], r["resourceType"], r["id"], group, date, pseudo(text))]
        for p in resource_paragraphs(r):
            lines.append(EvidenceLine(f"{r['id']}#{p.index}", r["resourceType"], r["id"], group, date,
                                      pseudo(p.text.replace("\n", " / ")), paragraph=p.index))
        blocks.append((_sort_key(group, r, date, text), lines))
    blocks.sort(key=lambda block: block[0])

    return PatientContext(
        patient_id=patient_id,
        evidence=[line for _, lines in blocks for line in lines],
        guideline_sets=sets,
        guidelines=sorted((g for g in guidelines if g.guideline_set in sets), key=lambda g: g.sort_key),
        trials=_trials(studies, sets),
        facts=facts,
        rule_results=list(rule_results),
        pseudonymized=pseudo.replacements,
    )


# ── Pomocné funkce ────────────────────────────────────────────────────────────
def _unique(resources: Iterable[dict]) -> list[dict]:
    seen: dict[tuple[str, str], dict] = {}
    for r in resources:
        seen.setdefault((r["resourceType"], r["id"]), r)
    return list(seen.values())


def _fetch_referenced(fhir, resources: list[dict], rtype: str) -> list[dict]:
    ids = sorted(_referenced_ids(resources, rtype) - {r["id"] for r in resources if r["resourceType"] == rtype})
    if not ids:
        return []
    # IRIS neznámé parametry tiše ignoruje, proto filtr ještě na straně klienta
    return [r for r in fhir.search(rtype, _id=",".join(ids)) if r.get("id") in ids]


def _referenced_ids(node: Any, rtype: str) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        ref = node.get("reference")
        if isinstance(ref, str) and ref.startswith(f"{rtype}/"):
            found.add(ref.split("/", 1)[1])
        for value in node.values():
            found |= _referenced_ids(value, rtype)
    elif isinstance(node, list):
        for value in node:
            found |= _referenced_ids(value, rtype)
    return found


def _diagnosis_codes(resources: Iterable[dict]) -> list[str]:
    conditions = [r for r in resources if r.get("resourceType") == "Condition"]
    oncologic = [c for c in conditions if "onkolog" in _category_text(c)] or conditions
    return [code for c in oncologic if (code := _coding_code(c.get("code"), "icd-10"))]


def _facts(patient_id: str, resources: list[dict]) -> dict[str, Any]:
    patient = next((r for r in resources if r["resourceType"] == "Patient"), {})
    request = next((r for r in resources if r["resourceType"] == "ServiceRequest"), {})
    task = next((r for r in resources if r["resourceType"] == "Task"
                 and _ref_id(r.get("focus")) == request.get("id")), None) \
        or next((r for r in resources if r["resourceType"] == "Task"), {})
    mdt_start = task.get("restriction", {}).get("period", {}).get("start", "")
    age = _ext(patient, "vek-k-datu-mdt")
    if age is None and patient.get("birthDate") and mdt_start:
        age = int(mdt_start[:4]) - int(patient["birthDate"][:4])
    diagnoses = [
        {"id": c["id"], "icd10": _coding_code(c.get("code"), "icd-10"), "text": _cc(c.get("code")),
         "verification": _coding_code(c.get("verificationStatus"), "")}
        for c in resources if c["resourceType"] == "Condition" and "onkolog" in _category_text(c)
    ]
    return {
        "patient_id": patient_id,
        "sex": patient.get("gender", "unknown"),
        "age": age,
        "mdt_date": mdt_start[:10],
        "mdt_datetime": _datetime(mdt_start),
        "service_request_id": request.get("id"),
        "mdt_question": (request.get("reasonCode") or [{}])[0].get("text"),
        "diagnoses": diagnoses,
    }


def _sort_key(group: str, r: dict, date: str, text: str) -> tuple:
    if group == "patient":
        within: tuple = (_PATIENT_GROUP_ORDER.get(r["resourceType"], 9), date, r["id"])
    elif group == "diagnosis":
        within = (0 if "onkolog" in _category_text(r) else 1, date, r["id"])   # nádory před komorbiditami
    elif group == "lab" and r["resourceType"] == "Observation":
        within = (0, text.split(":", 1)[0], date, r["id"])     # trend jednoho parametru pohromadě
    elif group == "lab":
        within = (1, date, r["id"])
    else:
        within = (date, r["id"])
    return _GROUP_ORDER.get(group, 99), within


def _ref_id(ref: dict | None) -> str:
    value = (ref or {}).get("reference", "")
    return value.rsplit("/", 1)[-1] if value else ""


def _ref_ids(refs: Iterable[dict] | None) -> str:
    return ", ".join(i for i in (_ref_id(r) for r in refs or []) if i)


def _cc(cc: dict | None) -> str:
    if not cc:
        return ""
    if cc.get("text"):
        return cc["text"]
    for coding in cc.get("coding", []):
        if coding.get("display") or coding.get("code"):
            return coding.get("display") or coding["code"]
    return ""


def _coding_code(cc: dict | None, system_part: str) -> str:
    for coding in (cc or {}).get("coding", []):
        if system_part in coding.get("system", ""):
            return coding.get("code", "")
    return ""


def _coding_display(cc: dict | None) -> str:
    return ", ".join(c.get("display") or c.get("code", "") for c in (cc or {}).get("coding", []))


def _code_and_display(cc: dict | None) -> str:
    """„8140/3 Adenokarcinom NOS“; bez display jen kód."""
    coding = ((cc or {}).get("coding") or [{}])[0]
    code, display = coding.get("code", ""), coding.get("display", "")
    return f"{code} {display}".strip() if display and display != code else code or _cc(cc)


def _category_label(r: dict) -> str:
    category = r.get("category")
    items = category if isinstance(category, list) else [category] if category else []
    return "; ".join(t for t in (_cc(c) for c in items) if t)


def _category_text(r: dict) -> str:
    return _category_label(r).lower()


def _num(value: Any) -> str:
    """Čísla s desetinnou čárkou jako v textech datasetu (13,9); 5.0 → 5."""
    if isinstance(value, bool):
        return "ano" if value else "ne"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).replace(".", ",")


def _quantity(q: dict | None) -> str:
    if not q or q.get("value") is None:
        return ""
    return f"{_num(q['value'])} {q.get('unit') or q.get('code') or ''}".strip()


def _datetime(value: str | None) -> str:
    if not value:
        return ""
    return value[:10] + (f" {value[11:16]}" if len(value) >= 16 else "")


def _join(parts: Iterable[str]) -> str:
    return " · ".join(p for p in parts if p)


def _notes(r: dict) -> str:
    notes = "; ".join(n["text"].replace("\n", " / ") for n in r.get("note", []) if n.get("text"))
    return f"pozn.: {notes}" if notes else ""


def _value_text(container: dict) -> str:
    for key, value in container.items():
        if not key.startswith("value"):
            continue
        if key == "valueQuantity":
            return _quantity(value)
        if key in ("valueCodeableConcept", "valueCoding"):
            return _cc(value) if key == "valueCodeableConcept" else (value.get("display") or value.get("code", ""))
        if key == "valueReference":
            return _ref_id(value)
        return _num(value) if isinstance(value, (int, float, bool)) else str(value)
    return ""


def _ext(r: dict, name: str) -> Any:
    for ext in r.get("extension", []):
        if ext.get("url", "").endswith("/" + name):
            for key, value in ext.items():
                if key.startswith("value"):
                    return value
    return None


def _ext_text(r: dict, name: str) -> str:
    for ext in r.get("extension", []):
        if ext.get("url", "").endswith("/" + name):
            return _value_text(ext)
    return ""


# ── Formátování podle typu resource: (skupina, datum, text) ───────────────────
def _patient(r: dict, facts: dict) -> tuple[str, str, str]:
    # Jméno, RČ (identifier), datum narození, adresa ani kontakty se do LLM nikdy neposílají (§5.7)
    age = facts.get("age")
    age_text = f"{age} let (věk k datu MDT)" if age is not None else "věk neuveden"
    return "patient", "", f"Pacient: {SEX_CS.get(r.get('gender', 'unknown'), 'neuvedeno')}, {age_text}"


def _service_request(r: dict, facts: dict) -> tuple[str, str, str]:
    question_types = _coding_display((r.get("reasonCode") or [{}])[0])
    informed = _ext(r, "mdt-pacient-informovan")
    text = _join([
        f"Nominace na MDT ({_cc((r.get('category') or [{}])[0])})",
        f"typ projednání: {_coding_display(r.get('code'))}" if r.get("code") else "",
        f"typ otázky: {question_types}" if question_types else "",
        f"priorita: {r['priority']}" if r.get("priority") else "",
        f"zadal: {_ref_id(r.get('requester'))}" if r.get("requester") else "",
        f"zadávající pracoviště: {_ext_text(r, 'mdt-zadajici-pracoviste')}",
        f"pacient informován: {_num(informed)}" if informed is not None else "",
        f"nejzazší termín: {r['occurrenceDateTime'][:10]}" if r.get("occurrenceDateTime") else "",
        f"diagnózy: {_ref_ids(r.get('reasonReference'))}" if r.get("reasonReference") else "",
        f"podklady: {_ref_ids(r.get('supportingInfo'))}" if r.get("supportingInfo") else "",
    ])
    return "patient", (r.get("authoredOn") or "")[:10], text


def _task(r: dict, facts: dict) -> tuple[str, str, str]:
    start = r.get("restriction", {}).get("period", {}).get("start")
    return "patient", (r.get("authoredOn") or "")[:10], _join([
        f"Stav nominace {_ref_id(r.get('focus'))}: {_coding_display(r.get('businessStatus')) or r.get('status', '')}",
        f"termín zasedání MDT: {_datetime(start)}" if start else "termín zasedání MDT neuveden",
    ])


def _condition(r: dict, facts: dict) -> tuple[str, str, str]:
    category = _cc((r.get("category") or [{}])[0]) or "diagnóza"
    icd = _coding_code(r.get("code"), "icd-10")
    verification = _coding_code(r.get("verificationStatus"), "")
    morphology = _ext(r, "icd-o-3-morfologie")
    topography = _ext(r, "icd-o-3-topografie")
    return "diagnosis", (r.get("onsetDateTime") or r.get("recordedDate") or "")[:10], _join([
        f"{category[:1].upper()}{category[1:]}: {icd} {_cc(r.get('code'))}".replace("  ", " "),
        "lokalizace: " + "; ".join(_cc(b) for b in r["bodySite"]) if r.get("bodySite") else "",
        "stadium: " + "; ".join(_cc(s.get("summary")) for s in r["stage"]) if r.get("stage") else "",
        f"morfologie ICD-O-3: {_code_and_display(morphology)}" if morphology else "",
        f"topografie ICD-O-3: {_code_and_display(topography)}" if topography else "",
        f"stav: {_coding_code(r.get('clinicalStatus'), '')}" if r.get("clinicalStatus") else "",
        f"ověření: {verification}" if verification and verification != "confirmed" else "",
        _notes(r),
    ])


def _observation(r: dict, facts: dict) -> tuple[str, str, str]:
    code = r.get("code", {})
    categories = r.get("category", [])
    cat_codes = {c.get("code") for cat in categories for c in cat.get("coding", [])}
    cat_texts = [cat["text"] for cat in categories if cat.get("text")]
    lab_section = any("v2-0074" in c.get("system", "") for cat in categories for c in cat.get("coding", []))
    if _coding_code(code, "loinc.org") == LOINC_ECOG or "vital-signs" in cat_codes:
        group = "performance"
    elif "laboratory" in cat_codes and lab_section:
        group = "lab"
    else:
        group = "staging"

    label = _cc(code)
    if group == "staging" and cat_texts:
        label = f"{cat_texts[-1]} – {label}"
    value = _value_text(r) or "bez hodnoty"
    reference = ""
    if r.get("referenceRange"):
        rr = r["referenceRange"][0]
        low, high = rr.get("low", {}).get("value"), rr.get("high", {}).get("value")
        if low is not None and high is not None:
            reference = f" (ref {_num(low)}–{_num(high)})"
        elif high is not None:
            reference = f" (ref ≤ {_num(high)})"
        elif low is not None:
            reference = f" (ref ≥ {_num(low)})"
        elif rr.get("text"):
            reference = f" (ref {rr['text']})"
    flags = [c.get("code") for i in r.get("interpretation", []) for c in i.get("coding", []) if c.get("code")]
    practitioners = [_ref_id(p) for p in r.get("performer", []) if p.get("reference", "").startswith("Practitioner/")]
    return group, (r.get("effectiveDateTime") or r.get("effectivePeriod", {}).get("start") or "")[:10], _join([
        f"{label}: {value}{reference}" + (f" {' '.join(flags)}" if flags else ""),
        f"hodnotil: {', '.join(practitioners)}" if practitioners else "",
        f"vzorek: {r['specimen'].get('display')}" if r.get("specimen", {}).get("display") else "",
        f"týká se: {_ref_ids(r.get('focus'))}" if r.get("focus") else "",
        f"zdroj: {_ref_ids(r.get('derivedFrom'))}" if r.get("derivedFrom") else "",
        _notes(r),
    ])


def _medication_request(r: dict, facts: dict) -> tuple[str, str, str]:
    med = r.get("medicationCodeableConcept")
    atc = _coding_code(med, "atc")
    dosage = "; ".join(d.get("text", "") for d in r.get("dosageInstruction", []) if d.get("text"))
    return "treatment", (r.get("authoredOn") or "")[:10], _join([
        f"Medikace ({_category_label(r) or 'předpis'}): {_cc(med)}" + (f" (ATC {atc})" if atc else ""),
        f"dávkování: {dosage}" if dosage else "",
        f"stav: {r['status']}" if r.get("status") else "",
        f"předepsal: {_ref_id(r.get('requester'))}" if r.get("requester") else "",
        _notes(r),
    ])


def _medication_administration(r: dict, facts: dict) -> tuple[str, str, str]:
    med = r.get("medicationCodeableConcept")
    atc = _coding_code(med, "atc")
    date = r.get("effectiveDateTime") or r.get("effectivePeriod", {}).get("start") or ""
    return "treatment", date[:10], _join([
        f"Podání ({_category_label(r) or 'léčba'}): {_cc(med)}" + (f" (ATC {atc})" if atc else ""),
        f"dávka: {r['dosage']['text']}" if r.get("dosage", {}).get("text") else "",
        f"stav: {r['status']}" if r.get("status") not in (None, "completed") else "",
        _notes(r),
    ])


def _procedure(r: dict, facts: dict) -> tuple[str, str, str]:
    period = r.get("performedPeriod", {})
    return "procedure", (r.get("performedDateTime") or period.get("start") or "")[:10], _join([
        f"Výkon ({_category_label(r) or 'výkon'}): {_cc(r.get('code'))}",
        f"do {period['end'][:10]}" if period.get("end") else "",
        "místo: " + "; ".join(_cc(b) for b in r["bodySite"]) if r.get("bodySite") else "",
        f"zpráva: {_ref_ids(r.get('report'))}" if r.get("report") else "",
        _notes(r),
    ])


def _imaging_study(r: dict, facts: dict) -> tuple[str, str, str]:
    modalities = ", ".join(m.get("code", "") for m in r.get("modality", []))
    pacs = _ext_text(r, "snimky-v-pacs")
    return "imaging", (r.get("started") or "")[:10], _join([
        f"Zobrazovací studie ({modalities}): {r.get('description', '')}",
        f"snímky v PACS: {pacs}" if pacs else "",
    ])


def _diagnostic_report(r: dict, facts: dict) -> tuple[str, str, str]:
    categories = r.get("category", [])
    section = _coding_code(categories[0] if categories else None, "v2-0074")
    department = categories[1].get("text", "") if len(categories) > 1 else ""
    date = (r.get("effectiveDateTime") or r.get("issued") or "")[:10]
    if section == "LAB":
        results = [_ref_id(x) for x in r.get("result", [])]
        return "lab", date, f"Laboratorní odběr: {len(results)} výsledků (řádky {r['id']}-…)"
    kinds = {"RAD": ("imaging", "Zobrazení"), "SP": ("pathology", "Patologie")}
    group, kind = kinds.get(section, ("document", "Nález"))
    return group, date, _join([
        f"{kind}" + (f" ({department})" if department else "") + f": {_cc(r.get('code'))}",
        f"provedl: {_ref_ids(r.get('performer'))}" if r.get("performer") else "",
        f"studie: {_ref_ids(r.get('imagingStudy'))}" if r.get("imagingStudy") else "",
        f"výsledky: {_ref_ids(r.get('result'))}" if r.get("result") else "",
    ])


def _document_reference(r: dict, facts: dict) -> tuple[str, str, str]:
    doc_type = r.get("type", {})
    title = _cc(doc_type) or r.get("description", "")
    meta = "; ".join(p for p in (_category_label(r), _coding_display(doc_type)) if p)
    return "document", (r.get("date") or "")[:10], _join([
        "Zpráva" + (f" ({meta})" if meta else "") + f": {title}",
        f"autor: {_ref_ids(r.get('author'))}" if r.get("author") else "",
    ])


def _questionnaire_response(r: dict, facts: dict) -> tuple[str, str, str]:
    answers = []
    for item in r.get("item", []):
        link = item.get("linkId", "")
        label = PROMS_LABELS.get(link, link)
        values = []
        for answer in item.get("answer", []):
            if "valueCoding" in answer:
                coding = answer["valueCoding"]
                values.append(f"{coding.get('code')} – {coding.get('display')}" if link == "samostatnost"
                              else coding.get("display") or coding.get("code", ""))
            elif "valueString" in answer:
                values.append(f"„{answer['valueString']}“")
            else:
                values.append(_value_text(answer))
        if not values:
            answers.append(f"{label}: bez odpovědi")
        elif link in PROMS_SYMPTOMS:
            answers.append(f"{label} {values[0]}/10")
        else:
            unit = PROMS_UNITS.get(link)
            answers.append(f"{label}: {', '.join(values)}" + (f" {unit}" if unit else ""))
    questionnaire = (r.get("questionnaire") or "").rsplit("/", 1)[-1]
    source = _ref_id(r.get("source"))
    head = f"Dotazník pacienta {questionnaire}" + (f" (vyplnil {source})" if source else "")
    return "performance", (r.get("authored") or "")[:10], (
        f"{head}, symptomy 0–10 (0 = žádné potíže, 10 = nejhorší): " + "; ".join(answers))


def _composition(r: dict, facts: dict) -> tuple[str, str, str]:
    kind = _coding_code(r.get("type"), "mdt-typ-zaznamu")
    categories = _category_label(r)
    details = [_ref_ids(e.get("detail")) for e in r.get("event", [])]
    appends = [_ref_id(x.get("targetReference")) for x in r.get("relatesTo", [])]
    extensions = [("forma zasedání", "mdt-forma-zasedani"), ("ošetřující lékař", "mdt-osetrujici-lekar"),
                  ("účast pacienta", "mdt-ucast-pacienta")]
    author_label = "předsedající" if kind == "mdt-zaznam" else "autor"
    return "mdt", (r.get("date") or "")[:10], _join([
        f"{r.get('title') or _coding_display(r.get('type'))}" + (f" ({categories})" if categories else ""),
        f"{author_label}: {_ref_ids(r.get('author'))}" if r.get("author") else "",
        f"ověřil: {', '.join(_ref_id(a.get('party')) for a in r['attester'])}" if r.get("attester") else "",
        *(f"{label}: {_ext_text(r, name)}" for label, name in extensions if _ext(r, name) is not None),
        f"navazuje: {', '.join(d for d in details if d)}" if any(details) else "",
        f"doplňuje: {', '.join(a for a in appends if a)}" if any(appends) else "",
    ])


def _care_plan(r: dict, facts: dict) -> tuple[str, str, str]:
    intent = _coding_display((r.get("category") or [{}])[0]) or _cc((r.get("category") or [{}])[0])
    activities = []
    for i, activity in enumerate(r.get("activity", []), 1):
        detail = activity.get("detail", {})
        modality = _coding_code(detail.get("code"), "mdt-modalita") or _cc(detail.get("code"))
        activities.append(f"{i}) [{modality}] {detail.get('description', '')}".strip())
    return "mdt", (r.get("created") or r.get("period", {}).get("start") or "")[:10], _join([
        f"{r.get('title') or 'Plán péče'}" + (f" (záměr: {intent})" if intent else ""),
        f"stav: {r['status']}" if r.get("status") else "",
        f"tým: {_ref_ids(r.get('careTeam'))}" if r.get("careTeam") else "",
        "postup: " + "; ".join(activities) if activities else "",
    ])


def _care_team(r: dict, facts: dict) -> tuple[str, str, str]:
    members = []
    for participant in r.get("participant", []):
        role = ", ".join(_cc(x) for x in participant.get("role", []))
        member = _ref_id(participant.get("member"))
        members.append(f"{role} ({member})" if member else role)
    return "mdt", (r.get("period", {}).get("start") or "")[:10], _join([
        f"Tým: {r.get('name', '')}",
        "účastníci: " + "; ".join(members) if members else "",
    ])


def _practitioner(r: dict, facts: dict) -> tuple[str, str, str]:
    # Lékař = kód + odbornost, nikdy jméno (§5.7)
    qualification = "; ".join(_cc(q.get("code")) for q in r.get("qualification", []))
    return "people", "", f"Lékař: {qualification or 'odbornost neuvedena'}"


def _organization(r: dict, facts: dict) -> tuple[str, str, str]:
    return "people", "", f"Pracoviště: {r.get('name', '')}"


def _generic(r: dict, facts: dict) -> tuple[str, str, str]:
    return "document", "", _join([r.get("resourceType", ""), r.get("status", "")])


_FORMATTERS: dict[str, Callable[[dict, dict], tuple[str, str, str]]] = {
    "Patient": _patient,
    "ServiceRequest": _service_request,
    "Task": _task,
    "Condition": _condition,
    "Observation": _observation,
    "MedicationRequest": _medication_request,
    "MedicationAdministration": _medication_administration,
    "Procedure": _procedure,
    "ImagingStudy": _imaging_study,
    "DiagnosticReport": _diagnostic_report,
    "DocumentReference": _document_reference,
    "QuestionnaireResponse": _questionnaire_response,
    "Composition": _composition,
    "CarePlan": _care_plan,
    "CareTeam": _care_team,
    "Practitioner": _practitioner,
    "Organization": _organization,
}


# ── Studie ────────────────────────────────────────────────────────────────────
_CRITERION_LINE = re.compile(r"^[ZV]\d+:")


def _trials(resources: Iterable[dict], guideline_sets: list[str]) -> list[Trial]:
    resources = list(resources)
    groups = {r["id"]: r for r in resources if r.get("resourceType") == "Group"}
    trials = []
    for study in sorted((r for r in resources if r.get("resourceType") == "ResearchStudy"), key=lambda r: r["id"]):
        conditions = tuple(_cc(c) for c in study.get("condition", []))
        if not trial_is_relevant(conditions, guideline_sets):
            continue
        criteria = []
        for ref in study.get("enrollment", []):
            for ch in groups.get(_ref_id(ref), {}).get("characteristic", []):
                code = _cc(ch.get("code"))
                criteria.append(TrialCriterion(
                    evidence_id=f"{study['id']}/{code}",
                    kind="exclusion" if ch.get("exclude") else "inclusion",
                    text=_cc(ch.get("valueCodeableConcept")) or _value_text(ch),
                ))
        protocol = " ".join(
            line.strip() for line in study.get("description", "").splitlines()
            if line.strip() and not _CRITERION_LINE.match(line.strip())
            and line.strip() not in ("Kritéria zařazení:", "Kritéria vyřazení:")
        )
        trials.append(Trial(
            study_id=study["id"],
            title=study.get("title", ""),
            phase=_cc(study.get("phase")),
            conditions=conditions,
            arms=tuple(_join([a.get("name", ""), a.get("description", "")]) for a in study.get("arm", [])),
            protocol=protocol,
            criteria=tuple(criteria),
        ))
    return trials
