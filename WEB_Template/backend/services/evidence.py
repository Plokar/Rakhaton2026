"""Resolver citací pro UI (T-104, ARCH §5.2, kontrakt `EvidenceSource` §8.2).

Evidence ID → zdroj: celý text se zvýrazněným odstavcem, hodnota s referenčním rozsahem a zdrojovým
dokumentem (`derivedFrom` + extension `derived-from`, Q15), pasáž guidelines nebo kritérium studie.
Čte jen z IRIS (FHIR + `MDT.GuidelineChunk` / `MDT.TrialCriterion`).
"""
from services.ai.text import resource_paragraphs, resource_text
from services.fhir import client as fhir
from services.fhir.ids import derived_from, parse_evidence_id
from services.iris import vector_store as vs
from services.patients import _category_text, _code, _date, _ref_id, _text

_AUTHOR_FIELDS = ('author', 'performer', 'resultsInterpreter', 'requester', 'asserter', 'recorder')


class InvalidEvidenceId(ValueError):
    pass


class EvidenceNotFound(LookupError):
    pass


def resolve(evidence_id: str, follow: bool = True) -> dict:
    ref = parse_evidence_id(evidence_id)
    if ref is None:
        raise InvalidEvidenceId(evidence_id)
    out = {'evidence_id': ref.evidence_id, 'kind': ref.kind}

    if ref.kind in ('guideline', 'external'):
        row = vs.get_guideline(ref.evidence_id) or _missing(ref.evidence_id)
        return {**out, 'title': f"{ref.evidence_id} – {row['Title']}", 'text': row['Text'],
                'source': row.get('Source'), 'region': row.get('Region')}
    if ref.kind == 'trial_criterion':
        row = vs.get_trial_criterion(ref.evidence_id) or _missing(ref.evidence_id)
        kind = 'kritérium zařazení' if row['Kind'] == 'inclusion' else 'kritérium vyřazení'
        return {**out, 'title': f"{row['StudyId']} – {kind} {ref.criterion}", 'text': row['Text'],
                'study_id': row['StudyId'], 'criterion_kind': row['Kind']}

    try:
        r = fhir.read(ref.resource_type, ref.resource_id)
    except fhir.FhirError as e:
        if e.status in (404, 410):
            _missing(ref.evidence_id)
        raise
    out.update({
        'resource_type': r['resourceType'], 'resource_id': r['id'], 'patient_id': ref.patient_id,
        'title': _title(r), 'date': _date(r) or None, 'department': _category_text(r) or None, 'author': _author(r),
    })
    text = resource_text(r) or _proms_text(r)
    if text:
        out['text'] = text
    if ref.kind == 'paragraph':
        paragraphs = resource_paragraphs(r)
        if ref.paragraph > len(paragraphs):
            _missing(ref.evidence_id)
        p = paragraphs[ref.paragraph - 1]
        out['highlight'] = {'paragraph': p.index, 'start': p.start, 'end': p.end}
    if r['resourceType'] == 'Observation':
        out['value'] = _value(r)
        if follow:
            out['derived_from'] = [_try_resolve(rid) for rid in _derived_ids(r)]
    return out


def _missing(evidence_id: str):
    raise EvidenceNotFound(evidence_id)


def _try_resolve(rid: str) -> dict:
    try:
        return resolve(rid, follow=False)
    except (EvidenceNotFound, InvalidEvidenceId):
        return {'evidence_id': rid, 'kind': 'resource', 'missing': True}


def _title(r: dict) -> str:
    t = r['resourceType']
    if t == 'DocumentReference':
        return _text(r.get('type')) or r.get('description', '')
    if t in ('Composition', 'ResearchStudy'):
        return r.get('title') or _text(r.get('type'))
    if t in ('MedicationAdministration', 'MedicationRequest'):
        return _text(r.get('medicationCodeableConcept'))
    if t == 'ServiceRequest':
        return 'Nominace na MDT'
    if t == 'Task':
        return 'Stav žádanky a termín MDT'
    if t == 'QuestionnaireResponse':
        return 'Dotazník pacienta (PROMs)'
    if t in ('Practitioner', 'Patient'):
        return (r.get('name') or [{}])[0].get('text', r['id'])
    return _text(r.get('code')) or t


def _author(r: dict) -> dict | None:
    for field in _AUTHOR_FIELDS:
        refs = r.get(field) or []
        refs = refs if isinstance(refs, list) else [refs]
        rid = next((_ref_id(x) for x in refs if (x.get('reference') or '').startswith('Practitioner/')), None)
        if rid:
            try:
                p = fhir.read('Practitioner', rid)
            except fhir.FhirError:
                return {'id': rid, 'text': rid, 'specialty': None}
            return {'id': rid, 'text': (p.get('name') or [{}])[0].get('text', rid),
                    'specialty': _text((p.get('qualification') or [{}])[0].get('code')) or None}
    return None


def _value(o: dict) -> dict:
    q = o.get('valueQuantity') or {}
    value = q.get('value', o.get('valueInteger'))
    rng = (o.get('referenceRange') or [{}])[0]
    text = o.get('valueString') or (f"{value} {q.get('unit', '')}".strip() if value is not None else '')
    return {
        'text': text, 'value': value, 'unit': q.get('unit'),
        'ref_low': rng.get('low', {}).get('value'), 'ref_high': rng.get('high', {}).get('value'),
        'interpretation': _code((o.get('interpretation') or [{}])[0], 'ObservationInterpretation') or None,
    }


def _derived_ids(o: dict) -> list[str]:
    return list(dict.fromkeys(_ref_id(x) for x in derived_from(o) if x.get('reference')))


def _proms_text(r: dict) -> str | None:
    """PROMs nemají `resource_text`; pro zdroj citace stačí `otázka: odpověď` po řádcích."""
    if r['resourceType'] != 'QuestionnaireResponse':
        return None
    lines = []
    for it in r.get('item', []):
        for a in it.get('answer', [])[:1]:
            v = next((v for k, v in a.items() if k.startswith('value')), None)
            if isinstance(v, dict):
                v = v.get('display') or v.get('code')
            lines.append(f"{it.get('text') or it['linkId']}: {v}")
    return '\n'.join(lines) or None
