# data/onko: znalostní báze onkologie (T-315)

Postupy léčby podle diagnózy a markeru, klinické studie, kritéria semaforu pro všechny modality, normální hodnoty a CTCAE. Formát je TSV (1 řádek = 1 záznam, první sloupec = klíč). **Nikdy nenačítej celý soubor do promptu.** Vyfiltruj ho přes `q.py` nebo podle prvního sloupce.

## Jak se ptát

```bash
python3 data/onko/q.py dg C34                    # jaké postupy u diagnózy (MKN-10)
python3 data/onko/q.py postup pli-sbrt intent=C rt.prior_same_area=ano rt.prior_months=3
                                                 # semafor: barva, proč, zdroj; bez faktů = co chybí
python3 data/onko/q.py fakta pli-sbrt            # jaké údaje postup potřebuje
python3 data/onko/q.py studie C50 | KEYNOTE-189 | RKT-03 [k=v …]   # studie, screening RKT
python3 data/onko/q.py pravidlo VS-RT-02         # pravidlo + na které postupy se vztahuje
python3 data/onko/q.py norma hemoglobin          # normální hodnota, jednotka, převod, onko prahy
python3 data/onko/q.py ctcae neutro              # stupně toxicity G1–G4
python3 data/onko/q.py sablona P04 [--json]      # doporučená šablona projektoru = BriefConfig + klíčové údaje
python3 data/onko/q.py doporuc P04 [--json]      # co v podkladech chybí → varování (IntakeWarning)
python3 data/onko/q.py pohled chirurg [P03]      # co jde lékaři nahoru; bez pacienta = všichni P01–P06
python3 data/onko/q.py odbornosti C50 kardiolog  # koho co zajímá a proč
python3 data/onko/q.py check                     # integrita (test: services/eval/test_onko_kb.py)
```

`Pxx` čte bundle z datasetu jen pro vývoj a testy. Aplikace má za běhu data jen z IRIS.

## Šablony, doporučené údaje a odbornosti (T-317)

- **`sablony.tsv`:** šablona podkladu pro projektor podle diagnózy a situace (`kdy`, např. `tnm.m1=ano&bm.her2=pos`).
  - `sekce` (pořadí, `:detail`), `role` a `detail` dávají platný `BriefConfig` (§8.5). Výstup `q.py sablona --json` jde rovnou do presetů.
  - `zobrazit` = klíčové údaje velkým písmem na projektor.
  - Výběr šablony: `prio` (jen když `kdy` platí) > konkrétní diagnóza > splněné `kdy` > počet shod. `sab-duplicita` (OBC-1.4) má přednost.
- **`udaje.tsv`:** katalog údajů podle diagnózy.
  - `P` = povinné (POZADAVKY §4 a standard péče) → „Chybí: …“, severity `moderate`.
  - `D` = doporučené → „Doporučeno: … (mohlo by se hodit)“, severity `low`. Ukáže se jen tehdy, když jeho `kdy` jistě platí, aby nevznikal šum.
  - Vyhledání: `fhir` (O Observation, R DiagnosticReport, D DocumentReference, C Composition, S ServiceRequest, Q PROMs, P Procedure, M léky, K Condition, A alergie) + `vzor` (regex).
  - Název zprávy nebo pozorování platí přímo. Hodnota „nevyšetřeno/probíhá“ nebo věta s „doporučeno/doplnit/?“ je jen **zmínka**: varování zůstane, ale cituje ten dokument.
  - `max_dni` = starší výsledek se hlásí jako zastaralý.
  - Položka konkrétní diagnózy (`pli.koureni`) přebíjí obecnou se stejným názvem (`obc.koureni`).
  - Varování mají tvar `IntakeWarning` (§8.6, `kind: "missing"`, id `DOP:…` / `CHYBI:…`), kontrakt se nemění.
- **`odbornosti.tsv`:** co kterého lékaře zajímá u diagnózy a léčby a proč.
  - `plati` = modality, o kterých rozhoduje (tagy postupů).
  - `sekce` = bloky, které mu jdou nahoru (souhrn zůstává první, ARCH §7.3).
  - `udaje` = jeho údaje a varování nahoru.
  - `role` = `RoleId` z `UserProfile.specialty`. `-` = odbornost mimo `RoleId`, jen informativně.

Fakta: `k=v` nebo `@fakta.json`. Hodnoty: číslo, `ano`/`ne`, kategorie. `ne` u „dní/měsíců od události“ znamená, že událost nebyla. `nezn` znamená nevyšetřeno nebo probíhá (= chybí údaj, pokud pravidlo na `nezn` výslovně nečeká).

## Soubory

| Soubor | Klíč | Obsah |
|---|---|---|
| `postupy.tsv` | `dg` | diagnóza → kontext (stadium, linie) → marker → postup, tagy, opora ve studiích, zdroj |
| `kriteria.tsv` | `id` | pravidla semaforu `VS-*`: na co platí, fakt, podmínka 🟢/🟠/🔴, proč, zdroj |
| `studie.tsv` | `studie` | registrační a klíčové studie (reálné, uzavřené): rameno, srovnání, výsledek, rok |
| `rkt.tsv` | `id` | fiktivní otevřené studie RKT-01…06 z datasetu, kritéria Z/V strojově |
| `fakta.tsv` | `fakt` | slovník faktů: typ, jednotka, kde je v IRIS/FHIR, výpočet odvozených |
| `normy.tsv` | `param` | normální hodnoty + jednotky, onko prahy, převody US → SI (`ds` = referenceRange datasetu) |
| `ctcae.tsv` | `param` | CTCAE v5 stupně G1–G4 |
| `zdroje.tsv` | `id` | nové externí zdroje `EXT-…` (k 13 v `services/iris/data/external_sources.json`) |
| `sablony.tsv` | `sablona` | šablony podkladu pro projektor podle diagnózy (BriefConfig + klíčové údaje) |
| `udaje.tsv` | `udaj` | povinné a doporučené údaje podle diagnózy + jak je najít ve FHIR |
| `odbornosti.tsv` | `role` | co kterého lékaře zajímá u diagnózy a léčby a proč |

## Diagnózy

C34 (NSCLC, SCLC) · C50 (časný i M1) · C18/C20/C18-C20 (kolon, rektum, mKRC) · C64 + D41 (ledvina) · C61 · C67 · C15, C16 · C25 · C22 · C56 · C53 · C54 · C43 · C00-C14,C32 (hlava a krk) · C71 · C79.3, C79.5, C78.x (metastázy) · `*` (podpůrná péče a studie pro všechny). Další nádor = další řádky.

## Tagy (`postupy.tagy` × `kriteria.plati`)

Pravidlo platí na postup, když sedí `dg` a některý tag. Tagy jsou hierarchické: pravidlo `CHT.platina` platí i na `CHT.platina.cis`. `*` = všechny postupy.

| Tag | mdt-modalita | Příklady podtagů |
|---|---|---|
| `CHIR` | chirurgie | `.plice` `.plice.segment` `.jatra` `.jatra.tx` `.pankreas` `.ledvina` `.prs.bcs` `.mozek` `.pater` |
| `RT` | rt | `.SBRT.plice` `.SRS` `.WBRT` `.hrudnik` `.panev` `.hn` `.pater` `.kost` `.brachy.prostata` `.jatra` |
| `CHT` | chemoterapie | `.platina.cis/.karbo/.oxali` `.FP` `.FP.cape` `.irino` `.taxan` `.taxan.doce` `.antra` `.pemetrexed` `.TMZ` |
| `IO` | imunoterapie | `.PD1` `.PDL1` `.CTLA4` `.LAG3` |
| `TT`, `ADC` | cilena | `TT.EGFR.osi` `TT.ALK.lorla` `TT.HER2` `TT.antiEGFR` `TT.antiVEGF.bev` `TT.VEGFR` `TT.CDK46.ribo` `TT.PARP.ola` … `ADC.HER2.tdxd` `ADC.TROP2.sg` |
| `HT` | hormonalni | `.AI` `.TAM` `.SERD` `.OFS` `.ADT` `.ARPI.abi/.enza/.apa/.daro` |
| `SYS`, `SUP` | jina-systemova | `SYS.BMA.deno/.zol` `SYS.steroid` `SYS.antikoag.doac` `SUP.paliat` `SUP.nutri` … |
| `ABL` | chirurgie (interv. radiologie) | `.RFA` `.TACE` `.SIRT` |
| `NUK` | rt (nukleární medicína) | `.Ra223` `.LuPSMA` |
| `DG` | diagnostika | `.biopsie.tt` `.EBUS` |
| `SLED`, `STUDIE` | sledování, zařazení do studie | `STUDIE` vyhodnotí i kritéria RKT |

Příznaky: `INT` = intenzivní léčba (ECOG, G8, hmotnost), `RAD` = radikální léčba (staging, nejasné ložisko).

## Podmínky (`zel` / `ora` / `cer`, `kdy`, `rkt.podm`)

`<x` `<=x` `>x` `>=x` `=a|b` (výčet) · `a-b` (rozsah včetně) · `&` = a zároveň · `;` = nebo · `fakt>=x` = jiný fakt než ve sloupci `fakt` · `*` = jinak · `-` = barva se nepoužívá. `kdy` = kdy pravidlo platí (`age>=70`, `intent=C`).

Vyhodnocení (POZADAVKY §5.1, D-015): nejdřív 🔴, pak 🟠, pak 🟢. Když chybí údaj, výsledek je ⚪. Celková barva postupu = nejhorší ze všech pravidel (🔴 > 🟠 > ⚪ > 🟢). Barvu počítá kód, LLM jen vytáhne hodnotu faktu s citací. Vždy se ukážou všechny postupy, i červené. Text u barvy je věcný a nikdy nepíše „doporučujeme“.

`VS-BM-01` hlídá sloupec `marker` postupu. Uplatní se jen tehdy, když marker nehlídá jiné pravidlo (např. `VS-KRC-06` pro RAS).

## Zdroje a ověření (`ov`)

- `D`: dodané guidelines nebo studie datasetu (`OBC/KRC/PLI/PRS-x.y`, `RKT-0x/Zn`). Na nich stojí demo.
- `E`: externí zdroj `EXT-…` (SmPC/EPAR, ESMO, EAU, ESC…). Vždy jen pro práh pravidla, nikdy pro fakt pacienta (D-016).
- `⚠`: práh potvrdil tým nebo je k ověření lékařem (Q-7), případně jde o novou indikaci po vydání guidelines.

**Pozor:**

- Nové `EXT-…` a obsah mimo dataset sestavil AI agent z odborných znalostí (10/2026). Proti originálům je **zatím nikdo neověřil**.
- Registrace v EU neznamená úhradu v ČR (SÚKL).
- Výsledky studií jsou zjednodušené (↑ = lepší v rameni).
- Studie RKT jsou fiktivní (dataset), ostatní jsou reálné a uzavřené.

## Vztah k aplikaci

- Aplikace (semafor T-503) má jako zdroj pravdy `services/rules/data/compatibility_rules.yaml` + `compatibility.py`. Báze je jeho nadmnožina se stejnými ID a zdroji (`[app]` ve výpisu q.py). Soulad hlídá test `services/eval/test_onko_kb.py`.
- Napojení báze na aplikaci je úkol T-316: generický vyhodnocovač podmínek, katalog postupů z `postupy.tsv` a nové `EXT-…` do `external_sources.json`.
- Za běhu aplikace čte fakta pacienta jen z IRIS. `rkt.tsv` je jen kompaktní pohled na `studie/` datasetu.
