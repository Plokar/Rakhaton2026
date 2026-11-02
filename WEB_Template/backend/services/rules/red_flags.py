"""
Deterministická pravidla varovných signálů (red flags), ARCHITEKTURA §5.4, T-202.

Vstup jsou FHIR resources pacienta (z IRIS, stejné jako pro context builder), výstup
`RedFlag` ve tvaru kontraktu §8.2. Každý flag má závažnost, citace obou zdrojů (ID z datasetu)
a pasáž guidelines. Prahy jsou z guidelines datasetu; prahy, které guidelines neuvádějí,
jsou v popisu označené „konvence týmu“.

Pravidla tu nic nedomýšlejí: když údaj chybí, pravidlo mlčí (chybějící údaje hlásí RF-MISSING).
Odkliknutí varování při zařazení pacienta flag neodstraní (D-019): pravidla o odkliknutí nevědí.
LLM detekce rozporů (`RF-LLM`) je v `services/ai/red_flags_llm.py`.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Iterable

from services.ai.text import resource_paragraphs, resource_text
from services.fhir.ids import derived_from_ids
from services.fhir.values import cc_text, fhir_code, ref_id
from services.rules.guideline_sets import guideline_sets_for, is_oncologic

SEVERITY_ORDER = {"high": 0, "moderate": 1, "low": 2}

LOINC = {"ecog": "89247-1", "weight": "29463-7", "hb": "718-7", "na": "2951-2", "glu": "15074-8",
         "alb": "1751-7", "cea": "2039-6", "ca199": "24108-3", "ca153": "6875-3", "neu": "751-8", "plt": "777-3",
         "krea": "14682-9", "bili": "14631-6", "height": "8302-2", "bmi": "39156-5"}
MARKERS = {"cea": "CEA", "ca199": "CA 19-9", "ca153": "CA 15-3"}
SYMPTOMS = {"bolest": "bolest", "unava": "únava", "nevolnost": "nevolnost", "dusnost": "dušnost",
            "chut": "chuť k jídlu", "brneni": "brnění", "prujem": "průjem", "psychika": "psychika",
            "spanek": "spánek"}

STALE_DAYS = 42                 # OBC-1.2: staging ≤ 6 týdnů k datu MDT
SYMPTOM_HIGH = 7                # OBC-1.3: symptom ≥ 7/10
SYMPTOM_RISE = 3                # konvence týmu: nárůst ≥ 3 body mezi vyplněními
TOX_PATIENT_TINGLING = 5        # konvence týmu: brnění ≥ 5/10 ~ omezení instrumentálních činností
HB_HIGH, HB_MODERATE, HB_DROP = 80, 100, 20      # g/l, konvence týmu
MARKER_RISE = 0.25              # konvence týmu: vzestup ≥ 25 % proti nadiru
GLUCOSE_STEROID = 10.0          # mmol/l, konvence týmu
LVEF_DROP, LVEF_LOW = 10, 50    # PRS-3.4
WEIGHT_LOSS, WEIGHT_WINDOW_DAYS = 0.05, 183      # OBC-2.3
GERI_AGE = 70                   # OBC-2.2

MISSING_VALUE = re.compile(r"nevyšetřen|probíhá|nedostupn|čeká se", re.IGNORECASE)
INSTRUMENTAL = re.compile(r"knoflík|zapín|psan|píš|drž|padají|upouští|z ruky", re.IGNORECASE)
NEW_LOCAL_SYMPTOM = re.compile(
    r"(bol\w*.{0,40}(kyčl|kost|páteř|záda|žebr|tříslo|stehn))|((kyčl|kost|páteř|žebr)\w*.{0,40}bol)"
    r"|hlav|vidě|rozmazan|závrat|ochrnut|necitliv|křeč", re.IGNORECASE)
PALLIATIVE_CARE = re.compile(r"paliativn\w*\s+(tým|péč|ambulanc|konzil|medicín|poradn)", re.IGNORECASE)
GERI_SCREEN = re.compile(r"\bG8\b|geriatr", re.IGNORECASE)
STEROID_TAPER = re.compile(r"snižov|snížen|vysaz|postupn|taper", re.IGNORECASE)
GENETIC_FAMILY = re.compile(r"prsu|\bprs\b|ovari|vaječník|ovárium", re.IGNORECASE)
LESION_UNCLEAR = re.compile(r"nelze vyloučit|k dořešení|doporučen\w* ověřen|nejasn", re.IGNORECASE)
ORGAN_STEMS = ("nadledvin", "plic", "jater", "jatr", "ledvin", "mozk", "kost", "skelet", "uzlin", "prsu", "pankrea",
               "slezin", "ovari", "vajecnik", "stitn")
NOTHING = re.compile(r"^\s*(nic|ne|žádné|nevím|nic nového|-)?\s*$", re.IGNORECASE)
# slova z odpovědi „léky navíc“, která nejsou názvem přípravku (bez diakritiky)
SUPPLEMENT_STOPWORDS = {"kazdy", "vecer", "spani", "denne", "lekarny", "doporucila", "znama", "bolest", "kycle"}

# Systémové kortikoidy a CYP3A substráty ovlivněné třezalkou (induktor CYP3A4)
STEROID_ATC = ("H02AB",)
CYP3A_SUBSTRATE_ATC = ("L01XK", "L01EF", "L01EA", "L01EB", "L01EC", "L01ED", "L01EH", "L01EX", "L01CD", "L01CE",
                       "H02AB02")
# kmen bez diakritiky → (název, vzor pro dohledání varování v dokumentaci)
INTERACTING_SUPPLEMENTS = {"trezalk": ("třezalka", re.compile(r"třezal", re.IGNORECASE))}


@dataclass(frozen=True)
class RedFlag:
    """Varovný signál ve tvaru kontraktu ARCHITEKTURA §8.2 (`RedFlag`)."""

    id: str                     # stabilní: pravidlo + hlavní citace
    rule: str                   # "RF-ECOG" …
    severity: str               # high | moderate | low
    title: str
    description: str
    citations: tuple[str, ...]  # ≥ 2 zdroje, kde to jde
    guideline: str | None = None
    verification: str = "verified"   # deterministické pravidlo = ověřeno z dat

    def as_dict(self) -> dict:
        return {"id": self.id, "rule": self.rule, "severity": self.severity, "title": self.title,
                "description": self.description, "citations": list(self.citations),
                "guideline": self.guideline, "verification": self.verification}

    def render_line(self) -> str:
        """Řádek do kontextu LLM (`PatientContext.rule_results`)."""
        guideline = f" · {self.guideline}" if self.guideline else ""
        return (f"{self.rule} ({self.severity}): {self.title}. {self.description} "
                f"[{', '.join(self.citations)}]{guideline}")


# ── Fakta z FHIR ──────────────────────────────────────────────────────────────
def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _date(value: str | None) -> date | None:
    if not value or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _num(value: float) -> str:
    return (str(int(value)) if float(value).is_integer() else str(round(value, 1))).replace(".", ",")


@dataclass
class Obs:
    id: str
    date: date | None
    text: str           # code.text
    value: float | int | str | None
    resource: dict = field(repr=False)

    @property
    def source(self) -> str | None:
        sources = derived_from_ids(self.resource)
        return sources[0] if sources else None


class PatientData:
    """Fakta pro pravidla vytažená z FHIR resources jednoho pacienta."""

    def __init__(self, resources: Iterable[dict], roles_present: Iterable[str] | None = None):
        self.resources = list(resources)
        self.by_type: dict[str, list[dict]] = {}
        for r in self.resources:
            self.by_type.setdefault(r.get("resourceType", ""), []).append(r)
        self.roles_present = set(roles_present) if roles_present is not None else None
        patient = (self.by_type.get("Patient") or [{}])[0]
        self.patient_id = patient.get("id", "")
        self.request = (self.by_type.get("ServiceRequest") or [{}])[0]
        self.task = next((t for t in self.by_type.get("Task", []) if ref_id(t.get("focus")) == self.request.get("id")),
                         (self.by_type.get("Task") or [{}])[0])
        self.mdt_date = _date(self.task.get("restriction", {}).get("period", {}).get("start"))
        self.age = next((e.get("valueInteger") for e in patient.get("extension", [])
                         if e.get("url", "").endswith("/vek-k-datu-mdt")), None)
        self.conditions = self.by_type.get("Condition", [])
        self.oncologic = [c for c in self.conditions if is_oncologic(c)]
        self.icd10 = [fhir_code(c.get("code"), "icd-10") for c in self.oncologic]
        self.sets = guideline_sets_for(self.icd10)
        self.observations = [self._obs(o) for o in self.by_type.get("Observation", [])]
        self.observations.sort(key=lambda o: (o.date or date.min, o.id))
        self.proms = sorted(self.by_type.get("QuestionnaireResponse", []), key=lambda q: q.get("authored", ""))
        self.texts = {r["id"]: t for r in self.resources if (t := resource_text(r))}

    @staticmethod
    def _obs(o: dict) -> Obs:
        value: float | int | str | None = None
        if "valueQuantity" in o:
            value = o["valueQuantity"].get("value")
        elif "valueInteger" in o:
            value = o["valueInteger"]
        elif "valueString" in o:
            value = o["valueString"]
        return Obs(o["id"], _date(o.get("effectiveDateTime")), cc_text(o.get("code")), value, o)

    # ── dotazy ──
    def by_loinc(self, key: str) -> list[Obs]:
        return [o for o in self.observations if fhir_code(o.resource.get("code"), "loinc.org") == LOINC[key]
                and isinstance(o.value, (int, float))]

    def by_category(self, text: str) -> list[Obs]:
        return [o for o in self.observations
                if any(text.lower() in cc_text(c).lower() for c in o.resource.get("category", []))]

    def answers(self, qr: dict) -> dict[str, object]:
        out: dict[str, object] = {}
        for item in qr.get("item", []):
            answer = (item.get("answer") or [None])[0]
            if answer is None:
                continue
            if "valueCoding" in answer:
                out[item["linkId"]] = answer["valueCoding"].get("code")
            else:
                out[item["linkId"]] = next((v for k, v in answer.items() if k.startswith("value")), None)
        return out

    def paragraph_with(self, resource_id: str, pattern: re.Pattern) -> str | None:
        """ID prvního odstavce resource, který odpovídá vzoru (`P03-img03#1`)."""
        resource = next((r for r in self.resources if r.get("id") == resource_id), None)
        for p in resource_paragraphs(resource) if resource else []:
            if pattern.search(p.text):
                return f"{resource_id}#{p.index}"
        return None

    def by_id(self, observation_id: str) -> Obs:
        return next(o for o in self.observations if o.id == observation_id)

    def paragraph_text(self, evidence_id: str) -> str:
        resource_id, _, index = evidence_id.partition("#")
        resource = next((r for r in self.resources if r.get("id") == resource_id), None)
        paragraphs = resource_paragraphs(resource) if resource else []
        return next((p.text for p in paragraphs if str(p.index) == index), "")

    def find_paragraphs(self, pattern: re.Pattern, types: tuple[str, ...] = ("DocumentReference",)) -> list[str]:
        found = []
        for rtype in types:
            for r in self.by_type.get(rtype, []):
                found += [f"{r['id']}#{p.index}" for p in resource_paragraphs(r) if pattern.search(p.text)]
        return found

    def any_text(self, pattern: re.Pattern) -> bool:
        return any(pattern.search(t) for t in self.texts.values())

    def days_before_mdt(self, d: date | None) -> int | None:
        return (self.mdt_date - d).days if self.mdt_date and d else None

    def guideline(self, by_set: dict[str, str], default: str | None = None) -> str | None:
        """Pasáž guidelines z diagnózou zvolené sady (jen ty smí LLM i UI citovat)."""
        return next((by_set[s] for s in self.sets if s in by_set), default)

    def radiology(self) -> list[dict]:
        reports = [r for r in self.by_type.get("DiagnosticReport", [])
                   if fhir_code((r.get("category") or [{}])[0], "v2-0074") == "RAD"]
        return sorted(reports, key=lambda r: (r.get("effectiveDateTime", ""), r["id"]))

    def active_medications(self) -> list[dict]:
        return [m for m in self.by_type.get("MedicationRequest", []) if m.get("status") in (None, "active")]

    def recent_administrations(self, days: int = 90) -> list[dict]:
        out = []
        for m in self.by_type.get("MedicationAdministration", []):
            d = _date(m.get("effectiveDateTime"))
            delta = self.days_before_mdt(d)
            if delta is None or delta <= days:
                out.append(m)
        return out


def _flag(rule: str, key: str, severity: str, title: str, description: str, citations: Iterable[str | None],
          guideline: str | None) -> RedFlag:
    unique = tuple(dict.fromkeys(c for c in citations if c))
    return RedFlag(id=f"{rule}:{key}", rule=rule, severity=severity, title=title, description=description,
                   citations=unique, guideline=guideline)


# ── Pravidla ──────────────────────────────────────────────────────────────────
def rf_ecog(data: PatientData) -> list[RedFlag]:
    physician = data.by_loinc("ecog")
    if not physician or not data.proms:
        return []
    last, qr = physician[-1], data.proms[-1]
    patient = data.answers(qr).get("samostatnost")
    if patient is None or not str(patient).isdigit():
        return []
    diff = abs(int(patient) - int(last.value))
    if diff < 1:
        return []
    return [_flag("RF-ECOG", last.id, "high" if diff >= 2 else "moderate",
                  f"ECOG lékař {last.value} vs. pacient {patient}",
                  f"Lékař hodnotí ECOG {last.value} ({last.date}), pacient v dotazníku ({qr['authored'][:10]}) "
                  f"odpovídá stupni {patient}. Rozdíl {diff} stupně se má na MDT výslovně zmínit.",
                  [last.id, qr["id"]], "OBC-1.3")]


def rf_proms(data: PatientData) -> list[RedFlag]:
    if not data.proms:
        return []
    last = data.answers(data.proms[-1])
    previous = data.answers(data.proms[-2]) if len(data.proms) > 1 else {}
    findings = []
    for link, label in SYMPTOMS.items():
        value, before = last.get(link), previous.get(link)
        if not isinstance(value, (int, float)):
            continue
        rise = value - before if isinstance(before, (int, float)) else None
        if value >= SYMPTOM_HIGH or (rise is not None and rise >= SYMPTOM_RISE):
            trend = f" (dříve {_num(before)}/10)" if isinstance(before, (int, float)) else ""
            findings.append((value, f"{label} {_num(value)}/10{trend}"))
    if not findings:
        return []
    findings.sort(key=lambda f: -f[0])
    qr_ids = [data.proms[-1]["id"]] + ([data.proms[-2]["id"]] if len(data.proms) > 1 else [])
    return [_flag("RF-PROMS", data.proms[-1]["id"], "moderate", "Výrazná symptomová zátěž podle pacienta",
                  "Pacient v dotazníku uvádí: " + ", ".join(f[1] for f in findings) +
                  f". Symptom ≥ {SYMPTOM_HIGH}/10 (OBC-1.3) nebo nárůst o ≥ {SYMPTOM_RISE} body (konvence týmu).",
                  qr_ids, "OBC-1.3")]


def rf_tox(data: PatientData) -> list[RedFlag]:
    neuro = [o for o in data.by_category("Toxicita") if "neuropat" in o.text.lower() and isinstance(o.value, str)]
    if not neuro or not data.proms:
        return []
    last = neuro[-1]
    grade = re.search(r"grade\s*(\d)", last.value or "", re.IGNORECASE)
    if not grade or int(grade.group(1)) >= 2:
        return []
    qr = data.proms[-1]
    answers = data.answers(qr)
    tingling = answers.get("brneni")
    complaint = str(answers.get("nove-obtize") or "")
    instrumental = bool(INSTRUMENTAL.search(complaint))
    if not (instrumental or (isinstance(tingling, (int, float)) and tingling >= TOX_PATIENT_TINGLING)):
        return []
    patient_view = f"brnění {_num(tingling)}/10" if isinstance(tingling, (int, float)) else ""
    if instrumental:
        patient_view += (", " if patient_view else "") + f"„{complaint.strip()}“"
    return [_flag("RF-TOX", last.id, "high", f"Neuropatie: lékař G{grade.group(1)}, pacient popisuje víc",
                  f"Lékař hodnotí neuropatii jako grade {grade.group(1)} ({last.date}), pacient uvádí {patient_view}. "
                  "Omezení instrumentálních činností odpovídá stupni 2; neuropatii je nutné hodnotit i podle výpovědi "
                  "pacienta.",
                  [last.id, qr["id"]], data.guideline({"KRC": "KRC-3.2"}, "OBC-1.3"))]


def rf_stale(data: PatientData) -> list[RedFlag]:
    reports = data.radiology()
    if not reports or not data.mdt_date:
        return []
    flags = []
    last = reports[-1]
    age = data.days_before_mdt(_date(last.get("effectiveDateTime")))
    if age is not None and age > STALE_DAYS:
        flags.append(_flag("RF-STALE", last["id"], "moderate", f"Zobrazení starší než 6 týdnů ({age} dní)",
                           f"Poslední zobrazení {cc_text(last.get('code'))} je z {last['effectiveDateTime'][:10]}, "
                           f"k datu MDT {data.mdt_date} je to {age} dní (limit {STALE_DAYS} dní).",
                           [last["id"], data.task.get("id")], "OBC-1.2"))

    # Plánovaná resekce jater (KRC-2.4): CT hrudníku, břicha a pánve + MR jater ne starší než 4–6 týdnů
    codes = {c.get("code") for c in (data.request.get("reasonCode") or [{}])[0].get("coding", [])}
    if "KRC" in data.sets and "indikace-operace" in codes:
        chest = [r for r in reports if "hrudník" in cc_text(r.get("code")).lower()]
        chest_age = data.days_before_mdt(_date(chest[-1].get("effectiveDateTime"))) if chest else None
        if chest_age is None or chest_age > STALE_DAYS:
            not_requested = next((p for r in reversed(reports)
                                  if (p := data.paragraph_with(r["id"], re.compile(r"hrudník", re.I)))), None)
            last_chest = (f"poslední CT hrudníku {chest[-1]['id']} je z {chest[-1]['effectiveDateTime'][:10]} "
                          f"({chest_age} dní před MDT)") if chest else "CT hrudníku chybí"
            flags.append(_flag("RF-STALE", "hrudnik", "high", "Restaging před resekcí jater bez aktuálního CT hrudníku",
                               f"Otázka MDT se týká resekce, ale {last_chest}. Před resekcí jater je nutný restaging "
                               "CT hrudníku, břicha a pánve a MR jater ne starší než 4–6 týdnů.",
                               [not_requested, chest[-1]["id"] if chest else None, data.request.get("id")], "KRC-2.4"))
    return flags


_REQUIRED_BIOMARKERS = {     # povinné prediktivní biomarkery podle sady (KRC-1.1, PLI-1.3)
    "KRC": (("RAS", r"\bk?ras\b|kras|nras"), ("BRAF", r"braf"), ("MMR/MSI", r"mmr|msi")),
    "PLI": (("EGFR", r"egfr"), ("ALK", r"\balk\b"), ("PD-L1", r"pd-?l1")),
}
_MISSING_GUIDELINE = {"KRC": "KRC-1.1", "PLI": "PLI-1.3", "PRS": "PRS-1.3"}


def rf_missing(data: PatientData) -> list[RedFlag]:
    biomarkers = data.by_category("Biomarker")
    latest: dict[str, list[Obs]] = {}
    for o in biomarkers:
        latest.setdefault(_plain(re.sub(r"\(.*?\)", "", o.text)).strip(), []).append(o)
    flags = []
    for name, series in latest.items():
        last = series[-1]
        if not isinstance(last.value, str) or not MISSING_VALUE.search(last.value):
            continue
        guideline = data.guideline(_MISSING_GUIDELINE, "OBC-1.1")
        if "PRS" in data.sets and re.search(r"her2|er\b|pr\b|receptor", name):
            guideline = "PRS-1.1"
        citations = [last.id, last.source] + [o.id for o in series[:-1]]
        flags.append(_flag("RF-MISSING", last.id, "moderate", f"Chybí výsledek: {last.text}",
                           f"{last.text}: „{last.value}“ ({last.date}). Prediktivní biomarker je součástí úplných "
                           "podkladů pro MDT.", citations, guideline))
    for s in data.sets:
        for label, pattern in _REQUIRED_BIOMARKERS.get(s, ()):
            if not any(re.search(pattern, _plain(o.text)) for o in biomarkers):
                flags.append(_flag("RF-MISSING", f"chybi-{_plain(label)}", "moderate", f"Chybí biomarker {label}",
                                   f"V datech pacienta není výsledek {label}, který je pro tuto diagnózu povinný.",
                                   [data.request.get("id"), data.patient_id], _MISSING_GUIDELINE[s]))
    return flags


def _supplement_items(text: str) -> list[str]:
    text = re.sub(r"\(.*?\)", "", text)
    return [item.strip() for item in re.split(r",|;|\ba\b", text) if item.strip()]


def rf_med(data: PatientData) -> list[RedFlag]:
    if not data.proms:
        return []
    qr = data.proms[-1]
    extra = str(data.answers(qr).get("leky-mimo") or "")
    if NOTHING.match(extra):
        return []
    medications = data.active_medications()
    listed = " ".join(_plain(cc_text(m.get("medicationCodeableConcept"))) for m in medications)
    missing = []
    for item in _supplement_items(extra):
        words = [w for w in re.findall(r"\w+", _plain(item)) if len(w) >= 4]
        stems = [w[:5] for w in words if w not in SUPPLEMENT_STOPWORDS]
        if stems and not any(stem in listed for stem in stems):
            missing.append(item)
    flags = []
    if missing:
        flags.append(_flag("RF-MED", qr["id"], "moderate", "Léky nebo doplňky mimo medikační záznam",
                           f"Pacient v dotazníku uvádí: {', '.join(missing)}. V medikaci to není.",
                           [qr["id"]] + [m["id"] for m in medications], None))
    # Známé interakce: třezalka (induktor CYP3A4) × CYP3A substráty v aktuální léčbě
    plain_extra = _plain(extra)
    for stem, (label, warning_pattern) in INTERACTING_SUPPLEMENTS.items():
        if stem not in plain_extra:
            continue
        drugs = [m for m in data.recent_administrations() + medications
                 if any(fhir_code(m.get("medicationCodeableConcept"), "atc").startswith(p) for p in CYP3A_SUBSTRATE_ATC)]
        if not drugs:
            continue
        names = sorted({cc_text(d.get("medicationCodeableConcept")) for d in drugs})
        warnings = data.find_paragraphs(warning_pattern)
        latest = max(drugs, key=lambda d: d.get("effectiveDateTime") or d.get("authoredOn") or "")
        flags.append(_flag("RF-MED", f"interakce-{stem}", "high", f"Léková interakce: {label} a {', '.join(names)}",
                           f"Pacient užívá {label} (induktor CYP3A4) a zároveň {', '.join(names)}, který se "
                           "metabolizuje přes CYP3A4; hladina léčiva může klesnout."
                           + (" Dokumentace před třezalkou výslovně varovala." if warnings else ""),
                           [qr["id"], latest["id"], *warnings], None))
    return flags


def rf_lab(data: PatientData) -> list[RedFlag]:
    flags = []
    hb = data.by_loinc("hb")
    if hb:
        last = hb[-1]
        peak = max(hb[:-1], key=lambda o: o.value) if len(hb) > 1 else None
        drop = (peak.value - last.value) if peak else 0
        if last.value < HB_MODERATE or drop >= HB_DROP:
            low = [o for o in hb if o.value < HB_HIGH]
            severity = "high" if last.value < HB_HIGH or len(low) >= 2 else "moderate"
            trend = f", pokles z {_num(peak.value)} ({peak.date})" if peak and drop >= HB_DROP else ""
            repeated = f"; hodnota pod {HB_HIGH} g/l opakovaně ({len(low)}×)" if len(low) >= 2 else ""
            title = (f"Opakovaně Hb < {HB_HIGH} g/l (naposledy {_num(last.value)} g/l)" if len(low) >= 2
                     else f"Hemoglobin {_num(last.value)} g/l")
            flags.append(_flag("RF-LAB", last.id, severity, title,
                               f"Hb {_num(last.value)} g/l ({last.date}){trend}{repeated}. Prahy < {HB_MODERATE} a "
                               f"< {HB_HIGH} g/l a pokles ≥ {HB_DROP} g/l jsou konvence týmu.",
                               [last.id] + [o.id for o in low if o.id != last.id] + ([peak.id] if peak else []),
                               None))
    for key, label in MARKERS.items():
        series = data.by_loinc(key)
        if len(series) < 2:
            continue
        last, nadir = series[-1], min(series[:-1], key=lambda o: o.value)
        if nadir.value > 0 and (last.value - nadir.value) / nadir.value >= MARKER_RISE:
            rise = round((last.value - nadir.value) / nadir.value * 100)
            flags.append(_flag("RF-LAB", last.id, "moderate", f"{label} roste (+{rise} % proti nadiru)",
                               f"{label} {_num(nadir.value)} ({nadir.date}) → {_num(last.value)} ({last.date}). "
                               "Vzestup markeru je důvod k časnějšímu zobrazení, sám o sobě není progrese "
                               f"(práh {int(MARKER_RISE * 100)} % je konvence týmu).",
                               [last.id, nadir.id], data.guideline({"PRS": "PRS-4.2"})))
    sodium = data.by_loinc("na")
    if sodium:
        last = sodium[-1]
        low = (last.resource.get("referenceRange") or [{}])[0].get("low", {}).get("value")
        if low is not None and last.value < low and (len(sodium) < 2 or last.value < sodium[-2].value):
            first = sodium[0]
            flags.append(_flag("RF-LAB", last.id, "moderate", f"Klesající sodík {_num(last.value)} mmol/l",
                               f"Na {_num(first.value)} ({first.date}) → {_num(last.value)} mmol/l ({last.date}), "
                               f"pod referenční mezí {_num(low)}. Vyšetřit SIADH (osmolalita séra a moči, natriurie) a "
                               "upravit před léčbou.", [last.id, first.id], data.guideline({"PLI": "PLI-3.2"})))
    glucose = data.by_loinc("glu")
    steroids = [m for m in data.active_medications()
                if any(fhir_code(m.get("medicationCodeableConcept"), "atc").startswith(p) for p in STEROID_ATC)]
    if glucose and steroids and glucose[-1].value > GLUCOSE_STEROID:
        last = glucose[-1]
        flags.append(_flag("RF-LAB", last.id, "moderate", f"Glykémie {_num(last.value)} mmol/l při kortikoidech",
                           f"Glykémie {_num(last.value)} mmol/l ({last.date}) u pacienta na "
                           f"{cc_text(steroids[0].get('medicationCodeableConcept'))}. Monitorovat glykémii a upravit "
                           f"antidiabetickou léčbu (práh {_num(GLUCOSE_STEROID)} mmol/l je konvence týmu).",
                           [last.id, steroids[0]["id"]], "OBC-3.1"))
    lvef = [o for o in data.observations if "lvef" in o.text.lower() and isinstance(o.value, (int, float))]
    if len(lvef) >= 2:
        last = lvef[-1]
        peak = max(lvef[:-1], key=lambda o: o.value)
        if peak.value - last.value >= LVEF_DROP or last.value < LVEF_LOW:
            flags.append(_flag("RF-LAB", last.id, "moderate",
                               f"LVEF {_num(last.value)} % (pokles o {_num(peak.value - last.value)} bodů)",
                               f"LVEF {_num(peak.value)} % ({peak.date}) → {_num(last.value)} % ({last.date}). "
                               f"Pokles o ≥ {LVEF_DROP} bodů nebo pod {LVEF_LOW} % vyžaduje kardiologické sledování.",
                               [last.id, peak.id], data.guideline({"PRS": "PRS-3.4"})))
    return flags


def weight_change(data: PatientData, window_days: int = WEIGHT_WINDOW_DAYS):
    """(maximum v okně, poslední měření, podíl úbytku) z `vaha` i PROMs `hmotnost`; body = (datum, kg, ID)."""
    points = [(o.date, o.value, o.id) for o in data.by_loinc("weight") if o.date]
    for qr in data.proms:
        weight = data.answers(qr).get("hmotnost")
        if isinstance(weight, (int, float)) and _date(qr.get("authored")):
            points.append((_date(qr["authored"]), weight, qr["id"]))
    if len(points) < 2:
        return None
    points.sort()
    last = points[-1]
    window = [p for p in points[:-1] if (last[0] - p[0]).days <= window_days]
    if not window:
        return None
    peak = max(window, key=lambda p: p[1])
    return peak, last, (peak[1] - last[1]) / peak[1]


def rf_weight(data: PatientData) -> list[RedFlag]:
    change = weight_change(data)
    if change is None:
        return []
    peak, last, loss = change
    if loss < WEIGHT_LOSS:
        return []
    return [_flag("RF-WEIGHT", last[2], "moderate", f"Úbytek hmotnosti {round(loss * 100)} %",
                  f"Hmotnost {_num(peak[1])} kg ({peak[0]}) → {_num(last[1])} kg ({last[0]}), úbytek "
                  f"{_num(loss * 100)} % za {(last[0] - peak[0]).days} dní. Úbytek ≥ 5 % za 6 měsíců je indikací "
                  "k nutričnímu vyšetření.", [last[2], peak[2]], "OBC-2.3")]


def patient_bmi(data: PatientData) -> tuple[float, list[str]] | None:
    """BMI k poslednímu vážení: zapsané BMI (LOINC 39156-5), jinak z poslední změřené výšky (8302-2).
    Bez výšky `None`: BMI se nikdy neodhaduje (T-341)."""
    from services.rules.fact_categories import bmi

    weight = data.by_loinc("weight")
    if not weight:
        return None
    last = weight[-1]
    recorded = data.by_loinc("bmi")
    if recorded and (recorded[-1].date or date.min) >= (last.date or date.min):
        return round(float(recorded[-1].value), 1), [recorded[-1].id]
    heights = data.by_loinc("height")
    if not heights:
        return None
    quantity = heights[-1].resource.get("valueQuantity") or {}
    value = bmi(float(last.value), float(heights[-1].value), quantity.get("unit") or quantity.get("code"))
    return (value, [last.id, heights[-1].id]) if value else None


def rf_bmi(data: PatientData) -> list[RedFlag]:
    """BMI pod hranicí malnutrice GLIM z Modré knihy ČOS (oddíl 31.3): < 20 do 70 let, < 22 od 70 let."""
    from services.rules.fact_categories import BMI_SOURCE, bmi_threshold

    value = patient_bmi(data)
    if value is None or value[0] >= bmi_threshold(data.age):
        return []
    threshold = bmi_threshold(data.age)
    return [_flag("RF-BMI", value[1][0], "moderate", f"BMI {_num(value[0])} pod hranicí malnutrice",
                  f"BMI {_num(value[0])} kg/m² < {_num(threshold)} kg/m² (fenotypické kritérium malnutrice GLIM "
                  f"{'od 70 let' if threshold > 20 else 'do 70 let'}). Indikace k nutričnímu vyšetření.",
                  value[1], BMI_SOURCE)]


def rf_geri(data: PatientData) -> list[RedFlag]:
    if data.age is None or data.age < GERI_AGE or data.any_text(GERI_SCREEN):
        return []
    return [_flag("RF-GERI", data.patient_id, "low", f"Věk {data.age} let bez geriatrického screeningu",
                  f"Pacientovi je {data.age} let a v dokumentaci chybí screening křehkosti (G8).",
                  [data.patient_id, data.request.get("id")], "OBC-2.2")]


def rf_lesion(data: PatientData) -> list[RedFlag]:
    flags = []
    guideline = data.guideline({"PLI": "PLI-1.2"}, "OBC-1.4")
    for c in data.oncologic:
        if fhir_code(c.get("verificationStatus"), "") == "provisional":
            evidence = [o.id for o in data.observations
                        if any(ref_id(f) == c["id"] for f in o.resource.get("focus", []))]
            flags.append(_flag("RF-LESION", c["id"], "high", f"Neověřená diagnóza: {cc_text(c.get('code'))}",
                               f"Diagnóza {fhir_code(c.get('code'), 'icd-10')} je vedená jako provizorní (bez "
                               "histologického ověření). Před zásadní změnou léčby ověřit histologicky včetně "
                               "imunohistochemie.",
                               [c["id"], *evidence, data.request.get("id")], guideline))
    pathology = [r for r in data.by_type.get("DiagnosticReport", [])
                 if fhir_code((r.get("category") or [{}])[0], "v2-0074") == "SP"]
    unclear: dict[tuple, list[tuple[dict, str, str]]] = {}     # orgán → [(zpráva, odstavec, věta)]
    for report in data.radiology():
        paragraph = data.paragraph_with(report["id"], LESION_UNCLEAR)
        if not paragraph:
            continue
        sentences = re.split(r"(?<=[.;])\s", data.paragraph_text(paragraph))
        sentence = next((s for s in sentences if LESION_UNCLEAR.search(s)), "")
        plain = _plain(sentence)
        found = sorted((plain.find(stem), stem) for stem in ORGAN_STEMS if stem in plain)
        organ = found[0][1] if found else None      # orgán zmíněný ve větě jako první
        # Ověřeno = novější histologie, která zmiňuje tentýž orgán
        verified = organ is not None and any(
            r.get("effectiveDateTime", "") > report.get("effectiveDateTime", "")
            and organ in _plain(data.texts.get(r["id"], "")) for r in pathology)
        if not verified:
            unclear.setdefault((organ or paragraph,), []).append((report, paragraph, sentence))
    for findings in unclear.values():     # jedno ložisko popsané víc vyšetřeními = jeden flag
        report, paragraph, sentence = findings[-1]
        earlier = [p for _, p, _ in findings[:-1]]
        flags.append(_flag("RF-LESION", paragraph, "high", "Nejasné ložisko bez histologického ověření",
                           f"Zobrazení {cc_text(report.get('code'))} ({report['effectiveDateTime'][:10]}): "
                           f"„{sentence.strip()}“ Novější histologie tohoto nálezu není; bez ověření nelze stanovit "
                           "stadium.", [paragraph, *earlier, data.request.get("id")], guideline))
    return flags


LYNCH_FAMILY = re.compile(r"tlust\w* střev|kolorekt|rekt|endometri|děloh|žaludk|ovari|vaječník|močov|ledvinn\w* pánvičk",
                          re.IGNORECASE)


def rf_lynch(data: PatientData) -> list[RedFlag]:
    """Kolorektum + karcinom Lynchova spektra v rodině + MMR/MSI nevyšetřeno → genetické poradenství (OBC-2.4, KRC-1.2)."""
    if "KRC" not in data.sets:
        return []
    family = data.find_paragraphs(re.compile(r"^RA:.*(" + LYNCH_FAMILY.pattern + ")", re.I | re.S))
    mmr = [o for o in data.by_category("Biomarker") if re.search(r"MMR|MSI", o.text)
           and isinstance(o.value, str) and MISSING_VALUE.search(o.value)]
    if not family or not mmr:
        return []
    return [_flag("RF-GENETIC", mmr[-1].id, "moderate", "Karcinom Lynchova spektra v rodině, MMR ani genetika neprovedeny",
                  f"Rodinná anamnéza uvádí nádor Lynchova spektra, MMR / MSI je „{mmr[-1].value}“ a genetické "
                  "poradenství neproběhlo.", [family[0], mmr[-1].id], "OBC-2.4")]


def rf_genetic(data: PatientData) -> list[RedFlag]:
    lynch = rf_lynch(data)
    germline = [o for o in data.by_category("Biomarker")
                if re.search(r"germin|zárodeč", o.text, re.I) and isinstance(o.value, str)
                and MISSING_VALUE.search(o.value)]
    if not germline:
        return lynch
    tumor = [o for o in data.by_category("Biomarker")
             if re.search(r"brca", o.text, re.I) and not re.search(r"germin|zárodeč", o.text, re.I)
             and isinstance(o.value, str) and re.search(r"patogen|mutac|variant", o.value, re.I)]
    family = data.find_paragraphs(re.compile(r"^RA:.*(" + GENETIC_FAMILY.pattern + ")", re.I | re.S))
    if not tumor and not family:
        return lynch
    reason = []
    if tumor:
        reason.append(f"patogenní varianta v nádoru ({tumor[-1].text})")
    if family:
        reason.append("rodinná anamnéza karcinomu prsu nebo vaječníků")
    return lynch + [_flag("RF-GENETIC", germline[-1].id, "moderate", "Genetické poradenství neproběhlo",
                  f"Indikace genetického poradenství: {' a '.join(reason)}. "
                  f"Germinální BRCA1/2 je „{germline[-1].value}“.",
                  [germline[-1].id, *(o.id for o in tumor[-1:]), *family[:1]],
                  data.guideline({"PRS": "PRS-1.4"}, "OBC-2.4"))]


def rf_nomination(data: PatientData) -> list[RedFlag]:
    flags = []
    if not data.request:
        return flags
    paragraphs = resource_paragraphs(data.request)
    lvef = [o for o in data.observations if "lvef" in o.text.lower() and isinstance(o.value, (int, float))]
    checks = (("ECOG", r"ECOG\s*(\d)", data.by_loinc("ecog"), ""),
              ("LVEF", r"LVEF\s*(\d+)\s*%", lvef, " %"))
    for label, pattern, series, unit in checks:
        if not series:
            continue
        last = series[-1]
        for p in paragraphs:
            match = re.search(pattern, p.text)
            if match and int(match.group(1)) != int(last.value):
                title = f"Nominace uvádí {label} {match.group(1)}{unit}, poslední měření {_num(last.value)}{unit}"
                flags.append(_flag("RF-NOMINATION", f"{label.lower()}", "moderate", title,
                                   f"Nominace uvádí {label} {match.group(1)}{unit}, poslední strukturovaný údaj je "
                                   f"{_num(last.value)}{unit} ({last.date}).",
                                   [f"{data.request['id']}#{p.index}", last.id], "OBC-1.1"))
                break
    primaries = [c for c in data.oncologic if not re.match(r"C7[789]|C80", fhir_code(c.get("code"), "icd-10"))]
    nominated = {ref_id(r) for r in data.request.get("reasonReference", [])}
    omitted = [c for c in primaries if c["id"] not in nominated]
    if len(primaries) > 1 and omitted:
        flags.append(_flag("RF-NOMINATION", "nadory", "moderate", "Nominace neuvádí všechny nádory",
                           "Při duplicitě malignit má nominace uvést všechny nádory; chybí "
                           + ", ".join(cc_text(c.get("code")) for c in omitted) + ".",
                           [data.request["id"], *(c["id"] for c in omitted)], "OBC-1.4"))
    return flags


def rf_tnm(data: PatientData) -> list[RedFlag]:
    groups: dict[tuple, list[Obs]] = {}
    for o in data.by_category("Staging"):
        focus = tuple(sorted(ref_id(f) for f in o.resource.get("focus", [])))
        groups.setdefault((o.text, focus), []).append(o)
    flags = []
    for (kind, _), series in groups.items():
        stages = {}
        for o in series:
            text = str(o.value or "")
            stage = re.search(r"stadium\s+([IV]+[ABC]?\d?)", text)
            metastatic = bool(re.search(r"\bc?M1", text))
            if stage:
                stages[o.id] = (stage.group(1), metastatic)
        ids = list(stages)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if stages[a][1] == stages[b][1] and stages[a][0] != stages[b][0]:
                    flags.append(_flag("RF-TNM", a, "moderate", f"Rozpor ve stadiu: {stages[a][0]} vs. {stages[b][0]}",
                                       f"{kind}: {a} uvádí stadium {stages[a][0]}, {b} stadium {stages[b][0]}.",
                                       [a, b, data.by_id(a).source, data.by_id(b).source], "OBC-1.1"))
    return flags


def rf_palliative(data: PatientData) -> list[RedFlag]:
    advanced = [c for c in data.oncologic if re.match(r"C7[89]", fhir_code(c.get("code"), "icd-10"))]
    advanced += [] if advanced else [c for c in data.oncologic if re.search(r"\bIV\b|M1", str(c.get("stage", "")))]
    if not advanced or not data.proms or data.any_text(PALLIATIVE_CARE):
        return []
    last = data.answers(data.proms[-1])
    heavy = [f"{label} {_num(last[link])}/10" for link, label in SYMPTOMS.items()
             if isinstance(last.get(link), (int, float)) and last[link] >= SYMPTOM_HIGH]
    physician = data.by_loinc("ecog")
    worse = bool(physician) and physician[-1].value > min(o.value for o in physician)
    patient = str(last.get("samostatnost", ""))
    reasons = heavy + (["zhoršení ECOG podle lékaře"] if worse else []) \
        + ([f"ECOG podle pacienta {patient}"] if patient.isdigit() and int(patient) >= 2 else [])
    if not reasons:
        return []
    return [_flag("RF-PALIATIVE", data.proms[-1]["id"], "moderate", "Zvážit zapojení paliativního týmu",
                  f"Pokročilé onemocnění a {', '.join(reasons)}; zapojení paliativní péče v dokumentaci chybí.",
                  [data.proms[-1]["id"], advanced[0]["id"]], "OBC-2.1")]


def rf_roles(data: PatientData) -> list[RedFlag]:
    if data.roles_present is None:
        return []
    required: dict[str, str] = {}
    question = ((data.request.get("reasonCode") or [{}])[0].get("text") or "").lower()
    codes = {c.get("code") for c in (data.request.get("reasonCode") or [{}])[0].get("coding", [])}
    if "KRC" in data.sets and ("indikace-operace" in codes or "resek" in question):
        required.update({"surgeon": "KRC-2.1", "radiologist": "KRC-2.1"})
    stage_iii = any(re.search(r"stadium\s+III", str(o.value or "")) for o in data.by_category("Staging"))
    if "PLI" in data.sets and stage_iii:
        for role in ("surgeon", "radiation_oncologist", "oncologist", "pulmonologist", "radiologist"):
            required[role] = "PLI-2.1"
    missing = {role: g for role, g in required.items() if role not in data.roles_present}
    if not missing:
        return []
    return [_flag("RF-ROLES", "roles", "moderate", "Chybí odbornost vyžadovaná guidelines",
                  f"Pro tuto otázku guidelines vyžadují přítomnost: {', '.join(sorted(missing))}.",
                  [f"{data.request.get('id')}#1", (data.oncologic or [{}])[0].get("id")],
                  sorted(set(missing.values()))[0])]


def rf_steroid(data: PatientData) -> list[RedFlag]:
    flags = []
    for m in data.active_medications():
        if not any(fhir_code(m.get("medicationCodeableConcept"), "atc").startswith(p) for p in STEROID_ATC):
            continue
        name = cc_text(m.get("medicationCodeableConcept"))
        mentions = data.find_paragraphs(re.compile(re.escape(name[:6]), re.I))
        if any(STEROID_TAPER.search(p_text) for p_text in (data.paragraph_text(p) for p in mentions)):
            continue
        flags.append(_flag("RF-STEROID", m["id"], "low", f"{name[:1].upper()}{name[1:]} bez plánu snižování",
                           f"{name} {(m.get('dosageInstruction') or [{}])[0].get('text', '')} je v medikaci, plán "
                           "postupného snižování dávky v dokumentaci není.",
                           [m["id"], *mentions[-1:]], data.guideline({"PRS": "PRS-3.3"}, "OBC-3.1")))
    return flags


def rf_newsymptom(data: PatientData) -> list[RedFlag]:
    if not data.proms:
        return []
    qr = data.proms[-1]
    complaint = str(data.answers(qr).get("nove-obtize") or "")
    if NOTHING.match(complaint) or not NEW_LOCAL_SYMPTOM.search(complaint):
        return []
    later = [d for d in data.by_type.get("DocumentReference", []) if d.get("date", "") >= qr.get("authored", "")]
    latest_doc = max(later, key=lambda d: d.get("date", ""))["id"] if later else None
    return [_flag("RF-NEWSYMPTOM", qr["id"], "high", "Nový lokalizovaný symptom podle pacienta",
                  f"Pacient uvádí: „{complaint.strip()}“. Nový lokalizovaný symptom vyžaduje cílené zobrazení bez "
                  "ohledu na plánovaný restaging; ověřit, zda na něj dokumentace reaguje.",
                  [qr["id"], latest_doc], data.guideline({"PRS": "PRS-4.2"}, "OBC-1.3"))]


# ── Pravidla z konzultace (T-312) ─────────────────────────────────────────────
SIDE = {"lev": "vlevo", "prav": "vpravo"}
ORGANS = {"prs": r"prsu?", "ledvin": r"ledvin[ayě]?", "plic": r"plíc[eií]|(?:horního|dolního|středního)\s+laloku"}
SIDE_MENTION = r"(?:karcinom|nádor|tumor|ca)\w*\s+(?:\w+\s+){0,2}?(lev|prav)(?:ého|ý|é|á)\s+(?:\w+\s+)?(%s)"
QUADRANT = re.compile(r"(zevní|vnitřní)\w*\s+kvadrant", re.IGNORECASE)
IMPLANT = re.compile(r"port|stent|endoprotéz|kardiostimul|defibrilátor|zkrat|chlopn", re.IGNORECASE)
ALLERGY_NONE = re.compile(r"^\s*(alergie:?\s*)?(neudává|nevím o žádné|žádné|nemá|bez alergií|ne|nic)\.?\s*$",
                          re.IGNORECASE)


def _side(text: str) -> str | None:
    text = text.lower()
    left, right = bool(re.search(r"\blev|vlevo|sin\.", text)), bool(re.search(r"\bprav|vpravo|dx\.", text))
    return "lev" if left and not right else "prav" if right and not left else None


def rf_identity(data: PatientData) -> list[RedFlag]:
    """Dokument nesedí k pacientovi: strana těla, kvadrant, pohlaví (věk a data hlídá RF-LLM a RF-DATAQUALITY)."""
    flags = []
    for c in data.oncologic:
        site = " ".join(cc_text(b) for b in c.get("bodySite", []))
        side = _side(site)
        organ = next((key for key in ORGANS if key in _plain(site)), None)
        if side is None or organ is None:
            continue
        pattern = re.compile(SIDE_MENTION % ORGANS[organ], re.IGNORECASE)
        for evidence_id in data.find_paragraphs(pattern, ("DocumentReference", "DiagnosticReport", "Composition")):
            mentioned = pattern.search(data.paragraph_text(evidence_id)).group(1).lower()
            if mentioned != side:
                flags.append(_flag("RF-IDENTITY", evidence_id, "high", f"Strana těla nesedí: {SIDE[mentioned]} vs. "
                                   f"{SIDE[side]}",
                                   f"Dokument uvádí nádor {SIDE[mentioned]}, diagnóza {fhir_code(c.get('code'), 'icd-10')} "
                                   f"je {SIDE[side]} ({site}). Ověřit, zda dokument patří k pacientovi a k tomuto "
                                   "nádoru.", [evidence_id, c["id"]], None))
        quadrant = QUADRANT.search(site)
        if organ == "prs" and quadrant:
            expected = quadrant.group(1).lower()
            for evidence_id in data.find_paragraphs(QUADRANT, ("DocumentReference", "DiagnosticReport")):
                found = {m.group(1).lower() for m in QUADRANT.finditer(data.paragraph_text(evidence_id))}
                if found and expected not in found:
                    flags.append(_flag("RF-IDENTITY", evidence_id, "high", "Lokalizace v prsu nesedí",
                                       f"Dokument popisuje {', '.join(sorted(found))} kvadrant, diagnóza uvádí {site}.",
                                       [evidence_id, c["id"]], None))
    patient = (data.by_type.get("Patient") or [{}])[0]
    if patient.get("gender") == "male":
        for evidence_id in data.find_paragraphs(re.compile(r"\bpacientk", re.IGNORECASE),
                                                ("DocumentReference", "DiagnosticReport", "Composition")):
            flags.append(_flag("RF-IDENTITY", evidence_id, "high", "Pohlaví v dokumentu nesedí",
                               "Dokument mluví o pacientce, pacient je muž.", [evidence_id, data.patient_id], None))
    return flags


def prior_procedures(data: PatientData) -> dict[str, list[dict]]:
    """Implantáty, předchozí operace a radioterapie z `Procedure` (FR-A4, RF-PRIOR-PROC)."""
    out: dict[str, list[dict]] = {"implant": [], "surgery": [], "radiotherapy": []}
    for p in sorted(data.by_type.get("Procedure", []), key=lambda p: p.get("performedDateTime", "")):
        text, category = cc_text(p.get("code")), cc_text(p.get("category")).lower()
        if IMPLANT.search(text):
            out["implant"].append(p)
        elif "radioterap" in category:
            out["radiotherapy"].append(p)
        elif "chirurg" in category:
            out["surgery"].append(p)
    return out


def allergies(data: PatientData) -> list[tuple[str, str]]:
    """Uvedené alergie: (text, Evidence ID) z PROMs `alergie` a odstavců „Alergie:“."""
    found = []
    for qr in data.proms[-1:]:
        text = str(data.answers(qr).get("alergie") or "")
        if text and not ALLERGY_NONE.match(text):
            found.append((text, qr["id"]))
    for evidence_id in data.find_paragraphs(re.compile(r"Alergi\w*:", re.IGNORECASE)):
        sentence = re.search(r"Alergi\w*:?([^.]*(?:\.[^A-ZÁ-Ž]*)?)", data.paragraph_text(evidence_id))
        text = sentence.group(1).strip() if sentence else ""
        if text and not ALLERGY_NONE.match(text):
            found.append((text, evidence_id))
    return found


def _performed(procedure: dict) -> str:
    return (procedure.get("performedDateTime") or procedure.get("performedPeriod", {}).get("start") or "?")[:10]


def rf_prior_proc(data: PatientData) -> list[RedFlag]:
    procedures = prior_procedures(data)
    allergy = allergies(data)
    parts, citations = [], []
    labels = {"implant": "implantáty", "surgery": "předchozí operace", "radiotherapy": "předchozí radioterapie"}
    for kind, items in procedures.items():
        if items:
            parts.append(f"{labels[kind]}: " + "; ".join(f"{cc_text(p.get('code'))} ({_performed(p)})" for p in items))
            citations += [p["id"] for p in items] + [ref_id(r) for p in items for r in p.get("report", [])]
    if allergy:
        texts = list(dict.fromkeys(text.strip().rstrip(".") for text, _ in allergy))
        parts.append("alergie: " + "; ".join(texts))
        citations += [evidence for _, evidence in allergy]
    if not parts:
        return []
    if len(set(citations)) < 2:
        citations.append(data.patient_id)
    return [_flag("RF-PRIOR-PROC", "info", "low", "Předchozí výkony, implantáty a alergie (info pro chirurga a RT)",
                  "; ".join(parts) + ".", citations, None)]


def rf_dataquality(data: PatientData) -> list[RedFlag]:
    flags = []
    # strukturovaná hodnota bez zdrojového dokumentu (mezera v dohledatelnosti); laboratoř má zdroj v panelu LAB
    no_source = [o for o in data.observations if not derived_from_ids(o.resource)
                 and not any("v2-0074" in c.get("system", "") for cat in o.resource.get("category", [])
                             for c in cat.get("coding", []))
                 and fhir_code(o.resource.get("code"), "loinc.org") not in (LOINC["weight"],)]
    if no_source:
        flags.append(_flag("RF-DATAQUALITY", "bez-zdroje", "low", "Hodnoty bez zdrojového dokumentu",
                           "Bez odkazu na zdrojový dokument (derivedFrom): "
                           + ", ".join(f"{o.text} {o.value if not isinstance(o.value, float) else _num(o.value)} "
                                       f"({o.date})" for o in no_source) + ". Hodnotu nejde dohledat ve zprávě.",
                           [o.id for o in no_source] + ([data.patient_id] if len(no_source) < 2 else []), None))
    units: dict[str, dict[str, str]] = {}
    for o in data.observations:
        quantity = o.resource.get("valueQuantity") or {}
        loinc = fhir_code(o.resource.get("code"), "loinc.org")
        if loinc and quantity.get("code"):
            units.setdefault(loinc, {}).setdefault(quantity["code"], o.id)
    for loinc, by_unit in units.items():
        if len(by_unit) > 1:
            flags.append(_flag("RF-DATAQUALITY", f"jednotky-{loinc}", "low", "Nesoulad jednotek",
                               f"LOINC {loinc} má v datech různé jednotky: {', '.join(by_unit)}.",
                               list(by_unit.values()), None))
    if data.mdt_date:
        late = [r for r in data.resources if r.get("resourceType") not in ("Task", "Patient")
                and (d := _date(r.get("effectiveDateTime") or r.get("date") or r.get("authored")
                                or r.get("performedDateTime"))) and d > data.mdt_date]
        if late:
            flags.append(_flag("RF-DATAQUALITY", "datum", "low", "Datum po termínu MDT",
                               f"Záznamy s datem po zasedání ({data.mdt_date}): {', '.join(r['id'] for r in late)}.",
                               [r["id"] for r in late] + [data.task.get("id")], None))
    seen: dict[tuple, str] = {}
    duplicates = []
    for o in data.observations:
        key = (o.text, o.date, str(o.value))
        if key in seen:
            duplicates.append((seen[key], o.id))
        seen.setdefault(key, o.id)
    if duplicates:
        flags.append(_flag("RF-DATAQUALITY", "duplicity", "low", "Duplicitní záznamy",
                           "Stejný údaj se stejným datem a hodnotou je v datech vícekrát: "
                           + ", ".join(f"{a} = {b}" for a, b in duplicates) + ".",
                           [i for pair in duplicates for i in pair], None))
    return flags


RULES: tuple[Callable[[PatientData], list[RedFlag]], ...] = (
    rf_ecog, rf_proms, rf_tox, rf_stale, rf_missing, rf_med, rf_newsymptom, rf_lab, rf_weight, rf_bmi, rf_geri,
    rf_lesion, rf_genetic, rf_nomination, rf_tnm, rf_palliative, rf_roles, rf_steroid,
    rf_identity, rf_prior_proc, rf_dataquality,
)


# Katalog pravidel pro nastavení podkladu (T-332): předseda je může pro board vypnout (`BriefConfig.disabled_rules`),
# výchozí jsou zapnutá všechna. Hodnota = (název pro lékaře, pasáž guidelines, ze které pravidlo vychází, nebo "").
RULE_CATALOG: dict[str, tuple[str, str]] = {
    "RF-ECOG": ("ECOG lékaře a pacienta se liší", "OBC-1.3"),
    "RF-PROMS": ("Výrazná symptomová zátěž podle pacienta", "OBC-1.3"),
    "RF-TOX": ("Toxicita podle lékaře a pacienta nesedí", "KRC-3.2"),
    "RF-STALE": ("Zastaralý staging nebo restaging", "OBC-1.2"),
    "RF-MISSING": ("Chybí povinný údaj nebo biomarker", "OBC-1.1"),
    "RF-MED": ("Léky mimo záznam a lékové interakce", ""),
    "RF-NEWSYMPTOM": ("Nový symptom bez cíleného vyšetření", "PRS-4.2"),
    "RF-LAB": ("Laboratoř mimo normu a trend markerů", "OBC-3.1"),
    "RF-WEIGHT": ("Úbytek hmotnosti", "OBC-2.3"),
    "RF-BMI": ("Nízké BMI (kritérium malnutrice GLIM, Modrá kniha)", "EXT-MK-31.3-2"),
    "RF-GERI": ("Geriatrický screening u věku od 70 let", "OBC-2.2"),
    "RF-LESION": ("Neověřené ložisko nebo diagnóza", "OBC-1.4"),
    "RF-GENETIC": ("Indikace genetického poradenství", "OBC-2.4"),
    "RF-NOMINATION": ("Nominace neodpovídá dokumentaci", "OBC-1.4"),
    "RF-TNM": ("Rozpor ve stadiu mezi zprávami", ""),
    "RF-PALIATIVE": ("Včasné zapojení paliativního týmu", "OBC-2.1"),
    "RF-ROLES": ("Chybí odbornost vyžadovaná guidelines", "KRC-2.1"),
    "RF-STEROID": ("Kortikoidy bez plánu snižování", "OBC-3.1"),
    "RF-IDENTITY": ("Strana těla, pohlaví nebo lokalizace nesedí", ""),
    "RF-PRIOR-PROC": ("Předchozí výkony, implantáty a alergie (informace)", ""),
    "RF-DATAQUALITY": ("Kvalita dat: jednotky, duplicity, data", ""),
    "RF-LLM": ("Rozpory mezi zdroji nalezené AI", ""),
}


def evaluate(resources: Iterable[dict], roles_present: Iterable[str] | None = None,
             disabled: Iterable[str] = ()) -> list[RedFlag]:
    """Všechna deterministická pravidla kromě vypnutých předsedou; seřazeno podle závažnosti, pak podle pravidla."""
    data = PatientData(resources, roles_present)
    off = set(disabled)
    flags = [flag for rule in RULES for flag in rule(data) if flag.rule not in off]
    return sorted(flags, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.rule, f.id))
