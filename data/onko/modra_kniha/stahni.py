"""Modrá kniha České onkologické společnosti → citovatelné pasáže (`pasaze.jsonl`).

    python3 data/onko/modra_kniha/stahni.py            # stáhne PDF (když chybí) a přegeneruje pasáže
    python3 data/onko/modra_kniha/stahni.py --offline  # jen z už staženého PDF

Zdroj: https://www.linkos.cz/lekar-a-multidisciplinarni-tym/personalizovana-onkologie/modra-kniha-cos/aktualni-vydani-modre-knihy/
(32. aktualizace, platnost od 1. 3. 2026). PDF se do gitu necommituje (`.gitignore`), pasáže ano.

Pasáž = oddíl knihy podle jejího číslování (`4.2.1 Endoskopická léčba T1 …`), dlouhý oddíl rozdělený po
odstavcích na části. Evidence ID `EXT-MK-4.2.1`, další části `EXT-MK-4.2.1-2`; úvod kapitoly před prvním
oddílem `EXT-MK-4.0`. U nádorových kapitol rozsah MKN-10 z názvu kapitoly, u obecných (podpůrná léčba,
toxicita…) `*`. Potřebuje `pdfplumber` (je v requirements backendu).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PDF = HERE / "modra_kniha_32_2026.pdf"
OUT = HERE / "pasaze.jsonl"
PDF_URL = "https://www.linkos.cz/files/modra-kniha/26.pdf"
PAGE_URL = ("https://www.linkos.cz/lekar-a-multidisciplinarni-tym/personalizovana-onkologie/modra-kniha-cos/"
            "aktualni-vydani-modre-knihy/")
SOURCE = "Modrá kniha ČOS, 32. aktualizace (platnost od 1. 3. 2026)"
MAX_CHARS = 1800

HEADING = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\.?\s+([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽa-záčďéěíňóřšťúůýž(„\"].{1,160})$")
CHAPTER_ICD = re.compile(r"\(([^)]*\b[CD]\d{2}[^)]*)\)")


def download() -> None:
    req = urllib.request.Request(PDF_URL, headers={"User-Agent": "Mozilla/5.0 (MDT Copilot, hackathon)"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        PDF.write_bytes(resp.read())


def icd_prefixes(title: str) -> list[str]:
    """„(C18-20)“ → C18, C19, C20; „(C38, 47-49)“ → C38, C47–C49; „(C15, C16.0)“ → C15, C16.0; jinak `*`."""
    m = CHAPTER_ICD.search(title)
    if not m:
        return ["*"]
    out, letter = [], "C"
    for part in re.split(r"\s*,\s*", m[1]):
        part = part.strip()
        rng = re.fullmatch(r"([CD])?(\d{2})\s*[-–]\s*[CD]?(\d{2})", part)
        if rng:
            letter = rng[1] or letter
            out += [f"{letter}{n:02d}" for n in range(int(rng[2]), int(rng[3]) + 1)]
            continue
        one = re.fullmatch(r"([CD])?(\d{2}(?:\.\d)?)", part)
        if one:
            letter = one[1] or letter
            out.append(f"{letter}{one[2]}")
    return out or ["*"]


def chapters(pdf, reader) -> list[dict]:
    """Kapitoly z osnovy PDF (1. úroveň): číslo, název, strany (od 1)."""
    items = []
    for item in reader.outline:
        if isinstance(item, list):
            continue
        m = re.match(r"\s*(\d{1,2})\.\s*(.+)", item.title)
        if m:
            items.append({"number": int(m[1]), "title": m[2].strip(), "start": reader.get_destination_page_number(item) + 1})
    items.sort(key=lambda c: c["start"])
    for i, c in enumerate(items):
        c["end"] = (items[i + 1]["start"] - 1) if i + 1 < len(items) else len(pdf.pages)
    return items


def _is_subheading(line: str, prev: str) -> bool:
    """Nečíslovaný podnadpis („Chirurgická léčba:“, „Skvamozní karcinom“): krátký řádek s velkým písmenem
    na začátku, bez tečky na konci, po ukončené větě nebo jiném podnadpisu."""
    return (len(line) <= 90 and line[0].isupper() and not line.startswith(("•", "–", "-", "*"))
            and not line.rstrip(":").endswith((".", ",", ";")) and not re.search(r"\d+\s*(mg|g|ml|Gy)\b", line)
            and (not prev or prev.endswith((".", ":", ")", "?")) or len(prev) <= 90))


_LIST_START = re.compile(r"^([•▪◦*–-]\s|[a-z]\.\s|[ivx]+\.\s|\d+\.\s|\(\d+\)\s)")


def _reflow(text: str) -> str:
    """Řádky z PDF → odstavce: zalomené věty spojí, slovo rozdělené na konci řádku („dlouhodo-|bou“) slepí.
    Odrážky, výčty a krátké řádky (tabulky, nadpisy) zůstávají na samostatném řádku."""
    out: list[str] = []
    for line in text.split("\n"):
        prev = out[-1] if out else ""
        joinable = prev and len(prev) >= 70 and not _LIST_START.match(line) and not prev.endswith((":", ";"))
        if joinable and re.search(r"[a-záčďéěíňóřšťúůýž]-$", prev) and line[:1].islower():
            out[-1] = prev[:-1] + line
        elif joinable and not prev.endswith((".", "?", "!")) or (joinable and line[:1].islower()):
            out[-1] = f"{prev} {line}"
        else:
            out.append(line)
    return "\n".join(out)


def _split(lines: list[str], heading: str) -> list[tuple[str, str]]:
    """Řádky oddílu → části (podnadpis, text) do MAX_CHARS; nová část hlavně u podnadpisu."""
    parts, current, title, prev = [], [], heading, ""
    for line in lines:
        if re.fullmatch(r"(Použitá\s+)?[Ll]iteratura:?|Reference:?|Odkazy:?", line):
            break                                            # seznam citací článků není doporučení
        size = sum(len(x) + 1 for x in current)
        sub = _is_subheading(line, prev)
        if current and ((sub and size > 400) or size + len(line) > MAX_CHARS):
            parts.append((title, "\n".join(current).strip()))
            current = []
        if sub:
            title = line.rstrip(":").strip()
        while len(line) > MAX_CHARS:                         # dlouhý řádek (tabulka) natvrdo
            parts.append((title, line[:MAX_CHARS]))
            line = line[MAX_CHARS:]
        current.append(line)
        prev = line
    if current and "\n".join(current).strip():
        parts.append((title, "\n".join(current).strip()))
    return parts


def passages(pdf, chapter: dict) -> list[dict]:
    number, prefixes = chapter["number"], icd_prefixes(chapter["title"])
    sections: list[dict] = [{"section": f"{number}.0", "title": "", "page": chapter["start"], "lines": [], "pages": []}]
    last = (number, 0)
    for page_no in range(chapter["start"], chapter["end"] + 1):
        for line in (pdf.pages[page_no - 1].extract_text() or "").splitlines():
            line = line.strip()
            if not line:
                continue
            m = HEADING.match(line)
            if m:
                key = tuple(int(x) for x in m[1].split("."))
                if key[0] == number and key > last and len(key) <= len(last) + 1 + (last == (number, 0)):
                    last = key
                    sections.append({"section": m[1], "title": m[2].strip(), "page": page_no, "lines": [], "pages": []})
                    continue
            sections[-1]["lines"].append(line)
            sections[-1]["pages"].append(page_no)
    out = []
    for s in sections:
        lines = s["lines"]
        if s["section"].endswith(".0") and lines and lines[0].startswith(f"{number}."):
            lines = lines[1:]                                # název kapitoly z první strany
        page_of = dict(enumerate(s["pages"][len(s["lines"]) - len(lines):]))
        if sum(len(x) for x in lines) < 40:
            continue
        offset = 0
        for i, (sub, text) in enumerate(_split(lines, s["title"]), 1):
            eid = f"EXT-MK-{s['section']}" + (f"-{i}" if i > 1 else "")
            page = page_of.get(offset, s["page"])
            offset += text.count("\n") + 1
            title = f"{number}. {chapter['title']}" + (f" – {sub}" if sub else "")
            out.append({"evidence_id": eid, "chapter": number, "section": s["section"], "title": title[:300],
                        "page": page, "icd_prefixes": prefixes, "text": _reflow(text), "url": f"{PDF_URL}#page={page}"})
    return out


def main(argv: list[str]) -> int:
    import pdfplumber
    from pypdf import PdfReader

    if not PDF.exists():
        if "--offline" in argv:
            print(f"PDF {PDF.name} chybí; spusťte bez --offline, nebo ho stáhněte z {PAGE_URL}", file=sys.stderr)
            return 1
        download()
    reader = PdfReader(str(PDF))
    with pdfplumber.open(str(PDF)) as pdf:
        rows = [p for c in chapters(pdf, reader) for p in passages(pdf, c)]
    ids = [r["evidence_id"] for r in rows]
    duplicate = {i for i in ids if ids.count(i) > 1}
    if duplicate:
        print(f"Duplicitní ID: {sorted(duplicate)[:5]}", file=sys.stderr)
        return 1
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({**r, "source": SOURCE}, ensure_ascii=False) + "\n")
    print(f"{len(rows)} pasáží z {len({r['chapter'] for r in rows})} kapitol → {OUT.relative_to(HERE.parents[2])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
