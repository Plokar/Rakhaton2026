"""Export závěru MDT (T-210, FR-C4): FHIR document Bundle z IRIS a PDF (+ `DocumentReference/Pxx-mdtNN-pdf`)."""
import base64
import io
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from services.fhir import client as fhir
from services.fhir.writeback import BASE, INTENTS, MODALITIES, ROLES_CS

TASK_STATUS = {'requested': 'zadáno', 'in-progress': 'probíhá', 'completed': 'hotovo'}
SOURCE_LABEL = {'ai': ' [AI návrh]', 'ai_edited': ' [AI, upraveno lékařem]', 'human': ''}
_FONT_DIRS = ('/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/dejavu', 'C:/Windows/Fonts')


# ── FHIR document Bundle ─────────────────────────────────────────────────────
def _references(node) -> set[str]:
    found = set()
    if isinstance(node, dict):
        ref = node.get('reference')
        if isinstance(ref, str) and ref.count('/') == 1 and '#' not in ref and not ref.startswith('http'):
            found.add(ref)
        for v in node.values():
            found |= _references(v)
    elif isinstance(node, list):
        for v in node:
            found |= _references(v)
    return found


def document_bundle(fhir_ids: dict, now: datetime) -> dict:
    """Composition jako 1. entry + zápis komise + všechno, na co přímo odkazuje (pacient, lékaři, citované zdroje)."""
    record = [('Composition', fhir_ids['composition']), ('CarePlan', fhir_ids['careplan']), ('CareTeam', fhir_ids['careteam'])]
    record += [('Task', i) for i in fhir_ids['tasks']] + [('DetectedIssue', i) for i in fhir_ids['detected_issues']]
    record += [('ResearchSubject', i) for i in fhir_ids['research_subjects']] + [('Provenance', fhir_ids['provenance'])]
    if fhir_ids.get('document_reference_pdf'):
        record.append(('DocumentReference', fhir_ids['document_reference_pdf']))
    resources = {f'{t}/{i}': fhir.read(t, i) for t, i in record}
    # ponytail: jen jeden skok referencí; hlubší graf (zdroje zdrojů) je v IRIS, dokument by zbytečně nabobtnal
    for ref in sorted(set().union(*map(_references, list(resources.values()))) - set(resources)):
        try:
            resources[ref] = fhir.read(*ref.split('/'))
        except fhir.FhirError:
            pass
    return {
        'resourceType': 'Bundle', 'type': 'document', 'timestamp': now.isoformat(),
        'identifier': {'system': f'{BASE}/sid/mdt-zaznam', 'value': fhir_ids['composition']},
        'entry': [{'fullUrl': f'{BASE}/{ref}', 'resource': r} for ref, r in resources.items()],
    }


# ── PDF ──────────────────────────────────────────────────────────────────────
def _fonts() -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for d in _FONT_DIRS:
        regular, bold = Path(d, 'DejaVuSans.ttf'), Path(d, 'DejaVuSans-Bold.ttf')
        if regular.is_file() and bold.is_file():
            pdfmetrics.registerFont(TTFont('DejaVu', str(regular)))
            pdfmetrics.registerFont(TTFont('DejaVu-Bold', str(bold)))
            return 'DejaVu', 'DejaVu-Bold'
    return 'Helvetica', 'Helvetica-Bold'      # bez diakritiky; v kontejneru je fonts-dejavu-core


def decision_pdf(decision: dict, *, title: str, mdt_date: datetime, patient: dict | None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    regular, bold = _fonts()
    body = ParagraphStyle('body', fontName=regular, fontSize=9.5, leading=13)
    small = ParagraphStyle('small', parent=body, fontSize=8, leading=10, textColor=colors.grey)
    h1 = ParagraphStyle('h1', parent=body, fontName=bold, fontSize=15, leading=19)
    h2 = ParagraphStyle('h2', parent=body, fontName=bold, fontSize=11, leading=15, spaceBefore=6, keepWithNext=1)
    warn = ParagraphStyle('warn', parent=body, fontName=bold, textColor=colors.red)

    def p(text, style=body):
        return Paragraph(escape(str(text)).replace('\n', '<br/>'), style)

    s = decision['sections']
    story = [p(f'Záznam MDT – {title}', h1), p(f'Zasedání {mdt_date:%d. %m. %Y %H:%M}', body)]
    if patient:
        dg = patient.get('diagnosis') or {}
        story.append(p(f"{patient['display_name']} · {dg.get('icd10', '')} {dg.get('text', '')}".strip()))
    if decision['status'] != 'confirmed':
        story.append(p('NÁVRH – nepotvrzeno předsedou komise', warn))
    story.append(Spacer(1, 4 * mm))

    def section(name, text, source='human'):
        story.extend([p(name + SOURCE_LABEL.get(source, ''), h2), p(text)])

    section('Projednaná otázka', s['question']['text'], s['question']['source'])
    section('Klinické zhodnocení', s['assessment']['text'], s['assessment']['source'])
    if s['assessment'].get('citations'):
        story.append(p('Zdroje: ' + ', '.join(s['assessment']['citations']), small))
    section('Léčebný záměr', INTENTS[s['intent']])
    story.append(p('Doporučený postup', h2))
    for i, r in enumerate(s['recommendation'], 1):
        story.append(p(f"{i}. [{MODALITIES.get(r['modality'], r['modality'])}] {r['text']}{SOURCE_LABEL.get(r['source'], '')}"))
    if s.get('extra_diagnostics'):
        section('Doplňující diagnostika', s['extra_diagnostics']['text'], s['extra_diagnostics']['source'])
    section('Klinická studie', s['trial']['text'] if s.get('trial') else 'Nezvažována.', (s.get('trial') or {}).get('source', 'human'))
    if s.get('re_mdt'):
        section('Plánované re-MDT', f"{s['re_mdt']['date']}: {s['re_mdt']['reason']}")
    if s.get('conditional'):
        section('Podmíněné doporučení', f"{s['conditional']['text']} Chybí: {', '.join(s['conditional']['missing'])}.",
                s['conditional']['source'])
    if s.get('tumor_priority'):
        section('Priorita nádorů', s['tumor_priority']['text'], s['tumor_priority']['source'])
    section('Závěr MDT', s['conclusion']['text'], s['conclusion']['source'])

    if decision['tasks']:
        story.append(p('Úkoly', h2))
        rows = [[p('Úkol', small), p('Odpovídá', small), p('Termín', small), p('Stav', small)]]
        rows += [[p(t['description']), p(t['owner']), p(t['due_date']), p(TASK_STATUS.get(t['status'], t['status']))]
                 for t in decision['tasks']]
        table = Table(rows, colWidths=[92 * mm, 34 * mm, 26 * mm, 22 * mm], repeatRows=1)
        table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.3, colors.lightgrey), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        story.append(table)
    story.append(p('Přítomní', h2))
    story.append(p(', '.join(f"{a['name']} ({ROLES_CS.get(a['role'], a['role'])})" for a in decision['attendees'])
                   + ('; pacient přítomen' if decision.get('patient_present') else '')))
    story.append(Spacer(1, 6 * mm))
    if decision.get('confirmed_by'):
        story.append(p(f"Potvrdil: {decision['confirmed_by']['name']}, {decision.get('confirmed_at', '')[:16].replace('T', ' ')}"))
    if decision.get('fhir_ids'):
        story.append(p(f"IRIS FHIR: Composition/{decision['fhir_ids']['composition']}", small))
    story.append(p('Části označené [AI] připravil MDT Copilot (AI asistent); obsah zkontroloval a potvrdil lékař. '
                   'Fiktivní data, nejedná se o zdravotnickou dokumentaci.', small))

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, title=f'Záznam MDT – {title}', author='MDT Copilot',
                      leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm).build(story)
    return buf.getvalue()


def store_pdf(patient_id: str, mdt_id: str, pdf: bytes, now: datetime) -> str:
    """`DocumentReference/Pxx-mdtNN-pdf` v IRIS (R4: `relatesTo` jen na DocumentReference → vazba v `context.related`)."""
    rid = f'{mdt_id}-pdf'
    fhir.put({
        'resourceType': 'DocumentReference', 'id': rid, 'status': 'current',
        'type': {'text': 'Záznam MDT (PDF)'}, 'subject': {'reference': f'Patient/{patient_id}'}, 'date': now.isoformat(),
        'content': [{'attachment': {'contentType': 'application/pdf', 'data': base64.b64encode(pdf).decode(),
                                    'title': f'{mdt_id}.pdf', 'creation': now.isoformat()}}],
        'context': {'related': [{'reference': f'Composition/{mdt_id}'}]},
    })
    return rid
