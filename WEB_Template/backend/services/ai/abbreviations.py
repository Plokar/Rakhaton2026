"""
Výklad zkratek podle kontextu a NEJISTOTA AI (FR-R5, docs/POZADAVKY_LEKARE.md §7, T-509).

Pravidla jsou data v `services/ai/data/abbreviations.yaml`. Výklad je deterministický:

1. zkratka hned před dvojtečkou je sekce anamnézy („OA:“ = osobní anamnéza);
2. rozhodne nejbližší kontextové slovo v odstavci (např. „neutropenie G3“ = toxicita);
3. jinak název zprávy a oddělení („MR jater“ → S3 = jaterní segment);
4. když nic nerozhodne, nebo se dva výklady přetahují, je výsledek NEJISTOTA AI. Nikdy odhad.

`prompt_rules()` vrátí stejná pravidla jako text pro systémový prompt LLM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import yaml

from services.ai.text import resource_paragraphs

RULES_FILE = Path(__file__).parent / "data" / "abbreviations.yaml"
TEXT_TYPES = ("DocumentReference", "DiagnosticReport", "Composition", "ServiceRequest")


@dataclass(frozen=True)
class Interpretation:
    abbreviation: str
    meaning: str | None             # None = nejisté
    reason: str
    evidence_id: str | None = None
    start: int = 0

    @property
    def uncertain(self) -> bool:
        return self.meaning is None


@lru_cache(maxsize=1)
def load_rules() -> dict:
    data = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    for entry in data["ambiguous"].values():
        entry["regex"] = re.compile(rf"(?<![\w-])({entry['pattern']})(?![\w-])")
        for meaning in entry["meanings"]:
            meaning["cue_regex"] = [_cue(c) for c in meaning.get("cues", [])]
            meaning["title_regex"] = [_cue(c) for c in meaning.get("title_cues", [])]
    return data


def _cue(cue: str) -> re.Pattern:
    exact = cue == "%" or (cue.upper() == cue and any(ch.isalpha() for ch in cue)) or any(ch.isdigit() for ch in cue)
    if exact:
        return re.compile(re.escape(cue) if cue == "%" else rf"(?<![\w-]){re.escape(cue)}(?![\w])")
    return re.compile(rf"(?<!\w){re.escape(cue)}", re.IGNORECASE)


def _nearest(patterns: list[re.Pattern], text: str, position: int, end: int, window: int) -> int | None:
    best = None
    for pattern in patterns:
        for match in pattern.finditer(text):
            if match.start() <= position < match.end() or match.start() < end <= match.end():
                continue                                  # samotná zkratka není kontext
            distance = position - match.end() if match.end() <= position else match.start() - end
            if 0 <= distance <= window and (best is None or distance < best):
                best = distance
    return best


def interpret(abbreviation: str, text: str, position: int | None = None, *, title: str = "",
              evidence_id: str | None = None) -> Interpretation:
    """Výklad jedné zkratky v textu (`position` = začátek zkratky, výchozí první výskyt)."""
    rules = load_rules()
    entry = next((e for e in rules["ambiguous"].values() if e["regex"].fullmatch(abbreviation)), None)
    if entry is None:
        return Interpretation(abbreviation, None, "zkratka není v pravidlech", evidence_id)
    if position is None:
        found = entry["regex"].search(text)
        position = found.start() if found else 0
    end = position + len(abbreviation)

    after = text[end:end + 2]
    if entry.get("section_meaning") and after.startswith(":"):
        return Interpretation(abbreviation, entry["section_meaning"], f"sekce „{abbreviation}:“", evidence_id, position)

    distances = [(meaning["meaning"], _nearest(meaning["cue_regex"], text, position, end, rules["window"]))
                 for meaning in entry["meanings"]]
    distances = sorted((d, m) for m, d in distances if d is not None)
    if distances:
        if len(distances) > 1 and distances[1][0] - distances[0][0] < rules["tie_margin"]:
            return Interpretation(abbreviation, None, f"kontext odpovídá více výkladům ({distances[0][1]}, "
                                  f"{distances[1][1]})", evidence_id, position)
        return Interpretation(abbreviation, distances[0][1], "podle okolních slov", evidence_id, position)

    by_title = [m["meaning"] for m in entry["meanings"] if any(p.search(title) for p in m["title_regex"])]
    if len(by_title) == 1:
        return Interpretation(abbreviation, by_title[0], f"podle názvu zprávy „{title[:60]}“", evidence_id, position)
    return Interpretation(abbreviation, None, "kontext nestačí k jednoznačnému výkladu", evidence_id, position)


def scan_text(text: str, *, title: str = "", evidence_id: str | None = None) -> list[Interpretation]:
    """Všechny nejednoznačné zkratky v textu s výkladem."""
    out = []
    for entry in load_rules()["ambiguous"].values():
        for match in entry["regex"].finditer(text):
            out.append(interpret(match.group(1), text, match.start(), title=title, evidence_id=evidence_id))
    return sorted(out, key=lambda i: i.start)


def _title(resource: dict) -> str:
    parts = [resource.get("type", {}).get("text"), resource.get("code", {}).get("text"), resource.get("description")]
    categories = resource.get("category") or []
    for c in categories if isinstance(categories, list) else [categories]:
        parts.append((c or {}).get("text"))
    return " ".join(p for p in parts if p)


def scan_resources(resources: Iterable[dict]) -> list[Interpretation]:
    """Výklad zkratek ve všech textech pacienta, po odstavcích (`P03-img02#2`)."""
    out = []
    for resource in resources:
        if resource.get("resourceType") not in TEXT_TYPES:
            continue
        title = _title(resource)
        for paragraph in resource_paragraphs(resource):
            out += scan_text(paragraph.text, title=title, evidence_id=f"{resource['id']}#{paragraph.index}")
    return out


def uncertainty_warnings(resources: Iterable[dict]) -> list[dict]:
    """NEJISTOTA AI pro zkratky bez jednoznačného výkladu (kontrakt §8.6 `IntakeWarning`)."""
    warnings = {}
    for item in scan_resources(resources):
        if item.uncertain:
            warning_id = f"ai_uncertain:abbr-{item.abbreviation}:{item.evidence_id}"
            warnings.setdefault(warning_id, {
                "id": warning_id, "kind": "ai_uncertain", "severity": "low",
                "title": f"Nejednoznačná zkratka „{item.abbreviation}“",
                "detail": f"{item.reason[:1].upper()}{item.reason[1:]}. AI zkratku nerozepisuje, výklad potvrdí lékař.",
                "citations": [item.evidence_id],
            })
    return list(warnings.values())


def prompt_rules() -> str:
    """Pravidla výkladu zkratek pro systémový prompt (docs/POZADAVKY_LEKARE.md §7.1, §7.2)."""
    lines = [
        "Výklad zkratek:",
        "- Zkratku vykládej podle kontextu: sekce zprávy (OA: = osobní anamnéza), oddělení, okolní slova, orgán.",
        "- Rozmezí (např. „ECOG 0–1“) nepřeváděj na jedno číslo; uveď rozmezí a označ ho jako nejisté.",
        "- Neznámou nebo nejednoznačnou zkratku nerozepisuj odhadem; ponech ji a označ jako nejistou.",
        "- Strana těla: l. dx. = vpravo, l. sin. = vlevo.",
        "Nejednoznačné zkratky (význam → typický kontext):",
    ]
    for name, entry in load_rules()["ambiguous"].items():
        options = "; ".join(f"{m['meaning']} ({', '.join(m.get('cues', [])[:4])})" for m in entry["meanings"])
        section = f"{entry['section_meaning']} (když následuje dvojtečka); " if entry.get("section_meaning") else ""
        lines.append(f"- {entry['pattern']}: {section}{options}")
    return "\n".join(lines)
