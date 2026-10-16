"""Ingest datasetu do IRIS FHIR (T-101, DATASET §6, ARCH §4.4).

Pořadí: Questionnaire → studie → pacienti. Každý bundle se sanitizuje (DATASET §6.2) a pošle jako
``transaction`` s ``PUT Type/id``: ID z datasetu zůstávají (D-005), opakovaný běh nic neduplikuje.
Po nahrání se ověří počty proti bundlům a DATASET §2.

Soubory datasetu se čtou jen tady (ingest, testy). Aplikace za běhu čte jen z IRIS.
"""
import copy
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from services.fhir import client as fhir
from services.fhir.ids import (
    DERIVED_FROM_EXTENSION, DERIVED_FROM_TYPES, resource_type_for_id, sanitize_id, sanitize_reference,
)

FICTIONAL_TAG = {
    'system': 'https://rakathon.example.org/fhir/tag',
    'code': 'fiktivni-data',
    'display': 'Fiktivní data – Rakathon 2026',
}
FULL_URL_BASE = 'https://rakathon.example.org/fhir'
QUESTIONNAIRE_FILE = 'dotaznik/dotaznik_PROMs_Questionnaire.json'
STUDIES_FILE = 'studie/studie_ResearchStudy_bundle.json'

# DATASET §2: kontrolní počty. Když nesedí už v souborech, dataset se změnil a §2 je potřeba aktualizovat.
EXPECTED_PATIENT_TOTALS = {'P01': 164, 'P02': 212, 'P03': 171, 'P04': 142, 'P05': 179, 'P06': 215}
EXPECTED_STUDY_RESOURCES = 12
EXPECTED_TOTAL = 1091          # unikátní resources: 1 078 pacientských (ORG-FN sdílená) + Questionnaire + 12 studií
ID_BATCH = 50                  # kolik ID poslat v jednom `_id=a,b,c` (délka URL)


class DatasetError(Exception):
    pass


# ── Načtení datasetu ──────────────────────────────────────────────────────────

def dataset_dir(path: str | os.PathLike | None = None) -> Path:
    """Kořen datasetu z argumentu nebo env ``DATASET_DIR`` (cestu nehardcodujeme)."""
    raw = path or os.environ.get('DATASET_DIR')
    if not raw:
        raise DatasetError('Není nastavená proměnná DATASET_DIR (cesta k Dataset_MDT_Copilot_v1.1).')
    root = Path(raw)
    if not (root / 'pacienti').is_dir():
        raise DatasetError(f'{root} není dataset MDT Copilot (chybí složka pacienti/).')
    return root


def patient_ids(root: Path) -> list[str]:
    return sorted(p.name for p in (root / 'pacienti').iterdir() if re.fullmatch(r'P\d{2}', p.name))


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def load_questionnaire(root: Path) -> list[dict]:
    return [sanitize(_read_json(root / QUESTIONNAIRE_FILE))]


def load_studies(root: Path) -> list[dict]:
    return prepare_bundle(_read_json(root / STUDIES_FILE))


def load_patient(root: Path, pid: str) -> list[dict]:
    path = root / 'pacienti' / pid / f'{pid}_bundle.json'
    if not path.is_file():
        raise DatasetError(f'Pacient {pid} v datasetu není ({path}).')
    return prepare_bundle(_read_json(path))


# ── Sanitizace (DATASET §6.2) ─────────────────────────────────────────────────

def prepare_bundle(bundle: dict) -> list[dict]:
    """Bundle ``collection`` → seznam sanitizovaných resources s ``meta.tag`` z bundlu."""
    tags = (bundle.get('meta') or {}).get('tag') or [FICTIONAL_TAG]
    return [sanitize(e['resource'], tags) for e in bundle.get('entry', [])]


def sanitize(resource: dict, tags: Iterable[dict] = (FICTIONAL_TAG,)) -> dict:
    """Kopie resource platná pro FHIR server.

    - ``_`` (a jiné nepovolené znaky) v ``id`` a ve všech ``reference`` → ``-``;
    - prázdné stringy pryč, a s nimi i prvky, které tím zůstaly prázdné (``answer: [{}]``);
    - ``Observation.derivedFrom`` na typ, který R4 nepovoluje (DiagnosticReport), → extension ``derived-from`` (Q15);
    - ``meta.tag`` z bundlu do každého resource (filtr ``_tag=fiktivni-data``).
    """
    out = _prune(copy.deepcopy(resource))
    out['id'] = sanitize_id(out['id'])
    _move_disallowed_derived_from(out)
    meta_tags = out.setdefault('meta', {}).setdefault('tag', [])
    for tag in tags:
        if not any(t.get('system') == tag['system'] and t.get('code') == tag['code'] for t in meta_tags):
            meta_tags.append(dict(tag))
    return out


def _reference_type(ref: dict) -> str:
    parts = ref.get('reference', '').split('/_history/')[0].rstrip('/').split('/')
    return parts[-2] if len(parts) >= 2 else ''


def _move_disallowed_derived_from(resource: dict) -> None:
    """IRIS odmítne ``derivedFrom`` → DiagnosticReport (44× bm/tnm). Odkaz se neztratí: čte ho ``ids.derived_from``."""
    if resource.get('resourceType') != 'Observation' or not resource.get('derivedFrom'):
        return
    keep = [r for r in resource['derivedFrom'] if _reference_type(r) in DERIVED_FROM_TYPES]
    move = [r for r in resource['derivedFrom'] if _reference_type(r) not in DERIVED_FROM_TYPES]
    if not move:
        return
    resource.setdefault('extension', []).extend({'url': DERIVED_FROM_EXTENSION, 'valueReference': r} for r in move)
    if keep:
        resource['derivedFrom'] = keep
    else:
        del resource['derivedFrom']


def _is_empty(value) -> bool:
    return value is None or value == '' or value == [] or value == {}


def _prune(node):
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == 'reference' and isinstance(value, str):
                value = sanitize_reference(value)
            value = _prune(value)
            if not _is_empty(value):
                out[key] = value
        return out
    if isinstance(node, list):
        return [v for v in map(_prune, node) if not _is_empty(v)]
    return node


# ── Transaction bundle ────────────────────────────────────────────────────────

def key(resource: dict) -> str:
    return f"{resource['resourceType']}/{resource['id']}"


def references(node) -> set[str]:
    """Všechny literal reference ``Type/id`` v resource (bez base URL a ``_history``)."""
    found = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'reference' and isinstance(v, str) and not v.startswith(('urn:', '#')):
                parts = v.split('/_history/')[0].rstrip('/').split('/')
                if len(parts) >= 2:
                    found.add(f'{parts[-2]}/{parts[-1]}')
            else:
                found |= references(v)
    elif isinstance(node, list):
        for v in node:
            found |= references(v)
    return found


def order_by_references(resources: list[dict]) -> list[dict]:
    """Odkazované resources dřív než ty, které na ně odkazují (cykly ponechá v původním pořadí).

    Transakce by měla projít v libovolném pořadí, ale kdyby server kontroloval reference
    položku po položce, takhle neselže.
    """
    keys = [key(r) for r in resources]
    present = set(keys)
    deps = {k: (references(r) & present) - {k} for k, r in zip(keys, resources)}
    pending = list(zip(keys, resources))
    ordered, done = [], set()
    while pending:
        ready = [(k, r) for k, r in pending if deps[k] <= done] or pending[:1]
        for k, r in ready:
            ordered.append(r)
            done.add(k)
        pending = [(k, r) for k, r in pending if k not in done]
    return ordered


def to_transaction(resources: list[dict], bundle_type: str = 'transaction') -> dict:
    """``collection`` → ``transaction`` (nebo ``batch`` pro ladění chyb po položkách), ``PUT Type/id``."""
    return {
        'resourceType': 'Bundle',
        'type': bundle_type,
        'entry': [
            {
                'fullUrl': f'{FULL_URL_BASE}/{key(r)}',
                'resource': r,
                'request': {'method': 'PUT', 'url': key(r)},
            }
            for r in order_by_references(resources)
        ],
    }


# ── Nahrání a kontrola ────────────────────────────────────────────────────────

@dataclass
class UploadResult:
    label: str
    sent: int
    statuses: Counter = field(default_factory=Counter)   # {"200": 160, "201": 11}
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def upload(resources: list[dict], label: str, bundle_type: str = 'transaction') -> UploadResult:
    """Pošle resources jedním bundlem. Chyba celé transakce vyhodí ``FhirError`` (s ``OperationOutcome``)."""
    bundle = to_transaction(resources, bundle_type)
    response = fhir.transaction(bundle) or {}
    result = UploadResult(label, len(bundle['entry']))
    for sent, got in zip(bundle['entry'], response.get('entry', [])):
        status = (got.get('response') or {}).get('status', '')
        code = status.split(' ')[0] or '?'
        result.statuses[code] += 1
        if not code.startswith('2'):
            outcome = (got.get('response') or {}).get('outcome') or got.get('resource') or {}
            details = '; '.join(
                i.get('details', {}).get('text') or i.get('diagnostics', '') for i in outcome.get('issue', [])
            )
            result.errors.append(f"{sent['request']['url']}: {status} {details}".strip())
    missing = len(bundle['entry']) - len(response.get('entry', []))
    if missing > 0:
        result.errors.append(f'odpověď serveru má o {missing} položek méně, než se poslalo')
    return result


@dataclass
class CountCheck:
    label: str
    what: str          # "Observation (_id)" | "Observation?patient=P03"
    expected: int
    actual: int
    exact: bool = True  # False: víc je v pořádku (zápisy aplikace, např. Composition/P03-mdt02)

    @property
    def ok(self) -> bool:
        return self.actual == self.expected if self.exact else self.actual >= self.expected


def _subject_patient(resource: dict) -> str | None:
    for field_name in ('subject', 'patient', 'for'):
        ref = (resource.get(field_name) or {}).get('reference', '')
        if ref.startswith('Patient/'):
            return ref.split('/', 1)[1]
    return None


def verify(resources: list[dict], label: str, patient_id: str | None = None) -> list[CountCheck]:
    """Ověří v IRIS, že je tam každý resource (``_id``) a že funguje search ``?patient=``."""
    by_type: dict[str, list[str]] = defaultdict(list)
    for r in resources:
        by_type[r['resourceType']].append(r['id'])
    checks = []
    for rtype, ids in sorted(by_type.items()):
        actual = sum(
            fhir.count(rtype, _id=','.join(ids[i:i + ID_BATCH])) for i in range(0, len(ids), ID_BATCH)
        )
        checks.append(CountCheck(label, f'{rtype} (_id)', len(ids), actual))
    if patient_id:
        per_patient = Counter(
            r['resourceType'] for r in resources
            if r['resourceType'] in fhir.PATIENT_TYPES and _subject_patient(r) == patient_id
        )
        for rtype, expected in sorted(per_patient.items()):
            actual = fhir.count(rtype, patient=patient_id)
            checks.append(CountCheck(label, f'{rtype}?patient={patient_id}', expected, actual, exact=False))
    return checks


def id_index_mismatches(resources: list[dict]) -> list[str]:
    """Resources, jejichž ID neodpovídá konvenci v ``ids.resource_type_for_id`` (= nový nález v datech)."""
    return [key(r) for r in resources if resource_type_for_id(r['id']) != r['resourceType']]


# ── Orchestrace ───────────────────────────────────────────────────────────────

@dataclass
class IngestPart:
    label: str                      # "Questionnaire" | "studie" | "P03"
    resources: list[dict]
    expected: int | None = None     # DATASET §2
    upload: UploadResult | None = None
    checks: list[CountCheck] = field(default_factory=list)


@dataclass
class IngestReport:
    parts: list[IngestPart] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def unique_resources(self) -> int:
        return len({key(r) for part in self.parts for r in part.resources})

    @property
    def errors(self) -> list[str]:
        out = []
        for part in self.parts:
            if part.upload:
                out += [f'{part.label}: {e}' for e in part.upload.errors]
            out += [f'{c.label}: {c.what} očekáváno {c.expected}, v IRIS {c.actual}' for c in part.checks if not c.ok]
        return out


def collect(root: Path, patients: Iterable[str] | None = None, include_shared: bool = True) -> IngestReport:
    """Načte a sanitizuje části k nahrání, bez sítě. ``include_shared`` = Questionnaire a studie."""
    report = IngestReport()
    if include_shared:
        report.parts.append(IngestPart('Questionnaire', load_questionnaire(root), expected=1))
        report.parts.append(IngestPart('studie', load_studies(root), expected=EXPECTED_STUDY_RESOURCES))
    available = patient_ids(root)
    for pid in patients or available:
        if pid not in available:
            raise DatasetError(f'Pacient {pid} v datasetu není (k dispozici: {", ".join(available)}).')
        report.parts.append(IngestPart(pid, load_patient(root, pid), expected=EXPECTED_PATIENT_TOTALS.get(pid)))
    for part in report.parts:
        if part.expected is not None and len(part.resources) != part.expected:
            report.warnings.append(
                f'{part.label}: v souborech {len(part.resources)} resources, DATASET §2 uvádí {part.expected}'
            )
        bad = id_index_mismatches(part.resources)
        if bad:
            report.warnings.append(f'{part.label}: ID mimo konvenci services/fhir/ids.py: {", ".join(bad)}')
    if include_shared and not patients and report.unique_resources != EXPECTED_TOTAL:
        report.warnings.append(f'celkem {report.unique_resources} unikátních resources, DATASET §2 uvádí {EXPECTED_TOTAL}')
    return report


def ingest(
    root: Path,
    patients: Iterable[str] | None = None,
    bundle_type: str = 'transaction',
    include_shared: bool = True,
    log: Callable[[str], None] = lambda msg: None,
) -> IngestReport:
    """Celý ingest do IRIS FHIR: Questionnaire → studie → pacienti, pak kontrola počtů."""
    report = collect(root, patients, include_shared)
    for part in report.parts:
        part.upload = upload(part.resources, part.label, bundle_type)
        log(f'{part.label}: odesláno {part.upload.sent}, odpověď {dict(part.upload.statuses)}')
    for part in report.parts:
        pid = part.label if re.fullmatch(r'P\d{2}', part.label) else None
        part.checks = verify(part.resources, part.label, pid)
        bad = [c for c in part.checks if not c.ok]
        log(f'{part.label}: kontrola počtů {"OK" if not bad else f"{len(bad)} nesedí"}')
    return report
