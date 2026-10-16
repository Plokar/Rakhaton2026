"""Údaje podle diagnózy v sekcích odborností (FR-B8) a katalog léčebných metod (FR-D5), T-506.

Obojí sestavuje kód z dat v IRIS (`PatientContext`) a z `data/diagnosis_data.yaml`, nezávisle na LLM:
chirurg u kolorekta vždy uvidí FLR a poslední dávku bevacizumabu, pneumolog spirometrii, onkolog u prsu
receptory a LVEF. Chybějící údaj je `missing` s pasáží guidelines, která ho vyžaduje (FR-R3).
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from services.ai.context_builder import PatientContext

DATA = Path(__file__).parent / "data" / "diagnosis_data.yaml"
DIGITS = re.compile(r"\d+")
_NOISE = re.compile(r"\s*·\s*zdroj:\s*\S+$")


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    return yaml.safe_load(DATA.read_text(encoding="utf-8"))


def _lines(context: PatientContext, spec: dict) -> list:
    pattern = re.compile(spec["pattern"], re.IGNORECASE)
    lines = [line for line in context.evidence if line.group == spec["group"] and pattern.search(line.text)]
    lines.sort(key=lambda line: (line.date, line.id))
    return lines[-spec["last"]:] if spec.get("last") else lines


def role_diagnosis_items(role: str, context: PatientContext, skip_citations: set[str] = frozenset()) -> list[dict]:
    """Údaje podle sad guidelines pacienta pro jednu roli; řádky, které sekce už cituje, přeskočí."""
    items, seen = [], set(skip_citations)
    allowed = context.allowed_ids
    for gset in context.guideline_sets:
        for spec in load_catalog()["data"].get(gset, {}).get(role, []):
            lines = _lines(context, spec)
            if not lines:
                required = spec.get("required_by")
                items.append({"kind": "missing", "text": f"{spec['label']}: v podkladech chybí", "citations": [],
                              "expected_source": required if required in allowed else None})
                continue
            for line in lines:
                if line.id in seen:
                    continue
                seen.add(line.id)
                text = _NOISE.sub("", line.text).strip()
                # Text i citaci skládá kód z řádku zdroje (`_computed`): vektorová kontrola se přeskočí.
                # Čísla z popisku („Ki-67“, „poslední 3“) nejsou fakt pacienta, grounding je nekontroluje (`_derived`).
                items.append({"kind": "claim", "text": f"{spec['label']}: {line.date} · {text}" if line.date
                              else f"{spec['label']}: {text}", "citations": [line.id], "_computed": True,
                              "_derived": DIGITS.findall(spec["label"])})
    return [{"id": f"{role}-dx-{i:02d}", **item} for i, item in enumerate(items, 1)]


def modality_items(context: PatientContext, compatibility: list[dict], role_titles: dict[str, str]) -> list[dict]:
    """Blok „Léčebné metody a odborníci“: metoda → kdo se vyjadřuje, co má mít u sebe, postupy ze sady guidelines."""
    catalog = load_catalog()["modalities"]
    allowed = context.allowed_ids
    by_modality: dict[str, list[dict]] = {}
    for procedure in compatibility:
        by_modality.setdefault(procedure["compatibility"]["modality"], []).append(procedure)
    items = []
    for i, (modality, procedures) in enumerate(by_modality.items(), 1):
        meta = catalog.get(modality, {"label": modality, "expert": "", "needs": ""})
        owner = role_titles.get(procedures[0]["compatibility"].get("owner_role"), "")
        expert = meta["expert"] or owner
        guidelines = [c for p in procedures for c in p.get("guideline_citations", []) if c in allowed]
        facts = [c for p in procedures for r in p["compatibility"]["rules"] for c in r["patient_citations"] if c in allowed]
        citations = list(dict.fromkeys(guidelines))[:3] + list(dict.fromkeys(facts))[:4]
        titles = "; ".join(p["title"] for p in procedures)
        text = f"{meta['label']}: vyjadřuje se {expert}. Postupy: {titles}."
        if meta.get("needs"):
            text += f" Má mít u sebe: {meta['needs']}."
        if citations:
            items.append({"id": f"modality-{i:02d}", "kind": "claim", "text": text, "citations": citations,
                          "_computed": True})
    return items

