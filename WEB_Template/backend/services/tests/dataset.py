"""
Načtení datasetu pro testy (AGENTS.md: JSON a .md datasetu jen pro ingest, testy a čtení člověkem).

Sanitizace je tu jen zjednodušená (`_` → `-` v ID a referencích, prázdné stringy pryč),
aby testy viděly stejná ID jako IRIS po ingestu (DATASET §6.2). Ostrá verze je v ingestu (T-101).
"""
import json
import os
import re
from pathlib import Path

import pytest

_INVALID_ID_CHARS = re.compile(r"[^A-Za-z0-9.\-]")


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


def _sanitize(node):
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == "id" and isinstance(value, str):
                value = _INVALID_ID_CHARS.sub("-", value)
            elif key == "reference" and isinstance(value, str) and "/" in value:
                rtype, rid = value.split("/", 1)
                value = f"{rtype}/{_INVALID_ID_CHARS.sub('-', rid)}"
            value = _sanitize(value)
            if value == "" or value == [] or value == {}:
                continue
            out[key] = value
        return out
    if isinstance(node, list):
        return [v for v in (_sanitize(v) for v in node) if v not in ("", [], {})]
    return node


def load_bundle_resources(relative_path: str) -> list[dict]:
    bundle = json.loads((dataset_dir() / relative_path).read_text(encoding="utf-8"))
    return [_sanitize(entry["resource"]) for entry in bundle["entry"]]


def load_patient(patient_id: str) -> list[dict]:
    return load_bundle_resources(f"pacienti/{patient_id}/{patient_id}_bundle.json")


def load_studies() -> list[dict]:
    return load_bundle_resources("studie/studie_ResearchStudy_bundle.json")


def load_guideline_markdowns() -> dict[str, str]:
    return {p.name[:3]: p.read_text(encoding="utf-8") for p in sorted((dataset_dir() / "guidelines").glob("*.md"))}
