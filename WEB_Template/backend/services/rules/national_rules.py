"""Modrá kniha ČOS u pravidel semaforu (T-340, D-026, docs/SABLONY_LEKARE.md R7).

Kurátorské mapování `data/onko/modra_kniha/pravidla.tsv`: u každého pravidla buď oddíl knihy s doslovnou citací
(`prah` = parametr a hodnota / kritérium, `tema` = stejná věc bez čísla), nebo `neuvadi` (kniha práh nemá).
Barvu semaforu to nemění (D-015); lékař jen vidí, o co se práh opírá v národních doporučeních.
"""
from __future__ import annotations

import csv
from functools import lru_cache


@lru_cache(maxsize=1)
def mapping() -> dict[str, dict]:
    """`{pravidlo: {status, refs: [{evidence_id, match, quote, note}]}}`; bez báze prázdné."""
    from services.rules.onko_kb import kb_dir

    root = kb_dir()
    path = root / "modra_kniha" / "pravidla.tsv" if root else None
    if path is None or not path.is_file():
        return {}
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            item = out.setdefault(row["pravidlo"], {"status": "neuvadi", "refs": []})
            if row["shoda"] == "neuvadi":
                continue
            item["refs"].append({"evidence_id": row["oddil"], "match": row["shoda"], "quote": row["citat"],
                                 "note": row["poznamka"] or None})
            if row["shoda"] == "prah" or item["status"] == "neuvadi":
                item["status"] = row["shoda"]
    return out


def attach(options: list[dict]) -> list[dict]:
    """K výsledkům pravidel (`compatibility.rules[]`) doplní `national` a `national_status`."""
    known = mapping()
    for option in options:
        for rule in option.get("compatibility", {}).get("rules", []):
            item = known.get(rule.get("rule_id"))
            if item:
                rule["national_status"] = item["status"]
                rule["national"] = item["refs"]
    return options
