"""
Evidence ID: citační klíč = ID z datasetu (ARCHITEKTURA §5.2, D-006, D-016).

Formáty:
- ``P03``, ``P03-img03``, ``P03-lab06-cea``: resource pacienta (fakt pacienta);
- ``P03-img03#3``: 3. odstavec textu resource (číslováno od 1, viz ``split_paragraphs``);
- ``KRC-2.4``: pasáž guidelines (KRC, PRS, PLI, OBC);
- ``RKT-03`` / ``RKT-03/V3``: studie / kritérium zařazení ``Zn`` nebo vyřazení ``Vn``;
- ``EXT-…``: externí zdroj prahu pravidla semaforu, nikdy fakt pacienta.

Pravidlo číslování odstavců sdílí ingest (T-102), resolver (T-104) a fixtures (T-009),
aby ``#n`` ukazovalo všude na stejný text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PATIENT_ID_RE = re.compile(r"^(P\d{2})(?:-[A-Za-z0-9-]+)?$")
GUIDELINE_ID_RE = re.compile(r"^(KRC|PRS|PLI|OBC)-\d+\.\d+$")
TRIAL_ID_RE = re.compile(r"^(RKT-\d{2})(?:/([ZV]\d+))?$")
EXTERNAL_ID_RE = re.compile(r"^EXT-[A-Z0-9]+(?:-[A-Z0-9]+)*$")

# Nový odstavec začíná za prázdným řádkem, nebo řádkem „Závěr:“ / „Nález:“ (ARCHITEKTURA §4.5).
_PARAGRAPH_START_RE = re.compile(r"^(Závěr|Nález):")


@dataclass(frozen=True)
class EvidenceRef:
    kind: str                       # "patient" | "guideline" | "trial" | "external"
    resource_id: str                # "P03-img03" | "KRC-2.4" | "RKT-03" | "EXT-EMA-DPD-2020"
    paragraph: int | None = None    # u "P03-img03#3"
    criterion: str | None = None    # u "RKT-03/V3" → "V3"
    patient_id: str | None = None   # u faktů pacienta → "P03"


def parse_evidence_id(evidence_id: str) -> EvidenceRef | None:
    """Rozloží Evidence ID; neplatný formát vrátí ``None``."""
    base, sep, para = evidence_id.partition("#")
    if sep and not (para.isdigit() and int(para) >= 1):
        return None

    if m := PATIENT_ID_RE.match(base):
        return EvidenceRef("patient", base, int(para) if sep else None, patient_id=m.group(1))
    if sep:
        return None   # odstavce mají jen texty pacienta
    if GUIDELINE_ID_RE.match(base):
        return EvidenceRef("guideline", base)
    if m := TRIAL_ID_RE.match(base):
        return EvidenceRef("trial", m.group(1), criterion=m.group(2))
    if EXTERNAL_ID_RE.match(base):
        return EvidenceRef("external", base)
    return None


def is_evidence_id(evidence_id: str) -> bool:
    return parse_evidence_id(evidence_id) is not None


def split_paragraphs(text: str) -> list[str]:
    """Rozdělí text zprávy na odstavce; ``P03-img03#n`` je ``split_paragraphs(text)[n - 1]``.

    Odstavce oddělují prázdné řádky. Řádek začínající „Závěr:“ nebo „Nález:“ začíná
    nový odstavec i bez prázdného řádku.
    """
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n", text.strip()):
        current: list[str] = []
        for line in block.splitlines():
            if current and _PARAGRAPH_START_RE.match(line):
                paragraphs.append("\n".join(current).strip())
                current = []
            current.append(line)
        if current and "\n".join(current).strip():
            paragraphs.append("\n".join(current).strip())
    return paragraphs
