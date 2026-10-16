"""
Načtení datasetu pro testy (AGENTS.md: JSON a .md datasetu jen pro ingest, testy a čtení člověkem).

Resources jsou sanitizované stejnou funkcí jako při ingestu do IRIS (`services.fhir.ingest`, T-101),
takže testy vidí stejná ID a data jako aplikace za běhu.
"""
import os
from pathlib import Path

import pytest

from services.fhir import ingest


def dataset_dir() -> Path:
    env = os.environ.get("DATASET_DIR")
    if env:
        path = Path(env)
    else:   # repo checkout (CI): <repo>/WEB_Template/backend/services/tests/dataset.py
        parents = Path(__file__).resolve().parents
        path = parents[min(4, len(parents) - 1)] / "Dataset_MDT_Copilot_v1.1_pre_timy" / "Dataset_MDT_Copilot_v1.1"
    if not (path / "pacienti").is_dir():
        pytest.skip(f"dataset není k dispozici ({path})")
    return path


def load_patient(patient_id: str) -> list[dict]:
    return ingest.load_patient(dataset_dir(), patient_id)


def load_studies() -> list[dict]:
    return ingest.load_studies(dataset_dir())


def load_guideline_markdowns() -> dict[str, str]:
    return {p.name[:3]: p.read_text(encoding="utf-8") for p in sorted((dataset_dir() / "guidelines").glob("*.md"))}
