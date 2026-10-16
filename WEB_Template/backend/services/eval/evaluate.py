"""Eval podkladu proti ground truth (T-301, ARCHITEKTURA §5.8).

`score(gt, brief, prefill)` porovná vygenerovaný podklad (`Brief` §8.2) a předvyplnění zařazení (`IntakePrefill`
§8.6) s ground truth jednoho pacienta. Pravidla shody podle data/dev_ground_truth/README.md:

- citace se porovnávají na úrovni zdroje (`P03-img03#2` = `P03-img03`);
- red flag je nalezený, když sedí pravidlo (`rule` nebo `also_rules`) a aspoň jeden citovaný zdroj;
- `also_acceptable` u studií se počítá jako shoda.

Každá metrika je `(shoda, celkem)`; `misses` vyjmenuje, co chybí (vstup pro ladění T-302).
"""
from __future__ import annotations

from services.ai.grounding import check_claim, has_vector
from services.eval.ground_truth import PatientGroundTruth, same_source, source_of


def _claims(brief: dict) -> list[dict]:
    claims = [c for s in brief["sections"] for c in s["items"]] + brief["header"].get("alerts", [])
    for option in (brief.get("decision_support") or {}).get("treatment_options", []):
        claims += option["rationale"] + option["prerequisites_missing"]
    return claims


def _cited_sources(brief: dict) -> set[str]:
    """Všechny zdroje, které podklad cituje (tvrzení, hlavička, red flags, B2)."""
    header = brief["header"]
    ids = [c for claim in _claims(brief) for c in claim["citations"]]
    ids += [header["diagnosis"]["citation"], header["mdt_question"]["citation"]]
    ids += [(header.get("tnm") or {}).get("citation", "")] + [c["citation"] for c in header.get("comorbidities", [])]
    ids += [(e or {}).get("citation", "") for e in (header.get("ecog") or {}).values()]
    ids += [c for f in brief.get("red_flags", []) for c in f["citations"]]
    ds = brief.get("decision_support") or {}
    ids += [c for t in ds.get("trials", []) for cr in t["criteria"] for c in cr["citations"]]
    ids += [c for q in ds.get("discussion_questions", []) for c in q["citations"]]
    return {source_of(i) for i in ids if i}


def unverified_reasons(brief: dict, context) -> list[str]:
    """Proč tvrzení neprošla groundingem (body 1–3 deterministicky; jinak sémantika / chybějící vektory)."""
    out = []
    for c in _claims(brief):
        if c["kind"] != "claim" or c.get("verification") != "unverified":
            continue
        reasons = check_claim(c, context).reasons
        if not reasons:
            reasons = ["sémantická podobnost pod prahem" if all(has_vector(context, x) for x in c["citations"])
                       else "?"]
        out.append(f"{c['id']}: {', '.join(reasons)}")
    return out


def score(gt: PatientGroundTruth, brief: dict, prefill: dict, context=None) -> dict:
    cited = _cited_sources(brief)
    misses: dict[str, list[str]] = {}
    if context is not None:
        misses["unverified"] = unverified_reasons(brief, context)

    def found_flag(rf) -> bool:
        rules = {rf.rule, *rf.also_rules}
        return any(f["rule"] in rules and same_source(rf.citations, f["citations"]) for f in brief.get("red_flags", []))

    key = [rf for rf in gt.red_flags if rf.importance == "key"]
    misses["red_flags_key"] = [f"{rf.id} {rf.rule}: {rf.title}" for rf in key if not found_flag(rf)]
    rf_all = sum(found_flag(rf) for rf in gt.red_flags)

    facts = [f for f in gt.key_facts if {source_of(c) for c in f.citations} & cited]
    misses["key_facts"] = [f"{f.id}: {f.text}" for f in gt.key_facts if f not in facts]

    fields = {f["id"]: f["status"] for f in prefill.get("fields", [])}
    missing_claims = [c for c in _claims(brief) if c["kind"] == "missing"]

    def found_missing(m) -> bool:
        if m.field and fields.get(m.field) in ("missing", "pending", "skipped"):
            return True
        return any(same_source(m.citations, c["citations"]) for c in missing_claims if c["citations"])

    missing_ok = [m for m in gt.missing_data if found_missing(m)]
    misses["missing_data"] = [f"{m.id}: {m.item}" for m in gt.missing_data if m not in missing_ok]

    uncertain = [w for w in prefill.get("warnings", []) if w["kind"] == "ai_uncertain"]
    unc_ok = [u for u in gt.ai_uncertainty if any(same_source(u.citations, w["citations"]) for w in uncertain)]
    misses["ai_uncertainty"] = [f"{u.id}: {u.text}" for u in gt.ai_uncertainty if u not in unc_ok]

    ds_trials = {t["study_id"]: t for t in (brief.get("decision_support") or {}).get("trials", [])}
    crit_total = crit_ok = overall_ok = 0
    misses["trials"] = []
    for trial in gt.trials:
        got = ds_trials.get(trial.study_id)
        if got and got["overall"] in {trial.overall, *trial.also_acceptable}:
            overall_ok += 1
        by_id = {c["criterion_id"]: c for c in (got or {}).get("criteria", [])}
        for c in trial.criteria:
            crit_total += 1
            status = (by_id.get(c.criterion_id) or {}).get("status")
            if status in {c.status, *c.also_acceptable}:
                crit_ok += 1
            else:
                misses["trials"].append(f"{c.criterion_id}: čekáno {c.status}, podklad {status}")

    recist = (0, 0)
    if gt.recist:
        items = [i for s in brief["sections"] if s.get("role") == "radiologist" for i in s["items"]
                 if i["id"] == "radiologist-recist"]
        ok = bool(items) and f"odpověď {gt.recist.response}" in items[0]["text"]
        recist = (int(ok), 1)
        if not ok:
            misses["recist"] = [f"čekáno {gt.recist.response}, podklad: {items[0]['text'][:80] if items else 'bez RECIST'}"]

    rules = {r["rule_id"]: r["status"] for o in (brief.get("decision_support") or {}).get("treatment_options", [])
             for r in o["compatibility"]["rules"]}
    expected = {r.rule_id: r.status for o in gt.compatibility for r in o.rules}
    expected |= {r.rule_id: r.status for r in gt.compatibility_rules}
    light_ok = [rid for rid, status in expected.items() if rules.get(rid) == status]
    misses["compatibility"] = [f"{rid}: čekáno {s}, podklad {rules.get(rid)}" for rid, s in expected.items()
                               if rid not in light_ok]

    stats = brief["stats"]
    return {
        "patient_id": gt.patient_id,
        "red_flags_key": (len(key) - len(misses["red_flags_key"]), len(key)),
        "red_flags_all": (rf_all, len(gt.red_flags)),
        "key_facts": (len(facts), len(gt.key_facts)),
        "unverified": (stats["claims_unverified"], stats["claims_total"]),
        "missing_data": (len(missing_ok), len(gt.missing_data)),
        "ai_uncertainty": (len(unc_ok), len(gt.ai_uncertainty)),
        "trial_criteria": (crit_ok, crit_total),
        "trial_overall": (overall_ok, len(gt.trials)),
        "recist": recist,
        "compatibility": (len(light_ok), len(expected)),
        "misses": {k: v for k, v in misses.items() if v},
    }


METRICS = [("red_flags_key", "Red flags (key)"), ("red_flags_all", "Red flags (vše)"), ("key_facts", "Klíčová fakta"),
           ("missing_data", "Údaj chybí"), ("ai_uncertainty", "Nejistota AI"), ("trial_criteria", "Kritéria studií"),
           ("trial_overall", "Studie celkem"), ("recist", "RECIST"), ("compatibility", "Semafor (pravidla)"),
           ("unverified", "Neověřená tvrzení")]


def _cell(pair: tuple[int, int]) -> str:
    ok, total = pair
    return f"{ok}/{total} ({ok / total:.0%})" if total else "–"


def report(results: list[dict], title: str) -> str:
    """Markdown tabulka (pacienti × metriky + celkem) a seznam nesouladů pro T-302."""
    head = "| Pacient | " + " | ".join(label for _, label in METRICS) + " | Čas |"
    lines = [f"## {title}", "", head, "|" + "---|" * (len(METRICS) + 2)]
    for r in results:
        lines.append(f"| {r['patient_id']} | " + " | ".join(_cell(r[k]) for k, _ in METRICS)
                     + f" | {r.get('seconds', 0):.0f} s |")
    totals = {k: (sum(r[k][0] for r in results), sum(r[k][1] for r in results)) for k, _ in METRICS}
    lines.append("| **Celkem** | " + " | ".join(f"**{_cell(totals[k])}**" for k, _ in METRICS)
                 + f" | {sum(r.get('seconds', 0) for r in results):.0f} s |")
    lines += ["", "U „Neověřená tvrzení“ je cíl 0 %, u ostatních 100 %.", "", "### Nesoulady (vstup pro T-302)", ""]
    for r in results:
        for metric, items in r["misses"].items():
            lines += [f"- **{r['patient_id']} · {metric}:** " + "; ".join(items[:8]) + (" …" if len(items) > 8 else "")]
    return "\n".join(lines) + "\n"
