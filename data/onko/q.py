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
  q.py check                                    kontrola integrity (exit 1 při chybě)

Fakta se zadávají jako `k=v` (např. `lab.crcl=48 rt.prior_months=ne`) nebo `@soubor.json`.
Barvu počítá kód podle kriteria.tsv (D-015), LLM ji nikdy nepřiřazuje. Tento skript je
referenční vyhodnocovač; v aplikaci je zdrojem pravdy services/rules/compatibility.py.
"""
from __future__ import annotations

import json
import os
import re
import sys
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
# Cesty pro `check()`; v kontejneru backendu (báze v /data/onko) je nastaví env (docker-compose.dev.yml).
GUIDELINES_DIR = Path(os.environ.get("ONKO_GUIDELINES_DIR")
                      or REPO / "Dataset_MDT_Copilot_v1.1_pre_timy" / "Dataset_MDT_Copilot_v1.1" / "guidelines")
EXT_CATALOG = Path(os.environ.get("ONKO_EXT_CATALOG")
                   or REPO / "WEB_Template" / "backend" / "services" / "iris" / "data" / "external_sources.json")
APP_RULES = Path(os.environ.get("ONKO_APP_RULES")
                 or REPO / "WEB_Template" / "backend" / "services" / "rules" / "data" / "compatibility_rules.yaml")

TABLES = ("postupy", "kriteria", "fakta", "studie", "rkt", "normy", "ctcae", "zdroje")
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


# ── Kontrola integrity ────────────────────────────────────────────────────────
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
    used_ext = {t for r in data["kriteria"] for t in r["zdroj"].split(",")} | \
               {t for p in data["postupy"] for t in p["zdroj"].split(",")}
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
    verbose = "-v" in argv
    argv = [a for a in argv if a != "-v"]
    cmd, rest = argv[1], argv[2:]
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
    else:
        sys.exit(f"neznámý příkaz {cmd}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
