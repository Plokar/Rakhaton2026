# Soulad se zadáním (T-326, T-332)

> Kontrola aplikace proti zadání *MDT Copilot – Asistovaná interpretace pro multidisciplinární onkologické konzilium* (verze v02, [docs/zadani](zadani/)), stav k 17. 10. 2026 (větev `t-332-soulad-video`).
> Pro tým před pitchem: každý bod zadání, kde je v aplikaci a jak ho ukázat. Katalog požadavků je v [ARCHITEKTURA §2](../ARCHITEKTURA.md#2-katalog-požadavků), scénář dema v [DEMO.md](DEMO.md).

**Legenda:** ✅ hotovo a ukazatelné v UI · 🟡 hotovo jen částečně · ❌ chybí. Položky bez „BONUS“ jsou **povinné minimum**.

## Shrnutí

- **Povinné minimum je pokryté celé** a ukazatelné v UI.
- **Bonusy:** po T-332 jsou v UI všechny ze zadání. Částečně jen dvě věci: u pravidel red flags jde zapínat a vypínat, ale ne měnit prahy, a sady guidelines a studií se volí automaticky podle diagnózy.
- T-332 doplnil: Q&A nad případem, podobné případy, zprávu pro praktického lékaře, verzování potvrzeného závěru s auditní stopou, zapínání pravidel red flags v nastavení boardu, další role (nukleární medicína, paliativní péče, geriatrie, klinická genetika, koordinátor), míru jistoty u citací a hlášku „V dostupné dokumentaci se nenachází“.

Demo účty: `predseda`, `onkolog`, `pneumolog`, `chirurg`, `radiolog`, `patolog`, `radioterapeut` (1-click na přihlášení). Pacient pro demo P03 (GIT), podobné případy P05 (mamární).

## 1. Hlavní cíl a principy

| Požadavek | Stav | Kde a jak ukázat |
|---|---|---|
| Prototyp: AI zkonsoliduje data pacienta, modulární podklad, oficiální záznam | ✅ | Detail pacienta `/dashboard/cases/[id]` (podklad po sekcích), `/record` (záznam do IRIS) |
| **Příprava:** nominace, kontrola úplnosti | ✅ | Kalendář → `+` u zasedání → zařazení pacienta: varování CHYBÍ / MIMO NORMU / ROZPOR / NEJISTOTA AI, otázku nelze přeskočit; připravenost v % |
| **Zasedání:** orientace, pohledy odborností, diskuse, zápis | ✅ | Jednání komise `/dashboard/mdt/[id]`, okno pro projektor, detail (Odbornosti), Závěr komise |
| **Po zasedání:** komunikace závěru, úkoly, sledování | ✅ | Shrnutí pro pacienta a zpráva pro PL, úkoly s vlastníkem a termínem (`/dashboard/tasks`), re-MDT |
| Human-in-the-loop, AI vizuálně odlišená | ✅ | Fialové bloky „AI návrh“, „AI návrh upravený lékařem“; nic oficiálního bez potvrzení předsedou |

## 2. Výstupní report

### A. Společný úvod

| Požadavek | Stav | Kde a jak ukázat |
|---|---|---|
| Identifikace případu a hlavní diagnóza | ✅ | Hlavička `P03 · muž · 67 let`, MKN-10 + TNM (bez jména a RČ, D-018) |
| ECOG lékař vs. pacient, rozdíl = red flag | ✅ | Dlaždice PS „0 / pac. 1“ oranžově, varování `RF-ECOG` (OBC-1.3) |
| Otázka pro MDT od navrhujícího lékaře, absence = neúplný případ | ✅ | Otázka dole v přehledu s citací nominace; bez otázky zařazení nejde (OBC-1.1) |
| Časová osa onemocnění | ✅ | Detail → Souhrn a časová osa (přepínač AI shrnutí / události z IRIS) |
| BONUS Stav připravenosti s doporučením doplnění | ✅ | Procento připravenosti v kalendáři a agendě, šablona „v podkladech 7 z 9“, stav „vrácen k doplnění“ |

### B. Sekce podle odborností

| Požadavek | Stav | Kde a jak ukázat |
|---|---|---|
| Chirurg, klinický onkolog, radiolog, patolog, pacient (PROMs) | ✅ | Detail → Odbornosti (barva odbornosti, posouzení role s kritérii), Hlas pacienta s trendem PROMs |
| BONUS RECIST 1.1 předvýpočet (orientační) | ✅ | Sekce radiologa: P03 83 → 50 mm = PR, označeno jako orientační |
| BONUS návrh chybějících biomarkerů | ✅ | Varování „Chybí biomarker …“ (`RF-MISSING`, KRC-1.1 / PLI-1.3 / PRS-1.3) |
| BONUS další role: nukleární medicína, paliativní péče, geriatrie, klinická genetika, koordinátor | ✅ | Nastavení podkladu → Přítomní: zaškrtnout role → v podkladu jejich pohledy s citacemi (T-332) |

### B2. Decision Support Panel

| Požadavek | Stav | Kde a jak ukázat |
|---|---|---|
| Možnosti léčby z guidelines s přesnou citací (RAG) | ✅ | Detail → Léčba a studie: všechny postupy se semaforem, citace `KRC-2.4` otevře pasáž |
| Screening studií (vhodný / nevhodný / chybí údaj + důvod) | ✅ | Klinické studie (screening RKT) po kritériích `RKT-03/V3` |
| 2–3 otázky k diskusi | ✅ | Detail → Otázky k diskusi |
| Kontrola závěru vůči guidelines, při odchylce zdůvodnění | ✅ | Závěr komise → zvolit postup s „pozor“ → výzva ke zdůvodnění; bez něj nejde potvrdit |
| BONUS podobné případy (anonymizované) | ✅ | Detail → Podobné případy (P05: jiné pacientky s C50.4, pohlaví a věková dekáda, citace záznamu) |

### C. Zápis a závěr

| Požadavek | Stav | Kde a jak ukázat |
|---|---|---|
| Editace a zápis rozhodnutí, termín re-evaluace | ✅ | `/record`: sekce záznamu MDT, Plánované re-MDT |
| Strukturovaný záznam: kvórum, zvolený postup, zdůvodnění, soulad s guidelines, odlišná stanoviska | ✅ | Přítomní, Zvažované možnosti a soulad, Odlišná stanoviska členů |
| Export PDF / HL7 FHIR | ✅ | Po potvrzení: Export PDF, FHIR document Bundle |
| BONUS FHIR R4 / mCODE | ✅ | Bundle s `meta.profile` mCODE, Composition, CarePlan, Task, DetectedIssue, Provenance |
| BONUS Ambient Scribe | ✅ | Jednání → Nahrát diskusi, nebo `/record` → AI zapisovatel (audio nebo přepis) → draft odlišený od potvrzeného textu |
| BONUS akční plán s úkoly a termíny | ✅ | Úkoly v závěru → `Task` v IRIS → `/dashboard/tasks` (stav, vlastník, termín) |
| BONUS shrnutí pro pacienta a zpráva pro praktického lékaře | ✅ | Po potvrzení: „Připravit shrnutí pro pacienta a zprávu pro PL“ (T-332), obojí s citacemi, v PDF i FHIR |
| BONUS uzamčení a verzování s auditní stopou | ✅ | Potvrzený závěr „zamčeno“; předseda „Upravit (nová verze)“ s důvodem → auditní stopa verzí; stejná `Composition` jako `amended` (T-332) |

## 3. Funkcionalita

| Požadavek | Stav | Kde a jak ukázat |
|---|---|---|
| Výběr sekcí a pořadí | ✅ | Jednání → Další → Nastavit podklad: zapnout / vypnout, přetáhnout |
| Skrytí sekcí nepřítomných odborností | ✅ | Přítomní: odškrtnutá role se negeneruje; chybí-li role vyžadovaná guidelines, upozornění s citací |
| Míra detailu | ✅ | Podrobnost stručně / standardně / podrobně, celkově i po sekcích |
| BONUS šablony podle typu nádoru | ✅ | Doporučená šablona podle diagnózy nahoře v nastavení |
| BONUS pravidla red flags | 🟡 | Pravidla varovných signálů: zapnout / vypnout pro board (T-332); prahy jsou v kódu s citací pasáže |
| BONUS výchozí pohled pro roli | ✅ | Detail → přepínač „Předsedy / Pro mě“ (odbornost nahoře) |
| Syntéza zpráv a dotazníku | ✅ | Souhrn a Hlas pacienta kombinují zprávy z IRIS a PROMs |
| Nesrovnalosti se závažností a citací obou zdrojů | ✅ | Varovné signály: závažnost, oba zdroje, „Porovnat zdroje“ |
| BONUS rozšířené red flags (zastaralé podklady, TNM, interakce…) | ✅ | `RF-STALE`, `RF-TNM`, `RF-MED` (interakce), `RF-LAB` (trend markerů), `RF-NEWSYMPTOM`, `RF-PROMS` |
| Klik na tvrzení → přesný zdroj | ✅ | Číselný štítek citace → panel se zdrojem a zvýrazněnou pasáží |
| „V dostupné dokumentaci se nenachází“ | ✅ | Chybějící údaje v podkladu i odpověď Q&A tímto zněním (T-332) |
| BONUS citace na úrovni věty (zvýraznění, datum, autor, jistota) | ✅ | Panel zdroje: odstavec zvýrazněný, datum a autor; u tvrzení „shoda 81 %“ z grounding validátoru (T-332) |
| Bezpečnost: AI odlišená, nic bez potvrzení | ✅ | Viz bod 1 |
| BONUS strukturovaná extrakce (NLP) s opravou | ✅ | Detail pacienta → Vložit zprávu: návrh hodnot s citací → oprava → potvrzení do IRIS |
| BONUS Q&A nad případem | ✅ | Detail → Zeptat se na případ: odpověď jen z dat pacienta s citacemi (T-332) |
| BONUS audit, GDPR, evaluace | ✅ | `LlmCallLog` (model, hash promptu, zdroje), `Provenance` u potvrzení, pseudonymizace před LLM, [EVAL.md](EVAL.md) |

## Co neříkat

- Prahy pravidel red flags v UI nastavit nejdou, jen zapnout a vypnout.
- Sady guidelines a studií vybírá aplikace podle diagnózy, předseda je nevolí ručně.
- Podobné případy jsou z dat hackathonu: pro P03 (C18) jiný pacient není, ukazovat na P05.
