"""
Chatbot u zasedání (T-338, ARCHITEKTURA §5.12): lékař se ptá AI, odpověď jsou tvrzení s citacemi.

- Kontext je stejný jako u podkladu (D-010): celý pacient na řadě z IRIS, jeho sada guidelines, studie a výsledky
  deterministických pravidel. Bez pacienta (dotaz bez štítku) jen všechny guidelines a studie.
- Gemini vrací strukturovaný výstup (`ChatbotOutput`), každé tvrzení projde grounding validátorem (§5.3):
  citace mimo povolená ID, číslo nebo datum, které ve zdroji není, = `unverified`.
- Co v podkladech chybí, je `missing`; rozmezí, rozpor nebo nejasná zkratka je NEJISTOTA AI (`uncertain`).
- Když LLM selže, nic nevrátí nebo běží mock, odpověď ukáže nejbližší místa v dokumentaci doslovně s citací (NFR-5).
- Dotaz lékaře i předchozí rozhovor projdou pseudonymizací (§5.7), pacient jde do LLM jen podle D-021.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from services.ai.abbreviations import prompt_rules
from services.ai.context_builder import (
    PatientContext,
    context_from_resources,
    general_context,
    load_resources,
    pseudonymizer_for,
)
from services.ai.grounding import verify_claims
from services.ai.guidelines import GuidelinesUnavailable, load_guidelines
from services.ai.pseudonymize import Pseudonymizer
from services.ai_service import BaseAIProvider, get_ai_provider, provider_for_patient
from services.rules import red_flags as rules
from services.rules.guideline_sets import GUIDELINE_SET_ORDER, guideline_sets_for

log = logging.getLogger(__name__)

CHATBOT_PROMPT = (Path(__file__).parent / "prompts" / "chatbot.md").read_text(encoding="utf-8")
MAX_CLAIMS = 6
NEAREST = 3                 # kolik míst z dokumentace ukáže odpověď bez LLM
QUOTE_LENGTH = 280


# ── Výstup LLM (response_schema) ──────────────────────────────────────────────
class ChatbotClaim(BaseModel):
    text: str = Field(description="Jedno tvrzení odpovědi, česky; čísla a data přesně podle zdrojů")
    citations: list[str] = Field(description="ID zdrojů z podkladů, ze kterých tvrzení vychází, např. P03-img03#4, KRC-2.4")


class ChatbotMissing(BaseModel):
    text: str = Field(description="Údaj potřebný k odpovědi, který v podkladech není")
    expected_source: str = Field(description="Kde by měl údaj být, např. histologie, CT hrudníku")


class ChatbotUncertainty(BaseModel):
    text: str = Field(description="Co je nejisté: rozmezí, nejednoznačná zkratka nebo rozpor zdrojů")
    citations: list[str] = Field(description="ID zdrojů, kterých se nejistota týká")


class ChatbotOutput(BaseModel):
    claims: list[ChatbotClaim] = Field(description="Odpověď po tvrzeních, nejvýš 6, každé s citací")
    missing: list[ChatbotMissing] = Field(description="Co k odpovědi v podkladech chybí; prázdné, když nic")
    uncertain: list[ChatbotUncertainty] = Field(description="NEJISTOTA AI; prázdné, když nic")


# ── Veřejné API ───────────────────────────────────────────────────────────────
def answer(question: str, patient_id: str | None, history: Iterable[dict] = (), *,
           provider: BaseAIProvider | None = None, log_call: Callable[[str, dict], Any] | None = None) -> dict:
    """Odpověď AI na dotaz lékaře: `{text, claims, uncertain, model}` (`ChatbotMessage` §8.6 bez metadat).

    `history` = předchozí `ChatbotMessage` rozhovoru od nejstarší. Výjimku nevyhodí: když nejdou načíst podklady,
    vrátí jen poznámku."""
    if log_call is None:
        from services.ai.brief import _llm_call_log
        log_call = _llm_call_log
    try:
        context, pseudo, resources = load_context(patient_id)
    except Exception:
        log.warning("T-338: podklady pro chatbot (%s) nejdou načíst z IRIS", patient_id or "bez pacienta", exc_info=True)
        return {"text": "Podklady se nepodařilo načíst z IRIS, AI teď neodpoví.", "claims": [], "uncertain": [],
                "model": None}
    if provider is None:
        provider = provider_for_patient(resources) if patient_id else get_ai_provider()     # D-021
    return answer_from_context(question, context, history, provider, log_call, pseudo)


def load_context(patient_id: str | None) -> tuple[PatientContext, Pseudonymizer, list[dict]]:
    """Kontext pro LLM, pseudonymizace dotazu a resources pacienta (pro D-021). Bez pacienta guidelines a studie."""
    if not patient_id:
        from services.fhir import client as fhir

        passages = []
        for guideline_set in GUIDELINE_SET_ORDER:        # chybějící sada neshodí ostatní
            try:
                passages += load_guidelines([guideline_set])
            except GuidelinesUnavailable as exc:
                log.warning("T-338: %s", exc)
        studies = fhir.search("ResearchStudy") + fhir.search("Group")
        return general_context(studies, passages), Pseudonymizer(), []

    from services.ai.brief import guideline_notices

    resources, studies = load_resources(patient_id)
    sets = guideline_sets_for(rules.PatientData(resources).icd10)
    try:
        passages = load_guidelines(sets)
    except GuidelinesUnavailable as exc:
        log.warning("T-338: %s", exc)
        passages = []
    notices = guideline_notices(sets, passages, resources)
    context = context_from_resources(patient_id, resources, studies=studies, guidelines=passages,
                                     red_flags=rules.evaluate(resources), rule_results=[n["text"] for n in notices])
    return context, pseudonymizer_for(resources), resources


def answer_from_context(question: str, context: PatientContext, history: Iterable[dict], provider: BaseAIProvider,
                        log_call: Callable[[str, dict], Any], pseudo: Pseudonymizer | None = None) -> dict:
    """Čisté jádro (testy bez IRIS): prompt → LLM → grounding; bez použitelné odpovědi nejbližší místa v dokumentaci."""
    pseudo = pseudo or Pseudonymizer()
    result = provider.generate(_prompt(question, context, list(history), pseudo),
                               system_prompt=f"{CHATBOT_PROMPT}\n\n{prompt_rules()}",
                               response_schema=ChatbotOutput, temperature=0.1)
    log_call("chatbot", result)
    data = (result.get("data") or {}) if result.get("status") == "success" else {}
    claims = [{"id": f"bot-{i:02d}", "kind": "claim", "text": c["text"].strip(),
               "citations": list(dict.fromkeys(c.get("citations") or []))}
              for i, c in enumerate(data.get("claims") or [], 1) if c.get("text", "").strip()][:MAX_CLAIMS]
    missing = [{"id": f"bot-miss-{i:02d}", "kind": "missing", "text": m["text"].strip(), "citations": [],
                **({"expected_source": m["expected_source"].strip()} if m.get("expected_source", "").strip() else {})}
               for i, m in enumerate(data.get("missing") or [], 1) if m.get("text", "").strip()]
    allowed = context.allowed_ids
    uncertain = [{"text": u["text"].strip(), "citations": [c for c in dict.fromkeys(u.get("citations") or []) if c in allowed]}
                 for u in data.get("uncertain") or [] if u.get("text", "").strip()]
    if claims or missing or uncertain:
        return {"text": "", "claims": _verified(claims + missing, context), "uncertain": uncertain,
                "model": result.get("model")}

    if result.get("status") != "success":
        log.warning("T-338: chatbot LLM selhal (%s), odpověď z dokumentace", result.get("error"))
        reason = "AI se teď nepodařilo odpovědět."
    elif provider.is_mock:
        reason = "Jazykový model není zapnutý (AI_PROVIDER=mock)."
    else:
        reason = "AI k otázce v podkladech nic nenašla."
    nearest = nearest_sources(question, context)
    note = " Nejbližší místa v dokumentaci k dotazu:" if nearest else " K dotazu se v dokumentaci nic nenašlo."
    return {"text": reason + note, "claims": _verified(nearest, context), "uncertain": [], "model": None}


def nearest_sources(question: str, context: PatientContext, limit: int = NEAREST) -> list[dict]:
    """Odpověď bez LLM: místa v dokumentaci se slovy dotazu, doslovně (citaci přiřadil kód).

    Slovo váží tím víc, čím méně míst ho obsahuje („CEA“ víc než „hodnota“); při shodě novější záznam dřív."""
    wanted = _stems(question)
    candidates = [(line.id, line.date, f"{line.date}: {line.text}" if line.date else line.text)
                  for line in context.evidence]
    candidates += [(p.evidence_id, "", f"{p.title}: {p.text}") for p in context.guidelines]
    candidates += [(c.evidence_id, "", c.text) for t in context.trials for c in t.criteria]
    hits = [(wanted & _stems(text), eid, date, text) for eid, date, text in candidates]
    df = Counter(stem for found, *_ in hits for stem in found)
    scored = [(sum(1 / df[s] for s in found), eid, date, text) for found, eid, date, text in hits if found]
    scored.sort(key=lambda s: s[2], reverse=True)                # stabilní řazení: novější první…
    scored.sort(key=lambda s: s[0], reverse=True)                # …v rámci stejného skóre
    return [{"id": f"bot-src-{n:02d}", "kind": "claim", "text": _quote(text), "citations": [eid], "_computed": True}
            for n, (_, eid, _, text) in enumerate(scored[:limit], 1)]


# ── Pomocné funkce ────────────────────────────────────────────────────────────
def _prompt(question: str, context: PatientContext, history: list[dict], pseudo: Pseudonymizer) -> str:
    out = [context.render()]
    if history:
        out.append("## Předchozí část rozhovoru")
        for m in history:
            if m.get("role") == "user":
                out.append(f"Lékař: {pseudo(m.get('text'))}")
                continue
            parts = [f"{c['text']} [{', '.join(c['citations'])}]" if c["kind"] == "claim" else f"Chybí: {c['text']}"
                     for c in m.get("claims") or []]
            out.append(f"AI: {' '.join(parts) or m.get('text') or '(bez odpovědi)'}")
        out.append("")
    out += ["## Otázka lékaře", pseudo(question)]
    return "\n".join(out) + "\n"


def _verified(claims: list[dict], context: PatientContext) -> list[dict]:
    return [{k: v for k, v in c.items() if not k.startswith("_")} for c in verify_claims(claims, context)]


_WORD = re.compile(r"\w{3,}")      # od 3 znaků kvůli zkratkám (CEA, PSA, PET)
# české koncovky (bez diakritiky), aby se potkaly tvary „hemoglobinu“ a „hemoglobin“, ale ne „hodnota“ a „hodnoceno“
_SUFFIXES = ("ami", "emi", "imi", "ymi", "ech", "ich", "ych", "ach", "ovi", "eho", "emu",
             "ou", "um", "em", "im", "ym", "ho", "mu", "a", "e", "i", "o", "u", "y")


def _fold(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(ch))


def _stem(word: str) -> str:
    return next((word[:-len(s)] for s in _SUFFIXES if word.endswith(s) and len(word) - len(s) >= 3), word)


# tázací a pomocná slova dotazu, která by našla skoro každý řádek (pořadí podle data řeší „poslední“)
_STOP = {_stem(_fold(w)) for w in (
    "jak", "jaký", "jaká", "jaké", "jací", "kde", "kdy", "kdo", "proč", "pro", "který", "která", "které", "nebo",
    "jsou", "byl", "byla", "bylo", "byly", "měl", "měla", "mělo", "má", "mají", "pacient", "pacienta", "podle",
    "nějak", "něco", "můžeš", "může", "řekni", "napiš", "prosím", "poslední", "aktuální", "uvádí", "the", "and")}


def _stems(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(_fold(text)) if not w.isdigit()} - _STOP


def _quote(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= QUOTE_LENGTH:
        return text
    return text[:QUOTE_LENGTH].rsplit(" ", 1)[0] + " …"
