"""
Kontrola úplnosti a varování při zařazení pacienta do boardu (ARCHITEKTURA §5.10, FR-P4, T-502).

`intake_prefill(resources, skipped_fields=())` vrátí `IntakePrefill` podle kontraktu §8.6:

- `fields`: povinné údaje podle diagnózy (docs/POZADAVKY_LEKARE.md §4), každý s citací zdroje
  a pasáží, která ho vyžaduje (`required_by`);
- `warnings`: CHYBÍ (`missing`), MIMO NORMU (`out_of_range`), ROZPOR (`conflict`), NEJISTOTA AI
  (`ai_uncertain`). Varování z red flags mají stejné `id` jako flag (`RF-ECOG:P03-ecog03`), takže
  odkliknutí jde dohledat a flag v podkladu zůstane (D-019);
- přeskočený údaj (`skipped_fields`) má stav `skipped` a nevyvolá varování. Otázku pro MDT přeskočit
  nelze (OBC-1.1).

Všechno je deterministické; LLM se tu nevolá.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from services.rules.red_flags import STALE_DAYS, PatientData, RedFlag, _cc_text, _code, _date, _num, evaluate

UNSKIPPABLE = {"mdt.question"}     # OBC-1.1: bez otázky je případ neúplný

RULE_KIND = {
    "RF-MISSING": "missing", "RF-STALE": "missing", "RF-GERI": "missing", "RF-GENETIC": "missing",
    "RF-PALIATIVE": "missing", "RF-STEROID": "missing", "RF-ROLES": "missing", "RF-LESION": "missing",
    "RF-LAB": "out_of_range", "RF-WEIGHT": "out_of_range", "RF-PROMS": "out_of_range",
    "RF-ECOG": "conflict", "RF-TOX": "conflict", "RF-NOMINATION": "conflict", "RF-TNM": "conflict",
    "RF-MED": "conflict", "RF-NEWSYMPTOM": "conflict", "RF-LLM": "conflict", "RF-IDENTITY": "conflict",
    "RF-DATAQUALITY": "missing",
}
INFO_RULES = {"RF-PRIOR-PROC"}     # jen informace do hlavičky (FR-A4), při zařazení se neodklikává
# Pole bez citace hlídané pravidlem: přeskočené pole flag umlčí, flag nahradí varování „Chybí: pole“.
# Ostatní pole se s flagy párují přes citaci zdroje.
FIELD_RULES = {"geri.g8": ("RF-GERI",)}

ECOG_RANGE = re.compile(r"ECOG\s*(\d)\s*[–-]\s*(\d)")
VO2_RESULT = re.compile(r"VO2\s?max\D{0,20}\d+([.,]\d+)?\s*ml|\d+([.,]\d+)?\s*ml/kg/min", re.IGNORECASE)
INTENT_LETTER = {"kurativni": "C", "paliativni": "P"}


@dataclass
class IntakeField:
    id: str
    label: str
    status: str                     # present | missing | pending | skipped
    value: str | None = None
    citation: str | None = None
    required_by: str | None = None

    def as_dict(self) -> dict:
        return {k: v for k, v in {"id": self.id, "label": self.label, "value": self.value, "citation": self.citation,
                                  "status": self.status, "required_by": self.required_by}.items() if v is not None}


@dataclass
class IntakeWarning:
    id: str
    kind: str                       # missing | out_of_range | conflict | ai_uncertain
    severity: str
    title: str
    detail: str
    citations: list[str]

    def as_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "severity": self.severity, "title": self.title,
                "detail": self.detail, "citations": self.citations}


# ── Pole formuláře ────────────────────────────────────────────────────────────
def _latest_obs(data: PatientData, pattern: str, category: str | None = None):
    candidates = data.by_category(category) if category else data.observations
    matches = [o for o in candidates if re.search(pattern, o.text, re.IGNORECASE)]
    return matches[-1] if matches else None


def _obs_field(data: PatientData, field_id: str, label: str, pattern: str, required_by: str,
               category: str | None = "Biomarker") -> IntakeField:
    obs = _latest_obs(data, pattern, category)
    if obs is None:
        return IntakeField(field_id, label, "missing", required_by=required_by)
    value = obs.value if isinstance(obs.value, str) else f"{_num(obs.value)}"
    unit = (obs.resource.get("valueQuantity") or {}).get("unit")
    value = f"{value} {unit}" if unit and not isinstance(obs.value, str) else value
    status = "present"
    if isinstance(obs.value, str):
        if re.search(r"probíhá|čeká se", obs.value, re.I):
            status = "pending"
        elif re.search(r"nevyšetřen|nedostupn", obs.value, re.I):
            status = "missing"
    return IntakeField(field_id, label, status, value, obs.id, required_by)


def _text_field(data: PatientData, field_id: str, label: str, pattern: re.Pattern, required_by: str,
                types: tuple[str, ...] = ("DocumentReference", "DiagnosticReport")) -> IntakeField:
    paragraphs = data.find_paragraphs(pattern, types)
    if not paragraphs:
        return IntakeField(field_id, label, "missing", required_by=required_by)
    latest = paragraphs[-1]
    return IntakeField(field_id, label, "present", data.paragraph_text(latest)[:160], latest, required_by)


def _radiology_field(data: PatientData, field_id: str, label: str, pattern: str, required_by: str,
                     max_days: int | None = None) -> IntakeField:
    reports = [r for r in data.radiology() if re.search(pattern, _cc_text(r.get("code")), re.IGNORECASE)]
    if not reports:
        return IntakeField(field_id, label, "missing", required_by=required_by)
    last = reports[-1]
    age = data.days_before_mdt(_date(last.get("effectiveDateTime")))
    value = f"{_cc_text(last.get('code'))} ({last['effectiveDateTime'][:10]}"
    value += f", {age} dní před MDT)" if age is not None else ")"
    status = "missing" if max_days is not None and age is not None and age > max_days else "present"
    return IntakeField(field_id, label, status, value, last["id"], required_by)


def _common_fields(data: PatientData) -> list[IntakeField]:
    request = data.request
    question = (request.get("reasonCode") or [{}])[0].get("text")
    fields = [IntakeField("mdt.question", "Otázka pro MDT", "present" if question else "missing", question,
                          f"{request['id']}#1" if question else None, "OBC-1.1")]

    morphology = next((e.get("valueCodeableConcept") for c in data.oncologic for e in c.get("extension", [])
                       if e.get("url", "").endswith("/icd-o-3-morfologie")), None)
    histology_note = _note_paragraph(data, r"Histologie")
    if morphology or histology_note:     # text nominace má i grade; jinak morfologie ICD-O-3 z diagnózy
        value = data.paragraph_text(histology_note) if histology_note else _cc_text(morphology)
        fields.append(IntakeField("dx.histology", "Histologie a grade", "present", value,
                                  histology_note or data.oncologic[0]["id"], "OBC-1.1"))
    else:
        fields.append(IntakeField("dx.histology", "Histologie a grade", "missing", required_by="OBC-1.1"))

    fields.append(_obs_field(data, "staging.tnm", "TNM", r"TNM", "OBC-1.1", category="Staging"))
    fields.append(_radiology_field(data, "staging.imaging", f"Zobrazení ≤ {STALE_DAYS // 7} týdnů k datu MDT", r".",
                                   "OBC-1.2", STALE_DAYS))

    ecog = data.by_loinc("ecog")
    fields.append(IntakeField("ecog.physician", "ECOG (lékař)", "present" if ecog else "missing",
                              str(ecog[-1].value) if ecog else None, ecog[-1].id if ecog else None, "OBC-1.3"))
    proms_ecog = next((qr for qr in reversed(data.proms) if data.answers(qr).get("samostatnost") is not None), None)
    fields.append(IntakeField("ecog.patient", "ECOG podle pacienta (PROMs)", "present" if proms_ecog else "missing",
                              str(data.answers(proms_ecog)["samostatnost"]) if proms_ecog else None,
                              proms_ecog["id"] if proms_ecog else None, "OBC-1.3"))

    comorbidities = [c for c in data.conditions if "komorbid" in _cc_text((c.get("category") or [{}])[0]).lower()]
    comorbidity_note = _note_paragraph(data, r"Relevantní komorbidity")
    if comorbidities:
        fields.append(IntakeField("comorbidities", "Komorbidity", "present",
                                  "; ".join(f"{_code(c.get('code'), 'icd-10')} {_cc_text(c.get('code'))}"
                                            for c in comorbidities), comorbidities[0]["id"], "OBC-1.1"))
    else:   # „bez komorbidit“ je platný údaj, když ho uvádí nominace
        fields.append(IntakeField("comorbidities", "Komorbidity", "present" if comorbidity_note else "missing",
                                  data.paragraph_text(comorbidity_note)[:160] if comorbidity_note else None,
                                  comorbidity_note, "OBC-1.1"))

    treatment = sorted(data.by_type.get("MedicationAdministration", []) + data.by_type.get("Procedure", []),
                       key=lambda r: r.get("effectiveDateTime") or r.get("performedDateTime") or "")
    treatment_note = _note_paragraph(data, r"Předchozí")
    fields.append(IntakeField("treatment.history", "Dosavadní léčba",
                              "present" if treatment or treatment_note else "missing",
                              data.paragraph_text(treatment_note)[:160] if treatment_note else None,
                              treatment_note or (treatment[-1]["id"] if treatment else None), "OBC-1.1"))

    preference_note = _note_paragraph(data, r"Preference")
    priority = next((qr for qr in reversed(data.proms) if data.answers(qr).get("priorita")), None)
    fields.append(IntakeField("preferences", "Preference pacienta",
                              "present" if preference_note or priority else "missing",
                              data.paragraph_text(preference_note) if preference_note else None,
                              preference_note or (priority["id"] if priority else None), "OBC-1.1"))

    allergy_qr = next((qr for qr in reversed(data.proms) if data.answers(qr).get("alergie")), None)
    fields.append(IntakeField("allergies", "Alergie", "present" if allergy_qr else "missing",
                              str(data.answers(allergy_qr)["alergie"]) if allergy_qr else None,
                              allergy_qr["id"] if allergy_qr else None, None))

    weight = data.by_loinc("weight")
    fields.append(IntakeField("weight", "Hmotnost a trend", "present" if weight else "missing",
                              f"{_num(weight[-1].value)} kg ({weight[-1].date})" if weight else None,
                              weight[-1].id if weight else None, "OBC-2.3"))

    if data.age is not None and data.age >= 70:
        g8 = data.find_paragraphs(re.compile(r"\bG8\b|geriatr", re.I))
        fields.append(IntakeField("geri.g8", f"Geriatrický screening G8 (věk {data.age})",
                                  "present" if g8 else "missing", data.paragraph_text(g8[-1])[:160] if g8 else None,
                                  g8[-1] if g8 else None, "OBC-2.2"))
    return fields


def _note_paragraph(data: PatientData, prefix: str) -> str | None:
    """Odstavec nominace (`P03-zad01#n`) začínající `prefix`; číslování ze services.ai.text jako u citací."""
    request_id = data.request.get("id")
    return data.paragraph_with(request_id, re.compile("^" + prefix)) if request_id else None


def _lung_fields(data: PatientData) -> list[IntakeField]:
    fields = [
        _radiology_field(data, "staging.pet", "PET-CT", r"PET", "PLI-1.1"),
        _radiology_field(data, "staging.brain_mr", "MR mozku", r"MR mozku", "PLI-1.1"),
        _text_field(data, "staging.ebus", "Invazivní staging mediastina (EBUS)", re.compile(r"EBUS", re.I), "PLI-1.1"),
        _obs_field(data, "bm.egfr", "EGFR", r"EGFR", "PLI-1.3"),
        _obs_field(data, "bm.alk", "ALK", r"\bALK\b", "PLI-1.3"),
        _obs_field(data, "bm.pdl1", "PD-L1", r"PD-?L1", "PLI-1.3"),
    ]
    spiro = {key: _obs_field(data, f"spiro.{key}", label, pattern, "PLI-3.1", category="plic")
             for key, label, pattern in (("fev1", "FEV1", r"^FEV1"), ("dlco", "DLCO", r"^DLCO"),
                                         ("ppo_fev1", "ppoFEV1", r"ppoFEV1"), ("ppo_dlco", "ppoDLCO", r"ppoDLCO"))}
    fields += spiro.values()
    low_ppo = [f for f in (spiro["ppo_fev1"], spiro["ppo_dlco"])
               if f.value and (m := re.search(r"(\d+)\s*%", f.value)) and int(m.group(1)) < 60]
    if low_ppo:     # výsledek = naměřená hodnota; „doporučena / neproveden“ výsledek není
        results = data.find_paragraphs(VO2_RESULT, ("DocumentReference", "DiagnosticReport"))
        mentions = data.find_paragraphs(re.compile(r"VO2|spiroergometri|zátěžov\w* test", re.I))
        fields.append(IntakeField("spiro.vo2max", "Zátěžový test (VO2max), ppo < 60 %",
                                  "present" if results else "missing",
                                  data.paragraph_text(results[-1])[:160] if results else None,
                                  results[-1] if results else (mentions[-1] if mentions else low_ppo[-1].citation),
                                  "PLI-3.1"))
    fields.append(_obs_field(data, "smoking", "Kouření", r"Kouření", "PLI-3.3", category="Rizikové"))
    sodium = data.by_loinc("na")
    fields.append(IntakeField("lab.na", "Sodík", "present" if sodium else "missing",
                              f"{_num(sodium[-1].value)} mmol/l ({sodium[-1].date})" if sodium else None,
                              sodium[-1].id if sodium else None, "PLI-3.2"))
    return fields


def _breast_fields(data: PatientData) -> list[IntakeField]:
    fields = [
        _obs_field(data, "bm.er", "ER", r"^(ER\b|Estrogen)", "PRS-1.1"),
        _obs_field(data, "bm.pr", "PR", r"^(PR\b|Progesteron)", "PRS-1.1"),
        _obs_field(data, "bm.her2", "HER2", r"HER2", "PRS-1.2"),
        _obs_field(data, "bm.ki67", "Ki-67", r"Ki-?67", "PRS-1.1"),
    ]
    # HER2+ podle kteréhokoli vzorku (P06: primární nádor 3+, plicní ložisko nevyšetřeno)
    her2_positive = any(re.search(r"3\+|pozitiv", str(o.value or ""), re.I)
                        for o in data.by_category("Biomarker") if "her2" in o.text.lower())
    if not her2_positive:      # HR+/HER2− při progresi (PRS-1.3)
        fields += [
            _obs_field(data, "bm.esr1", "ESR1 (ctDNA)", r"ESR1", "PRS-1.3"),
            _obs_field(data, "bm.pik3ca", "PIK3CA / AKT1 / PTEN", r"PIK3CA", "PRS-1.3"),
            _obs_field(data, "bm.gbrca", "Germinální BRCA1/2", r"germin|zárodeč", "PRS-1.3"),
        ]
    else:                      # anti-HER2 léčba: LVEF à 3 měsíce (PRS-3.4)
        lvef = [o for o in data.observations if "lvef" in o.text.lower()]
        last = lvef[-1] if lvef else None
        age = data.days_before_mdt(last.date) if last else None
        recent = last is not None and age is not None and age <= 92
        fields.append(IntakeField("lvef", "LVEF ≤ 3 měsíce", "present" if recent else "missing",
                                  f"{_num(last.value)} % ({last.date})" if last else None,
                                  last.id if last else None, "PRS-3.4"))
    return fields


def _colorectal_fields(data: PatientData) -> list[IntakeField]:
    fields = [
        _obs_field(data, "bm.ras", "RAS (KRAS, NRAS)", r"\b[KN]?RAS\b", "KRC-1.1"),
        _obs_field(data, "bm.braf", "BRAF V600E", r"BRAF", "KRC-1.1"),
        _obs_field(data, "bm.mmr", "MMR / MSI", r"MMR|MSI", "KRC-1.1"),
    ]
    codes = {c.get("code") for c in (data.request.get("reasonCode") or [{}])[0].get("coding", [])}
    if "indikace-operace" in codes:        # restaging před resekcí jater (KRC-2.4)
        fields.append(_radiology_field(data, "staging.chest_ct", "CT hrudníku ≤ 6 týdnů", r"hrudník", "KRC-2.4",
                                       STALE_DAYS))
        fields.append(_radiology_field(data, "staging.liver_mr", "MR jater ≤ 6 týdnů", r"MR jater", "KRC-2.4",
                                       STALE_DAYS))
        flr = data.find_paragraphs(re.compile(r"FLR|remnant|celkového objemu jater", re.I), ("DiagnosticReport",))
        fields.append(IntakeField("liver.flr", "Budoucí jaterní remnant (FLR)", "present" if flr else "missing",
                                  data.paragraph_text(flr[-1])[:160] if flr else None,
                                  flr[-1] if flr else None, "KRC-2.1"))
    bevacizumab = [m for m in data.by_type.get("MedicationAdministration", [])
                   if _code(m.get("medicationCodeableConcept"), "atc").startswith("L01FG01")]
    if bevacizumab:
        last = max(bevacizumab, key=lambda m: m.get("effectiveDateTime", ""))
        fields.append(IntakeField("treatment.bevacizumab", "Poslední dávka bevacizumabu", "present",
                                  last["effectiveDateTime"][:10], last["id"], "KRC-2.3"))
    fields.append(_obs_field(data, "tox.neuropathy", "Neuropatie (lékař)", r"neuropat", "KRC-3.2",
                             category="Toxicita"))
    return fields


# ── Varování ──────────────────────────────────────────────────────────────────
def _range_warnings(data: PatientData) -> list[IntakeWarning]:
    """NEJISTOTA AI: rozmezí ECOG v textu („ECOG 0–1“) se nepřevádí na jedno číslo (FR-R5)."""
    warnings = []
    for evidence_id in data.find_paragraphs(ECOG_RANGE, ("DocumentReference", "DiagnosticReport", "Composition")):
        text = data.paragraph_text(evidence_id)
        match = ECOG_RANGE.search(text)
        resource_id = evidence_id.split("#")[0]
        structured = [o for o in data.by_loinc("ecog") if o.source == resource_id]
        detail = f"Zpráva uvádí rozmezí „{match.group(0)}“."
        if structured:
            detail += f" Strukturovaně je uloženo ECOG {structured[-1].value} ({structured[-1].id}); AI rozmezí " \
                      "nepřevádí na jedno číslo, hodnotu potvrdí lékař."
        warnings.append(IntakeWarning(f"ai_uncertain:ecog-range:{evidence_id}", "ai_uncertain", "low",
                                      f"Nejisté ECOG: {match.group(0)}", detail,
                                      [evidence_id, *(o.id for o in structured)]))
    return warnings


def _lab_warnings(data: PatientData, flagged: set[str]) -> list[IntakeWarning]:
    """MIMO NORMU: poslední hodnota každého parametru s příznakem H/L (bez těch, které už hlásí RF-LAB)."""
    latest: dict[str, object] = {}
    for o in data.observations:
        if o.resource.get("interpretation") is not None or "referenceRange" in o.resource:
            if any(c.get("code") == "laboratory" for cat in o.resource.get("category", [])
                   for c in cat.get("coding", [])):
                latest[_code(o.resource.get("code"), "loinc.org") or o.text] = o
    warnings = []
    for o in latest.values():
        flags = [c.get("code") for i in o.resource.get("interpretation", []) for c in i.get("coding", [])]
        if not flags or o.id in flagged:
            continue
        unit = (o.resource.get("valueQuantity") or {}).get("unit", "")
        rr = (o.resource.get("referenceRange") or [{}])[0]
        reference = f" (ref {_num(rr['low']['value'])}–{_num(rr['high']['value'])})" \
            if "low" in rr and "high" in rr else ""
        warnings.append(IntakeWarning(f"out_of_range:{o.id}", "out_of_range", "low",
                                      f"{o.text} {_num(o.value)} {unit}".strip(),
                                      f"Poslední hodnota {o.text} {_num(o.value)} {unit}{reference} ({o.date}) "
                                      "je mimo referenční rozmezí.", [o.id]))
    return warnings


def _flag_warning(flag: RedFlag) -> IntakeWarning:
    citations = list(flag.citations) + ([flag.guideline] if flag.guideline else [])
    return IntakeWarning(flag.id, RULE_KIND.get(flag.rule, "conflict"), flag.severity, flag.title,
                         flag.description, citations)


def _field_warning(field: IntakeField) -> IntakeWarning:
    pending = field.status == "pending"
    return IntakeWarning(f"missing:{field.id}", "missing", "moderate" if field.required_by else "low",
                         f"{'Čeká se na výsledek' if pending else 'Chybí'}: {field.label}",
                         (f"{field.label}: „{field.value}“." if field.value else f"Údaj {field.label} v datech není.")
                         + (f" Povinný podle {field.required_by}." if field.required_by else ""),
                         [c for c in (field.citation, field.required_by) if c])


# ── Veřejné API ───────────────────────────────────────────────────────────────
def intake_prefill(resources: Iterable[dict], skipped_fields: Iterable[str] = (),
                   red_flags: Iterable[RedFlag] | None = None) -> dict:
    """`IntakePrefill` (ARCHITEKTURA §8.6) z FHIR resources pacienta."""
    resources = list(resources)
    data = PatientData(resources)
    skipped = set(skipped_fields) - UNSKIPPABLE
    flags = list(evaluate(resources) if red_flags is None else red_flags)

    fields = _common_fields(data)
    if "PLI" in data.sets:
        fields += _lung_fields(data)
    if "PRS" in data.sets:
        fields += _breast_fields(data)
    if "KRC" in data.sets:
        fields += _colorectal_fields(data)
    for f in fields:
        if f.id in skipped:
            f.status = "skipped"

    # Přeskočený údaj se dál nehlídá: umlčí pravidla, která na něm stojí (v podkladu zůstane „Chybí (přeskočeno)“)
    skipped_citations = {f.citation for f in fields if f.status == "skipped" and f.citation}
    skipped_rules = {rule for field_id in skipped for rule in FIELD_RULES.get(field_id, ())}
    warnings: list[IntakeWarning] = []
    covered_citations: set[str] = set()
    raised_rules: set[str] = set()
    for flag in flags:
        if flag.rule in INFO_RULES or flag.rule in skipped_rules or skipped_citations & set(flag.citations):
            continue
        warnings.append(_flag_warning(flag))
        covered_citations |= set(flag.citations)
        raised_rules.add(flag.rule)
    for f in fields:     # chybějící pole, která žádný flag nehlásí
        if f.status not in ("missing", "pending"):
            continue
        if (f.citation and f.citation in covered_citations) or raised_rules & set(FIELD_RULES.get(f.id, ())):
            continue
        warnings.append(_field_warning(f))
    warnings += _range_warnings(data)
    warnings += _lab_warnings(data, {c for f in flags if f.rule == "RF-LAB" for c in f.citations})

    severity = {"high": 0, "moderate": 1, "low": 2}
    kind = {"missing": 0, "conflict": 1, "out_of_range": 2, "ai_uncertain": 3}
    warnings.sort(key=lambda w: (severity.get(w.severity, 9), kind.get(w.kind, 9), w.id))

    ecog = data.by_loinc("ecog")
    care_plans = sorted(data.by_type.get("CarePlan", []), key=lambda c: c.get("created", ""))
    intent_code = _code((care_plans[-1].get("category") or [{}])[0], "mdt-lecebny-zamer") if care_plans else ""
    prefill = {
        "patient_id": data.patient_id,
        "service_request_id": data.request.get("id"),
        "fields": [f.as_dict() for f in fields],
        "warnings": [w.as_dict() for w in warnings],
    }
    if ecog:
        prefill["ecog_physician"] = {"value": int(ecog[-1].value), "citation": ecog[-1].id}
    if intent_code in INTENT_LETTER:      # „odlozeno“ → nepředvyplňuje se (POZADAVKY_LEKARE §3.3)
        prefill["intent_prefill"] = INTENT_LETTER[intent_code]
    return prefill
