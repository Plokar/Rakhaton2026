"""
Pasáže guidelines (ARCHITEKTURA §4.5, DATASET §7).

- `parse_guidelines()` čte markdown z datasetu (ingest T-203 a testy);
- `load_guidelines()` je čte za běhu z IRIS `MDT.GuidelineChunk` (data jen z IRIS, AGENTS.md).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from services.rules.guideline_sets import GUIDELINE_SET_ORDER

# `**KRC-2.3 – Název.** text…`, pasáž pokračuje do prázdného řádku (DATASET §7)
_PASSAGE = re.compile(r"^\*\*([A-Z]{3}-\d+\.\d+) – (.+?)\.\*\*\s*(.*)")


class GuidelinesUnavailable(RuntimeError):
    """Tabulka `MDT.GuidelineChunk` chybí nebo nemá pasáže pro požadované sady (T-203)."""


NATIONAL_SET = "MK"          # Modrá kniha ČOS (services/iris/indexing.modra_kniha_chunks)


@dataclass(frozen=True)
class GuidelinePassage:
    evidence_id: str        # "KRC-2.4" | "EXT-MK-4.6.3"
    guideline_set: str      # "KRC" | "MK"
    title: str              # "Restaging před resekcí jater"
    text: str
    url: str | None = None  # u Modré knihy odkaz na stránku PDF

    @property
    def sort_key(self) -> tuple:
        order = GUIDELINE_SET_ORDER.index(self.guideline_set) if self.guideline_set in GUIDELINE_SET_ORDER else 99
        numbers = tuple(int(n) for n in re.findall(r"\d+", self.evidence_id.split("-", 1)[1]))
        return (order, *numbers)


def parse_guidelines(markdown: str) -> list[GuidelinePassage]:
    passages: list[GuidelinePassage] = []
    current: list | None = None
    for line in markdown.splitlines():
        match = _PASSAGE.match(line)
        if match:
            current = [match.group(1), match.group(2), [match.group(3).strip()]]
            passages.append(current)
        elif not line.strip() or line.startswith("#"):
            current = None
        elif current is not None:
            current[2].append(line.strip())
    return [
        GuidelinePassage(evidence_id=pid, guideline_set=pid.split("-")[0], title=title,
                         text=" ".join(t for t in body if t))
        for pid, title, body in passages
    ]


def load_guidelines(guideline_sets: Iterable[str]) -> list[GuidelinePassage]:
    """Pasáže zvolených sad z IRIS `MDT.GuidelineChunk`, seřazené KRC/PRS/PLI/OBC a podle čísla."""
    sets = list(guideline_sets)
    if not sets:
        return []
    from services.iris.db import connect

    sql = ("SELECT EvidenceId, GuidelineSet, Title, Text FROM MDT.GuidelineChunk "
           f"WHERE GuidelineSet IN ({', '.join('?' * len(sets))})")
    try:
        with connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, sets)
                rows = cursor.fetchall()
            finally:
                cursor.close()
    except Exception as exc:
        raise GuidelinesUnavailable(
            f"Guidelines nejdou načíst z IRIS MDT.GuidelineChunk ({exc}); nahrát je má ingest (T-203)") from exc
    passages = [GuidelinePassage(evidence_id=r[0], guideline_set=r[1], title=r[2], text=r[3]) for r in rows]
    missing = set(sets) - {p.guideline_set for p in passages}
    if missing:
        raise GuidelinesUnavailable(f"V MDT.GuidelineChunk chybí sady {sorted(missing)} (ingest T-203)")
    return sorted(passages, key=lambda p: p.sort_key)


def national_passages(icd10: Iterable[str], query: str, *, tumor_k: int = 3, general_k: int = 1) -> list[GuidelinePassage]:
    """Pasáže Modré knihy ČOS k pacientovi: vektorové hledání podle otázky a diagnózy, z kapitoly jeho nádoru
    (rozsah MKN-10 kapitoly) ``tumor_k`` a z obecných kapitol (podpůrná léčba, toxicita…) ``general_k``.
    Sada v IRIS chybí nebo hledání selže → prázdný seznam (podklad jede dál bez ní)."""
    codes = [c.strip().upper() for c in icd10 if c]
    if not codes or not query.strip():
        return []
    from services.iris import vector_store as vs

    try:
        rows = vs.search_guidelines(query, [NATIONAL_SET], top_k=80)
    except Exception:                                   # IRIS / embedding nedostupné
        return []
    tumor, general = [], []
    for row in rows:
        prefixes = [p for p in (row.get("IcdPrefixes") or "").split(",") if p]
        passage = GuidelinePassage(evidence_id=row["EvidenceId"], guideline_set=NATIONAL_SET, title=row["Title"],
                                   text=row["Text"], url=row.get("Url"))
        if any(code.startswith(p) for p in prefixes if p != "*" for code in codes):
            if len(tumor) < tumor_k:
                tumor.append(passage)
        elif "*" in prefixes and len(general) < general_k:
            general.append(passage)
    return tumor + general
