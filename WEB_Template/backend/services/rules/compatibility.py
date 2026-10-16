"""
Semafor souladu léčebných postupů se stavem pacienta (ARCHITEKTURA §5.9, D-015, FR-D4, T-503).

Barvu počítá jen tento kód, LLM ji nikdy nepřiřazuje. Pravidla, prahy, zdroje a katalog postupů
jsou data v `services/rules/data/compatibility_rules.yaml` (env `COMPATIBILITY_RULES_FILE`);
tady jsou jen kontrolní funkce (`check` v YAML).

`evaluate_compatibility(resources)` vrátí pro každý postup ze sady guidelines pacienta
`{id, title, guideline_citations, compatibility: TreatmentCompatibility}` (kontrakt §8.3):

- 🟢 `green` nevylučuje · 🟠 `orange` pozor · 🔴 `red` vylučuje (jen se zdrojem) · ⚪ `grey` nelze
  posoudit · `skipped` lékař údaj přeskočil;
- celková barva = nejhorší z pravidel (red > orange > grey > skipped > green);
- vždy se vrátí všechny postupy, i červené; preference pacienta barvu nemění (štítek).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

import yaml

from services.rules import red_flags as rf
from services.rules.red_flags import PatientData, _cc_text, _code, _date, _num

LIGHT_ORDER = {"red": 0, "orange": 1, "grey": 2, "skipped": 3, "green": 4}
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_RULES_FILE = Path(__file__).parent / "data" / "compatibility_rules.yaml"
TEAM_NOTE = " (práh potvrdil tým, Q-7)"

OXALIPLATIN_IRINOTECAN_ATC = ("L01XA03", "L01CE02")
BEVACIZUMAB_ATC = "L01FG01"
ANTIPLATELET_ATC = ("B01AC",)
MI_ICD = ("I21", "I22", "I25.2")
ARTERIAL_EVENT_ICD = MI_ICD + ("I63", "I64", "I74", "G45")


# ── Katalog ───────────────────────────────────────────────────────────────────
@lru_cache(maxsize=4)
def load_catalog(path: str | None = None) -> dict:
    raw = path or os.environ.get("COMPATIBILITY_RULES_FILE")
    file = Path(raw) if raw else DEFAULT_RULES_FILE
    if not file.is_absolute() and not file.exists():
        file = BACKEND_DIR / file          # ARCHITEKTURA §9: cesta relativně k backendu
    return yaml.safe_load(file.read_text(encoding="utf-8"))


@dataclass
class Result:
    status: str
    text: str
    patient_citations: list[str] = field(default_factory=list)
    derived: dict | None = None
    rule_citation: str | None = None    # jiný zdroj než `source` (např. práh z EXT-…)


# ── Fakta ─────────────────────────────────────────────────────────────────────
class Facts(PatientData):
    """`PatientData` z red flags + odvozené hodnoty pro semafor."""

    def __init__(self, resources: Iterable[dict], comorbidities_confirmed: bool = False):
        super().__init__(resources)
        self.comorbidities_confirmed = comorbidities_confirmed
        self._flags: list[rf.RedFlag] | None = None

    @property
    def flags(self) -> list[rf.RedFlag]:
        if self._flags is None:
            self._flags = rf.evaluate(self.resources)
        return self._flags

    def latest(self, key: str) -> rf.Obs | None:
        series = self.by_loinc(key)
        return series[-1] if series else None

    def biomarker(self, pattern: str) -> rf.Obs | None:
        matches = [o for o in self.by_category("Biomarker") if re.search(pattern, o.text, re.IGNORECASE)]
        return matches[-1] if matches else None

    def administrations(self, atc_prefixes: tuple[str, ...]) -> list[dict]:
        items = [m for m in self.by_type.get("MedicationAdministration", [])
                 if _code(m.get("medicationCodeableConcept"), "atc").startswith(atc_prefixes)]
        return sorted(items, key=lambda m: m.get("effectiveDateTime", ""))

    def conditions_icd(self, prefixes: tuple[str, ...]) -> list[dict]:
        return [c for c in self.conditions if _code(c.get("code"), "icd-10").startswith(prefixes)]

    def weight(self) -> tuple[float, str] | None:
        series = self.by_loinc("weight")
        if series:
            return series[-1].value, series[-1].id
        for qr in reversed(self.proms):
            value = self.answers(qr).get("hmotnost")
            if isinstance(value, (int, float)):
                return value, qr["id"]
        return None

    def crcl(self) -> tuple[float, dict] | None:
        """Cockcroft-Gault (ml/min) s kreatininem v µmol/l; vrací hodnotu a `derived` pro kontrakt."""
        creatinine, weight = self.latest("krea"), self.weight()
        patient = (self.by_type.get("Patient") or [{}])[0]
        sex = patient.get("gender")
        if creatinine is None or weight is None or self.age is None or sex not in ("male", "female"):
            return None
        factor = 1.23 if sex == "male" else 1.04
        value = (140 - self.age) * weight[0] * factor / creatinine.value
        formula = (f"CrCl = (140 − věk {self.age}) × hmotnost {_num(weight[0])} kg × {str(factor).replace('.', ',')} "
                   f"/ kreatinin {_num(creatinine.value)} µmol/l (Cockcroft-Gault)")
        return value, {"formula": formula, "inputs": [self.patient_id, weight[1], creatinine.id]}

    def neuropathy(self) -> tuple[rf.Obs, int] | None:
        neuro = [o for o in self.by_category("Toxicita") if "neuropat" in o.text.lower() and isinstance(o.value, str)]
        if not neuro:
            return None
        grade = re.search(r"grade\s*(\d)", neuro[-1].value, re.IGNORECASE)
        return (neuro[-1], int(grade.group(1))) if grade else None

    def text_value(self, pattern: re.Pattern, types: tuple[str, ...] = ("DiagnosticReport", "DocumentReference")):
        """Poslední odstavec s hodnotou podle vzoru: (číslo, Evidence ID odstavce)."""
        for evidence_id in reversed(self.find_paragraphs(pattern, types)):
            match = pattern.search(self.paragraph_text(evidence_id))
            number = next((g for g in match.groups() if g), None) if match else None
            if number:
                return float(number.replace(",", ".")), evidence_id
        return None


# ── Kontroly (jméno = `check` v YAML) ─────────────────────────────────────────
def ecog_physician(f: Facts, rule: dict) -> Result:
    last = f.latest("ecog")
    if last is None:
        return Result("grey", "ECOG lékaře v podkladech není")
    if last.value <= rule["green_max"]:
        return Result("green", f"ECOG {last.value} ({last.date})", [last.id])
    if last.value <= rule["orange_max"]:
        return Result("orange", f"ECOG {last.value} ({last.date}): hraniční výkonnost pro intenzivní léčbu", [last.id])
    return Result("red", f"ECOG {last.value} ({last.date}): kritéria intenzivní léčby vyžadují ECOG 0–1", [last.id])


def ecog_difference(f: Facts, rule: dict) -> Result:
    last = f.latest("ecog")
    qr = next((q for q in reversed(f.proms) if str(f.answers(q).get("samostatnost", "")).isdigit()), None)
    if last is None or qr is None:
        return Result("grey", "ECOG lékaře nebo pacienta chybí", [x for x in (last and last.id, qr and qr["id"]) if x])
    patient = int(f.answers(qr)["samostatnost"])
    if patient == last.value:
        return Result("green", f"ECOG lékař {last.value} = pacient {patient}", [last.id, qr["id"]])
    return Result("orange", f"ECOG lékař {last.value} vs. pacient {patient} → výslovně zmínit na MDT",
                  [last.id, qr["id"]])


G8_VALUE = re.compile(r"\bG8\D{0,15}(\d{1,2})")


def g8(f: Facts, rule: dict) -> Result | None:
    if f.age is None or f.age < rule["min_age"]:
        return None                                   # pravidlo platí od 70 let
    found = f.text_value(G8_VALUE, ("DocumentReference", "DiagnosticReport", "Composition"))
    if found is None:
        return Result("grey", f"G8 chybí (věk {f.age} let)", [f.patient_id])
    value, evidence = found
    threshold = rule.get("threshold_source")
    if value <= rule["g8_threshold"]:
        return Result("orange", f"G8 {_num(value)} ≤ {rule['g8_threshold']} → komplexní geriatrické hodnocení",
                      [evidence], rule_citation=threshold)
    return Result("green", f"G8 {_num(value)}", [evidence], rule_citation=threshold)


def weight_loss(f: Facts, rule: dict) -> Result:
    change = rf.weight_change(f, rule["window_days"])
    if change is None:
        return Result("grey", "Trend hmotnosti za 6 měsíců v podkladech není")
    peak, last, loss = change
    derived = {"formula": f"({_num(peak[1])} − {_num(last[1])}) / {_num(peak[1])} kg = {_num(round(loss * 100, 1))} %",
               "inputs": [peak[2], last[2]]}
    percent = _num(round(loss * 100, 1))
    text = f"Hmotnost {_num(peak[1])} → {_num(last[1])} kg ({peak[0]} → {last[0]}), úbytek {percent} %"
    if loss >= rule["loss_orange"]:
        return Result("orange", f"{text} → nutriční vyšetření", [last[2], peak[2]], derived)
    return Result("green", text, [last[2], peak[2]], derived)


def blood_counts(f: Facts, rule: dict) -> Result:
    checks = (("neu", "neutrofily", rule["neu_min"]), ("plt", "trombocyty", rule["plt_min"]),
              ("hb", "Hb", rule["hb_min"]))
    values = [(label, f.latest(key), minimum) for key, label, minimum in checks]
    present = [(label, obs, minimum) for label, obs, minimum in values if obs is not None]
    if not present:
        return Result("grey", "Krevní obraz v podkladech není")
    low = [f"{label} {_num(obs.value)} < {_num(minimum)}" for label, obs, minimum in present if obs.value < minimum]
    citations = [obs.id for _, obs, _ in present]
    if low:
        return Result("orange", ", ".join(low) + " → posoudit před myelotoxickou léčbou", citations)
    return Result("green", ", ".join(f"{label} {_num(obs.value)}" for label, obs, _ in present), citations)


def bilirubin(f: Facts, rule: dict) -> Result:
    last = f.latest("bili")
    if last is None:
        return Result("grey", "Bilirubin v podkladech není")
    uln = (last.resource.get("referenceRange") or [{}])[0].get("high", {}).get("value")
    if uln is None:
        return Result("grey", f"Bilirubin {_num(last.value)} bez referenční meze", [last.id])
    limit = uln * rule["uln_factor"]
    if last.value > limit:
        return Result("orange", f"Bilirubin {_num(last.value)} > {_num(rule['uln_factor'])}× ULN ({_num(limit)}) "
                                "→ úprava léčby; u studie RKT-01 vyřazení", [last.id])
    return Result("green", f"Bilirubin {_num(last.value)} µmol/l (≤ {_num(rule['uln_factor'])}× ULN)", [last.id])


def staging_age(f: Facts, rule: dict) -> Result:
    reports = f.radiology()
    if not reports or not f.mdt_date:
        return Result("grey", "Zobrazení nebo datum MDT chybí")
    last = reports[-1]
    age = f.days_before_mdt(_date(last.get("effectiveDateTime")))
    text = f"Poslední zobrazení {last['effectiveDateTime'][:10]}, {age} dní před MDT"
    if age is not None and age > rule["max_days"]:
        return Result("orange", f"{text} (> {rule['max_days']} dní)", [last["id"], f.task.get("id")])
    return Result("green", text, [last["id"], f.task.get("id")])


def unclear_lesion(f: Facts, rule: dict) -> Result:
    lesions = [flag for flag in f.flags if flag.rule == "RF-LESION"]
    if lesions:
        citations = [c for flag in lesions for c in flag.citations if c != f.request.get("id")]
        return Result("orange", "; ".join(flag.title for flag in lesions) + " → nutné ověřit", citations)
    reports = f.radiology()
    return Result("green", "Nejasné ložisko ani neověřený nádor v podkladech nejsou",
                  [reports[-1]["id"]] if reports else [])


def cyp3a_interaction(f: Facts, rule: dict) -> Result:
    interactions = [flag for flag in f.flags if flag.id.startswith("RF-MED:interakce")]
    if interactions:
        return Result("orange", "; ".join(flag.title for flag in interactions) + " → vyřešit",
                      list(interactions[0].citations))
    if not f.proms:
        return Result("grey", "Dotazník s léky mimo medikaci chybí")
    qr = f.proms[-1]
    extra = str(f.answers(qr).get("leky-mimo") or "nic")
    return Result("green", f"Známá interakce CYP3A není (léky navíc: {extra})", [qr["id"]])


def cardiac_events(f: Facts, rule: dict) -> Result:
    events = []
    for c in f.conditions_icd(MI_ICD):
        onset = c.get("onsetDateTime", "")
        events.append(("IM", _date(onset if len(onset) >= 10 else f"{onset[:7]}-01" if onset else None), c["id"]))
    for p in f.by_type.get("Procedure", []):
        if "stent" in _cc_text(p.get("code")).lower():
            events.append(("stent", _date(p.get("performedDateTime")), p["id"]))
    antiplatelet = [m for m in f.active_medications()
                    if _code(m.get("medicationCodeableConcept"), "atc").startswith(ANTIPLATELET_ATC)]
    info = (f"; užívá {_cc_text(antiplatelet[0].get('medicationCodeableConcept'))} → info pro operatéra"
            if antiplatelet else "")
    citations = [e[2] for e in events] + [m["id"] for m in antiplatelet]
    if not events:
        if f.comorbidities_confirmed:
            return Result("green", "IM ani koronární stent v anamnéze nejsou (seznam komorbidit potvrzen)" + info,
                          citations)
        return Result("grey", "IM ani stent v dokumentaci nejsou, úplnost komorbidit lékař nepotvrdil" + info,
                      citations)
    recent_mi = [e for e in events if e[0] == "IM" and e[1] and f.days_before_mdt(e[1]) is not None
                 and f.days_before_mdt(e[1]) <= rule["mi_days"]]
    recent_stent = [e for e in events if e[0] == "stent" and e[1] and f.days_before_mdt(e[1]) is not None
                    and f.days_before_mdt(e[1]) <= rule["stent_days"]]
    described = ", ".join(f"{kind} {d.year if d else '?'}" for kind, d, _ in events)
    if recent_mi:
        return Result("red", f"IM {recent_mi[0][1]} (≤ {rule['mi_days']} dní před MDT) → odložit elektivní "
                             "operaci" + info, citations)
    if recent_stent:
        return Result("orange", f"Lékový stent {recent_stent[0][1]} (≤ 6 měsíců) → kardiologické posouzení" + info,
                      citations)
    return Result("green", f"{described}: > {rule['mi_days']} dní po IM a > 6 měsíců po stentu" + info, citations)


def smoking(f: Facts, rule: dict) -> Result:
    obs = next((o for o in reversed(f.by_category("Rizikové")) if "kouř" in o.text.lower()), None)
    if obs is None:
        return Result("grey", "Kuřácký status v podkladech není")
    value = str(obs.value or "")
    active = re.search(r"aktivní|kouří|kuřák", value, re.IGNORECASE)
    if active and not re.search(r"bývalý|nekuřák|exkuřák", value, re.IGNORECASE):
        return Result("orange", f"{value} → odvykání nejméně 4 týdny před operací", [obs.id])
    return Result("green", value, [obs.id])


def bevacizumab_interval(f: Facts, rule: dict) -> Result | None:
    doses = f.administrations((BEVACIZUMAB_ATC,))
    if not doses:
        return None                                   # bez bevacizumabu pravidlo neplatí
    last = doses[-1]
    given = _date(last.get("effectiveDateTime"))
    days = f.days_before_mdt(given)
    if days is None:
        return Result("grey", f"Poslední bevacizumab {given}, datum MDT chybí", [last["id"]])
    earliest = given + timedelta(days=rule["min_days"])
    derived = {"formula": f"datum MDT {f.mdt_date} − poslední dávka {given} = {days} dní",
               "inputs": [last["id"], f.task.get("id")]}
    text = f"Poslední bevacizumab {given}, k MDT {days} dní; operace nejdříve {earliest}"
    if days >= rule["min_days"]:
        return Result("green", f"{text} (≥ 6 týdnů)", [last["id"], f.task.get("id")], derived)
    return Result("red", f"{text} (< 6 týdnů)", [last["id"], f.task.get("id")], derived)


FLR_VALUE = re.compile(r"FLR\D{0,20}(\d+(?:[,.]\d+)?)\s*%|(\d+(?:[,.]\d+)?)\s*%\s*celkového objemu jater",
                       re.IGNORECASE)


def flr(f: Facts, rule: dict) -> Result:
    found = f.text_value(FLR_VALUE, ("DiagnosticReport",))
    if found is None:
        return Result("grey", "FLR (budoucí jaterní remnant) v podkladech není")
    value, evidence = found
    cycles = f.administrations(OXALIPLATIN_IRINOTECAN_ATC)
    intensive = len(cycles) >= rule["intensive_cycles"]
    minimum = rule["flr_min_after_chemo"] if intensive else rule["flr_min"]
    context = f" po intenzivní chemoterapii ({len(cycles)} podání)" if intensive else ""
    citations = [evidence] + ([cycles[-1]["id"]] if intensive else [])
    if value < rule["flr_min"]:
        return Result("red", f"FLR {_num(value)} % < {rule['flr_min']} % (KRC-2.1, RKT-03/V4)", citations)
    if value < minimum:
        return Result("orange", f"FLR {_num(value)} % < {minimum} %{context} → posoudí HPB chirurg, zvážit dvoudobý "
                                "postup (KRC-2.5)", citations)
    return Result("green", f"FLR {_num(value)} % (≥ {minimum} %{context})", citations)


def liver_restaging(f: Facts, rule: dict) -> Result:
    reports = f.radiology()
    parts = {"CT hrudníku": [r for r in reports if "hrudník" in _cc_text(r.get("code")).lower()],
             "MR jater": [r for r in reports if "mr jater" in _cc_text(r.get("code")).lower()]}
    missing, citations, present = [], [], []
    for label, items in parts.items():
        if not items:
            missing.append(f"{label} chybí")
            continue
        last = items[-1]
        age = f.days_before_mdt(_date(last.get("effectiveDateTime")))
        citations.append(last["id"])
        if age is not None and age > rule["max_days"]:
            missing.append(f"{label} z {last['effectiveDateTime'][:10]} ({age} dní)")
        else:
            present.append(f"{label} {last['effectiveDateTime'][:10]}")
    if missing:
        not_requested = re.compile("hrudník nebyl", re.IGNORECASE)
        note = next((p for r in reversed(reports) if (p := f.paragraph_with(r["id"], not_requested))), None)
        return Result("orange", "Restaging neúplný: " + ", ".join(missing) + " (limit 4–6 týdnů)",
                      ([note] if note else []) + citations)
    return Result("green", "Restaging kompletní: " + ", ".join(present), citations)


LIVER_FEATURES = (
    ("postižení obou laloků", re.compile(r"obou\s+lalok|oba\s+laloky|bilobár", re.IGNORECASE)),
    ("vymizelé ložisko (plánovat podle původní lokalizace)", re.compile(r"vymizel|disappearing", re.IGNORECASE)),
    ("kontakt s jaterní žílou", re.compile(r"(naléhá|kontakt)\w*[^.]{0,40}jatern\w* žíl", re.IGNORECASE)),
)


def liver_extent(f: Facts, rule: dict) -> Result:
    liver = [r for r in f.radiology() if re.search(r"jater|játr", _cc_text(r.get("code")), re.IGNORECASE)]
    if not liver:
        return Result("grey", "Zobrazení jater v podkladech není")
    last = liver[-1]
    found = [(label, p) for label, pattern in LIVER_FEATURES if (p := f.paragraph_with(last["id"], pattern))]
    if found:
        return Result("orange", ", ".join(label for label, _ in found), list(dict.fromkeys(p for _, p in found)))
    return Result("green", "Postižení jednoho laloku bez kontaktu s cévami", [last["id"]])


def neuropathy_oxaliplatin(f: Facts, rule: dict) -> Result:
    found = f.neuropathy()
    if found is None:
        return Result("grey", "Neuropatie podle lékaře v podkladech není")
    obs, grade = found
    if grade >= 2:
        return Result("red", f"Neuropatie G{grade} podle lékaře ({obs.date}) → vysadit nebo přerušit oxaliplatinu",
                      [obs.id])
    tox = [flag for flag in f.flags if flag.rule == "RF-TOX"]
    if tox:
        return Result("orange", f"Lékař G{grade}, pacient popisuje omezení instrumentálních činností → odpovídá G2",
                      list(tox[0].citations))
    return Result("green", f"Neuropatie G{grade} bez omezení podle pacienta", [obs.id])


def _mutation_state(value: str) -> str:
    text = value.lower()
    if re.search(r"nevyšetřen|probíhá|nedostupn|čeká", text):
        return "unknown"
    if re.search(r"wild|bez mutace|bez patogenní|neprokázán|negativ", text):
        return "negative"
    if re.search(r"mutace|mutovan|g12|g13|q61|p\.\(|exon|pozitiv|přestavb|fúze", text):
        return "positive"
    return "unknown"


def ras_status(f: Facts, rule: dict) -> Result:
    genes = {name: f.biomarker(rf"^{name}\b") for name in ("KRAS", "NRAS")}
    states = {name: _mutation_state(str(obs.value)) if obs else "unknown" for name, obs in genes.items()}
    citations = [obs.id for obs in genes.values() if obs]
    mutated = [name for name, state in states.items() if state == "positive"]
    if mutated:
        values = "; ".join(f"{name} {genes[name].value}" for name in mutated)
        return Result("red", f"{values} → anti-EGFR není u RAS-mutovaného nádoru indikováno", citations)
    if all(state == "negative" for state in states.values()):
        return Result("green", "KRAS i NRAS wild-type", citations)
    return Result("orange", "Stav RAS není kompletně známý → doplnit", citations)


def mmr_status(f: Facts, rule: dict) -> Result:
    obs = f.biomarker(r"MMR|MSI")
    if obs is None:
        return Result("grey", "MMR/MSI v podkladech není")
    value = str(obs.value)
    if re.search(r"dMMR|MSI-H|deficit", value, re.IGNORECASE):
        return Result("green", f"{value} → imunoterapie v 1. linii preferována", [obs.id])
    if re.search(r"nevyšetřen|probíhá", value, re.IGNORECASE):
        return Result("grey", f"MMR/MSI {value}", [obs.id])
    return Result("grey", f"{value}: pro pMMR/MSS podklady imunoterapii neřeší", [obs.id])


def bevacizumab_safety(f: Facts, rule: dict) -> Result:
    uncontrolled = f.find_paragraphs(re.compile(r"nekontrolovan\w* hypertenz|hypertenz\w*[^.]{0,20}nekompenzovan"
                                                r"|nekompenzovan\w* hypertenz", re.IGNORECASE))
    if uncontrolled:
        return Result("red", "Nekontrolovaná hypertenze → bevacizumab nezahajovat", uncontrolled[-1:])
    events = f.conditions_icd(ARTERIAL_EVENT_ICD)
    stents = [p for p in f.by_type.get("Procedure", []) if "stent" in _cc_text(p.get("code")).lower()]
    controlled = f.find_paragraphs(re.compile(r"hypertenz\w*\s+kompenzovan", re.IGNORECASE))
    if events or stents:
        described = ", ".join(_cc_text(c.get("code")) for c in events) or "koronární stent"
        return Result("orange", f"Arteriální tromboembolie v anamnéze ({described}) → opatrnost",
                      [c["id"] for c in events] + [p["id"] for p in stents] + controlled[-1:])
    if controlled:
        return Result("green", "Hypertenze kompenzovaná, arteriální tromboembolie v anamnéze není", controlled[-1:])
    return Result("grey", "Krevní tlak a proteinurie v podkladech nejsou")


def dpd(f: Facts, rule: dict) -> Result:
    obs = f.biomarker(r"DPD|DPYD")
    mentions = f.find_paragraphs(re.compile(r"\bDPD\b|DPYD", re.IGNORECASE))
    if obs is None and not mentions:
        return Result("grey", "Deficit DPD v podkladech není vyšetřen")
    value = str(obs.value) if obs else f.paragraph_text(mentions[-1])
    citations = [obs.id] if obs else mentions[-1:]
    if re.search(r"úplný deficit", value, re.IGNORECASE):
        return Result("red", "Úplný deficit DPD → fluoropyrimidiny nepodávat", citations)
    if re.search(r"částečný deficit|heterozyg", value, re.IGNORECASE):
        return Result("orange", "Částečný deficit DPD → snížit úvodní dávku", citations)
    if re.search(r"normální|bez deficitu|wild", value, re.IGNORECASE):
        return Result("green", "Aktivita DPD normální", citations)
    return Result("grey", "Výsledek DPD nejde jednoznačně vyhodnotit", citations)


def conversion_cycles(f: Facts, rule: dict) -> Result | None:
    cycles = f.administrations(OXALIPLATIN_IRINOTECAN_ATC)
    if not cycles:
        return None
    vanished = next((p for r in reversed(f.radiology()) if (p := f.paragraph_with(r["id"], LIVER_FEATURES[1][1]))),
                    None)
    text = f"{len(cycles)} podání (poslední {cycles[-1]['effectiveDateTime'][:10]})"
    if len(cycles) >= rule["cycles_orange"]:
        extra = ", vymizelé ložisko" if vanished else ""
        return Result("orange", f"{text}{extra} → po dosažení resekability neprodlužovat (hepatotoxicita, "
                                "riziko vymizení ložisek)", [cycles[-1]["id"]] + ([vanished] if vanished else []))
    return Result("green", f"{text}: restaging po 4–8 cyklech", [cycles[-1]["id"]])


PERCENT = re.compile(r"(\d+(?:[,.]\d+)?)\s*%")


def _percent(obs: rf.Obs | None) -> float | None:
    match = PERCENT.search(str(obs.value)) if obs else None
    return float(match.group(1).replace(",", ".")) if match else None


def ppo_lung_function(f: Facts, rule: dict) -> Result:
    values = {label: _latest_category(f, "plic", pattern) for label, pattern in
              (("ppoFEV1", r"ppoFEV1"), ("ppoDLCO", r"ppoDLCO"))}
    measured = {label: (obs, _percent(obs)) for label, obs in values.items() if obs and _percent(obs) is not None}
    if not measured:
        return Result("grey", "ppoFEV1 a ppoDLCO v podkladech nejsou")
    citations = [obs.id for obs, _ in measured.values()]
    text = ", ".join(f"{label} {_num(value)} %" for label, (_, value) in measured.items())
    lowest = min(value for _, value in measured.values())
    if lowest < rule["ppo_high_risk"]:
        return Result("red", f"{text} < {rule['ppo_high_risk']} % → vysoké riziko resekce", citations)
    if lowest < rule["ppo_min"]:
        return Result("orange", f"{text} < {rule['ppo_min']} % → zátěžový test", citations)
    if len(measured) < 2:
        return Result("grey", f"{text}; druhá hodnota chybí", citations)
    return Result("green", f"{text} (≥ {rule['ppo_min']} %)", citations)


def _latest_category(f: Facts, category: str, pattern: str) -> rf.Obs | None:
    matches = [o for o in f.by_category(category) if re.search(pattern, o.text, re.IGNORECASE)]
    return matches[-1] if matches else None


VO2_VALUE = re.compile(r"VO2\s?max\D{0,20}(\d+(?:[,.]\d+)?)\s*ml|(\d+(?:[,.]\d+)?)\s*ml/kg/min", re.IGNORECASE)


def vo2max(f: Facts, rule: dict) -> Result:
    found = f.text_value(VO2_VALUE)
    if found is None:
        mention = f.find_paragraphs(re.compile(r"spiroergometri|VO2", re.IGNORECASE))
        return Result("grey", "VO2max v podkladech není (spiroergometrie neprovedena)", mention[-1:])
    value, evidence = found
    text = f"VO2max {_num(value)} ml/kg/min"
    if value < rule["vo2_red"]:
        return Result("red", f"{text} < {rule['vo2_red']} → vysoké riziko resekce", [evidence])
    if value <= rule["vo2_green"]:
        return Result("orange", f"{text} (10–20) → zvýšené riziko", [evidence])
    return Result("green", text, [evidence])


def dyspnea_walking(f: Facts, rule: dict) -> Result:
    if not f.proms:
        return Result("grey", "Dotazník pacienta chybí")
    qr = f.proms[-1]
    answers = f.answers(qr)
    dyspnea, walking = answers.get("dusnost"), answers.get("chuze")
    problems = []
    if isinstance(dyspnea, (int, float)) and dyspnea >= rule["dyspnea_orange"]:
        problems.append(f"dušnost {_num(dyspnea)}/10")
    if walking in rule["walking_limited"]:
        problems.append(f"chůze: {walking}")
    if problems:
        return Result("orange", ", ".join(problems) + " → zohlednit při hodnocení operability", [qr["id"]])
    return Result("green", f"dušnost {_num(dyspnea) if dyspnea is not None else '?'}/10, chůze: {walking}", [qr["id"]])


def lung_staging(f: Facts, rule: dict) -> Result:
    brain = [r for r in f.radiology() if "mr mozku" in _cc_text(r.get("code")).lower()]
    ebus = f.find_paragraphs(re.compile(r"EBUS", re.IGNORECASE), ("DiagnosticReport", "DocumentReference"))
    missing = (["MR mozku"] if not brain else []) + (["invazivní staging mediastina"] if not ebus else [])
    citations = ([brain[-1]["id"]] if brain else []) + ebus[-1:]
    if missing:
        return Result("orange", "Chybí: " + ", ".join(missing), citations)
    return Result("green", "MR mozku i invazivní staging mediastina provedeny", citations)


def egfr_alk(f: Facts, rule: dict) -> Result:
    markers = {name: f.biomarker(rf"^{name}\b") for name in ("EGFR", "ALK")}
    states = {name: _mutation_state(str(obs.value)) if obs else "unknown" for name, obs in markers.items()}
    citations = [obs.id for obs in markers.values() if obs]
    positive = [name for name, state in states.items() if state == "positive"]
    if positive:
        return Result("red", f"{', '.join(positive)} pozitivní → imunoterapie bez přínosu (PLI-2.3)", citations)
    unknown = [f"{name} {markers[name].value if markers[name] else 'chybí'}" for name, s in states.items()
               if s == "unknown"]
    if unknown:
        return Result("orange", "; ".join(unknown) + " → doplnit před imunoterapií", citations)
    return Result("green", "EGFR i ALK negativní", citations)


def pdl1(f: Facts, rule: dict) -> Result:
    obs = f.biomarker(r"PD-?L1")
    tps = re.search(r"TPS\D{0,5}(\d+(?:[,.]\d+)?)\s*%", str(obs.value)) if obs else None
    if tps is None:
        return Result("orange", "PD-L1 TPS neznámé → doplnit", [obs.id] if obs else [])
    value = float(tps.group(1).replace(",", "."))
    if value < rule["tps_min"]:
        return Result("red", f"PD-L1 TPS {_num(value)} % < {rule['tps_min']} % → durvalumab se nepodává", [obs.id])
    return Result("green", f"PD-L1 TPS {_num(value)} %", [obs.id])


def sodium(f: Facts, rule: dict) -> Result:
    series = f.by_loinc("na")
    if not series:
        return Result("grey", "Sodík v podkladech není")
    last = series[-1]
    low = (last.resource.get("referenceRange") or [{}])[0].get("low", {}).get("value")
    if low is not None and last.value < low:
        trend = f" (dříve {_num(series[0].value)}, {series[0].date})" if len(series) > 1 else ""
        return Result("orange", f"Na {_num(last.value)} mmol/l < {_num(low)}{trend} → vyšetřit SIADH a upravit před "
                                "léčbou", [last.id] + ([series[0].id] if len(series) > 1 else []))
    return Result("green", f"Na {_num(last.value)} mmol/l", [last.id])


def no_threshold(f: Facts, rule: dict) -> Result:
    return Result("grey", rule.get("text", "Práh v podkladech není"))


def cisplatin_fitness(f: Facts, rule: dict) -> Result:
    crcl = f.crcl()
    if crcl is None:
        return Result("grey", "CrCl nejde spočítat (chybí kreatinin, hmotnost nebo věk)")
    value, derived = crcl
    problems = [f"CrCl ≈ {round(value)} ml/min < {rule['crcl_min']}"] if value < rule["crcl_min"] else []
    neuro = f.neuropathy()
    if neuro and neuro[1] >= 2:
        problems.append(f"neuropatie G{neuro[1]}")
    ecog = f.latest("ecog")
    if ecog and ecog.value >= 2:
        problems.append(f"ECOG {ecog.value}")
    citations = list(derived["inputs"]) + ([neuro[0].id] if neuro and neuro[1] >= 2 else [])
    if problems:
        return Result("orange", ", ".join(problems) + " → zvážit karboplatinu", citations, derived)
    return Result("green", f"CrCl ≈ {round(value)} ml/min, bez neuropatie ≥ G2 a ECOG < 2", citations, derived)


def steroid_glucose(f: Facts, rule: dict) -> Result | None:
    steroids = [m for m in f.active_medications()
                if _code(m.get("medicationCodeableConcept"), "atc").startswith(rf.STEROID_ATC)]
    if not steroids:
        return None                                   # bez systémového kortikoidu pravidlo neplatí
    name = _cc_text(steroids[0].get("medicationCodeableConcept"))
    glucose = f.latest("glu")
    if glucose is None:
        return Result("grey", f"{name}: glykémie v podkladech není", [steroids[0]["id"]])
    citations = [glucose.id, steroids[0]["id"]]
    if glucose.value > rule["glucose_max"]:
        return Result("orange", f"Glykémie {_num(glucose.value)} mmol/l > {rule['glucose_max']} při {name} → "
                                "monitorovat, upravit antidiabetickou léčbu", citations)
    return Result("green", f"Glykémie {_num(glucose.value)} mmol/l při {name}", citations)


def lvef_anti_her2(f: Facts, rule: dict) -> Result:
    series = [o for o in f.observations if "lvef" in o.text.lower() and isinstance(o.value, (int, float))]
    if not series:
        return Result("grey", "LVEF v podkladech není")
    last = series[-1]
    peak = max(series, key=lambda o: o.value)
    drop = peak.value - last.value
    age = f.days_before_mdt(last.date)
    citations = [last.id] + ([peak.id] if peak.id != last.id else [])
    text = f"LVEF {_num(peak.value)} → {_num(last.value)} % (pokles {_num(drop)} bodů)"
    if drop >= rule["drop_orange"] and last.value < rule["lvef_min"]:
        return Result("red", f"{text}, pod {rule['lvef_min']} % → přerušit anti-HER2 léčbu", citations)
    if drop >= rule["drop_orange"]:
        return Result("orange", f"{text}, LVEF ≥ {rule['lvef_min']} % → častější kontroly", citations)
    if age is not None and age > rule["max_age_days"]:
        return Result("orange", f"Poslední echo {last.date} ({age} dní) je starší než 3 měsíce", citations)
    return Result("green", f"LVEF {_num(last.value)} % ({last.date})", citations)


ILD_PATTERN = re.compile(r"\bILD\b|intersticiáln\w* plicn|pneumonitid(?!y\b)", re.IGNORECASE)


def ild_history(f: Facts, rule: dict) -> Result:
    conditions = f.conditions_icd(("J84", "J70"))
    mentions = [p for p in f.find_paragraphs(ILD_PATTERN, ("DocumentReference", "DiagnosticReport"))
                if not re.search(r"bez (známek )?pneumonitid", f.paragraph_text(p), re.IGNORECASE)]
    if conditions or mentions:
        return Result("orange", "ILD nebo pneumonitida v anamnéze → zhodnotit riziko před T-DXd",
                      [c["id"] for c in conditions] + mentions[-1:])
    if f.comorbidities_confirmed:
        return Result("green", "ILD ani pneumonitida v anamnéze nejsou (seznam komorbidit potvrzen)")
    return Result("grey", "ILD v dokumentaci není, úplnost komorbidit lékař nepotvrdil")


def _her2_samples(f: Facts) -> list[tuple[rf.Obs, str]]:
    out = []
    for o in f.by_category("Biomarker"):
        if "her2" not in o.text.lower() or not isinstance(o.value, str):
            continue
        value = o.value.lower()
        if re.search(r"nevyšetřen|probíhá", value):
            continue
        if re.search(r"3\+|pozitiv", value):
            out.append((o, "positive"))
        elif re.search(r"[12]\+|low", value):
            out.append((o, "low"))
        elif re.search(r"(?<![\d+])0(?![\d,%])|negativ", value):
            out.append((o, "zero"))
    return out


def her2_tdxd(f: Facts, rule: dict) -> Result:
    samples = _her2_samples(f)
    if not samples:
        return Result("grey", "HER2 v podkladech není")
    citations = [o.id for o, _ in samples]
    states = {state for _, state in samples}
    described = "; ".join(f"{o.text}: {o.value}" for o, _ in samples)
    if "positive" in states:
        return Result("green", f"HER2 pozitivní ({described}) → T-DXd ve 2. linii (PRS-3.2)", citations)
    if "low" in states and "zero" in states:
        return Result("orange", f"Diskordance HER2: {described} → HER2-low platí z kteréhokoli vzorku (PRS-1.1)",
                      citations)
    if "low" in states:
        return Result("green", f"HER2-low ({described})", citations)
    return Result("red", f"HER2 0 ve všech vzorcích ({described}) → T-DXd pro HER2-low není indikován", citations)


def visceral_crisis(f: Facts, rule: dict) -> Result:
    bili = f.latest("bili")
    if bili is None:
        return Result("grey", "Bilirubin pro posouzení viscerální krize chybí")
    uln = (bili.resource.get("referenceRange") or [{}])[0].get("high", {}).get("value")
    if uln is not None and bili.value > uln * rule["uln_factor"]:
        return Result("red", f"Bilirubin {_num(bili.value)} > {_num(rule['uln_factor'])}× ULN → známka viscerální "
                             "krize "
                             "(chemoterapie nebo ADC)", [bili.id])
    return Result("green", f"Bilirubin {_num(bili.value)} µmol/l v normě, viscerální krize podle laboratoře není",
                  [bili.id])


QTC_VALUE = re.compile(r"QTc\w?\D{0,10}(\d{3})\s*ms", re.IGNORECASE)


def qtc(f: Facts, rule: dict) -> Result:
    found = f.text_value(QTC_VALUE, ("DocumentReference", "DiagnosticReport"))
    if found is None:
        return Result("grey", "QTc v podkladech není")
    value, evidence = found
    resource = next((r for r in f.resources if r.get("id") == evidence.split("#")[0]), {})
    when = (resource.get("date") or resource.get("effectiveDateTime") or "")[:10]
    if value >= rule["qtc_max"]:
        return Result("red", f"QTc {_num(value)} ms ({when}) ≥ {rule['qtc_max']} → ribociklib nezahajovat", [evidence])
    return Result("green", f"QTc {_num(value)} ms ({when})", [evidence])


PARPI_ATC = ("L01XK",)
DOSE_MG = re.compile(r"(\d+)\s*mg")


def parpi_anemia(f: Facts, rule: dict) -> Result:
    hb = f.latest("hb")
    doses = f.administrations(PARPI_ATC)
    anemia = [o for o in f.by_category("Toxicita") if "anémi" in o.text.lower() and "3" in str(o.value)]
    citations = [x for x in (hb and hb.id, doses[-1]["id"] if doses else None, anemia[-1].id if anemia else None) if x]
    if hb is None:
        return Result("grey", "Hemoglobin v podkladech není", citations)
    level = int(DOSE_MG.search(doses[-1]["dosage"]["text"]).group(1)) if doses and DOSE_MG.search(
        doses[-1].get("dosage", {}).get("text", "")) else None
    levels = rule["dose_levels"]
    lowest = levels[-1]
    if hb.value < rule["hb_stop"]:
        return Result("red", f"Hb {_num(hb.value)} g/l < {rule['hb_stop']} → přerušit podávání", citations)
    if anemia and level == lowest:
        return Result("red", f"Anémie G3 při nejnižší dávce {lowest} mg 2× → ukončit studijní léčbu", citations)
    next_level = levels[levels.index(level) + 1] if level in levels[:-1] and anemia else level
    if hb.value < rule["hb_continue"]:
        return Result("orange", f"Hb {_num(hb.value)} g/l (80–89) → pokračovat až po úpravě na ≥ {rule['hb_continue']}",
                      citations)
    if next_level == lowest and anemia:
        return Result("orange", f"Hb {_num(hb.value)} g/l; po opakované anémii G3 při {level} mg zbývá nejnižší dávka "
                                f"{lowest} mg 2×, další anémie G3 = ukončení", citations)
    return Result("green", f"Hb {_num(hb.value)} g/l ≥ {rule['hb_continue']} → lze pokračovat", citations)


def mds_aml(f: Facts, rule: dict) -> Result:
    found = f.conditions_icd(("D46", "C92"))
    if found:
        return Result("red", "MDS nebo AML v anamnéze → vyřazení (RKT-06/V2)", [c["id"] for c in found])
    if f.comorbidities_confirmed:
        return Result("green", "MDS ani AML v anamnéze nejsou (seznam komorbidit potvrzen)")
    return Result("grey", "MDS ani AML v dokumentaci nejsou, úplnost komorbidit lékař nepotvrdil")


def neuropathy_taxane(f: Facts, rule: dict) -> Result:
    found = f.neuropathy()
    if found is None:
        return Result("grey", "Neuropatie podle lékaře v podkladech není")
    obs, grade = found
    if grade >= rule["grade_orange"]:
        return Result("orange", f"Neuropatie G{grade} ({obs.date}) → taxan zvážit opatrně", [obs.id])
    return Result("green", f"Neuropatie G{grade} ({obs.date})", [obs.id])


NUMBERS_CS = {"jedno": 1, "jedna": 1, "jeden": 1, "dvě": 2, "dva": 2, "tři": 3, "čtyři": 4, "pět": 5}
BRAIN_METS = re.compile(r"(\d+|jedno|jedna|jeden|dvě|dva|tři|čtyři|pět)\s+(?:nov\w+\s+)?mozkov\w+\s+metast",
                        re.IGNORECASE)


def brain_metastases(f: Facts, rule: dict) -> Result:
    found = f.find_paragraphs(BRAIN_METS, ("ServiceRequest", "DocumentReference", "DiagnosticReport"))
    if not found:
        return Result("grey", "Počet mozkových metastáz v podkladech není")
    evidence = found[-1]
    raw = BRAIN_METS.search(f.paragraph_text(evidence)).group(1).lower()
    count = int(raw) if raw.isdigit() else NUMBERS_CS[raw]
    if count <= rule["srs_max"]:
        return Result("green", f"{count} mozkové metastázy → stereotaktická RT; celomozková RT se odkládá", [evidence])
    return Result("orange", f"{count} mozkových metastáz → zvážit celomozkovou RT (kognitivní toxicita)", [evidence])


def zoledronate_crcl(f: Facts, rule: dict) -> Result:
    crcl = f.crcl()
    if crcl is None:
        return Result("grey", "CrCl nejde spočítat (chybí kreatinin, hmotnost nebo věk)")
    value, derived = crcl
    citations = list(derived["inputs"])
    if value < rule["crcl_min"]:
        return Result("red", f"CrCl ≈ {round(value)} ml/min < {rule['crcl_min']} → kyselina zoledronová se "
                             "nedoporučuje", citations, derived)
    if value < rule["crcl_full"]:
        return Result("orange", f"CrCl ≈ {round(value)} ml/min → snížit dávku na 3,0–3,5 mg", citations, derived)
    return Result("green", f"CrCl ≈ {round(value)} ml/min → plná dávka 4 mg", citations, derived)


def dental_exam(f: Facts, rule: dict) -> Result:
    pattern = re.compile(r"stomatolog", re.IGNORECASE)
    found = f.find_paragraphs(pattern)
    if found:
        sentence = next(s for s in re.split(r"(?<=[.;])\s+", f.paragraph_text(found[-1])) if pattern.search(s))
        return Result("green", f"Stomatologické vyšetření: {sentence.strip()}", found[-1:])
    return Result("orange", "Stomatologické vyšetření v dokumentaci chybí → doplnit před antiresorpční léčbou")


CHECKS: dict[str, Callable[[Facts, dict], Result | None]] = {
    fn.__name__: fn for fn in (
        ecog_physician, ecog_difference, g8, weight_loss, blood_counts, bilirubin, staging_age, unclear_lesion,
        cyp3a_interaction, cardiac_events, smoking, bevacizumab_interval, flr, liver_restaging, liver_extent,
        neuropathy_oxaliplatin, ras_status, mmr_status, bevacizumab_safety, dpd, conversion_cycles, ppo_lung_function,
        vo2max, dyspnea_walking, lung_staging, egfr_alk, pdl1, sodium, no_threshold, cisplatin_fitness,
        steroid_glucose, lvef_anti_her2, ild_history, her2_tdxd, visceral_crisis, qtc, parpi_anemia, mds_aml,
        neuropathy_taxane, brain_metastases, zoledronate_crcl, dental_exam,
    )
}


# ── Použitelnost postupu (`requires` v YAML) ──────────────────────────────────
def _er_positive(f: Facts) -> bool:
    return any(re.search(r"pozitiv", str(o.value), re.IGNORECASE) for o in f.by_category("Biomarker")
               if re.match(r"(ER\b|Estrogen)", o.text))


REQUIRES: dict[str, Callable[[Facts], bool]] = {
    "her2_positive": lambda f: any(state == "positive" for _, state in _her2_samples(f)),
    "her2_tested": lambda f: bool(_her2_samples(f)),
    "hr_positive_her2_not_positive": lambda f: _er_positive(f)
    and not any(state == "positive" for _, state in _her2_samples(f)),
    "brca_pathogenic": lambda f: any(re.search(r"brca", o.text, re.IGNORECASE)
                                     and _mutation_state(str(o.value)) == "positive"
                                     for o in f.by_category("Biomarker")),
}


# ── Preference pacienta (štítek, barvu nemění) ────────────────────────────────
def _preferences(f: Facts, keywords: list[str], procedure_id: str) -> list[dict]:
    if not keywords:
        return []
    sources = [(p, f.paragraph_text(p)) for p in [f.paragraph_with(f.request.get("id", ""), re.compile("^Preference"))]
               if p]
    if f.proms:
        qr = f.proms[-1]
        sources += [(qr["id"], str(f.answers(qr).get("postoj") or ""))]
    claims = []
    for evidence_id, text in sources:
        for sentence in re.split(r"(?<=[.;])\s+", re.sub(r"^Preference[^:]*:\s*", "", text)):
            if sentence and any(k in sentence.lower() for k in keywords):
                claims.append({"id": f"pref-{procedure_id}-{len(claims) + 1}", "kind": "claim",
                               "text": sentence.strip(), "citations": [evidence_id], "verification": "verified"})
    return claims


# ── Veřejné API ───────────────────────────────────────────────────────────────
def _applies(procedure: dict, f: Facts) -> bool:
    if not set(procedure.get("sets", [])) & set(f.sets):
        return False
    if procedure.get("requires") and not REQUIRES[procedure["requires"]](f):
        return False
    required = procedure.get("requires_icd")
    codes = [_code(c.get("code"), "icd-10") for c in f.oncologic]
    return not required or any(code.startswith(tuple(required)) for code in codes)


def evaluate_compatibility(resources: Iterable[dict], *, skipped_fields: Iterable[str] = (),
                           comorbidities_confirmed: bool = False, catalog: dict | None = None) -> list[dict]:
    """Semafor pro všechny postupy ze sady guidelines pacienta (kontrakt §8.3)."""
    catalog = catalog or load_catalog()
    facts = Facts(resources, comorbidities_confirmed)
    skipped = set(skipped_fields)
    out = []
    for procedure in catalog["procedures"]:
        if not _applies(procedure, facts):
            continue
        results = []
        for rule_id in procedure["rules"]:
            rule = catalog["rules"][rule_id]
            if set(rule.get("fields", [])) & skipped:
                results.append({"rule_id": rule_id, "status": "skipped", "text": f"{rule['title']}: neposuzováno "
                                "(údaj lékař přeskočil)", "patient_citations": [], "rule_citation": rule.get("source")})
                continue
            result = CHECKS[rule["check"]](facts, rule)
            if result is None:
                continue
            status = result.status
            if status == "red" and not rule.get("source"):
                status = "orange"                         # červená jen se zdrojem (§5.9)
            text = result.text + (TEAM_NOTE if status == "red" and rule.get("team_threshold") else "")
            item = {"rule_id": rule_id, "status": status, "text": text,
                    "patient_citations": list(dict.fromkeys(c for c in result.patient_citations if c)),
                    "rule_citation": result.rule_citation or rule.get("source")}
            if result.derived:
                item["derived"] = result.derived
            results.append(item)
        overall = min((r["status"] for r in results), key=LIGHT_ORDER.get, default="grey")
        out.append({
            "id": procedure["id"],
            "title": procedure["title"],
            "guideline_citations": list(procedure.get("guidelines", [])),
            "compatibility": {
                "modality": procedure["modality"],
                "owner_role": procedure["owner_role"],
                "overall": overall,
                "rules": results,
                "patient_preferences": _preferences(facts, procedure.get("preference_keywords", []), procedure["id"]),
            },
        })
    return out
