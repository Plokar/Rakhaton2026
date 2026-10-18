"""Zápisy aplikace do IRIS FHIR (ARCH §4.3 výstupy). Struktura kopíruje předchozí MDT v datasetu (D-009)."""
import html
import logging
import re
from datetime import datetime

from services.fhir import client as fhir
from services.fhir.ids import resource_type_for_id
from services.fhir.ingest import prune
from services.fhir.values import ref_id

logger = logging.getLogger(__name__)

BASE = 'https://rakathon.example.org/fhir'
CS = f'{BASE}/CodeSystem'
SD = f'{BASE}/StructureDefinition'
AI_LABEL = {'system': 'http://terminology.hl7.org/CodeSystem/v3-ObservationValue', 'code': 'AIAST',
            'display': 'artificial intelligence asserted'}
MDT_TYPES = {'primarni': 'Primární projednání', 'progrese': 'Progrese / recidiva', 'restaging': 'Restaging / hodnocení odpovědi'}
INTENTS = {'kurativni': 'Kurativní', 'paliativni': 'Paliativní', 'odlozeno': 'Rozhodnutí odloženo'}
MODALITIES = {'chirurgie': 'Chirurgie', 'chemoterapie': 'Chemoterapie', 'rt': 'Radioterapie', 'hormonalni': 'Hormonální léčba',
              'cilena': 'Cílená léčba', 'imunoterapie': 'Imunoterapie', 'jina-systemova': 'Jiná systémová léčba',
              'diagnostika': 'Diagnostika', 'sledovani': 'Sledování'}
ROLES_CS = {'chair': 'předseda komise', 'surgeon': 'chirurg', 'oncologist': 'klinický onkolog',
            'radiation_oncologist': 'radiační onkolog', 'radiologist': 'radiolog', 'pathologist': 'patolog',
            'pulmonologist': 'pneumolog', 'cardiologist': 'kardiolog', 'patient': 'pacient',
            'nuclear_medicine': 'nukleární medicína', 'palliative_care': 'paliativní péče',
            'geriatrician': 'geriatr', 'geneticist': 'klinický genetik', 'coordinator': 'koordinátor'}
SEVERITY = {'high': 'high', 'moderate': 'moderate', 'low': 'low'}
LIGHTS = {'green': 'nevylučuje', 'orange': 'pozor', 'red': 'vylučuje', 'grey': 'nelze posoudit', 'skipped': 'nehodnoceno'}
RE_MDT = 'Plánované re-MDT'
_FOCUS_PREFIX = 'Požadované zaměření MDT:'


# ── nominace a termín ─────────────────────────────────────────────────────────
def nomination_task(patient_id: str, service_request_id: str) -> dict:
    """`Task` nominace (stav žádanky + termín MDT), `Task.focus` → `ServiceRequest`."""
    # IRIS neznámé parametry ignoruje, proto i filtr na focus u klienta
    task = next((t for t in fhir.search('Task', patient=patient_id)
                 if ref_id(t.get('focus')) == service_request_id), None)
    if task is None:
        raise LookupError(f'Task pro {service_request_id} v IRIS není')
    return task


def set_mdt_date(patient_id: str, service_request_id: str, start: datetime) -> dict:
    """Přesun mezi boardy / změna termínu (FR-P1): `Task.restriction.period.start` = datum zasedání."""
    task = nomination_task(patient_id, service_request_id)
    task.setdefault('restriction', {}).setdefault('period', {})['start'] = start.isoformat()
    return fhir.put(task)


# ── potvrzení závěru (T-209) ─────────────────────────────────────────────────
def next_mdt_id(patient_id: str) -> str:
    """Číslo zasedání = poslední `Pxx-mdtNN` + 1 (P03 → P03-mdt02)."""
    pattern = re.compile(rf'^{re.escape(patient_id)}-mdt(\d+)$')
    numbers = [int(m[1]) for c in fhir.search('Composition', patient=patient_id) if (m := pattern.match(c['id']))]
    return f'{patient_id}-mdt{max(numbers, default=0) + 1:02d}'


def _ref(rtype: str, rid: str) -> dict:
    return {'reference': f'{rtype}/{rid}'}


def _person(user_id: str, name: str) -> dict:
    """Lékař v IRIS (`LEK-…`, i účty aplikace `LEK-APP-…`, T-328) jako reference se jménem, jinak jen jméno."""
    if str(user_id).startswith('LEK-'):
        return {**_ref('Practitioner', user_id), **({'display': name} if name and name != user_id else {})}
    return {'display': name}


def _div(text: str) -> dict:
    body = '<br/>'.join(html.escape(line) for line in str(text).splitlines()) or '—'
    return {'status': 'generated', 'div': f'<div xmlns="http://www.w3.org/1999/xhtml">{body}</div>'}


def _coding(system: str, code: str, display: str) -> dict:
    return {'coding': [{'system': f'{CS}/{system}', 'code': code, 'display': display}]}


def _ai(*sources: str) -> dict:
    return {'meta': {'security': [AI_LABEL]}} if any(s in ('ai', 'ai_edited') for s in sources) else {}


def _cited_resources(evidence_ids) -> list[dict]:
    """Citace faktů pacienta → reference na resource (odstavec `#n` → celý resource), bez guidelines a kritérií."""
    out = {}
    for eid in evidence_ids:
        base = eid.split('#', 1)[0]
        rtype = resource_type_for_id(base)
        if rtype and re.match(r'^P\d{2}-', base):
            out[base] = _ref(rtype, base)
    return list(out.values())


def record_extras(s: dict) -> list[tuple[str, str]]:
    """Zvažované možnosti, soulad s guidelines a odlišná stanoviska (zadání C, T-326) jako sekce záznamu MDT."""
    out = []
    options = s.get('options_considered') or []
    if options:
        lines = []
        for i, o in enumerate(options, 1):
            light = f" (semafor: {LIGHTS[o['light']]})" if o.get('light') in LIGHTS else ''
            lines.append(f"{i}. {o['title']}{' – zvoleno' if o.get('chosen') else ''}{light}")
        out.append(('Zvažované možnosti', '\n'.join(lines)))
    compliance = s.get('guideline_compliance')
    if compliance:
        text = 'Ano.' if compliance['compliant'] else 'Ne.'
        if compliance.get('reason'):
            text += f" Zdůvodnění: {compliance['reason']}"
        if compliance.get('citations'):
            text += f" ({', '.join(compliance['citations'])})"
        out.append(('Soulad s doporučenými postupy', text))
    dissent = s.get('dissent') or []
    if dissent:
        out.append(('Odlišná stanoviska', '\n'.join(
            f"{d['member']} ({ROLES_CS.get(d['role'], d['role'])}): {d['text']}" for d in dissent)))
    return out


def guideline_deviation(s: dict) -> str | None:
    """Kontrola souladu s guidelines při zápisu (zadání B2): odchylka nic neblokuje, jen chce krátké zdůvodnění.

    Odchylka = komise zvolila postup, který má v semaforu „pozor“ nebo „vylučuje“ (barvu počítá kód, D-015),
    nebo předseda sám uvedl „není v souladu“. Vrátí text pro lékaře, nebo None.
    """
    risky = [o['title'] for o in s.get('options_considered') or [] if o.get('chosen') and o.get('light') in ('red', 'orange')]
    compliance = s.get('guideline_compliance')
    if not risky and not (compliance and not compliance['compliant']):
        return None
    if compliance and compliance.get('reason', '').strip():
        return None
    if risky:
        return (f"Zvolený postup má v semaforu „pozor“ nebo „vylučuje“ ({'; '.join(risky)}). "
                'Uveďte soulad s doporučenými postupy a krátké zdůvodnění.')
    return 'Závěr se odchyluje od doporučených postupů. Doplňte krátké zdůvodnění odchylky.'


def decision_gaps(decision: dict, red_flag_ids) -> list[str]:
    """Co před potvrzením závěru zbývá (stejná pravidla jako `decisionChecklist` v UI): nic se nesmí zapomenout.
    Prázdný seznam = jde potvrdit. Odchylku od guidelines hlídá `guideline_deviation`."""
    s = decision['sections']
    todo = []
    if not s['question']['text'].strip():
        todo.append('Projednaná otázka')
    if not s['assessment']['text'].strip():
        todo.append('Klinické zhodnocení')
    if not any(o.get('chosen') for o in s.get('options_considered') or []) \
            and not any(r['text'].strip() for r in s.get('recommendation') or []):
        todo.append('Zvolený postup (zvažované možnosti) nebo krok doporučeného postupu')
    if not s.get('guideline_compliance'):
        todo.append('V souladu s guidelines? Ano / Ne')
    if not s['conclusion']['text'].strip():
        todo.append('Závěr MDT')
    unnamed = [a.get('name') or 'bez role' for a in decision.get('attendees') or []
               if not a.get('user_id') and a.get('role') != 'chair']
    if unnamed:
        todo.append(f'Přítomní: vybrat lékaře ({", ".join(unnamed)})')
    for i, t in enumerate(decision.get('tasks') or [], 1):
        gaps = [name for name, ok in (('popis', t.get('description', '').strip()), ('komu', t.get('owner')),
                                      ('termín', t.get('due_date'))) if not ok]
        if gaps:
            todo.append(f'Úkol {i}: {", ".join(gaps)}')
    acked = set(decision.get('red_flags_acknowledged') or [])
    if open_flags := [f for f in red_flag_ids if f not in acked]:
        todo.append(f'Varovné signály vzít na vědomí: {len(open_flags)}')
    return todo


def build_decision_bundle(decision: dict, *, patient_id: str, service_request: dict, task: dict, mdt_id: str,
                          mdt_date: datetime, confirmed_by: dict, red_flags: dict[str, dict], now: datetime) -> tuple[dict, dict]:
    """Potvrzený závěr (Decision §8.4) → transaction Bundle + `fhir_ids`. Čistá funkce (testovatelná bez IRIS)."""
    s = decision['sections']
    focus = next((c.get('text', '') for c in service_request.get('category', []) if c.get('text')), '')
    focus = focus.replace(_FOCUS_PREFIX, '').strip()
    date = mdt_date.date().isoformat()
    patient = _ref('Patient', patient_id)
    chair = next((a for a in decision['attendees'] if a['role'] == 'chair'), None)
    chair_ref = _person(chair['user_id'], chair['name']) if chair else {'display': confirmed_by['name']}
    ids = {'composition': mdt_id, 'careplan': f'{mdt_id}-careplan', 'careteam': f'{mdt_id}-careteam',
           'tasks': [], 'detected_issues': [], 'research_subjects': [], 'provenance': f'{mdt_id}-prov'}
    resources = []

    careteam = {
        'resourceType': 'CareTeam', 'id': ids['careteam'], 'status': 'active', 'name': f'MDT – {focus} ({date})',
        'subject': patient,
        'participant': [{'role': [{'text': ROLES_CS.get(a['role'], a['role'])}], 'member': _person(a['user_id'], a['name'])}
                        for a in decision['attendees']],
    }
    activities = [{'detail': {'kind': 'ServiceRequest', 'status': 'scheduled',
                              'code': _coding('mdt-modalita', r['modality'], MODALITIES.get(r['modality'], r['modality'])),
                              'description': f"{i}. {r['text']}"}}
                  for i, r in enumerate(s['recommendation'], 1)]
    if s.get('re_mdt'):
        activities.append({'detail': {'status': 'scheduled', 'code': {'text': RE_MDT},
                                      'scheduledPeriod': {'start': s['re_mdt']['date']},
                                      'description': f"{s['re_mdt']['reason']} ({s['re_mdt']['date']})"}})
    careplan = {
        'resourceType': 'CarePlan', 'id': ids['careplan'], 'status': 'active', 'intent': 'plan',
        'category': [_coding('mdt-lecebny-zamer', s['intent'], INTENTS[s['intent']])], 'title': 'Doporučení MDT',
        'subject': patient, 'created': date, 'careTeam': [_ref('CareTeam', ids['careteam'])],
        'supportingInfo': [_ref('ServiceRequest', service_request['id'])],   # R4: basedOn jen CarePlan
        'addresses': [r for r in service_request.get('reasonReference', []) if r.get('reference', '').startswith('Condition/')],
        'activity': activities, **_ai(*(r['source'] for r in s['recommendation'])),
    }
    resources += [careteam, careplan]

    for i, t in enumerate(decision['tasks'], 1):
        tid = f'{mdt_id}-task{i:02d}'
        ids['tasks'].append(tid)
        resources.append({
            'resourceType': 'Task', 'id': tid, 'status': t['status'], 'intent': 'order', 'description': t['description'],
            'basedOn': [_ref('CarePlan', ids['careplan'])], 'for': patient, 'authoredOn': now.isoformat(),
            'owner': _person(t['owner'], t.get('owner_name') or t['owner']), 'restriction': {'period': {'end': t['due_date']}}, **_ai(t['source']),
        })

    for i, flag_id in enumerate(decision.get('red_flags_acknowledged', []), 1):
        rid = f'{mdt_id}-rf{i:02d}'
        ids['detected_issues'].append(rid)
        flag = red_flags.get(flag_id, {})
        implicated = _cited_resources(flag.get('citations') or [flag_id.split(':', 1)[-1]])
        detail = flag.get('description') or flag.get('title') or flag_id
        if flag.get('guideline'):
            detail += f" ({flag['guideline']})"
        issue = {
            'resourceType': 'DetectedIssue', 'id': rid, 'status': 'final',
            'code': {'text': flag.get('rule') or flag_id.split(':', 1)[0]}, 'patient': patient,
            'identifiedDateTime': now.isoformat(), 'detail': detail,
            'mitigation': [{'action': {'text': 'Projednáno na MDT'}, 'date': now.isoformat(), 'author': chair_ref}],
        }
        if flag.get('severity') in SEVERITY:
            issue['severity'] = SEVERITY[flag['severity']]
        if implicated:
            issue['implicated'] = implicated
        resources.append(issue)

    for i, study in enumerate((s.get('trial') or {}).get('study_ids', []), 1):
        rid = f'{mdt_id}-rs{i:02d}'
        ids['research_subjects'].append(rid)
        resources.append({'resourceType': 'ResearchSubject', 'id': rid, 'status': 'candidate',
                          'study': _ref('ResearchStudy', study), 'individual': patient})

    sections = [('Projednaná otázka', s['question']['text']), ('Klinické zhodnocení', s['assessment']['text']),
                ('Léčebný záměr', INTENTS[s['intent']]),
                ('Doporučený postup', '\n'.join(f"{i}. [{MODALITIES.get(r['modality'], r['modality'])}] {r['text']}"
                                                for i, r in enumerate(s['recommendation'], 1)))]
    if s.get('extra_diagnostics'):
        sections.append(('Doplňující diagnostika', s['extra_diagnostics']['text']))
    sections.append(('Klinická studie', s['trial']['text'] if s.get('trial') else 'Nezvažována.'))
    if s.get('re_mdt'):
        sections.append(('Plánované re-MDT', f"{s['re_mdt']['reason']} ({s['re_mdt']['date']})"))
    if s.get('conditional'):
        sections.append(('Podmíněné doporučení', f"{s['conditional']['text']} Chybí: {', '.join(s['conditional']['missing'])}."))
    if s.get('tumor_priority'):
        sections.append(('Priorita nádorů', s['tumor_priority']['text']))
    sections.extend(record_extras(s))
    sections.append(('Závěr MDT', s['conclusion']['text']))
    composition_sections = [{'title': title, 'text': _div(text)} for title, text in sections]
    composition_sections[1]['entry'] = _cited_resources(s['assessment']['citations'])
    if ids['detected_issues']:
        composition_sections.append({'title': 'Varovné signály', 'text': _div(f"{len(ids['detected_issues'])} projednaných varování"),
                                     'entry': [_ref('DetectedIssue', d) for d in ids['detected_issues']]})
    composition_sections = [{k: v for k, v in sec.items() if v} for sec in composition_sections]
    sources = [v['source'] for v in s.values() if isinstance(v, dict) and 'source' in v]
    composition = {
        'resourceType': 'Composition', 'id': mdt_id,
        # nová verze potvrzeného záznamu (T-332) je „amended“, IRIS drží předchozí verzi v historii
        'identifier': {'system': f'{BASE}/sid/mdt-zaznam', 'value': mdt_id},
        'status': 'amended' if decision.get('version', 1) > 1 else 'final',
        'type': _coding('mdt-typ-zaznamu', 'mdt-zaznam', 'Záznam MDT'),
        'category': [_coding('mdt-typ-projednani', decision['mdt_type'], MDT_TYPES[decision['mdt_type']]),
                     {'text': f'Zaměření MDT: {focus}'}],
        'subject': patient, 'date': mdt_date.isoformat(), 'author': [chair_ref],
        'attester': [{'mode': 'legal', 'party': chair_ref, 'time': now.isoformat()}],
        'custodian': _ref('Organization', 'ORG-FN'), 'title': f'Záznam MDT – {focus} – {date}',
        'event': [{'period': {'start': date}, 'detail': [_ref('CarePlan', ids['careplan']), _ref('CareTeam', ids['careteam'])]}],
        'section': composition_sections,
        'extension': [
            {'url': f'{SD}/mdt-forma-zasedani', 'valueString': 'prezenčně'},
            *([{'url': f'{SD}/mdt-osetrujici-lekar', 'valueReference': service_request['requester']}]
              if service_request.get('requester') else []),
            {'url': f'{SD}/mdt-ucast-pacienta', 'valueBoolean': bool(decision.get('patient_present'))},
        ],
        **_ai(*sources),
    }
    resources.insert(0, composition)

    service_request = {**service_request, 'status': 'completed'}
    task = {**task, 'status': 'completed',
            'businessStatus': _coding('mdt-stav-zadanky', 'projednana', 'Projednaná')}
    resources += [service_request, task]

    cited = _cited_resources(s['assessment']['citations'] + [c for f in red_flags.values() for c in f.get('citations', [])])
    resources.append({
        'resourceType': 'Provenance', 'id': ids['provenance'], 'recorded': now.isoformat(),
        'target': [_ref(r['resourceType'], r['id']) for r in resources],
        'agent': [
            {'type': _participant('assembler', 'Assembler'), 'who': _ref('Device', 'mdt-copilot')},
            {'type': _participant('verifier', 'Verifier'), 'who': chair_ref},
        ],
        **({'entity': [{'role': 'source', 'what': ref} for ref in cited]} if cited else {}),
    })
    bundle = _transaction(resources)
    return bundle, ids


def _transaction(resources: list[dict]) -> dict:
    """Transaction Bundle s `PUT`; `prune`, protože IRIS odmítne prázdné pole (např. závěr bez kroků → `CarePlan.activity: []`)."""
    return {'resourceType': 'Bundle', 'type': 'transaction', 'entry': [
        {'fullUrl': f"{BASE}/{r['resourceType']}/{r['id']}", 'resource': prune(r),
         'request': {'method': 'PUT', 'url': f"{r['resourceType']}/{r['id']}"}} for r in resources
    ]}


def _participant(code: str, display: str) -> dict:
    return {'coding': [{'system': 'http://terminology.hl7.org/CodeSystem/provenance-participant-type',
                        'code': code, 'display': display}]}


def confirm_decision(decision: dict, *, patient_id: str, service_request_id: str, mdt_date: datetime,
                     confirmed_by: dict, red_flags: dict[str, dict], now: datetime, mdt_id: str | None = None) -> dict:
    """Jeden transaction Bundle do IRIS. Vrací `fhir_ids`; při chybě `FhirError` a nic se nezapíše (transaction).
    `mdt_id` = nová verze už potvrzeného záznamu (T-332): stejné ID, IRIS uchová předchozí verzi v historii."""
    bundle, ids = build_decision_bundle(
        decision, patient_id=patient_id, service_request=fhir.read('ServiceRequest', service_request_id),
        task=nomination_task(patient_id, service_request_id), mdt_id=mdt_id or next_mdt_id(patient_id), mdt_date=mdt_date,
        confirmed_by=confirmed_by, red_flags=red_flags, now=now,
    )
    fhir.transaction(bundle)
    _reindex_vectors(patient_id)
    return ids


def _reindex_vectors(patient_id: str) -> None:
    """Nový záznam MDT do vektorového hledání a groundingu (ARCH §4.5). Selhání potvrzení nebrání:
    oficiální záznam je už ve FHIR, vektory jdou dopočítat (`ingest_dataset --skip-fhir --patients Pxx`)."""
    try:
        from services.iris import indexing
        indexing.index_patient(patient_id)
    except Exception:
        logger.warning('Reindex vektorů %s po zápisu závěru selhal (ručně: ingest_dataset --skip-fhir --patients %s)',
                       patient_id, patient_id, exc_info=True)


# ── zařazení pacienta (T-211, FR-P4) ─────────────────────────────────────────
INTENT_EXT = f'{SD}/mdt-predpokladany-zamer'
INTENT_CODES = {'C': 'kurativni', 'P': 'paliativni'}


def build_intake_bundle(*, patient_id: str, case_no: int, service_request: dict, ecog: int | None, intent: str | None,
                        acknowledged: list[tuple[int, dict]], warnings: dict[str, dict], entered_by: str,
                        now: datetime) -> tuple[dict, list[str]]:
    """Ruční údaje ze zařazení → transaction: ECOG `Observation/Pxx-ecog-caseNN`, záměr C/P na nominaci,
    odkliknutá varování `DetectedIssue/Pxx-caseNN-wNN` (mitigation, D-019) a `Provenance` ručního zadání."""
    patient = _ref('Patient', patient_id)
    author = service_request.get('requester') or {'display': entered_by}   # zadávající lékař nominace
    prefix = f'{patient_id}-case{case_no:02d}'
    resources = []
    if ecog is not None:
        resources.append({
            'resourceType': 'Observation', 'id': f'{patient_id}-ecog-case{case_no:02d}', 'status': 'final',
            'category': [{'coding': [{'system': 'http://terminology.hl7.org/CodeSystem/observation-category', 'code': 'survey'}]}],
            'code': {'coding': [{'system': 'http://loinc.org', 'code': '89247-1', 'display': 'ECOG Performance Status score'}],
                     'text': 'ECOG – hodnoceno lékařem'},
            'subject': patient, 'effectiveDateTime': now.isoformat(), 'valueInteger': ecog, 'performer': [author],
            'note': [{'text': f'Zadáno při zařazení do MDT ({entered_by})'}],
        })
    if intent in INTENT_CODES:
        code = INTENT_CODES[intent]
        extensions = [e for e in service_request.get('extension', []) if e.get('url') != INTENT_EXT]
        extensions.append({'url': INTENT_EXT, 'valueCodeableConcept': _coding('mdt-lecebny-zamer', code, INTENTS[code])})
        resources.append({**service_request, 'extension': extensions})
    for i, ack in acknowledged:     # (pořadí v MdtCase.acknowledged_warnings od 1, odkliknutí)
        w = warnings.get(ack['id'], {})
        issue = {
            'resourceType': 'DetectedIssue', 'id': f'{prefix}-w{i:02d}', 'status': 'final',
            'code': {'text': w.get('title') or ack['id']}, 'patient': patient, 'identifiedDateTime': ack.get('at') or now.isoformat(),
            'detail': f"{w.get('detail') or ack['id']} [{ack['id']}]",
            'mitigation': [{'action': {'text': 'Beru na vědomí'}, 'date': ack.get('at') or now.isoformat(), 'author': author}],
        }
        if w.get('severity') in SEVERITY:
            issue['severity'] = SEVERITY[w['severity']]
        if implicated := _cited_resources(w.get('citations', [])):
            issue['implicated'] = implicated
        resources.append(issue)
    if resources:
        resources.append({
            'resourceType': 'Provenance', 'id': f'{prefix}-prov', 'recorded': now.isoformat(),
            'target': [_ref(r['resourceType'], r['id']) for r in resources],
            'activity': {'text': 'Ruční zadání při zařazení pacienta do MDT'},
            'agent': [{'type': _participant('author', 'Author'), 'who': author}],
        })
    bundle = _transaction(resources)
    return bundle, [f"{r['resourceType']}/{r['id']}" for r in resources]


def write_intake(*, patient_id: str, case_no: int, service_request_id: str, ecog: int | None, intent: str | None,
                 acknowledged: list[tuple[int, dict]], warnings: dict[str, dict], entered_by: str, now: datetime) -> list[str]:
    bundle, written = build_intake_bundle(
        patient_id=patient_id, case_no=case_no, service_request=fhir.read('ServiceRequest', service_request_id),
        ecog=ecog, intent=intent, acknowledged=acknowledged, warnings=warnings, entered_by=entered_by, now=now)
    if bundle['entry']:
        fhir.transaction(bundle)
    return written
