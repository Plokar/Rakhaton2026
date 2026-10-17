# Soulad se zadáním (T-326)

> Kontrola aplikace proti zadání *MDT Copilot – Asistovaná interpretace pro multidisciplinární onkologické konzilium* (verze v02, [docs/zadani](zadani/)), stav k 17. 10. 2026 (větev `t-324-spoluprace-projektor`).
> Pro tým před pitchem: co splňujeme, kde to ukázat a co ještě chybí. Katalog požadavků je v [ARCHITEKTURA §2](../ARCHITEKTURA.md#2-katalog-požadavků), scénář dema v [DEMO.md](DEMO.md).

**Legenda:** ✅ hotovo a ukazatelné v UI · 🟡 hotovo jen částečně nebo jen v API (Swagger) · ❌ chybí.
Všechny položky bez „BONUS“ jsou **povinné minimum**.

## Shrnutí

- **Povinné minimum je pokryté celé.** T-326 doplnil poslední mezery: *kontrolu souladu s guidelines při zápisu závěru* (B2) a ve strukturovaném záznamu *zvažované možnosti*, *soulad s guidelines (ano / ne + důvod odchylky)* a *odlišná stanoviska členů* (C).
- **Bonusy:** 9 hotových v UI, 8 částečně nebo jen v API (Swagger), chybí podobné případy a zpráva pro praktického lékaře. Hodnotí se kvalita, ne počet: v demu ukázat 2–3 nejsilnější (readiness, RECIST, AI zapisovatel nebo mCODE export).
- **Největší rizika pro finále:** nasazení (T-110, T-212 ⬜), slidy (T-402 ⬜), záložní video (T-403 ⬜) a tlačítka pro AI zapisovatele a shrnutí pro pacienta (bez nich jde ukázat jen přes Swagger).

## 1. Tři fáze MDT

| Fáze | Stav | Kde |
|---|---|---|
| Před: nominace s otázkou, kontrola úplnosti (histologie, staging, biomarkery, PROMs), program zasedání | ✅ | Zařazení pacienta (T-211, T-502): otázku nelze přeskočit, varování CHYBÍ / MIMO NORMU / ROZPOR / NEJISTOTA AI; kalendář zasedání s agendou (T-519); boardy zakládá a mění předseda (T-501) |
| Během: orientace, pohledy odborností, možnosti vs. guidelines, studie a preference pacienta, zápis rozhodnutí se zdůvodněním | ✅ | Jednání komise `/dashboard/mdt/[id]` (T-520), okno pro projektor (T-512, T-326), detail pacienta (T-521), závěr `/record` (T-208, T-326) |
| Po: komunikace závěru, úkoly s odpovědností a termínem, kontrola realizace, re-evaluace | ✅ / 🟡 | Úkoly po zasedání (T-511), plánované re-MDT v závěru, export PDF + FHIR (T-210). Shrnutí pro pacienta jen v API a v PDF (T-306) |

## 2. Výstupní report

### A. Společný úvod (30 s)

| Požadavek | Stav | Kde |
|---|---|---|
| Identifikace bez jména a RČ, diagnóza, aktuální stav | ✅ | `CaseHeader` / `QuickIdentity`: `P03 · muž · 67 let`, MKN-10 + TNM (D-018) |
| ECOG lékaře i pacienta, výrazný rozdíl = red flag | ✅ | velká čísla PS + „pac. 1“, `RF-ECOG` (OBC-1.3) |
| Hlavní důvod zařazení, otázka pro MDT od navrhujícího lékaře, bez domýšlení; chybí → neúplný případ | ✅ | `QuestionStrip`, zařazení bez otázky nejde (OBC-1.1) |
| Časová osa onemocnění | ✅ | `Timeline` v detailu pacienta (T-103, T-106) |
| BONUS Case Readiness: semafor úplnosti podle šablony, doporučení vrátit / přesunout | ✅ | `ReadinessBadge` (T-303), šablony podle diagnózy (T-317, T-318), stav „vrácen k doplnění“ |

### B. Sekce podle odborností (≥ 3 role)

| Požadavek | Stav | Kde |
|---|---|---|
| Chirurg, onkolog, radiolog, patolog, pacient (PROMs, preference, trend) | ✅ | `RoleSection` (T-201, T-205), „pro mě nahoře“ podle odbornosti (T-319) |
| BONUS RECIST 1.1 předvýpočet, označený jako orientační | ✅ | `rules/recist.py` (T-304): P03 83 → 50 mm = PR |
| BONUS návrh chybějících biomarkerů | ✅ | `RF-MISSING` (KRC-1.1, PLI-1.3, PRS-1.3) |
| BONUS další role (nukleární medicína, paliativní péče, geriatrie, genetika, koordinátor) | 🟡 | jako pravidla a podpůrná péče v B2 (`RF-PALIATIVE`, `RF-GERI`, `RF-GENETIC`, `RF-WEIGHT`), ne jako samostatné sekce |

### B2. Decision Support Panel (povinné)

| Požadavek | Stav | Kde |
|---|---|---|
| Možnosti léčby z dodaných guidelines s odkazem na pasáž (RAG, ne znalosti modelu) | ✅ | `TreatmentOptions` + semafor (T-204, T-503): všechny postupy i červené, citace `KRC-2.4`; na projektoru bublina „proč“ po najetí na barvu (T-326) |
| Screening studií: vhodný / nevhodný / chybí údaj s důvodem u každého kritéria | ✅ | `TrialScreening` (`RKT-03/V3`) |
| 2–3 klíčové otázky k diskusi | ✅ | blok otázek v B2 (T-204) |
| **Kontrola souladu s guidelines při zápisu závěru**: odchylka → upozornění a krátké zdůvodnění, bez blokace | ✅ | **T-326:** `/record` → „Zvažované možnosti a soulad s doporučenými postupy“. Zvolený postup s „pozor“ / „vylučuje“ nebo „Ne, odchylka“ vyžádá zdůvodnění; bez něj nejde závěr potvrdit (backend `guideline_deviation`, 400) |
| BONUS podobné případy | ❌ | nápad: vektorové hledání nad `Composition` předchozích MDT (IRIS Vector Search už máme) |

### C. Zápis a závěr (MDT Resolution & Action Plan)

| Požadavek | Stav | Kde |
|---|---|---|
| Zapsat a upravit rozhodnutí během zasedání nebo na konci | ✅ | `/record` (T-208), z jednání klávesa Z |
| Doporučení dalšího postupu včetně termínu re-evaluace | ✅ | „Doporučený postup“ po modalitách + „Plánované re-MDT“ |
| Strukturovaný záznam: přítomní (kvórum), **zvažované možnosti**, zvolený postup, zdůvodnění, **soulad s guidelines (ano / ne + důvod)**, **odlišná stanoviska**, zařazení do studie | ✅ | T-326 doplnil tučné položky; vše jde do `Composition` v IRIS i do PDF |
| Export PDF / HL7 FHIR | ✅ | po potvrzení: Export PDF, FHIR document Bundle (T-210) |
| BONUS mapování na FHIR R4 / mCODE (Condition, Observation, QuestionnaireResponse, CarePlan + Task, Provenance) | ✅ | T-307, T-209 |
| BONUS AI zapisovatel (návrh odlišený od potvrzeného textu) | 🟡 | backend hotový (T-305, T-314), **v UI chybí tlačítko**, v demu přes Swagger (DEMO.md) |
| BONUS akční plán s úkoly a sledováním realizace | ✅ | úkoly v závěru → `Task` v IRIS, přehled `/dashboard/tasks` (T-511) |
| BONUS shrnutí pro pacienta a pro praktického lékaře | 🟡 | pacient: API + PDF (T-306), **bez tlačítka v UI**; zpráva pro praktického lékaře ❌ |
| BONUS uzamčení a verzování | 🟡 | potvrzený závěr je zamčený (409), `Provenance` s autorem; nové verze po potvrzení ❌ |

## 3. Klíčové požadavky na funkcionalitu

| Požadavek | Stav | Kde |
|---|---|---|
| Konfigurace: sekce a pořadí, přítomné odbornosti, míra detailu | ✅ | konfigurátor `/setup` (T-206, T-207), `detail_level` |
| BONUS šablony podle typu nádoru / komise s povinnými prvky | ✅ | T-317, T-318 |
| BONUS pravidla red flags (aktivace, prahy) a výběr dokumentů guidelines | 🟡 | prahy jsou v kódu s citací pasáže; sada guidelines se volí podle diagnózy automaticky (T-105). Zapínání pravidel v UI ❌ |
| BONUS výchozí pohled pro roli | ✅ | „Pro mě“ (T-319) |
| Syntéza zpráv a dotazníku | ✅ | `context_builder` (T-105), PROMs v hlavičce a v sekci pacienta |
| Red flags se závažností a citací obou zdrojů | ✅ | T-202, T-312, „Porovnat zdroje“ |
| BONUS rozšířené red flags (rozpor TNM, zastaralé podklady, symptom bez vyšetření, rostoucí marker, lékové interakce, horšící se PROMs) | ✅ | `RF-STALE`, `RF-NEWSYMPTOM`, `RF-LAB`, interakce v `red_flags.py`, `RF-PROMS` |
| Klik na tvrzení → přesný zdroj; chybějící údaj výslovně | ✅ | `SourceDrawer` (T-104), „Údaj chybí v podkladech“ (T-108, T-213) |
| BONUS citace na úrovni věty se zvýrazněním, datem a autorem; míra jistoty u odvozených údajů | 🟡 | odstavce `P03-img03#2` se zvýrazněním, odvozené údaje se vzorcem (`derived`); jistota jako číslo ❌ |
| Zodpovědná AI: nic bez potvrzení lékařem, AI obsah označený | ✅ | fialový styl a „AI návrh“ (D-017), potvrzení předsedou → IRIS |
| BONUS strukturovaná extrakce (NLP) s potvrzením jedním klikem | 🟡 | vložení zprávy → návrh hodnot → potvrzení (T-510), **jen v API** |
| BONUS konverzační asistent (Q&A) | 🟡 | MCP server nad IRIS (T-308) pro externí klienty; v aplikaci ❌ |
| BONUS audit, ochrana údajů, AI Act / MDR, evaluace | ✅ | `LlmCallLog` + `Provenance`, pseudonymizace (NFR-3), [EVAL.md](EVAL.md) (T-301) |

**Nad rámec zadání (požadavky lékaře):** okno pro projektor s mřížkou klíčových údajů (zkratka + hodnota, důvod v bublině), semafor s bublinou „proč“, spolupráce na případu (upravuje jen zadávající nebo přizvaný lékař a předseda), anamnéza, zkratky a NEJISTOTA AI, Lung-RADS / Fleischner.

## 4. Hodnoticí kritéria → co v demu zdůraznit

| Kritérium | Váha | Ukázat |
|---|---|---|
| Klinická hodnota & UX | 30 % | 30 s orientace v okně pro projektor: hlavička, mřížka klíčových údajů, semafor s bublinou; jednání komise s agendou |
| Konfigurovatelnost | 20 % | `/setup`: sekce, pořadí, přítomné role, míra detailu, šablona podle diagnózy; upozornění na chybějící roli (`RF-ROLES`) |
| AI & spolehlivost | 20 % | klik na citaci, „údaj chybí“, NEJISTOTA AI, čísla z EVAL.md |
| Data & standardy | 15 % | rozpor ECOG lékař vs. pacient, export FHIR document Bundle s mCODE, zápis do IRIS (`Composition` + `Provenance`) |
| MDT proces & zodpovědná AI | 15 % | B2 se semaforem a studiemi, **kontrola souladu s guidelines při zápisu závěru**, odlišná stanoviska, potvrzení předsedou |
| Bonusy | +10 % | readiness, RECIST, AI zapisovatel, mCODE |

## 5. Co ještě udělat (podle priority)

1. **Nasazení a smoke test** (T-110, T-212) a **záložní video** (T-403): bez nich je demo závislé na jednom notebooku.
2. **Slidy** (T-402) s architekturou AI: Gemini, RAG nad IRIS FHIR + Vector Search s filtrem na pacienta, grounding validátor, pseudonymizace, AI Act / MDR.
3. **DEMO.md krok 6**: po zápisu zvolit resekci (🟠) → ukázat kontrolu souladu s guidelines a doplnit zdůvodnění, pak potvrdit. Je to povinná část B2 a v demu ji porota hledá.
4. **Tlačítka v `/record`**: AI zapisovatel (nahrát `data/audio/P03_mdt02.m4a`) a po potvrzení „Shrnutí pro pacienta“. Backend i joby jsou hotové.
5. Volitelně: podobné případy, Q&A nad případem, zpráva pro praktického lékaře, verzování po potvrzení.

## Poznámky pro tým

- **Oprávnění (T-326, ⚠️ KONTRAKT):** případ, závěr, generování podkladu, shrnutí pro pacienta a zapisovatele smí měnit jen předseda, zadávající lékař nebo přizvaný (`MdtCase.collaborators`). Přizvat smí předseda nebo zadávající lékař: tlačítko „Spolupráce“ v jednání a v menu pacienta v kalendáři.
- **Dev v Dockeru na Windows:** frontend kontejner nevidí změny souborů spolehlivě. Po změně kódu `docker compose -f docker-compose.dev.yml restart frontend` (a `backend`, když se mění `urls.py` nebo views).
