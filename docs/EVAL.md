# Eval MDT Copilot (T-301, T-302)

> Pro tým a pro slide „Tech“ v pitchi. Postup je v [ARCHITEKTURA §5.8](../ARCHITEKTURA.md#58-evaluace), formát ground truth v [data/dev_ground_truth/README.md](../data/dev_ground_truth/README.md).

**Pozor: dev ground truth není oficiální.** Sestavili jsme ho ručně z dat a z hypotéz v DATASET §9 (T-013), ne z výstupu aplikace. Oficiální ground truth zveřejní organizátor po odevzdání; pak stačí `--gt`.

## Jak se měří

`python manage.py eval_ground_truth --gt data/dev_ground_truth [--patients P03] [--model ID] [--out docs/EVAL.md]` vygeneruje podklad každého pacienta **stejnou cestou jako aplikace**: data z IRIS FHIR, guidelines, studie a grounding přes IRIS Vector Search. Pak ho porovná s ground truth (`services/eval/evaluate.py`).

| Metrika | Co znamená |
|---|---|
| Red flags (key / vše) | varování nalezené se správným pravidlem **a** aspoň jedním správným zdrojem (key = hlavní nálezy datasetu) |
| Klíčová fakta | fakt má v podkladu citaci svého zdroje (měřeno na úrovni citací, ne znění) |
| Údaj chybí | chybějící povinný údaj podklad nebo kontrola úplnosti hlásí jako „chybí“ |
| Nejistota AI | rozmezí / nejednoznačnost hlášená jako NEJISTOTA AI (např. „ECOG 0–1“) |
| Kritéria studií, studie celkem | status `met` / `not_met` / `unknown` po kritériích a celkový stav (obhajitelné alternativy se počítají) |
| RECIST | odpověď CR / PR / SD / PD |
| Semafor (pravidla) | barva pravidla souladu postupu se stavem pacienta |
| Neověřená tvrzení | podíl tvrzení, která neprošla grounding validátorem (cíl 0 %) |

## Výsledek: deterministická vrstva (bez LLM), 17. 10. 2026

Pravidla, semafor, screening studií, RECIST a grounding běží bez LLM (`AI_PROVIDER=mock`). Je to spodní hranice: s Gemini přibude souhrn, pohledy odborníků, RF-LLM (rozpory mezi texty) a extrakce SLD / nových lézí.

| Pacient | Red flags (key) | Red flags (vše) | Klíčová fakta | Údaj chybí | Nejistota AI | Kritéria studií | Studie celkem | RECIST | Semafor (pravidla) | Neověřená tvrzení | Čas |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P01 | 7/7 (100%) | 11/12 (92%) | 13/13 (100%) | 4/4 (100%) | – | 14/19 (74%) | 4/6 (67%) | 1/1 (100%) | 5/5 (100%) | 0/86 (0%) | 1 s |
| P02 | 7/10 (70%) | 11/14 (79%) | 13/13 (100%) | 0/2 (0%) | – | 13/17 (76%) | 3/6 (50%) | 0/1 (0%) | 4/4 (100%) | 0/76 (0%) | 1 s |
| P03 | 6/6 (100%) | 10/10 (100%) | 19/19 (100%) | 2/3 (67%) | 1/1 (100%) | 18/18 (100%) | 3/6 (50%) | 1/1 (100%) | 13/13 (100%) | 0/79 (0%) | 1 s |
| P04 | 8/8 (100%) | 9/9 (100%) | 12/12 (100%) | 3/5 (60%) | – | 11/15 (73%) | 1/6 (17%) | – | 12/12 (100%) | 0/82 (0%) | 1 s |
| P05 | 6/7 (86%) | 8/11 (73%) | 12/12 (100%) | 3/3 (100%) | 1/1 (100%) | 13/17 (76%) | 2/6 (33%) | 1/1 (100%) | 4/7 (57%) | 0/78 (0%) | 1 s |
| P06 | 9/10 (90%) | 13/14 (93%) | 12/12 (100%) | 2/4 (50%) | 1/1 (100%) | 17/19 (89%) | 4/6 (67%) | 1/1 (100%) | 5/9 (56%) | 0/83 (0%) | 1 s |
| **Celkem** | **43/48 (90%)** | **62/70 (89%)** | **81/81 (100%)** | **14/21 (67%)** | **3/3 (100%)** | **86/105 (82%)** | **17/36 (47%)** | **4/5 (80%)** | **43/50 (86%)** | **0/484 (0%)** | 7 s |

**Pro pitch:** 90 % klíčových varovných signálů, 100 % klíčových faktů s citací zdroje, 86 % barev semaforu, **0 neověřených tvrzení z 484**. Všechno deterministicky, bez LLM, takže výsledek je opakovatelný.

## NVIDIA (`nvidia/nemotron-3-super-120b-a12b`, výchozí LLM), 17. 10. 2026

Plný běh nad 6 pacienty se stejnou cestou jako aplikace (T-323): LLM NVIDIA bez přemýšlení, vektory v IRIS z `nvidia/nemotron-3-embed-1b` @ 2048 (index přepočítaný z datasetu), práh grounding v2 0,40 (kalibrace v ARCH §5.3).

| Pacient | Red flags (key) | Red flags (vše) | Klíčová fakta | Údaj chybí | Nejistota AI | Kritéria studií | Studie celkem | RECIST | Semafor (pravidla) | Neověřená tvrzení | Čas |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P01 | 7/7 (100%) | 11/12 (92%) | 13/13 (100%) | 4/4 (100%) | – | 18/19 (95%) | 4/6 (67%) | 1/1 (100%) | 5/5 (100%) | 6/83 (7%) | 30 s |
| P02 | 7/10 (70%) | 11/14 (79%) | 13/13 (100%) | 1/2 (50%) | – | 17/17 (100%) | 4/6 (67%) | 1/1 (100%) | 4/4 (100%) | 5/71 (7%) | 194 s |
| P03 | 6/6 (100%) | 10/10 (100%) | 19/19 (100%) | 2/3 (67%) | 1/1 (100%) | 18/18 (100%) | 3/6 (50%) | 0/1 (0%) | 13/13 (100%) | 11/74 (15%) | 28 s |
| P04 | 8/8 (100%) | 9/9 (100%) | 12/12 (100%) | 5/5 (100%) | – | 11/15 (73%) | 1/6 (17%) | – | 12/12 (100%) | 7/74 (9%) | 51 s |
| P05 | 6/7 (86%) | 8/11 (73%) | 12/12 (100%) | 3/3 (100%) | 1/1 (100%) | 16/17 (94%) | 3/6 (50%) | 1/1 (100%) | 4/7 (57%) | 8/76 (11%) | 97 s |
| P06 | 9/10 (90%) | 13/14 (93%) | 12/12 (100%) | 3/4 (75%) | 1/1 (100%) | 18/19 (95%) | 4/6 (67%) | 1/1 (100%) | 5/9 (56%) | 10/80 (12%) | 123 s |
| **Celkem** | **43/48 (90%)** | **62/70 (89%)** | **81/81 (100%)** | **18/21 (86%)** | **3/3 (100%)** | **98/105 (93%)** | **19/36 (53%)** | **4/5 (80%)** | **43/50 (86%)** | **47/458 (10%)** | 524 s |

**Co přidal LLM proti deterministické vrstvě:** „údaj chybí“ 67 % → **86 %**, kritéria studií 82 % → **93 %**, studie celkem 47 % → 53 %. Klíčové red flags 90 %, fakta 100 % a semafor 86 % drží pravidla.

**Neověřená tvrzení 10 %** (47 z 458): validátor dělá, co má, a v UI jsou označená „Neověřeno“. Nejčastěji jde o čísla, která model dopočítal a ve zdroji doslova nejsou (součet lézí 83 mm, věk, procenta). Citace „odstavce“ dotazníku (`P02-prom02#3`) se po tomto běhu převádí na celý zdroj, další kolo ladění promptů je T-302.

**Čas:** 28–51 s na pacienta bez čekání na limit; s limitem hostovaného API (429, 40 požadavků za minutu) až 194 s. Cíl NFR-1 (< 20 s) splní vyhrazený NIM, na demo slouží záloha podkladu (`demo save`, `MDT_DEMO_OFFLINE`).

### Srovnání modelů NVIDIA po opravách (T-301), 17. 10. 2026

Oba běhy už s opravami z prvního běhu (citace bez závorek, citace odstavce dotazníku → celý zdroj, B2 ve dvou krocích, RF-LLM bez šumu). Součty za 6 pacientů:

| Model | Red flags (key) | Red flags (vše) | Klíčová fakta | Údaj chybí | Nejistota AI | Kritéria studií | Studie celkem | RECIST | Semafor (pravidla) | Neověřená tvrzení | Čas |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `nemotron-3-super-120b-a12b` (výchozí) | **45/48 (94%)** | **64/70 (91%)** | **81/81 (100%)** | **18/21 (86%)** | **3/3 (100%)** | **98/105 (93%)** | **19/36 (53%)** | **4/5 (80%)** | **43/50 (86%)** | **48/455 (11%)** | 284 s |
| `nemotron-3-ultra-550b-a55b` | **45/48 (94%)** | **64/70 (91%)** | **81/81 (100%)** | **18/21 (86%)** | **3/3 (100%)** | **98/105 (93%)** | **19/36 (53%)** | **4/5 (80%)** | **43/50 (86%)** | **17/470 (4%)** | 238 s |

**Závěr:** `ultra` má o dost méně neověřených tvrzení (4 % proti 11 %) při stejných ostatních metrikách a podobném čase, ale hostované API u něj během běhu hlásilo přetížení (503, část volání se opakovala nebo spadla na deterministický záložní výstup). Výchozí proto zůstává `super`; `ultra` se zapne `NVIDIA_MODEL=nvidia/nemotron-3-ultra-550b-a55b` (na vyhrazeném NIM bez přetížení je to lepší volba). Red flags 94 % (proti 90 % deterministicky) přidalo vyladěné RF-LLM (P05 „únava mírná“ vs. 8/10).

## Gemini (`gemini-3.8-flash`)

**Stav:** plný běh nad 6 pacienty a srovnání s `gemini-4-argon` **neproběhlo**. Free tier (D-021) má limit **5 požadavků za minutu a 20 požadavků za den** na model (embeddingy 1 000 za den). Jeden podklad potřebuje ~9 volání LLM, takže denní limit stačí zhruba na 2 podklady. Běh 17. 10. v 01:22 po vyčerpání denního limitu spadl na fallback a jeho čísla neměří Gemini, proto tu nejsou. **Pro plný eval a srovnání modelů je potřeba placený tier (Q9).**

Co ukázal jeden platný běh na P03 (před vyčerpáním limitu) a co jsme opravili (T-302):

| Nález | Oprava |
|---|---|
| 37 % tvrzení neověřených; velká část „citované zdroje nemají vektory“ | reindex s mockem po potvrzení závěru mazal Gemini vektory; teď se mažou jen vektory stejného modelu (`vector_store._replace`) |
| LLM psal odvozená čísla a data („po 8 cyklech“ bez citace zdroje, datum + 6 týdnů) | pravidlo v promptu souhrnu a rolí: každé číslo a datum musí být v citovaném zdroji, nic se nepřepočítává |
| „grade 2“ neprošlo, ve zdroji je „G2“ | grounding bere čísla i z tokenů zdroje (`G2`, `S3`) |
| paralelní volání padala („client has been closed“) | Gemini klient se zakládá pod zámkem (thread-safe) |
| limit za minutu shodil volání | `generate` i `embed` čekají podle „retry in Ns“ (max 65 s, 3 pokusy) |

Další běh až po resetu limitu nebo s placeným tierem: `AI_PROVIDER=gemini python manage.py eval_ground_truth --gt /data/dev_ground_truth --patients P03 --out /data/demo_cache/eval.md`.

## Změny T-302 v deterministické vrstvě

- `RF-GENETIC` pro Lynchův syndrom: kolorektum + nádor Lynchova spektra v rodinné anamnéze + MMR / MSI nevyšetřeno (P03-RF08, OBC-2.4). Klíčové red flags 42 → **43 / 48**.
- RECIST: nová léze → PD (P02, nové mozkové metastázy). Novou lézi pozná až LLM, bez něj P02 zůstává PR.
- Znalostní báze `data/onko` v semaforu (T-316): další postupy pro diagnózu pacienta, semafor (pravidla) 39 → **43 / 50**.

## Zbývající nesoulady (vstup pro další T-302)

Nejvíc chybí rozpory mezi texty (P02 „EF v normě“ vs. LVEF 52 %, P05 „únava mírná“ vs. 8/10) a nesplněná doporučení kontrol (echokardiografie u P02 a P06). Najít je má RF-LLM, tedy Gemini. Část kritérií studií je `unknown`, kde ground truth zná odpověď (RKT-01, RKT-02, RKT-06): deterministická pravidla pro tato kritéria zatím chybí.

- **P01 · trials:** RKT-01/Z3: čekáno met, podklad unknown; RKT-01/Z4: čekáno met, podklad unknown; RKT-01/V4: čekáno not_met, podklad unknown; RKT-06/V1: čekáno not_met, podklad unknown; RKT-06/V2: čekáno not_met, podklad unknown
- **P02 · red_flags_key:** P02-RF07 RF-NOMINATION: Zpráva k nominaci uvádí „EF v normě“, poslední LVEF je 52 %; P02-RF08 RF-MISSING: Chybí kontrolní echokardiografie; P02-RF10 RF-LLM: TNM v záznamu MDT cN2 vs. cN1
- **P02 · missing_data:** P02-M01: Kontrolní echokardiografie (doporučena za 3–4 týdny od 20. 8.); P02-M02: Plán snižování dexametazonu
- **P02 · trials:** RKT-02/Z2: čekáno met, podklad unknown; RKT-02/V1: čekáno not_met, podklad unknown; RKT-02/V2: čekáno not_met, podklad unknown; RKT-06/V3: čekáno met, podklad unknown
- **P02 · recist:** čekáno PD, podklad: RECIST 1.1, cílové léze: SLD 112 → 46 mm (-59 % od baseline), nadir 46 mm; odpov
- **P03 · missing_data:** P03-M03: Stav DPD před fluoropyrimidiny
- **P04 · missing_data:** P04-M04: Ověření ložiska levé nadledviny (MR nadledvin / biopsie); P04-M05: Vyšetření SIADH (osmolalita séra a moči, natriurie)
- **P04 · trials:** RKT-04/V2: čekáno not_met, podklad unknown; RKT-05/Z1: čekáno met, podklad unknown; RKT-05/V1: čekáno not_met, podklad unknown; RKT-06/Z2: čekáno not_met, podklad unknown
- **P05 · red_flags_key:** P05-RF06 RF-LLM: Zpráva uvádí „únava mírná“, pacientka den předtím 8/10
- **P05 · trials:** RKT-06/V2: čekáno not_met, podklad unknown; RKT-01/Z3: čekáno met, podklad unknown; RKT-01/Z4: čekáno met, podklad unknown; RKT-01/V4: čekáno met, podklad unknown
- **P05 · compatibility:** VS-PRS-07: čekáno green, podklad orange; VS-OBC-11: čekáno orange, podklad None; VS-PRS-08: čekáno green, podklad grey
- **P06 · red_flags_key:** P06-RF05 RF-MISSING: Chybí kontrolní echokardiografie (začátek října)
- **P06 · missing_data:** P06-M03: Kontrolní echokardiografie (začátek října 2026); P06-M04: Ověření nádoru ledviny a stanovisko urologa
- **P06 · trials:** RKT-02/V1: čekáno not_met, podklad unknown; RKT-02/V2: čekáno not_met, podklad unknown
- **P06 · compatibility:** VS-OBC-03: čekáno grey, podklad None; VS-OBC-04: čekáno orange, podklad None; VS-URO-01: čekáno orange, podklad None; VS-DG-01: čekáno orange, podklad None
