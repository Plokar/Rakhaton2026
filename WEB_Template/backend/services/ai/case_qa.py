"""Konverzační asistent nad případem (BONUS Q&A, T-332).

Člen komise položí během zasedání otázku v přirozeném jazyce („Kdy byla poslední dávka oxaliplatiny?“).
Odpověď je výhradně z dat pacienta v IRIS: stejný pseudonymizovaný kontext jako podklad (NFR-2, NFR-3),
každá věta s citací a přes grounding validátor. Co v datech není, AI výslovně uvede jako „V dostupné
dokumentaci se nenachází“ (zadání §3.3), nikdy neodhaduje. Bez LLM (mock, výpadek) odpoví vyhledáním:
vrátí nejbližší řádky dokumentace doslova, s citací a datem.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field

from services.ai.abbreviations import prompt_rules
from services.ai.context_builder import PatientContext, context_from_resources
from services.ai.grounding import verify_claims
from services.ai_service import BaseAIProvider

NOT_FOUND = "V dostupné dokumentaci se nenachází odpověď na tuto otázku."
MAX_QUESTION = 500
PROMPT = """Jsi asistent onkologické komise. Odpověz na otázku lékaře výhradně z podkladů pacienta výše.
Pravidla:
- 1 až 4 krátké věty, česky, čísla, jednotky a data přesně podle zdroje;
- ke každé větě uveď Evidence ID z hranatých závorek, ze kterých věta vychází (jen ta, která jsou v podkladech);
- když odpověď v podkladech není, nastav found = false a nic nedomýšlej;
- neradíš, co dělat, a nikdy nepíšeš „doporučujeme“: rozhoduje komise."""

STOPWORDS = {"jaka", "jaky", "jake", "jaký", "kdy", "byla", "bylo", "byl", "jsou", "jake", "pacient", "pacienta",
             "pacientka", "pacientky", "mela", "mel", "ktera", "ktery", "ktere", "proc", "jestli", "zda", "jak"}


class QaSentence(BaseModel):
    text: str
    citations: list[str] = Field(description="Evidence ID z podkladů, např. P03-img03#2")


class QaOutput(BaseModel):
    found: bool = Field(description="False, když odpověď v podkladech pacienta není")
    items: list[QaSentence]


def _plain(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


def search_evidence(context: PatientContext, question: str, limit: int = 3) -> list[dict]:
    """Vyhledání bez LLM: řádky dokumentace s nejvíc slovy z otázky (předpona slova kvůli českým koncovkám)."""
    words = {w[:6] for w in re.findall(r"\w+", _plain(question)) if len(w) > 2 and w not in STOPWORDS}
    if not words:
        return []
    scored = []
    for line in context.evidence:
        text = _plain(line.text)
        score = sum(1 for w in words if w in text)
        if score:
            scored.append((score, line.date or "", line))
    best = sorted(scored, key=lambda s: (s[0], s[1]), reverse=True)[:limit]
    return [{"kind": "claim", "citations": [line.id], "_computed": True,
             "text": (f"{line.date}: " if line.date else "") + (line.text if len(line.text) <= 300 else line.text[:297] + "…")}
            for _, _, line in best]


def answer_question(patient_id: str, question: str, resources: list[dict], provider: BaseAIProvider,
                    log_call: Callable[[str, dict], Any], *, studies: list[dict] | tuple = ()) -> dict:
    """Otázka → ověřená tvrzení s citacemi (`Claim` §8.1), `mode` = "ai" (LLM) nebo "search" (bez LLM)."""
    context = context_from_resources(patient_id, resources, studies=studies)
    items: list[dict] = []
    mode = "search"
    if not provider.is_mock or "QaOutput" in getattr(provider, "responses", {}):
        result = provider.generate(f"{context.render()}\n\nOtázka lékaře: {question}",
                                   system_prompt=f"{PROMPT}\n\n{prompt_rules()}", response_schema=QaOutput,
                                   temperature=0.1)
        log_call("case.qa", result)
        data = (result.get("data") or {}) if result.get("status") == "success" else {}
        if data:
            mode = "ai"
            if data.get("found") is False:
                items = [{"kind": "missing", "text": NOT_FOUND, "citations": [], "expected_source": "dokumentace pacienta v IRIS"}]
            else:
                items = [{"kind": "claim", "text": i["text"].strip(), "citations": list(dict.fromkeys(i.get("citations") or []))}
                         for i in data.get("items") or [] if i.get("text", "").strip()]
    if not items:
        mode = "search"
        items = search_evidence(context, question) or [
            {"kind": "missing", "text": NOT_FOUND, "citations": [], "expected_source": "dokumentace pacienta v IRIS"}]
    items = [{"id": f"qa-{i:02d}", **item} for i, item in enumerate(items, 1)]
    verified = [{k: v for k, v in c.items() if not k.startswith("_")} for c in verify_claims(items, context)]
    return {"question": question, "mode": mode, "items": verified,
            "answered_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
