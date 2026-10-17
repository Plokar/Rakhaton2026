#!/usr/bin/env python3
"""Dotazovač znalostní báze onkologie `data/onko/` (T-315). Jen standardní knihovna.

Vypíše jen výřez, který je potřeba (šetří tokeny):

  q.py dg C34                                   postupy pro diagnózu (MKN-10)
  q.py postup pli-chrt-durvalumab [k=v …]       semafor postupu: barva, proč, zdroj
  q.py fakta pli-chrt-durvalumab                jaké údaje postup potřebuje
  q.py studie C50 | KEYNOTE-189 | RKT-03 [k=v …]
  q.py pravidlo VS-RT-02
  q.py norma hemoglobin | PSA
  q.py ctcae neutro
  q.py sablona C34 | P04 | bundle.json [k=v …] [--json]   doporučená šablona projektoru (BriefConfig)
  q.py doporuc P04 | bundle.json [k=v …] [--json]          co v podkladech chybí → varování
  q.py pohled chirurg [P03 | C18 | bundle.json]            co jde lékaři nahoru (bez pacienta: všichni P01–P06)
  q.py odbornosti C34 [role]                              koho co zajímá a proč
  q.py check                                    kontrola integrity (exit 1 při chybě)

Fakta se zadávají jako `k=v` (např. `lab.crcl=48 rt.prior_months=ne`) nebo `@soubor.json`.
`Pxx` = bundle z datasetu: jen pro vývoj a testy, aplikace za běhu čte data jen z IRIS.
Barvu počítá kód podle kriteria.tsv (D-015), LLM ji nikdy nepřiřazuje. Tento skript je
referenční vyhodnocovač; v aplikaci je zdrojem pravdy services/rules/compatibility.py.
"""
from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATASET_DIR = REPO / "Dataset_MDT_Copilot_v1.1_pre_timy" / "Dataset_MDT_Copilot_v1.1"
GUIDELINES_DIR = DATASET_DIR / "guidelines"
EXT_CATALOG = REPO / "WEB_Template" / "backend" / "services" / "iris" / "data" / "external_sources.json"
APP_RULES = REPO / "WEB_Template" / "backend" / "services" / "rules" / "data" / "compatibility_rules.yaml"
ARCH = REPO / "ARCHITEKTURA.md"

TABLES = ("postupy", "kriteria", "fakta", "studie", "rkt", "normy", "ctcae", "zdroje", "sablony", "udaje", "odbornosti")
# výchozí pořadí bloků podkladu (ARCH §7.3, apps/mdt/config.py SECTION_ORDER)
SECTION_ORDER = ("summary", "timeline", "red_flags", "anamnesis", "role_views", "modalities", "decision_support",
                 "trials", "questions", "mdt_question")
ROLE_ALIAS = {"chirurg": "surgeon", "onkolog": "oncologist", "predseda": "oncologist", "radioterapeut": "radiation_oncologist",
              "radiolog": "radiologist", "patolog": "pathologist", "pneumolog": "pulmonologist",
              "kardiolog": "cardiologist", "pacient": "patient"}
FHIR_LETTER = {"Observation": "O", "DiagnosticReport": "R", "DocumentReference": "D", "Composition": "C",
               "ServiceRequest": "S", "QuestionnaireResponse": "Q", "Procedure": "P", "MedicationRequest": "M",
               "MedicationAdministration": "M", "MedicationStatement": "M", "Condition": "K", "AllergyIntolerance": "A"}
# zmínka ≠ výsledek: „doporučena spiroergometrie“, „EGFR nevyšetřen“, „Indikovat rebiopsii …?“
NEG = re.compile(r"nevyšetřen|neproveden|nebyl[oa]?\s+(?:proveden|požadován|vyšetřen)|nepožadován|chybí|probíhá|"
                 r"čeká se|nedostat|neurčen|doporučen|doplni?t|doplnění|plánuj|plánován|objedn|zvážit|indikovat",
                 re.IGNORECASE)
COLORS = ("cer", "ora", "zel")                       # pořadí vyhodnocení: nejhorší první
LIGHT = {"cer": "red", "ora": "orange", "zel": "green"}
ICON = {"red": "🔴", "orange": "🟠", "grey": "⚪", "green": "🟢"}
WORST = ("red", "orange", "grey", "green")            # celková barva = nejhorší (POZADAVKY §5.1)

ATOM = re.compile(r"^([a-z][a-z0-9_.]*)?(<=|>=|<|>|=)(.+)$")
RANGE = re.compile(r"^(-?\d+(?:\.\d+)?)-(-?\d+(?:\.\d+)?)$")
MARKER_KEY = re.compile(r"([A-Z][A-Z0-9]*)(?=<=|>=|<|>|=)")
ICD_RANGE = re.compile(r"^([A-Z])(\d\d)-([A-Z])(\d\d)$")


# ── Načtení ───────────────────────────────────────────────────────────────────
def read_tsv(name: str, errors: list[str] | None = None) -> list[dict]:
    lines = [line.rstrip("\n") for line in (HERE / f"{name}.tsv").read_text(encoding="utf-8").splitlines()]
    head = lines[0].split("\t")
    rows = []
    for n, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) != len(head):
            msg = f"{name}.tsv:{n}: {len(cells)} sloupců, čekám {len(head)}"
            if errors is None:
                raise ValueError(msg)
            errors.append(msg)
            continue
        rows.append(dict(zip(head, (c.strip() for c in cells))))
    return rows


@lru_cache(maxsize=1)
def kb() -> dict[str, list[dict]]:
    return {name: read_tsv(name) for name in TABLES}


@lru_cache(maxsize=1)
def app_rule_ids() -> frozenset[str]:
    """ID pravidel, která už implementuje aplikace (compatibility_rules.yaml, T-503)."""
    if not APP_RULES.exists():
        return frozenset()
    return frozenset(re.findall(r"^  (VS-[A-Z]+-\d+):", APP_RULES.read_text(encoding="utf-8"), re.M))


# ── Mini-DSL podmínek ─────────────────────────────────────────────────────────
def value(v) -> float | str | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return "ano" if v else "ne"
    s = str(v).strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return s.lower()


def parse(cond: str, primary: str | None):
    """`-` → None (barva se nepoužívá), `*` → '*' (jinak), jinak OR (`;`) skupin AND (`&`) atomů."""
    if cond == "-":
        return None
    if cond == "*":
        return "*"
    groups = []
    for group in cond.split(";"):
        atoms = []
        for raw in group.split("&"):
            atom = raw.strip()
            m = RANGE.match(atom)
            if m:
                if not primary:
                    raise ValueError(f"rozsah bez faktu: {atom!r}")
                atoms.append((primary, "range", (float(m[1]), float(m[2]))))
                continue
            m = ATOM.match(atom)
            if not m:
                raise ValueError(f"nečitelná podmínka: {atom!r}")
            fact = m[1] or primary
            if not fact:
                raise ValueError(f"podmínka bez faktu: {atom!r}")
            op, val = m[2], m[3]
            atoms.append((fact, op, tuple(v.strip().lower() for v in val.split("|")) if op == "=" else float(val)))
        groups.append(atoms)
    return groups


def facts_in(*parsed) -> set[str]:
    return {a[0] for p in parsed if isinstance(p, list) for g in p for a in g}


def _atom(facts: dict, fact: str, op: str, val):
    if fact not in facts or facts[fact] is None:
        return None
    fv = facts[fact]
    if fv == "nezn" and not (op == "=" and "nezn" in val):
        return None                                 # „nevyšetřeno / probíhá“ = neznámé, pokud na to pravidlo nečeká
    if op == "=":
        for alt in val:
            if isinstance(fv, float):
                try:
                    if float(alt) == fv:
                        return True
                except ValueError:
                    pass
            elif fv == alt:
                return True
        return False
    if op == "range":
        return isinstance(fv, float) and val[0] <= fv <= val[1]
    if not isinstance(fv, float):
        return fv == "ne" and op in (">", ">=")    # „ne“ = událost nebyla → jako nekonečně dávno
    return {"<": fv < val, "<=": fv <= val, ">": fv > val, ">=": fv >= val}[op]


def ev(parsed, facts: dict):
    """Tříhodnotová logika: True / False / None (chybí údaj)."""
    if not isinstance(parsed, list):
        return None
    out = False
    for group in parsed:
        res = [_atom(facts, *a) for a in group]
        g = False if False in res else (None if None in res else True)
        if g is True:
            return True
        if g is None:
            out = None
    return out


# ── Diagnózy a tagy ───────────────────────────────────────────────────────────
def codes(dg: str) -> list[str]:
    out = []
    for part in dg.split(","):
        m = ICD_RANGE.match(part.strip())
        if m and m[1] == m[3]:
            out += [f"{m[1]}{i:02d}" for i in range(int(m[2]), int(m[4]) + 1)]
        elif part.strip():
            out.append(part.strip())
    return out


def dg_match(rule_dg: str, target: list[str]) -> bool:
    if rule_dg == "*":
        return True
    if "*" in target:
        return False
    return any(t.startswith(r) or r.startswith(t) for r in codes(rule_dg) for t in target)


def tag_match(plati: str, tags: list[str]) -> bool:
    if plati == "*":
        return True
    return any(t == p or t.startswith(p + ".") for p in plati.split(",") for t in tags)


# ── Vyhodnocení ───────────────────────────────────────────────────────────────
def postup(pid: str) -> dict:
    row = next((p for p in kb()["postupy"] if p["postup"] == pid), None)
    if row is None:
        raise KeyError(f"postup {pid!r} není v postupy.tsv")
    return row


def marker_parsed(marker: str):
    return None if marker == "-" else parse(MARKER_KEY.sub(lambda m: "bm." + m[1].lower(), marker), None)


def applicable_rules(p: dict, facts: dict) -> list[dict]:
    tags = p["tagy"].split(",")
    target = codes(p["dg"])
    if "*" in target and facts.get("dg"):
        target = codes(str(facts["dg"]).upper())
    rules = []
    for r in kb()["kriteria"]:
        if r["id"] == "VS-BM-01" or not dg_match(r["dg"], target) or not tag_match(r["plati"], tags):
            continue
        if r["kdy"] != "-" and ev(parse(r["kdy"], None), facts) is False:
            continue
        rules.append(r)
    mp = marker_parsed(p["marker"])
    if mp:
        used = set().union(*(rule_facts(r) for r in rules)) if rules else set()
        if not facts_in(mp) & used:                  # marker nehlídá jiné pravidlo → VS-BM-01
            bm = next(r for r in kb()["kriteria"] if r["id"] == "VS-BM-01")
            rules.append({**bm, "zdroj": p["zdroj"]})
    return rules


def rule_facts(r: dict) -> set[str]:
    primary = None if r["fakt"] == "-" else r["fakt"]
    return facts_in(*(parse(r[c], primary) for c in COLORS)) | ({primary} if primary else set())


def marker_value(p: dict, facts: dict):
    mp = marker_parsed(p["marker"])
    res = ev(mp, facts)
    if res is True:
        return "ano"
    if any(facts.get(f) == "nezn" for f in facts_in(mp)):
        return "nezn"
    return None if res is None else "ne"


def evaluate_rule(r: dict, facts: dict) -> dict:
    primary = None if r["fakt"] == "-" else r["fakt"]
    conds = {c: parse(r[c], primary) for c in COLORS}
    res = {c: ev(conds[c], facts) for c in COLORS if isinstance(conds[c], list)}
    missing = sorted(f for f in facts_in(*conds.values()) if facts.get(f) in (None, "nezn"))
    hit = next((c for c in COLORS if res.get(c) is True), None)
    if hit:
        unsure = [ICON[LIGHT[c]] for c in COLORS[:COLORS.index(hit)] if c in res and res[c] is None]
        light, note = LIGHT[hit], (f"nelze vyloučit {' '.join(unsure)}" if unsure else "")
    elif None in res.values():
        light, note = "grey", "chybí údaj"
    else:
        star = next((c for c in COLORS if conds[c] == "*"), None)
        light, note = (LIGHT[star], "") if star else ("grey", "posoudí lékař" if not res else "mimo pravidlo")
    shown = {f: facts[f] for f in sorted(facts_in(*conds.values())) if facts.get(f) is not None}
    return {"id": r["id"], "light": light, "kontrola": r["kontrola"], "proc": r["proc"], "zdroj": r["zdroj"],
            "ov": r["ov"], "fakta": shown, "chybi": missing if light == "grey" or note else [], "pozn": note,
            "app": r["id"] in app_rule_ids()}


def evaluate_postup(pid: str, facts: dict | None = None) -> dict:
    """Semafor postupu: všechna použitelná pravidla s barvou, důvodem a zdrojem (+ screening studie)."""
    facts = {k: value(v) for k, v in (facts or {}).items()}
    p = postup(pid)
    if p["marker"] != "-":
        facts.setdefault("marker", marker_value(p, facts))
    results = [evaluate_rule(r, facts) for r in applicable_rules(p, facts)]
    results.sort(key=lambda x: (WORST.index(x["light"]), x["id"]))
    overall = min((x["light"] for x in results), key=WORST.index, default="grey")
    trial = None
    if "STUDIE" in p["tagy"].split(","):
        trial = screen_trial(p["zdroj"].split(",")[0], facts)
        overall = min(overall, trial["light"], key=WORST.index)
    return {"postup": p, "light": overall, "pravidla": results, "studie": trial}


def screen_trial(tid: str, facts: dict) -> dict:
    facts = {k: value(v) for k, v in facts.items()}
    crit = []
    for c in kb()["rkt"]:
        if not c["id"].startswith(tid + "/") or c["typ"] not in ("Z", "V"):
            continue
        res = None if c["fakt"] == "-" else ev(parse(c["podm"], c["fakt"]), facts)
        if c["fakt"] == "-":
            status = "posoudí lékař"
        elif res is None:
            status = "chybí údaj"
        elif c["typ"] == "Z":
            status = "splněno" if res else "nesplněno"
        else:
            status = "platí, vyřazuje" if res else "neplatí"
        crit.append({"id": c["id"], "typ": c["typ"], "text": c["text"], "status": status})
    if any(x["status"] in ("nesplněno", "platí, vyřazuje") for x in crit):
        light = "red"
    elif any(x["status"] in ("chybí údaj", "posoudí lékař") for x in crit):
        light = "grey"
    else:
        light = "green"
    return {"id": tid, "light": light, "kriteria": crit}


# ── Výpis ─────────────────────────────────────────────────────────────────────
def fmt_facts(d: dict) -> str:
    return " ".join(f"{k}={int(v) if isinstance(v, float) and v.is_integer() else v}" for k, v in d.items())


def print_postup(pid: str, facts: dict, verbose: bool = False) -> None:
    out = evaluate_postup(pid, facts)
    p = out["postup"]
    print(f"{p['postup']} · {p['dg']} · {p['kontext']}" + (f" · marker {p['marker']}" if p["marker"] != "-" else ""))
    print(f"{p['nazev']} | tagy {p['tagy']} | opora {p['opora']} | zdroj {p['zdroj']} [{p['ov']}]")
    counts = {lt: sum(r["light"] == lt for r in out["pravidla"]) for lt in WORST}
    print(f"CELKEM {ICON[out['light']]}  ({' '.join(f'{n}{ICON[lt]}' for lt, n in counts.items() if n)})")
    missing_only = [r for r in out["pravidla"] if r["light"] == "grey" and r["pozn"] == "chybí údaj"]
    for r in out["pravidla"]:
        if r in missing_only and not verbose:
            continue
        bits = [f"{ICON[r['light']]} {r['id']} {r['kontrola']}"]
        if r["fakta"]:
            bits.append(f"[{fmt_facts(r['fakta'])}]")
        if r["light"] in ("red", "orange") or r["pozn"] == "posoudí lékař":
            bits.append(f"→ {r['proc']}")
        if r["chybi"]:
            bits.append(f"({r['pozn']}: {', '.join(r['chybi'])})" if r["pozn"] else f"(chybí: {', '.join(r['chybi'])})")
        elif r["pozn"] and r["pozn"] != "posoudí lékař":
            bits.append(f"({r['pozn']})")
        bits.append(f"· {r['zdroj']}" + (" ⚠" if r["ov"] == "⚠" else "") + (" [app]" if r["app"] else ""))
        print(" ".join(bits))
    if missing_only and not verbose:
        print("⚪ chybí údaj (-v vypíše celé): " + " · ".join(f"{r['id']} {','.join(r['chybi'])}" for r in missing_only))
    if out["studie"]:
        t = out["studie"]
        print(f"STUDIE {t['id']} {ICON[t['light']]}")
        for c in t["kriteria"]:
            print(f"  {c['id']} {c['status']}: {c['text']}")


def print_fakta(pid: str) -> None:
    p = postup(pid)
    need = set()
    for r in applicable_rules(p, {}):
        need |= rule_facts(r)
        if r["kdy"] != "-":
            need |= facts_in(parse(r["kdy"], None))
    if p["marker"] != "-":
        need |= facts_in(marker_parsed(p["marker"]))
    need.discard("marker")
    fakta = {f["fakt"]: f for f in kb()["fakta"]}
    for f in sorted(need):
        d = fakta.get(f, {"typ": "?", "jedn": "?", "popis": "není ve fakta.tsv"})
        print(f"{f}\t{d['typ']}\t{d['jedn']}\t{d['popis']}")


def print_dg(q: str) -> None:
    target = codes(q.upper())
    rows = [p for p in kb()["postupy"] if p["dg"] != "*" and dg_match(p["dg"], target)]
    for p in rows:
        marker = f" [{p['marker']}]" if p["marker"] != "-" else ""
        print(f"{p['postup']} · {p['kontext']}{marker} · {p['nazev']} · opora {p['opora']} · {p['zdroj']} [{p['ov']}]")
    if rows:
        print(f"# {len(rows)} postupů; metastázy: q.py dg C79, podpůrná péče: q.py dg '*'")
    if q == "*":
        for p in kb()["postupy"]:
            if p["dg"] == "*":
                print(f"{p['postup']} · {p['kontext']} · {p['nazev']} · {p['zdroj']}")


def print_studie(q: str, facts: dict) -> None:
    if re.fullmatch(r"RKT-\d\d", q):
        s = next(c for c in kb()["rkt"] if c["id"] == q and c["typ"] == "S")
        print(f"{q} {s['text']}")
        t = screen_trial(q, facts)
        if facts:
            print(f"screening {ICON[t['light']]}")
        for c in t["kriteria"]:
            print(f"  {c['id']} {c['status'] if facts else c['typ']}: {c['text']}")
        for c in kb()["rkt"]:
            if c["id"] == q and c["typ"] == "P":
                print(f"  {c['text']}")
        return
    rows = [s for s in kb()["studie"] if s["studie"].lower() == q.lower()]
    if not rows and re.fullmatch(r"[A-Z]\d\d.*|\*", q.upper()):
        target = codes(q.upper())
        rows = [s for s in kb()["studie"] if s["dg"] == q or (s["dg"] != "*" and dg_match(s["dg"], target))]
        for c in kb()["rkt"]:
            if c["typ"] == "S" and (c["fakt"] == "*" or dg_match(c["fakt"], target)):
                print(f"{c['id']} (dataset, otevřená) {c['text']}")
    for s in rows:
        used = [p["postup"] for p in kb()["postupy"] if s["studie"] in p["opora"].split(",")]
        print(f"{s['studie']} {s['rok']} · {s['kontext']} · {s['rameno']} vs {s['vs']} → {s['vysledek']}"
              + (f" · postupy {','.join(used)}" if used else ""))


def print_pravidlo(rid: str) -> None:
    r = next((x for x in kb()["kriteria"] if x["id"] == rid), None)
    if r is None:
        sys.exit(f"pravidlo {rid} není v kriteria.tsv")
    for k, v in r.items():
        print(f"{k}\t{v}")
    used = [p["postup"] for p in kb()["postupy"] if r in applicable_rules(p, {})]
    print(f"postupy\t{len(used)}: {','.join(used)}")


def print_lookup(table: str, q: str) -> None:
    ql = q.lower()
    for r in kb()[table]:
        if ql in r["param"].lower() or ql == r.get("fakt", "").lower():
            print("\t".join(r.values()))


# ── Podklady pacienta (FHIR bundle → dokumenty a fakta) ───────────────────────
def _cc(c) -> str:
    c = c or {}
    return c.get("text") or " ".join(x.get("display", "") for x in c.get("coding", []))


def _b64(data: str | None) -> str:
    import base64
    try:
        return base64.b64decode(data or "").decode("utf-8", "replace")
    except ValueError:
        return ""


def _label_body(r: dict) -> tuple[str, str]:
    t = r["resourceType"]
    notes = [n.get("text", "") for n in r.get("note", [])]
    if t == "Observation":
        v = r.get("valueQuantity", {}).get("value", r.get("valueString") or _cc(r.get("valueCodeableConcept")))
        return _cc(r.get("code")), " | ".join([str(v or "")] + notes)
    if t == "DiagnosticReport":
        return _cc(r.get("code")), " ".join([_b64(f.get("data")) for f in r.get("presentedForm", [])] + [r.get("conclusion", "")])
    if t == "DocumentReference":
        return _cc(r.get("type")), " ".join(_b64(c.get("attachment", {}).get("data")) for c in r.get("content", []))
    if t == "Composition":
        return r.get("title", ""), " ".join(f"{s.get('title', '')}: {re.sub('<[^>]+>', ' ', s.get('text', {}).get('div', ''))}."
                                             for s in r.get("section", []))
    if t == "ServiceRequest":
        return "", " | ".join([_cc(x) for x in r.get("reasonCode", [])] + notes)
    if t == "QuestionnaireResponse":
        parts = []

        def walk(items):
            for i in items:
                answers = [next(iter(a.values())) for a in i.get("answer", [])]
                parts.append(f"{i.get('text', '')}: " + ", ".join(a.get("display", "") if isinstance(a, dict) else str(a)
                                                                    for a in answers))
                walk(i.get("item", []))
        walk(r.get("item", []))
        return "", " | ".join(parts)
    label = _cc(r.get("code") or r.get("medicationCodeableConcept"))
    return label, " | ".join(notes)


def _date(r: dict) -> str:
    for k in ("effectiveDateTime", "issued", "date", "authored", "authoredOn", "performedDateTime", "recordedDate",
              "onsetDateTime"):
        if r.get(k):
            return str(r[k])[:10]
    for k in ("effectivePeriod", "performedPeriod"):
        if r.get(k, {}).get("start"):
            return r[k]["start"][:10]
    return ""


def _her2(value: str) -> str | None:
    v = value.lower()
    if NEG.search(v):
        return None
    if "ultralow" in v:
        return "ultralow"
    if "3+" in v or "pozitiv" in v or ("2+" in v and re.search(r"ish\s*(\+|pozit)|amplif", v)):
        return "pos"
    if "1+" in v or "2+" in v or "low" in v:
        return "low"
    return "0" if re.search(r"(^|\D)0(\D|$)", v) else None


def bundle_facts(resources: list[dict]) -> dict:
    """Fakta pro výběr šablony a podmínky `kdy` (referenční odvození; v aplikaci z IRIS)."""
    f: dict = {}
    codes_ = [c.get("code", "") for r in resources if r["resourceType"] == "Condition"
              for c in r.get("code", {}).get("coding", []) if "icd-10" in c.get("system", "")]
    f["dg"] = ",".join(codes_)
    primary = {c[:3] for c in codes_ if (c[0] == "C" and not "C77" <= c[:3] <= "C79") or "D37" <= c[:3] <= "D48"}
    if primary:
        f["tnm.m1"] = "ano" if any("C78" <= c[:3] <= "C79" for c in codes_) else "ne"
        f["dg.multiple"] = "ano" if len(primary) > 1 else "ne"
        f["brain.mets"] = "ano" if any(c.startswith("C79.3") for c in codes_) else "ne"
        f["bone.mets"] = "ano" if any(c.startswith("C79.5") for c in codes_) else "ne"
    texts = " ".join(_cc(r.get("code")) + " " + " ".join(n.get("text", "") for n in r.get("note", []))
                     for r in resources if r["resourceType"] in ("Condition", "ServiceRequest"))
    texts += " ".join(_cc(x) for r in resources if r["resourceType"] == "ServiceRequest" for x in r.get("reasonCode", []))
    if re.search(r"(?<!ne)malobuněčn", texts, re.I):
        f["hist.sclc"] = "ano"
    mdt = next((r.get("restriction", {}).get("period", {}).get("start") for r in resources
                if r["resourceType"] == "Task" and r.get("restriction")), None)
    mdt = mdt or next((r.get("occurrenceDateTime") for r in resources if r["resourceType"] == "ServiceRequest"), None)
    f["_mdt"] = (mdt or "")[:10]
    patient = next((r for r in resources if r["resourceType"] == "Patient"), {})
    if patient.get("gender"):
        f["sex"] = "Z" if patient["gender"] == "female" else "M"
    if patient.get("birthDate") and f["_mdt"]:
        f["age"] = int(f["_mdt"][:4]) - int(patient["birthDate"][:4])
    obs = sorted((r for r in resources if r["resourceType"] == "Observation"), key=_date)
    for o in obs:
        label, body = _label_body(o)
        if re.search(r"HER2", label) and not re.search(r"mut", label, re.I):
            f["bm.her2"] = _her2(body) or f.get("bm.her2")
        if re.search(r"\bER\b|Estrogen|\bPR\b|Progesteron", label) and not NEG.search(body):
            if re.search(r"pozitiv", body, re.I):
                f["bm.hr"] = "pos"
            elif re.search(r"negativ", body, re.I) and f.get("bm.hr") != "pos":
                f["bm.hr"] = "neg"
        if re.search(r"^Sodík|Natrium", label):
            f["lab.na"] = value(o.get("valueQuantity", {}).get("value"))
        m = re.search(r"(\d+)\s*%", body) if re.search(r"ppoFEV1|ppoDLCO", label) else None
        if m:
            f["spiro.ppo_min"] = min(float(m[1]), f.get("spiro.ppo_min", 999.0))
        for fact, pattern in BIOMARKERS.items():
            if re.search(pattern, label) and not re.search(r"anti-", label, re.I) and f.get(fact) != "mut":
                f[fact] = _biomarker(fact, body)          # RAS = mut, když je mutovaný KRAS nebo NRAS
        if "NGS" in label and not NEG.search(body):
            f["bm.ngs"] = "ano"
    meds = " ".join(_cc(r.get("medicationCodeableConcept")) for r in resources if FHIR_LETTER.get(r["resourceType"]) == "M")
    f["med.steroid"] = "ano" if re.search(r"dexametazon|prednison|methylprednisolon|hydrokortison", meds, re.I) else "ne"
    proms = sorted((r for r in resources if r["resourceType"] == "QuestionnaireResponse"), key=_date)
    if proms:                                   # nejvyšší symptom 0–10 v posledním dotazníku (OBC-1.3)
        scores = re.findall(r"\(0–10\):\s*(\d+)", _label_body(proms[-1])[1])
        f["prom.symptom_max"] = max(map(float, scores)) if scores else None
    return {k: v for k, v in f.items() if v is not None}


BIOMARKERS = {"bm.ras": r"\bRAS\b|KRAS|NRAS", "bm.egfr": r"EGFR", "bm.braf": r"BRAF", "bm.mmr": r"\bMMR\b|\bMSI\b"}


def _biomarker(fact: str, body: str) -> str:
    if NEG.search(body):
        return "nezn"
    if fact == "bm.mmr":
        return "dmmr" if re.search(r"dMMR|MSI-H|deficit|ztráta exprese", body, re.I) else "pmmr"
    if re.search(r"wild|\bwt\b|nemutov|neprokázán|negativ|bez (patogenní )?(mutac|varian)", body, re.I):
        return "wt"
    if fact == "bm.braf" and re.search(r"V600E", body):
        return "v600e"
    return "mut"


def load_bundle(src: str) -> dict:
    """`Pxx` (dataset, jen dev/test) nebo cesta k FHIR bundlu → {docs, facts, mdt}."""
    path = DATASET_DIR / "pacienti" / src / f"{src}_bundle.json" if re.fullmatch(r"P\d\d", src) else Path(src)
    resources = [e["resource"] for e in json.loads(path.read_text(encoding="utf-8")).get("entry", [])]
    docs = []
    for r in resources:
        letter = FHIR_LETTER.get(r["resourceType"])
        if letter:
            label, body = _label_body(r)
            docs.append({"t": letter, "id": r["id"], "date": _date(r), "label": label, "body": body})
    facts = bundle_facts(resources)
    return {"docs": docs, "mdt": facts.pop("_mdt"), "facts": facts}


def _sentence(text: str, start: int, end: int) -> str:
    left = max(text.rfind(c, 0, start) for c in ".!?\n|") + 1
    rights = [i for i in (text.find(c, end) for c in ".!?\n|") if i >= 0]
    return text[left:(min(rights) + 1 if rights else len(text))]


def _days(a: str, b: str) -> int | None:
    from datetime import date
    try:
        return (date.fromisoformat(b) - date.fromisoformat(a)).days
    except ValueError:
        return None


def find_item(u: dict, docs: list[dict], mdt: str | None) -> dict:
    """Stav údaje v podkladech: present | mention (jen zmínka/nevyšetřeno) | stale (starší než max_dni) | missing."""
    rx = re.compile(u["vzor"], re.IGNORECASE)
    types = u["fhir"].split(",")
    present, mentions = {}, {}
    for d in docs:
        if "*" not in types and d["t"] not in types:
            continue
        if u["vzor"] == ".":
            present[d["id"]] = d
        elif d["t"] == "O":                        # strukturované: název + hodnota („probíhá“ = zmínka)
            if rx.search(f"{d['label']} | {d['body']}"):
                (mentions if NEG.search(d["body"]) else present)[d["id"]] = d
        elif d["label"] and rx.search(d["label"]):
            present[d["id"]] = d
        else:
            for m in rx.finditer(d["body"]):
                sent = _sentence(d["body"], m.start(), m.end())
                if NEG.search(sent) or sent.rstrip().endswith("?"):
                    mentions[d["id"]] = d
                else:
                    present[d["id"]] = d
                    break
    if present and u["max_dni"] != "-" and mdt:
        fresh = {k: d for k, d in present.items() if (_days(d["date"], mdt) or 0) <= int(u["max_dni"])}
        if not fresh:
            last = max(present.values(), key=lambda d: d["date"])
            return {"status": "stale", "ids": [last["id"]], "age": _days(last["date"], mdt)}
        present = fresh
    if present:
        return {"status": "present", "ids": sorted(present, key=lambda k: present[k]["date"])[-3:]}
    if mentions:
        return {"status": "mention", "ids": sorted(mentions)[:3]}
    return {"status": "missing", "ids": []}


# ── Šablony projektoru a doporučené údaje (T-317) ─────────────────────────────
def _atoms_true(parsed, facts) -> int:
    return sum(1 for g in parsed for a in g if _atom(facts, *a) is True) if isinstance(parsed, list) else 0


def pick_template(dg_codes: list[str], facts: dict) -> dict:
    """Nejlepší šablona: priorita (jen při splněném `kdy`) > konkrétní diagnóza > splněné `kdy` > počet shod."""
    best, best_rank = None, None
    for i, t in enumerate(kb()["sablony"]):
        if t["dg"] != "*" and not dg_match(t["dg"], dg_codes):
            continue
        parsed = parse(t["kdy"], None) if t["kdy"] != "-" else None
        verdict = ev(parsed, facts) if parsed else "-"
        if verdict is False:
            continue
        rank = (int(t["prio"]) if verdict is True else 0, t["dg"] != "*",
                {True: 2, "-": 1, None: 0}[verdict], _atoms_true(parsed, facts), -i)
        if best_rank is None or rank > best_rank:
            best, best_rank = t, rank
    return best


def template_config(t: dict) -> dict:
    """Šablona → `BriefConfig` (ARCH §8.5): zapnuté sekce v pořadí šablony, ostatní vypnuté."""
    chosen = [s.split(":") for s in t["sekce"].split(",")]
    enabled = [c[0] for c in chosen]
    sections = [{"id": c[0], "enabled": True, "order": i, **({"detail": c[1]} if len(c) > 1 else {})}
                for i, c in enumerate(chosen)]
    sections += [{"id": s, "enabled": False, "order": len(sections) + i}
                 for i, s in enumerate(x for x in SECTION_ORDER if x not in enabled)]
    return {"name": f"Šablona: {t['nazev']}", "is_preset": True, "sections": sections,
            "roles_present": t["role"].split(","), "detail_level": t["detail"], "language": "cs",
            "hide_unverified": False}


def applicable_items(dg_codes: list[str], facts: dict) -> list[dict]:
    """Údaje pro diagnózu. P: když `kdy` neplatí jistě, zůstává; D: jen když `kdy` jistě platí (méně šumu)."""
    out = []
    for u in kb()["udaje"]:
        if u["dg"] != "*" and not dg_match(u["dg"], dg_codes):
            continue
        verdict = ev(parse(u["kdy"], None), facts) if u["kdy"] != "-" else True
        if verdict is False or (u["uroven"] == "D" and verdict is not True):
            continue
        out.append(u)
    specific = {u["udaj"].split(".", 1)[1] for u in out if not u["udaj"].startswith("obc.")}
    return [u for u in out if not (u["udaj"].startswith("obc.") and u["udaj"].split(".", 1)[1] in specific)]


def recommend(dg_codes: list[str], facts: dict, docs: list[dict] | None, mdt: str | None) -> list[dict]:
    """Údaje se stavem v podkladech + varování kompatibilní s `IntakeWarning` (§8.6), bez změny kontraktu."""
    out = []
    for u in applicable_items(dg_codes, facts):
        found = find_item(u, docs, mdt) if docs is not None else {"status": "?", "ids": []}
        item = {"udaj": u["udaj"], "uroven": u["uroven"], "nazev": u["nazev"], "proc": u["proc"],
                "zdroj": u["zdroj"], **found}
        if found["status"] in ("missing", "mention", "stale"):
            why = {"missing": "V podkladech nenalezeno", "mention": "V podkladech jen zmínka (doporučeno, probíhá, nevyšetřeno)",
                   "stale": f"Poslední je {found.get('age')} dní staré (limit {u['max_dni']})"}[found["status"]]
            doporuceno = u["uroven"] == "D"
            item["warning"] = {
                "id": f"{'DOP' if doporuceno else 'CHYBI'}:{u['udaj']}", "kind": "missing",
                "severity": "low" if doporuceno else "moderate",
                "title": f"{'Doporučeno' if doporuceno else 'Chybí'}: {u['nazev']}",
                "detail": f"{why}. {'Mohlo by se hodit' if doporuceno else 'Potřebné'}: {u['proc']}.",
                "citations": u["zdroj"].split(",") + found["ids"]}
        out.append(item)
    return out


def resolve_role(r: str) -> str:
    return ROLE_ALIAS.get(r.lower(), r)


def role_view(role: str, dg_codes: list[str], facts: dict, items: list[dict]) -> dict:
    """Co jde lékaři nahoru: jeho sekce, jeho údaje a varování, jeho postupy (odbornosti.tsv)."""
    rows = [o for o in kb()["odbornosti"] if o["role"] == role and (o["dg"] == "*" or dg_match(o["dg"], dg_codes))]
    rows.sort(key=lambda o: o["dg"] == "*")                        # konkrétní diagnóza před obecným
    mine = list(dict.fromkeys(i for o in rows for i in o["udaje"].split(",")))
    tags = sorted({p for o in rows for p in o["plati"].split(",")})
    pref = next((o["sekce"].split(",") for o in rows if o["dg"] == "*" and o["sekce"] != "-"), [])
    t = pick_template(dg_codes, facts)
    enabled = [s.split(":")[0] for s in t["sekce"].split(",")]
    first = [s for s in ["summary"] + pref if s in enabled]       # hlavička a souhrn zůstávají nahoře (ARCH §7.3)
    sections = list(dict.fromkeys(first + enabled))
    rank = {u: i for i, u in enumerate(mine)}
    items = sorted(items, key=lambda x: (x["udaj"] not in rank, rank.get(x["udaj"], 0)))
    postupy = [p for p in kb()["postupy"] if p["dg"] != "*" and dg_match(p["dg"], dg_codes)]
    postupy.sort(key=lambda p: (not tag_match(",".join(tags), p["tagy"].split(",")), not _fits_stage(p, facts)))
    return {"role": role, "sablona": t["sablona"], "sekce": sections, "udaje": items, "moje": set(mine),
            "postupy": postupy, "tagy": tags, "zajima": rows}


METASTATIC = re.compile(r"\bM1\b|\bIV\b|mHSPC|mCRPC|nmCRPC|R/M|relaps|\b[23]L\b|BCLC C|metast|oligomet|předléčen|po CDK|"
                        r"po anti-PD-1|po ARPI|po IO|po platin|po gemcitabin|po sorafenib")


def _fits_stage(p: dict, facts: dict) -> bool:
    """Jen pro řazení: u M1 napřed postupy pro metastatické onemocnění, u M0 pro lokalizované."""
    m1 = facts.get("tnm.m1")
    return True if m1 not in ("ano", "ne") else bool(METASTATIC.search(p["kontext"])) == (m1 == "ano")


def _source(src: str, facts_cli: dict) -> tuple[list[str], dict, list[dict] | None, str | None, str]:
    """Argument → (dg kódy, fakta, dokumenty, datum MDT, popisek)."""
    if re.fullmatch(r"P\d\d", src) or src.endswith(".json"):
        b = load_bundle(src)
        facts = {k: v if k == "dg" else value(v) for k, v in {**b["facts"], **facts_cli}.items()}
        return codes(facts.pop("dg")), facts, b["docs"], b["mdt"], src
    return codes(src.upper()), {k: value(v) for k, v in facts_cli.items()}, None, None, src.upper()


def _status_icon(s: str) -> str:
    return {"present": "✓", "mention": "~", "stale": "⌛", "missing": "✗", "?": "·"}[s]


def print_sablona(src: str, facts_cli: dict, as_json: bool) -> None:
    dg_codes, facts, docs, mdt, label = _source(src, facts_cli)
    t = pick_template(dg_codes, facts)
    items = {i["udaj"]: i for i in recommend(dg_codes, facts, docs, mdt)}
    if as_json:
        print(json.dumps({"sablona": t["sablona"], "config": template_config(t),
                          "projektor": [{"udaj": u, **{k: items[u][k] for k in ("nazev", "status", "ids")}} if u in items
                                        else {"udaj": u, "status": "neplatí"} for u in t["zobrazit"].split(",")],
                          "studie": [] if t["studie"] == "-" else t["studie"].split(","),
                          "warnings": [i["warning"] for i in items.values() if "warning" in i]}, ensure_ascii=False, indent=1))
        return
    print(f"{label} → {t['sablona']}: {t['nazev']}  [{fmt_facts({k: v for k, v in facts.items() if k in ('tnm.m1', 'bm.hr', 'bm.her2', 'dg.multiple', 'age')})}]")
    print(f"sekce {t['sekce']} | detail {t['detail']}")
    print(f"role {t['role']} ({t['odbornosti']}) | studie {t['studie']} | {t['zdroj']}")
    print("na projektor: " + " · ".join(
        f"{_status_icon(items[u]['status']) if u in items else '–'} {items[u]['nazev'] if u in items else u}"
        for u in t["zobrazit"].split(",")))
    warns = [i for i in items.values() if "warning" in i]
    if docs is not None:
        print(f"varování: {len(warns)} (q.py doporuc {src})")


def print_doporuc(src: str, facts_cli: dict, as_json: bool) -> None:
    dg_codes, facts, docs, mdt, label = _source(src, facts_cli)
    items = recommend(dg_codes, facts, docs, mdt)
    warns = [i["warning"] for i in items if "warning" in i]
    if as_json:
        print(json.dumps(warns, ensure_ascii=False, indent=1))
        return
    for i in sorted(items, key=lambda x: (x["uroven"], x["status"] == "present")):
        if "warning" in i:
            w = i["warning"]
            print(f"{'🟡' if i['uroven'] == 'D' else '🟠'} {w['title']} · {w['detail']} · {','.join(w['citations'])}")
    ok = [i["nazev"] for i in items if i["status"] == "present"]
    print(f"✓ nalezeno {len(ok)}/{len(items)}: {', '.join(ok)}")


def print_pohled(role_arg: str, src: str | None, facts_cli: dict) -> None:
    role = resolve_role(role_arg)
    if src is None:                                       # každý lékař vidí každého pacienta (P01–P06)
        for pid in sorted(p.name for p in (DATASET_DIR / "pacienti").iterdir() if re.fullmatch(r"P\d\d", p.name)):
            dg_codes, facts, docs, mdt, _ = _source(pid, facts_cli)
            v = role_view(role, dg_codes, facts, recommend(dg_codes, facts, docs, mdt))
            top = [i for i in v["udaje"] if i["udaj"] in v["moje"]][:4]
            warn = sum(1 for i in v["udaje"] if "warning" in i and i["udaj"] in v["moje"])
            print(f"{pid} {','.join(dg_codes)} · {v['sablona']} · pro {role_arg}: "
                  + " · ".join(f"{_status_icon(i['status'])} {i['nazev']}" for i in top)
                  + f" · tvoje varování {warn} · tvé postupy: {', '.join(p['postup'] for p in v['postupy'][:2])}")
        return
    dg_codes, facts, docs, mdt, label = _source(src, facts_cli)
    v = role_view(role, dg_codes, facts, recommend(dg_codes, facts, docs, mdt))
    print(f"{label} pro {role_arg} ({role}) · šablona {v['sablona']}")
    print(f"sekce (tvoje nahoře): {','.join(v['sekce'])}")
    for o in v["zajima"]:
        print(f"zajímá tě ({o['odbornost']}, {o['dg']}): {o['zajima']} → {o['proc']} · {o['zdroj']}")
    for i in v["udaje"]:
        if i["udaj"] in v["moje"]:
            extra = f" · {i['warning']['title']}" if "warning" in i else ""
            print(f"  {_status_icon(i['status'])} {i['nazev']}{extra} · {','.join(i['ids']) or i['zdroj']}")
    mine = [p["postup"] for p in v["postupy"] if tag_match(",".join(v["tagy"]), p["tagy"].split(","))]
    print(f"tvé postupy nahoře: {', '.join(mine) or '-'}")


def print_odbornosti(q: str, role: str | None) -> None:
    target = codes(q.upper())
    for o in kb()["odbornosti"]:
        if (o["dg"] == "*" or dg_match(o["dg"], target)) and (role is None or o["role"] == resolve_role(role)):
            print(f"{o['odbornost']} [{o['role']}] {o['dg']} · {o['zajima']} → {o['proc']} · {o['zdroj']}")


# ── Kontrola integrity ────────────────────────────────────────────────────────
def contract_ids(name: str) -> set[str]:
    """`SectionId` / `RoleId` z ARCHITEKTURA.md §8.1 (aby šablony odpovídaly kontraktu)."""
    if not ARCH.exists():
        return set()
    m = re.search(rf"type {name} = ([^;]+);", ARCH.read_text(encoding="utf-8"))
    return set(re.findall(r'"([^"]+)"', m[1])) if m else set()


def check() -> list[str]:
    errors: list[str] = []
    data = {name: read_tsv(name, errors) for name in TABLES}
    fakta = {f["fakt"] for f in data["fakta"]}
    trials = {s["studie"] for s in data["studie"]}
    rkt_ids = {c["id"] for c in data["rkt"]}
    ext = {z["id"] for z in data["zdroje"]}
    if EXT_CATALOG.exists():
        ext |= {s["evidence_id"] for s in json.loads(EXT_CATALOG.read_text(encoding="utf-8"))["sources"]}
    guideline_ids = set()
    if GUIDELINES_DIR.is_dir():
        for f in GUIDELINES_DIR.glob("*.md"):
            guideline_ids |= set(re.findall(r"\*\*((?:OBC|KRC|PLI|PRS)-\d+\.\d+) ", f.read_text(encoding="utf-8")))

    def dup(name, key):
        seen = set()
        for r in data[name]:
            k = tuple(r[x] for x in key)
            if k in seen:
                errors.append(f"{name}: duplicitní {'/'.join(k)}")
            seen.add(k)

    def source_ok(token: str) -> bool:
        if token.startswith("EXT-"):
            return token in ext
        if re.fullmatch(r"RKT-\d\d(/[ZV]\d)?", token):
            return token in rkt_ids
        if re.fullmatch(r"(OBC|KRC|PLI|PRS)-\d+\.\d+", token):
            return not guideline_ids or token in guideline_ids
        return token == "(zdroj postupu)"

    def cond_ok(where: str, cond: str, primary: str | None):
        try:
            parsed = parse(cond, primary)
        except ValueError as e:
            errors.append(f"{where}: {e}")
            return
        for f in facts_in(parsed) - fakta:
            errors.append(f"{where}: fakt {f} není ve fakta.tsv")

    dup("kriteria", ("id",)), dup("postupy", ("postup",)), dup("studie", ("studie",))
    dup("fakta", ("fakt",)), dup("zdroje", ("id",)), dup("rkt", ("id", "typ"))
    all_tags = {t for p in data["postupy"] for t in p["tagy"].split(",")}
    for r in data["kriteria"]:
        where = f"kriteria {r['id']}"
        primary = None if r["fakt"] == "-" else r["fakt"]
        if primary and primary not in fakta:
            errors.append(f"{where}: fakt {primary} není ve fakta.tsv")
        for c in COLORS:
            cond_ok(f"{where}.{c}", r[c], primary)
        if r["kdy"] != "-":
            cond_ok(f"{where}.kdy", r["kdy"], None)
        for token in r["zdroj"].split(","):
            if not source_ok(token):
                errors.append(f"{where}: neznámý zdroj {token}")
        if r["ov"] not in ("D", "E", "⚠"):
            errors.append(f"{where}: ov {r['ov']!r} (D, E nebo ⚠)")
        if r["plati"] != "*" and not tag_match(r["plati"], sorted(all_tags)):
            errors.append(f"{where}: plati {r['plati']} nesedí na žádný postup")
    for p in data["postupy"]:
        where = f"postupy {p['postup']}"
        if p["marker"] != "-":
            try:
                mp = marker_parsed(p["marker"])
                for f in facts_in(mp) - fakta:
                    errors.append(f"{where}: marker → {f} není ve fakta.tsv")
            except ValueError as e:
                errors.append(f"{where}: marker {e}")
        for token in p["zdroj"].split(","):
            if not source_ok(token):
                errors.append(f"{where}: neznámý zdroj {token}")
        for o in p["opora"].split(","):
            if o != "-" and o not in trials and o not in rkt_ids:
                errors.append(f"{where}: opora {o} není ve studie.tsv ani rkt.tsv")
        if p["ov"] not in ("D", "E", "⚠"):
            errors.append(f"{where}: ov {p['ov']!r}")
    for c in data["rkt"]:
        if c["typ"] in ("Z", "V") and c["fakt"] != "-":
            if c["fakt"] not in fakta:
                errors.append(f"rkt {c['id']}: fakt {c['fakt']} není ve fakta.tsv")
            cond_ok(f"rkt {c['id']}", c["podm"], c["fakt"])
    for s in data["studie"]:
        if s["marker"] != "-":
            try:
                for f in facts_in(marker_parsed(s["marker"])) - fakta:
                    errors.append(f"studie {s['studie']}: marker → {f} není ve fakta.tsv")
            except ValueError as e:
                errors.append(f"studie {s['studie']}: marker {e}")
    for n in data["normy"]:
        if n["fakt"] != "-" and n["fakt"] not in fakta:
            errors.append(f"normy {n['param']}: fakt {n['fakt']} není ve fakta.tsv")
    sections, roles = contract_ids("SectionId") or set(SECTION_ORDER), contract_ids("RoleId")
    udaje = {u["udaj"] for u in data["udaje"]}
    dup("sablony", ("sablona",)), dup("udaje", ("udaj",))
    for u in data["udaje"]:
        where = f"udaje {u['udaj']}"
        if u["kdy"] != "-":
            cond_ok(f"{where}.kdy", u["kdy"], None)
        if u["uroven"] not in ("P", "D"):
            errors.append(f"{where}: uroven {u['uroven']!r} (P nebo D)")
        if not set(u["fhir"].split(",")) <= set(FHIR_LETTER.values()) | {"*"}:
            errors.append(f"{where}: fhir {u['fhir']}")
        try:
            re.compile(u["vzor"])
        except re.error as e:
            errors.append(f"{where}: vzor {e}")
        if u["fakt"] != "-" and u["fakt"] not in fakta:
            errors.append(f"{where}: fakt {u['fakt']} není ve fakta.tsv")
        if u["max_dni"] != "-" and not u["max_dni"].isdigit():
            errors.append(f"{where}: max_dni {u['max_dni']!r}")
        for token in u["zdroj"].split(","):
            if not source_ok(token):
                errors.append(f"{where}: neznámý zdroj {token}")
    for t in data["sablony"]:
        where = f"sablony {t['sablona']}"
        if t["kdy"] != "-":
            cond_ok(f"{where}.kdy", t["kdy"], None)
        for s in t["sekce"].split(","):
            sid, *detail = s.split(":")
            if sid not in sections or (detail and detail[0] not in ("brief", "standard", "detailed")):
                errors.append(f"{where}: sekce {s} (SectionId §8.1)")
        if roles and not set(t["role"].split(",")) <= roles:
            errors.append(f"{where}: role {set(t['role'].split(',')) - roles} nejsou RoleId")
        if t["detail"] not in ("brief", "standard", "detailed") or not t["prio"].isdigit():
            errors.append(f"{where}: detail/prio")
        for u in t["zobrazit"].split(","):
            if u not in udaje:
                errors.append(f"{where}: zobrazit {u} není v udaje.tsv")
        for s in ([] if t["studie"] == "-" else t["studie"].split(",")):
            if s not in rkt_ids:
                errors.append(f"{where}: studie {s} není v rkt.tsv")
        for token in t["zdroj"].split(","):
            if not source_ok(token):
                errors.append(f"{where}: neznámý zdroj {token}")
    covered = [t["dg"] for t in data["sablony"] if t["dg"] != "*"]
    for p in data["postupy"]:
        own = [c for c in codes(p["dg"]) if c != "*" and not c.startswith(("C77", "C78", "C79"))]
        if own and not any(dg_match(d, own) for d in covered):
            errors.append(f"postupy {p['postup']}: diagnóza {p['dg']} nemá šablonu v sablony.tsv")
    for o in data["odbornosti"]:
        where = f"odbornosti {o['odbornost']} {o['dg']}"
        if o["role"] != "-" and roles and o["role"] not in roles:
            errors.append(f"{where}: role {o['role']} není RoleId")
        if o["sekce"] != "-" and not set(o["sekce"].split(",")) <= sections:
            errors.append(f"{where}: sekce {o['sekce']}")
        if o["plati"] != "*" and not tag_match(o["plati"], sorted(all_tags)):
            errors.append(f"{where}: plati {o['plati']} nesedí na žádný postup")
        for u in o["udaje"].split(","):
            if u not in udaje:
                errors.append(f"{where}: udaj {u} není v udaje.tsv")
        for token in o["zdroj"].split(","):
            if not source_ok(token):
                errors.append(f"{where}: neznámý zdroj {token}")
    used_ext = {t for r in data["kriteria"] for t in r["zdroj"].split(",")} | \
               {t for p in data["postupy"] for t in p["zdroj"].split(",")} | \
               {t for name in ("udaje", "sablony", "odbornosti") for r in data[name] for t in r["zdroj"].split(",")}
    for z in data["zdroje"]:
        if z["id"] not in used_ext:
            errors.append(f"zdroje {z['id']}: nikde se necituje")
    return errors


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_facts(args: list[str]) -> dict:
    facts: dict = {}
    for a in args:
        if a.startswith("@"):
            facts.update(json.loads(Path(a[1:]).read_text(encoding="utf-8")))
        elif "=" in a:
            k, v = a.split("=", 1)
            facts[k.strip()] = v
        else:
            sys.exit(f"nečekaný argument {a!r} (čekám k=v nebo @soubor.json)")
    return facts


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    verbose, as_json = "-v" in argv, "--json" in argv
    argv = [a for a in argv if a not in ("-v", "--json")]
    cmd, rest = argv[1], argv[2:]
    if cmd == "pohled" and rest:
        src = rest[1] if len(rest) > 1 and "=" not in rest[1] else None
        print_pohled(rest[0], src, parse_facts(rest[2:] if src else rest[1:]))
        return 0
    if cmd == "odbornosti" and rest:
        print_odbornosti(rest[0], rest[1] if len(rest) > 1 else None)
        return 0
    if cmd == "check":
        errors = check()
        for e in errors:
            print(e)
        sizes = {n: len(kb()[n]) for n in TABLES} if not errors else {}
        print("OK " + " ".join(f"{n}={c}" for n, c in sizes.items()) if not errors else f"{len(errors)} chyb")
        return 1 if errors else 0
    if not rest:
        sys.exit(f"{cmd}: chybí argument")
    q, facts = rest[0], parse_facts(rest[1:])
    if cmd == "dg":
        print_dg(q)
    elif cmd == "postup":
        print_postup(q, facts, verbose)
    elif cmd == "fakta":
        print_fakta(q)
    elif cmd == "studie":
        print_studie(q, facts)
    elif cmd == "pravidlo":
        print_pravidlo(q)
    elif cmd in ("norma", "ctcae"):
        print_lookup("normy" if cmd == "norma" else "ctcae", q)
    elif cmd == "sablona":
        print_sablona(q, facts, as_json)
    elif cmd == "doporuc":
        print_doporuc(q, facts, as_json)
    else:
        sys.exit(f"neznámý příkaz {cmd}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
