"""FHIR ID a Evidence ID datasetu (D-005, D-006, ARCH §5.2, DATASET §3).

- ``sanitize_id`` / ``sanitize_reference``: FHIR povoluje v ID jen ``[A-Za-z0-9-.]{1,64}``, dataset má ``_``
  (``P01-lab01-hb_f`` → ``P01-lab01-hb-f``, DATASET §6.2).
- ``resource_type_for_id``: index ID → ResourceType podle konvence ID datasetu a výstupů z ARCH §4.3.
  Resolver citací (T-104) z něj pozná, kde v IRIS resource hledat.
- ``parse_evidence_id``: rozloží citaci (``P03-img03#2``, ``KRC-2.4``, ``RKT-03/V3``, ``EXT-…``).
  ``None`` = neplatný formát, grounding validátor takové tvrzení označí ``unverified``.
"""
import re
from dataclasses import dataclass

from services.fhir.values import ref_id

_INVALID_ID_CHARS = re.compile(r'[^A-Za-z0-9.\-]')
_REFERENCE = re.compile(r'^(?P<head>(?:.*/)?[A-Z][A-Za-z]+/)(?P<id>[^/]+)(?P<history>/_history/.+)?$')


def sanitize_id(rid: str) -> str:
    return _INVALID_ID_CHARS.sub('-', rid)


def sanitize_reference(ref: str) -> str:
    """``Observation/P01-lab01-hb_f`` → ``Observation/P01-lab01-hb-f``; i absolutní URL. ``urn:``/``#`` nechá být."""
    m = _REFERENCE.match(ref)
    if not m or ref.startswith(('urn:', '#')):
        return ref
    return f"{m['head']}{sanitize_id(m['id'])}{m['history'] or ''}"


# Konvence ID (DATASET §3 + výstupy aplikace ARCH §4.3). Pořadí nehraje roli, vzory se nepřekrývají.
_GLOBAL_RULES = (
    (r'P\d{2}', 'Patient'),
    (r'LEK-[A-Za-z0-9-]+', 'Practitioner'),
    (r'ORG-[A-Za-z0-9-]+', 'Organization'),
    (r'MDT-PROMS-\d+', 'Questionnaire'),
    (r'RKT-\d{2}', 'ResearchStudy'),
    (r'RKT-\d{2}-kriteria', 'Group'),
    (r'mdt-copilot', 'Device'),
)
_PATIENT_RULES = (  # část ID za `Pxx-`
    (r'(dg|kom|ae)\d+', 'Condition'),                     # ae = nežádoucí účinek léčby (P05-ae1)
    (r'doc\d+', 'DocumentReference'),
    (r'img\d+-study', 'ImagingStudy'),
    (r'(img|pat|lab)\d+', 'DiagnosticReport'),
    (r'lab\d+-[a-z0-9-]+', 'Observation'),
    (r'(ecog|vaha|bm|tnm|neuro|anem|lvef|spiro|kour)\d+', 'Observation'),
    (r'ecog-case\d+', 'Observation'),                     # ECOG zadaný při zařazení (FR-P4)
    (r'med\d+', 'MedicationRequest'),
    (r'tx-[a-z0-9]+-\d+', 'MedicationAdministration'),
    (r'proc\d+', 'Procedure'),
    (r'prom\d+', 'QuestionnaireResponse'),
    (r'zad\d+', 'ServiceRequest'),
    (r'zad\d+-task', 'Task'),
    (r'mdt\d+(-rozhodnuti)?', 'Composition'),
    (r'mdt\d+-careplan', 'CarePlan'),
    (r'mdt\d+-careteam', 'CareTeam'),
    (r'mdt\d+-task\d+', 'Task'),
    (r'mdt\d+-rf\d+', 'DetectedIssue'),
    (r'mdt\d+-rs\d+', 'ResearchSubject'),
    (r'mdt\d+-prov', 'Provenance'),
    (r'mdt\d+-(prepis|pdf|pacient)', 'DocumentReference'),
    (r'case\d+-w\d+', 'DetectedIssue'),                   # odkliknuté varování (FR-P4)
    (r'case\d+-prov', 'Provenance'),
    (r'imp\d+', 'DocumentReference'),                     # zpráva vložená lékařem (BON-7)
    (r'imp\d+-(lab|bm|tnm|ecog|vit)\d+', 'Observation'),  # hodnota ze zprávy, druh v ID jako v datasetu
    (r'imp\d+-prov', 'Provenance'),
    (r'novy-prov', 'Provenance'),                         # pacient založený v aplikaci
)
_GLOBAL = [(re.compile(p), t) for p, t in _GLOBAL_RULES]
_PATIENT = [(re.compile(p), t) for p, t in _PATIENT_RULES]
_PATIENT_PREFIX = re.compile(r'(P\d{2})-(.+)')
_PRACTITIONER_PATIENT = re.compile(r'LEK-(P\d{2})-\d+')


def resource_type_for_id(rid: str) -> str | None:
    """Typ resource podle ID (``P03-img03`` → ``DiagnosticReport``). ``None`` = ID mimo konvence."""
    for pattern, rtype in _GLOBAL:
        if pattern.fullmatch(rid):
            return rtype
    m = _PATIENT_PREFIX.fullmatch(rid)
    if m:
        for pattern, rtype in _PATIENT:
            if pattern.fullmatch(m[2]):
                return rtype
    return None


# Observation.derivedFrom smí v R4 ukazovat jen na tyto typy. Odkazy datasetu na DiagnosticReport (bm, tnm → patologie)
# IRIS odmítá, proto je ingest přesouvá do této extension (Q15, DATASET §6.2).
DERIVED_FROM_TYPES = frozenset(
    {'DocumentReference', 'ImagingStudy', 'Media', 'QuestionnaireResponse', 'Observation', 'MolecularSequence'}
)
DERIVED_FROM_EXTENSION = 'https://rakathon.example.org/fhir/StructureDefinition/derived-from'


def derived_from(resource: dict) -> list[dict]:
    """Zdroje strukturovaného údaje: ``derivedFrom`` + extension ``derived-from`` (odkazy na DiagnosticReport).

    Kdo potřebuje zdroj ``Observation`` (citace, red flags, resolver), čte tuhle funkci, ne ``derivedFrom`` přímo.
    """
    refs = list(resource.get('derivedFrom') or [])
    refs += [
        e['valueReference'] for e in resource.get('extension') or []
        if e.get('url') == DERIVED_FROM_EXTENSION and e.get('valueReference')
    ]
    return refs


def derived_from_ids(resource: dict) -> list[str]:
    """ID zdrojových dokumentů hodnoty (bez duplicit), pro citace: ``P01-bm01`` → ``['P01-pat01']``."""
    return [i for i in dict.fromkeys(ref_id(r) for r in derived_from(resource)) if i]


def patient_id_for(rid: str) -> str | None:
    """Pacient, ke kterému ID patří (``P03-img03`` i ``LEK-P03-01`` → ``P03``)."""
    m = _PATIENT_PREFIX.fullmatch(rid) or _PRACTITIONER_PATIENT.fullmatch(rid)
    if m:
        return m[1]
    return rid if re.fullmatch(r'P\d{2}', rid) else None


@dataclass(frozen=True)
class EvidenceRef:
    evidence_id: str
    kind: str                          # resource | paragraph | guideline | trial_criterion | external
    resource_type: str | None = None   # u resource a paragraph
    resource_id: str | None = None     # u resource a paragraph
    paragraph: int | None = None       # P03-img03#2 → 2 (číslováno od 1, services/fhir/text.py)
    patient_id: str | None = None
    study_id: str | None = None        # u trial_criterion
    criterion: str | None = None       # RKT-03/V3 → V3


_GUIDELINE = re.compile(r'[A-Z]{3}-\d+\.\d+')                 # KRC-2.4
_CRITERION = re.compile(r'(RKT-\d{2})/([ZV]\d+)')             # RKT-03/V3
_EXTERNAL = re.compile(r'EXT-[A-Z0-9][A-Z0-9.-]*')            # EXT-EMA-DPD-2020 (D-016)
_PARAGRAPH = re.compile(r'(.+)#([1-9]\d*)')                   # P03-img03#2


def parse_evidence_id(evidence_id: str) -> EvidenceRef | None:
    """Rozloží Evidence ID podle ARCH §5.2. ``None`` pro neplatný formát nebo neznámé ID."""
    eid = (evidence_id or '').strip()
    if _GUIDELINE.fullmatch(eid):
        return EvidenceRef(eid, 'guideline')
    m = _CRITERION.fullmatch(eid)
    if m:
        return EvidenceRef(eid, 'trial_criterion', study_id=m[1], criterion=m[2])
    if _EXTERNAL.fullmatch(eid):
        return EvidenceRef(eid, 'external')
    m = _PARAGRAPH.fullmatch(eid)
    base, paragraph = (m[1], int(m[2])) if m else (eid, None)
    rtype = resource_type_for_id(base)
    if rtype is None:
        return None
    return EvidenceRef(
        eid, 'paragraph' if paragraph else 'resource', resource_type=rtype, resource_id=base,
        paragraph=paragraph, patient_id=patient_id_for(base),
    )
