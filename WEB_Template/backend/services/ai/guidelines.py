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


@dataclass(frozen=True)
class GuidelinePassage:
    evidence_id: str        # "KRC-2.4"
    guideline_set: str      # "KRC"
    title: str              # "Restaging před resekcí jater"
    text: str

    @property
    def sort_key(self) -> tuple:
        major, minor = self.evidence_id.split("-", 1)[1].split(".")
        order = GUIDELINE_SET_ORDER.index(self.guideline_set) if self.guideline_set in GUIDELINE_SET_ORDER else 99
        return order, int(major), int(minor)


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
