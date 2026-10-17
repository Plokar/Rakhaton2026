"""Text lékařské zprávy z PDF (BON-7, T-323): textová vrstva parserem, sken přes OCR.

Strukturovaná zpráva (hlavička nemocnice, oddíly Anamnéza / Laboratoř / Závěr, tabulky hodnot, patička se stránkou)
se převede na prostý text, kde:

- tabulka (s linkami) = řádky „buňka | buňka | …“ na svém místě v pořadí čtení, sloupce bez linek drží „ | “ z rozložení;
- opakovaná hlavička a patička stránek a čísla stránek zmizí (jinak by byly v každém odstavci a v RAG);
- slovo rozdělené na konci řádku se spojí, ligatury a nezlomitelné mezery se srovnají (NFKC);
- odstavec = blok oddělený prázdným řádkem; nadpis oddílu (verzálky) začíná nový odstavec, takže citace
  `Pxx-impNN#n` míří na oddíl (services/ai/text.py).

Stránka bez textové vrstvy (sken) jde přes OCR: NVIDIA `nemotron-parse` (stránka po stránce), jinak Gemini (celé PDF),
jinak srozumitelná chyba. Nic se nedomýšlí: OCR jen přepisuje, hodnoty pak ověří `report_import` proti odstavci.
"""
from __future__ import annotations

import io
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from statistics import median

MAX_PAGES = 40
MIN_TEXT_CHARS = 20                   # méně znaků na stránce = sken / obrázek
EDGE_LINES = 3                        # kde hledat opakovanou hlavičku a patičku
RENDER_SCALE = 2.5                    # ~180 dpi: OCR čte i drobné písmo laboratorních tabulek

PAGE_NUMBER = re.compile(r"^(?:strana|str\.|page|list)?\s*\d{1,3}\s*(?:/|z|ze|of|ze\s+celkem)?\s*\d{0,3}\s*$", re.IGNORECASE)
HYPHENATED = re.compile(r"([^\W\d_])-\n([a-záčďéěíňóřšťúůýž])")       # „léčeb-\nného“ → „léčebného“, „CA 19-9“ zůstane
# nadpis oddílu: verzálky bez číslic, nekončí tečkou („ZÁVĚR“, „FUNKČNÍ VYŠETŘENÍ PLIC“; ne „MDT.“ ani „CEA 6,8“)
CAPS_HEADING = re.compile(r"^[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ ,/()-]{3,60}[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ):]$")


def _norm(line: str) -> str:
    """Klíč pro porovnání hlavičky / patičky mezi stránkami (čísla stránek a datum tisku se liší)."""
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", line)).strip().lower()


def _layout_text(region) -> str:
    """Text oblasti ze slov s pozicemi: řádek = slova se stejnou výškou; mezera mezi slovy větší než 3 znaky = sloupec
    („ | “, tabulka bez linek); svislá mezera větší než běžný rozestup řádků = nový odstavec (prázdný řádek)."""
    words = sorted(region.extract_words(x_tolerance=1.5, y_tolerance=3), key=lambda w: (w["top"], w["x0"]))
    rows: list[dict] = []
    for word in words:
        if rows and abs(word["top"] - rows[-1]["top"]) <= 3:
            rows[-1]["words"].append(word)
            rows[-1]["bottom"] = max(rows[-1]["bottom"], word["bottom"])
        else:
            rows.append({"top": word["top"], "bottom": word["bottom"], "words": [word]})
    lines = []
    for row in rows:
        row_words = sorted(row["words"], key=lambda w: w["x0"])
        char = median((w["x1"] - w["x0"]) / max(len(w["text"]), 1) for w in row_words)
        text = row_words[0]["text"]
        for prev, word in zip(row_words, row_words[1:]):
            text += (" | " if word["x0"] - prev["x1"] > 3 * char else " ") + word["text"]
        lines.append((row["top"], row["bottom"], text))
    gaps = [b[0] - a[1] for a, b in zip(lines, lines[1:])]
    usual = median(gaps) if gaps else 0
    out = []
    for i, (_, _, text) in enumerate(lines):
        if i and gaps[i - 1] > max(1.7 * usual, usual + 3):
            out.append("")
        out.append(text)
    return "\n".join(out)


def _table_text(table) -> str:
    rows = []
    for row in table.extract():
        cells = [re.sub(r"\s+", " ", c).strip() for c in row if c and c.strip()]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _page_text(page) -> str:
    """Stránka v pořadí čtení: pásy textu nad / mezi / pod tabulkami s linkami, tabulka jako řádky s „ | “."""
    tables = sorted(page.find_tables(), key=lambda t: t.bbox[1])
    blocks, top = [], 0.0
    for table in tables:
        _, t_top, _, t_bottom = table.bbox
        if t_top > top + 1:
            blocks.append(_layout_text(page.crop((0, top, page.width, t_top))))
        blocks.append(_table_text(table))
        top = max(top, t_bottom)
    if top < page.height - 1:
        blocks.append(_layout_text(page.crop((0, top, page.width, page.height))))
    return "\n\n".join(b for b in blocks if b.strip())


def _strip_running_lines(pages: list[str]) -> list[str]:
    """Hlavička a patička, které se opakují na většině stránek, a čísla stránek pryč."""
    page_lines = [[line for line in p.splitlines()] for p in pages]
    edges = Counter()
    for lines in page_lines:
        content = [line for line in lines if line.strip()]
        edges.update({_norm(line) for line in content[:EDGE_LINES] + content[-EDGE_LINES:]})
    running = {key for key, n in edges.items() if key and len(pages) >= 2 and n >= max(2, (len(pages) + 1) // 2)}
    out = []
    for lines in page_lines:
        kept = [line for line in lines if _norm(line) not in running and not PAGE_NUMBER.match(line.strip())]
        out.append("\n".join(kept))
    return out


def _join_pages(pages: list[str]) -> str:
    """Věta přes zlom stránky zůstane v jednom odstavci (stránka nekončí . : ; ! ? ani tabulkou)."""
    text = ""
    for page in (p.strip() for p in pages):
        if not page:
            continue
        continues = text and not re.search(r"[.:;!?)]\s*$", text) and " | " not in text.rsplit("\n", 1)[-1]
        text = f"{text}\n{page}" if continues else f"{text}\n\n{page}" if text else page
    return text


def clean_text(pages: list[str]) -> str:
    """Stránky → jeden text s odstavci (viz docstring modulu)."""
    # NFKC srovná ligatury a mezery, ale mikro (µ) by změnil na řecké mí
    pages = [unicodedata.normalize("NFKC", p).replace("­", "").replace("μ", "µ") for p in pages]
    text = HYPHENATED.sub(r"\1\2", _join_pages(_strip_running_lines(pages)))
    lines = []
    for line in text.splitlines():
        line = line.rstrip()
        if CAPS_HEADING.match(line.strip()) and lines and lines[-1].strip():
            lines.append("")                                        # nadpis oddílu = nový odstavec
        lines.append(line)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", "\n".join(lines)) if b.strip()]
    merged: list[str] = []
    for block in blocks:                                            # samotný nadpis patří k obsahu pod ním
        if merged and CAPS_HEADING.match(merged[-1]) and "\n" not in merged[-1] and not CAPS_HEADING.match(block):
            merged[-1] = f"{merged[-1]}\n{block}"
        else:
            merged.append(block)
    return "\n\n".join(merged)


def text_layer_pages(pdf: bytes) -> list[str]:
    """Text každé stránky z textové vrstvy (prázdný = sken). Chybný / zaheslovaný / dlouhý soubor = `ValueError`."""
    import pdfplumber
    from pdfminer.pdfdocument import PDFPasswordIncorrect

    try:
        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            count = len(doc.pages)
            if count <= MAX_PAGES:
                return [_page_text(page) for page in doc.pages]
    except PDFPasswordIncorrect:
        raise ValueError("PDF je zaheslované.") from None
    except Exception as exc:            # pdfminer hlásí poškozený soubor různými výjimkami
        raise ValueError(f"Soubor nejde přečíst jako PDF ({type(exc).__name__}).") from None
    raise ValueError(f"PDF má {count} stran, víc než {MAX_PAGES}. Nahrajte zprávu po částech.")


def render_page(pdf: bytes, index: int) -> bytes:
    """Stránka jako PNG ve stupních šedi pro OCR."""
    import pypdfium2

    doc = pypdfium2.PdfDocument(pdf)
    try:
        image = doc[index].render(scale=RENDER_SCALE).to_pil().convert("L")
        out = io.BytesIO()
        image.save(out, format="PNG", optimize=True)
        return out.getvalue()
    finally:
        doc.close()


def _latex_table(text: str) -> str:
    """Tabulka z OCR (LaTeX `tabular`) → řádky „buňka | buňka“ jako tabulka z textové vrstvy."""
    body = re.sub(r"\\(?:begin|end)\{tabular\}(?:\{[^}]*\})?|\\hline|\\cline\{[^}]*\}", "", text)
    body = re.sub(r"\\multicolumn\{\d+\}\{[^}]*\}\{([^}]*)\}", r"\1", body)
    rows = []
    for row in re.split(r"\\\\", body):
        cells = [re.sub(r"\*\*|\\textbf\{|[{}]", "", cell).strip() for cell in row.split("&")]
        if any(cells):
            rows.append(" | ".join(c for c in cells if c))
    return "\n".join(rows)


def ocr_pages_text(pages: list[list[dict]]) -> list[str]:
    """Prvky OCR stránek → text stránek. Hlavička / patička označená na kterékoli stránce zmizí ze všech
    (OCR ji na některé stránce označí jen jako text)."""
    def norm(e: dict) -> str:
        return _norm(re.sub(r"<[^>]+>", "", e.get("text") or ""))

    def at_edge(e: dict) -> bool:                       # jen horní a dolní okraj, obsah stránky se nikdy nemaže
        box = e.get("bbox") or {}
        return box.get("ymin", 0.5) < 0.12 or box.get("ymax", 0.5) > 0.88

    running = [norm(e) for page in pages for e in page if e.get("type") in ("Page-header", "Page-footer")]
    def repeated(e: dict) -> bool:                      # OCR čte tutéž hlavičku pokaždé trochu jinak
        return at_edge(e) and any(SequenceMatcher(None, norm(e), r).ratio() > 0.8 for r in running)

    return [ocr_page_text([e for e in page if not repeated(e)]) for page in pages]


def ocr_page_text(elements: list[dict]) -> str:
    """Prvky OCR stránky → text v pořadí čtení: bez hlavičky a patičky stránky, nadpis oddílu u svého obsahu."""
    blocks: list[str] = []
    lone_heading = False
    for element in sorted(elements, key=lambda e: ((e.get("bbox") or {}).get("ymin", 0), (e.get("bbox") or {}).get("xmin", 0))):
        kind, text = element.get("type", "Text"), (element.get("text") or "").strip()
        if kind in ("Page-header", "Page-footer") or not text:
            continue
        text = _latex_table(text) if kind == "Table" or "\\begin{tabular}" in text else text
        text = re.sub(r"<br\s*/?>", "\n", re.sub(r"\*\*(.+?)\*\*", r"\1", re.sub(r"^#+\s*", "", text)))
        text = re.sub(r"<[^>\n]{1,10}>", "", text).strip()     # značky OCR (<tbc> = pokračování na další straně)
        if lone_heading:
            blocks[-1] = f"{blocks[-1]}\n{text}"
        else:
            blocks.append(text)
        lone_heading = kind in ("Section-header", "Title") and not lone_heading
    return "\n\n".join(blocks)


def ocr_model() -> str:
    from services.ai_service import DEFAULT_NVIDIA_PARSE_MODEL, _env

    return _env("NVIDIA_PARSE_MODEL", DEFAULT_NVIDIA_PARSE_MODEL)


def is_scan(text: str) -> bool:
    return len(re.sub(r"\s", "", text)) < MIN_TEXT_CHARS
