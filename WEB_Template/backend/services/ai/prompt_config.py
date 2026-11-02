"""Prompt instructions derived from a BriefConfig snapshot (T-207)."""
from __future__ import annotations


LANGUAGES = {"cs": "česky", "sk": "slovensky", "en": "anglicky"}
LANGUAGE_DIRECTIVES = {
    "cs": "Veškerý nově vytvořený text napiš výhradně česky.",
    "sk": "Všetok novo vytvorený text napíš výhradne po slovensky.",
    "en": "Write all newly generated text exclusively in English.",
}
COUNTS = {
    "brief": {"summary": "3 stručné body", "role_views": "3 body", "decision_support": "2 možnosti"},
    "standard": {"summary": "3 až 4 body", "role_views": "3 až 4 body", "decision_support": "3 možnosti"},
    "detailed": {"summary": "5 bodů", "role_views": "5 až 6 bodů", "decision_support": "4 možnosti"},
}
MAX_ITEMS = {
    "brief": {"summary": 3, "role_views": 3},
    "standard": {"summary": 4, "role_views": 4},
    "detailed": {"summary": 5, "role_views": 6},
}


def detail_level(config: dict | None, section_id: str) -> str:
    config = config or {}
    section = next((item for item in config.get("sections", []) if item.get("id") == section_id), {})
    level = section.get("detail") or config.get("detail_level") or "standard"
    return level if level in COUNTS else "standard"


def output_limit(config: dict | None, section_id: str) -> int:
    return MAX_ITEMS[detail_level(config, section_id)][section_id]


# SectionId z UI → část podkladu, kterou generuje jedno volání LLM
FEEDBACK_PARTS = {"summary": "summary", "timeline": "summary", "role_views": "role_views", "modalities": "role_views",
                  "decision_support": "decision_support", "trials": "decision_support", "questions": "decision_support",
                  "red_flags": "red_flags", "anamnesis": "anamnesis"}


def feedback_note(config: dict | None, section_id: str) -> str:
    """Připomínka lékaře k předchozí verzi (T-323) pro tuto část; prázdná, když se jí netýká."""
    feedback = (config or {}).get("_feedback") or {}
    text = (feedback.get("text") or "").strip()
    parts = {FEEDBACK_PARTS.get(s, s) for s in feedback.get("sections") or []}
    if not text or (parts and section_id not in parts):
        return ""
    return ("\n\nZpětná vazba lékaře k předchozí verzi (oprav, na co upozorňuje, a zaměř se na to; pořád jen fakta "
            f"z podkladů s citacemi, nic nedomýšlej, chybějící údaj označ jako chybějící): „{text}“")


def prompt_settings(config: dict | None, section_id: str) -> str:
    """Return explicit language/detail directions, honoring section detail overrides."""
    config = config or {}
    level = detail_level(config, section_id)
    language = LANGUAGES.get(config.get("language"), "česky")
    count = COUNTS[level].get(section_id)
    instructions = [f"Piš {language}.", "Evidence ID a citované zdroje ponech beze změny."]
    if count:
        instructions.append(f"Úroveň detailu {level}: připrav {count}.")
    if level == "brief":
        instructions.append("Upřednostni hlavní fakta a vynech opakování.")
    elif level == "detailed":
        instructions.append("Zahrň důležité souvislosti a explicitně uveď, co chybí.")
    instructions.append(LANGUAGE_DIRECTIVES.get(config.get("language"), LANGUAGE_DIRECTIVES["cs"]))
    return " ".join(instructions) + feedback_note(config, section_id)
