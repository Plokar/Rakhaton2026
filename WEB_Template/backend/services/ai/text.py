"""
Texty FHIR resources a jejich odstavce (ARCHITEKTURA §4.5, §5.2).

Jediný zdroj číslování odstavců pro citace `Pxx-…#n`. Stejné funkce musí používat
context builder (T-105), vektory `MDT.EvidenceChunk` (T-102) i resolver citací (T-104),
jinak `P03-img03#2` v různých částech aplikace ukáže na jiný text.

Pravidla:
- text resource: DocumentReference = `content[0].attachment.data`, DiagnosticReport =
  `presentedForm[0].data` (bez něj `conclusion`), Composition = sekce `Název: text`,
  ServiceRequest = otázka pro MDT + poznámky (`note[]`);
- nový odstavec začíná za prázdným řádkem a na řádku s nadpisem (`Závěr:`, `Nález:`,
  `Subjektivně:`, `OA:` …); odstavce se číslují od 1.
"""
from __future__ import annotations

import base64
import html
import re
from dataclasses import dataclass

# Nadpis: velké písmeno, max. 40 znaků bez dvojtečky, pak dvojtečka a mezera / konec řádku
_HEADER = re.compile(r"^[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][^\n:]{0,40}:(?:\s|$)")
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_BLOCK_END = re.compile(r"</(?:p|div|li|tr|h\d)>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Paragraph:
    index: int      # od 1, část Evidence ID za `#`
    start: int      # offset v textu resource (pro zvýraznění v UI)
    end: int
    text: str


def decode_base64(data: str | None) -> str:
    if not data:
        return ""
    return base64.b64decode(data).decode("utf-8")


def strip_xhtml(div: str | None) -> str:
    """XHTML narrative (`text.div`) → prostý text; `<br/>` a konce bloků jako nové řádky."""
    if not div:
        return ""
    text = _BLOCK_END.sub("\n", _BR.sub("\n", div))
    text = html.unescape(_TAG.sub("", text))
    return "\n".join(line.strip() for line in text.splitlines()).strip()


def _is_text(attachment: dict) -> bool:
    """Jen textové přílohy; PDF závěru MDT (`Pxx-mdtNN-pdf`, T-210) se nedekóduje."""
    return attachment.get("contentType", "text/plain").startswith("text/")


def resource_text(resource: dict) -> str | None:
    """Kanonický text resource, ze kterého se počítají odstavce. `None` = resource nemá text."""
    rtype = resource.get("resourceType")
    if rtype == "DocumentReference":
        parts = [decode_base64(c.get("attachment", {}).get("data")) for c in resource.get("content", [])
                 if _is_text(c.get("attachment", {}))]
        text = "\n\n".join(p for p in parts if p.strip())
    elif rtype == "DiagnosticReport":
        parts = [decode_base64(f.get("data")) for f in resource.get("presentedForm", []) if _is_text(f)]
        text = "\n\n".join(p for p in parts if p.strip()) or resource.get("conclusion", "")
    elif rtype == "Composition":
        sections = []
        for section in resource.get("section", []):
            body = strip_xhtml(section.get("text", {}).get("div"))
            title = section.get("title", "").strip()
            if title or body:
                sections.append(f"{title}: {body}" if title else body)
        text = "\n\n".join(sections)
    elif rtype == "ServiceRequest":
        parts = []
        question = (resource.get("reasonCode") or [{}])[0].get("text")
        if question:
            parts.append(f"Otázka pro MDT: {question}")
        parts += [n["text"] for n in resource.get("note", []) if n.get("text", "").strip()]
        text = "\n\n".join(parts)
    else:
        return None
    text = text.replace("\r\n", "\n").strip()
    return text or None


def split_paragraphs(text: str | None) -> list[Paragraph]:
    """Rozdělí text na odstavce s offsety; `text[p.start:p.end] == p.text`."""
    if not text:
        return []
    paragraphs: list[Paragraph] = []
    start = end = None
    pos = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        line_start, pos = pos, pos + len(line)
        if not content.strip():
            if start is not None:
                paragraphs.append(_paragraph(text, len(paragraphs) + 1, start, end))
                start = None
            continue
        if start is not None and _HEADER.match(content.strip()):
            paragraphs.append(_paragraph(text, len(paragraphs) + 1, start, end))
            start = None
        if start is None:
            start = line_start + (len(content) - len(content.lstrip()))
        end = line_start + len(content.rstrip())
    if start is not None:
        paragraphs.append(_paragraph(text, len(paragraphs) + 1, start, end))
    return paragraphs


def _paragraph(text: str, index: int, start: int, end: int) -> Paragraph:
    return Paragraph(index=index, start=start, end=end, text=text[start:end])


def resource_paragraphs(resource: dict) -> list[Paragraph]:
    return split_paragraphs(resource_text(resource))
