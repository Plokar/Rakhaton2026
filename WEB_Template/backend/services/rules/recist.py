"""Deterministické vyhodnocení změny součtu cílových lézí (RECIST 1.1, T-304).

Vstupem jsou pouze součty SLD z radiologických zpráv. Výsledek proto popisuje
odpověď cílových lézí; úplné RECIST hodnocení včetně necílových lézí a nových
ložisek musí potvrdit radiolog.
"""
from __future__ import annotations

from collections.abc import Iterable


def evaluate_sld(measurements: Iterable[dict]) -> dict | None:
    """Vrátí SLD, baseline, nadir, procentní změnu a odpověď pro alespoň 2 měření."""
    points = sorted(
        (item for item in measurements
         if isinstance(item.get("sld_mm"), (int, float)) and item["sld_mm"] >= 0 and item.get("date")),
        key=lambda item: (item["date"], item["citation"]),
    )
    # Duplicitní extrakce téhož zdroje se nesmí započítat jako další vyšetření.
    points = list({item["citation"]: item for item in points}.values())
    points.sort(key=lambda item: (item["date"], item["citation"]))
    if len(points) < 2:
        return None

    baseline, current = points[0], points[-1]
    nadir = min(points, key=lambda item: item["sld_mm"])
    baseline_mm, nadir_mm, current_mm = baseline["sld_mm"], nadir["sld_mm"], current["sld_mm"]
    if baseline_mm <= 0:
        return None

    change_from_baseline = (current_mm - baseline_mm) / baseline_mm * 100
    change_from_nadir = ((current_mm - nadir_mm) / nadir_mm * 100) if nadir_mm else (0 if current_mm == 0 else float("inf"))

    if current_mm == 0:
        response = "CR"
    elif change_from_nadir >= 20 and current_mm - nadir_mm >= 5:
        response = "PD"
    elif change_from_baseline <= -30:
        response = "PR"
    else:
        response = "SD"

    return {
        "baseline": baseline,
        "nadir": nadir,
        "current": current,
        "change_from_baseline_pct": change_from_baseline,
        "change_from_nadir_pct": change_from_nadir,
        "response": response,
    }
