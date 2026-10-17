"""Čtení PDF lékařské zprávy (T-323): textová vrstva, tabulky, hlavička / patička, zlom stránky, OCR skenu."""
import io

import pytest

from services.ai import pdf_text, report_import
from services.ai.text import split_paragraphs
from services.ai_service import MockAIProvider, NvidiaProvider


def _report_pdf() -> bytes:
    """Dvě strany: hlavička a patička na obou, oddíly verzálkami, tabulka laboratoře s linkami, věta přes zlom."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle

    body = ParagraphStyle('b', fontName='Helvetica', fontSize=10, leading=14)
    head = ParagraphStyle('h', fontName='Helvetica-Bold', fontSize=11, leading=16, spaceBefore=8)

    def frame(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.drawString(40, 815, 'Fakultni nemocnice - Klinika pneumologie')
        canvas.drawRightString(555, 25, f'Strana {doc.page} z 2')
        canvas.restoreState()

    table = Table([['Parametr', 'Vysledek', 'Jednotka'], ['Hemoglobin', '128', 'g/l'], ['CEA', '6,8', 'ug/l']])
    table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('FONT', (0, 0), (-1, -1), 'Helvetica', 9)]))
    story = [Paragraph('ANAMNEZA', head), Paragraph('Hypertenze, DM 2. typu. Kuracka 40 balickoroku.', body),
             Paragraph('LABORATOR', head), table, PageBreak(), Paragraph('DOPORUCENI', head),
             Paragraph(' '.join(['Spiroergometrie a PET-CT, kontrola po MDT.'] * 3), body)]
    out = io.BytesIO()
    SimpleDocTemplate(out, pagesize=A4, topMargin=60, bottomMargin=50).build(story, onFirstPage=frame, onLaterPages=frame)
    return out.getvalue()


def test_structured_report_text_layer():
    text = report_import.pdf_text(_report_pdf(), MockAIProvider(), lambda *a: None)
    assert 'Fakultni nemocnice' not in text and 'Strana' not in text            # hlavička, patička, číslo stránky
    paragraphs = [p.text for p in split_paragraphs(text)]
    assert 'Hemoglobin | 128 | g/l' in text and 'CEA | 6,8 | ug/l' in text     # tabulka po řádcích
    assert any(p.startswith('ANAMNEZA\nHypertenze') for p in paragraphs)       # nadpis u svého obsahu
    assert any(p.startswith('DOPORUCENI\nSpiroergometrie') for p in paragraphs)


def test_clean_text_joins_hyphenation_and_page_break():
    text = pdf_text.clean_text(['ZÁVĚR\nHraniční plicní funkce, doporučuji léčeb-\nného onkologa a kontrolu po', 'MDT.\n\nCA 19-\n9 v normě'])
    assert 'léčebného onkologa a kontrolu po\nMDT.' in text                        # věta přes zlom stránky
    assert 'CA 19-\n9' in text                                                    # číslo se nespojuje
    assert pdf_text.clean_text(['Kreatinin 92 µmol/l']) == 'Kreatinin 92 µmol/l'  # mikro zůstane


def test_ocr_elements_to_text():
    page1 = [
        {'type': 'Page-header', 'bbox': {'ymin': 0.02, 'ymax': 0.05}, 'text': 'Fakultní nemocnice · syntetická data'},
        {'type': 'Section-header', 'bbox': {'ymin': 0.27, 'ymax': 0.29}, 'text': 'LABORATOŘ'},
        {'type': 'Table', 'bbox': {'ymin': 0.29, 'ymax': 0.39}, 'text': '\\begin{tabular}{ccc}\n**Parametr** & **Výsledek** & '
         '**Jednotka**\\\\\nHemoglobin & 128 & g/l\\\\\n\\end{tabular}'},
        {'type': 'Page-footer', 'bbox': {'ymin': 0.96, 'ymax': 0.97}, 'text': 'Strana 1 z 2'},
        {'type': 'Text', 'bbox': {'ymin': 0.08, 'ymax': 0.1}, 'text': '**Datum:** 10. 10. 2026<br>Pneumologie'},
    ]
    page2 = [{'type': 'Text', 'bbox': {'ymin': 0.02, 'ymax': 0.05}, 'text': '<tbc>Fakultní nemocnice · synetická data'},
             {'type': 'Text', 'bbox': {'ymin': 0.2, 'ymax': 0.3}, 'text': 'Kontrola po MDT.'}]
    first, second = pdf_text.ocr_pages_text([page1, page2])
    assert first == 'Datum: 10. 10. 2026\nPneumologie\n\nLABORATOŘ\nParametr | Výsledek | Jednotka\nHemoglobin | 128 | g/l'
    assert second == 'Kontrola po MDT.'                    # hlavička rozpoznaná na 1. straně zmizí i z druhé


def test_scanned_pdf_goes_through_ocr(monkeypatch):
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    scan = canvas.Canvas(buffer)
    scan.rect(100, 100, 300, 300, fill=1)                              # stránka bez textové vrstvy = sken
    scan.showPage()
    scan.save()
    with pytest.raises(ValueError, match='sken'):
        report_import.pdf_text(buffer.getvalue(), MockAIProvider(), lambda *a: None)
    monkeypatch.setattr(NvidiaProvider, 'parse_page_image', lambda self, png: [
        {'type': 'Section-header', 'bbox': {'ymin': 0.1}, 'text': 'ZÁVĚR'},
        {'type': 'Text', 'bbox': {'ymin': 0.12}, 'text': 'Adenokarcinom plic cT2a cN1 cM0, ECOG 1.'}])
    logged = []
    text = report_import.pdf_text(buffer.getvalue(), NvidiaProvider(api_key='k'), lambda purpose, result: logged.append(purpose))
    assert text == 'ZÁVĚR\nAdenokarcinom plic cT2a cN1 cM0, ECOG 1.' and logged == ['import.ocr']


def test_broken_or_too_long_pdf():
    with pytest.raises(ValueError, match='PDF'):
        report_import.pdf_text(b'%PDF-1.4 broken', MockAIProvider(), lambda *a: None)
