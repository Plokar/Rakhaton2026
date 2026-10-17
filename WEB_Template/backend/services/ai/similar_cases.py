"""Podobné případy (BONUS B2, T-332): předchozí závěry MDT jiných pacientů s obdobnou diagnózou.

Jen jako inspirace pro diskusi, nikdy doporučení. Bez AI: pořadí podle shody kódu MKN-10 (celý kód, pak
kategorie C50), novější záznamy dřív. Případy jsou anonymizované: místo pseudonymu pacienta jen pohlaví
a věková dekáda; dohledatelnost drží citace záznamu (`P05-mdt02`), které otevře zdroj jako každé jiné tvrzení.
"""
from __future__ import annotations

import html
import re

from services import patients
from services.fhir import client as fhir

SECTIONS = {"Projednaná otázka": "question", "Léčebný záměr": "intent", "Doporučený postup": "recommendation",
            "Závěr MDT": "conclusion"}
SEX = {"male": "muž", "female": "žena"}


def _text(section: dict) -> str:
    div = (section.get("text") or {}).get("div") or ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", div))).strip()


def _age_band(age: int | None) -> str:
    return f"{age // 10 * 10}–{age // 10 * 10 + 9} let" if isinstance(age, int) else "věk neuveden"


def _is_mdt_record(composition: dict) -> bool:
    return any(c.get("code") == "mdt-zaznam" for c in (composition.get("type") or {}).get("coding", []))


def similar_cases(patient_id: str, limit: int = 3) -> dict:
    """`{diagnosis, cases: [...]}`; `cases` prázdné, když v IRIS není jiný pacient s obdobnou diagnózou."""
    everyone = patients.list_patients()
    me = next((p for p in everyone if p["id"] == patient_id), None)
    icd = ((me or {}).get("diagnosis") or {}).get("icd10") or ""
    if not icd:
        return {"diagnosis": None, "cases": []}
    found = []
    for other in everyone:
        code = (other.get("diagnosis") or {}).get("icd10") or ""
        if other["id"] == patient_id or not code:
            continue
        match = "code" if code == icd else "category" if code[:3] == icd[:3] else None
        if match is None:
            continue
        for comp in fhir.search("Composition", patient=other["id"]):
            if not _is_mdt_record(comp):
                continue
            parts = {SECTIONS[s["title"]]: _text(s) for s in comp.get("section", []) if s.get("title") in SECTIONS}
            if not parts.get("conclusion") and not parts.get("recommendation"):
                continue
            found.append({
                "composition_id": comp["id"],
                "date": (comp.get("date") or "")[:10],
                "match": match,
                "diagnosis": {"icd10": code, "text": other["diagnosis"]["text"]},
                "patient": f"{SEX.get(other.get('sex'), 'pohlaví neuvedeno')}, {_age_band(other.get('age'))}",
                **parts,
                "citations": [comp["id"]],
            })
    # celý kód MKN-10 dřív než jen kategorie, uvnitř novější záznamy dřív
    ordered = [c for m in ("code", "category")
               for c in sorted((c for c in found if c["match"] == m), key=lambda c: c["date"], reverse=True)]
    return {"diagnosis": {"icd10": icd, "text": me["diagnosis"]["text"]}, "cases": ordered[:limit]}
