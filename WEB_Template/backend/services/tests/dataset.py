"""
Načtení datasetu pro testy (AGENTS.md: JSON a .md datasetu jen pro ingest, testy a čtení člověkem).

Resources jsou sanitizované stejnou funkcí jako při ingestu do IRIS (`services.fhir.ingest`, T-101),
takže testy vidí stejná ID a data jako aplikace za běhu.
"""
from pathlib import Path

import pytest

from services.fhir import ingest


def dataset_dir() -> Path:
    """Dataset jako při ingestu (env `DATASET_DIR`, jinak checkout repa); bez datasetu se test přeskočí."""
    try:
        return ingest.dataset_dir()
    except ingest.DatasetError as e:
        pytest.skip(f"dataset není k dispozici ({e})")


def load_patient(patient_id: str) -> list[dict]:
    return ingest.load_patient(dataset_dir(), patient_id)


def load_studies() -> list[dict]:
    return ingest.load_studies(dataset_dir())


def load_guideline_markdowns() -> dict[str, str]:
    return {p.name[:3]: p.read_text(encoding="utf-8") for p in sorted((dataset_dir() / "guidelines").glob("*.md"))}
