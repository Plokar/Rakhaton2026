# Požadavky lékaře pro MDT Copilot — poznámky a pokyny pro AI agenty

> **Stav: zapracováno do ARCHITEKTURA.md a PROGRESS.md** (Pá 16. 10. 2026 večer). Vychází z požadavků budoucího uživatele (lékaře), které předal tým, z revize datasetu v1.1 a z porovnání se zadáním ([Soulad se zadáním](#soulad-se-zadáním)). V kódu zatím nic není.
>
> - Požadavky (FR-…), rozhodnutí (D-014 až D-020) a kontrakty jsou v [ARCHITEKTURA.md](../ARCHITEKTURA.md), ta má při rozporu přednost. Tento dokument drží detail: obrazovky, katalog pravidel semaforu, škály a zkratky.
> - Data: [DATASET.md](../DATASET.md) · úkoly: [PROGRESS.md](../PROGRESS.md) · pravidla: [AGENTS.md](../AGENTS.md)
>
> **Značky:**
>
> - ✅ máme v datech · 🟨 částečně · ❌ chybí;
> - ⚠ = práh, ke kterému nemáme primární zdroj (jen sekundární souhrn nebo praxi z datasetu). **Tým tyto prahy potvrdil 16. 10. 2026** ([Q-7](#12-otevřené-otázky)). Platí tedy i červená tam, kde ji tabulka uvádí. Klinicky je zatím neověřil lékař.
> - Citace ve tvaru `P03-img03`, `KRC-2.4`, `RKT-03/V3` jsou ID z datasetu. Externí zdroje jsou v [§13](#13-zdroje).

---

## 0. Shrnutí v 10 bodech

1. **Tři role podle oprávnění:** předseda (administrátor MDT), zadávající lékař a prohlížející. Odbornost (chirurg, onkolog…) je zvláštní vlastnost uživatele.
2. **Board = jedno zasedání MDT.** Předseda ho zakládá a mění termín. Pacient se do boardu zařazuje formulářem předvyplněným z IRIS.
3. **Všechno je FHIR.** Dnes jdou data z datasetu nahraného v IRIS. V budoucnu každý vstup nejdřív projde překladačem do FHIR a validací, teprve pak s ním pracuje AI (BON-7).
4. **Chybějící údaj** lékař doplní ručně, nebo klikne na **Přeskočit**. Přeskočený údaj nevyvolá varování, ale v podkladu zůstane jako „Chybí (přeskočeno lékařem)“.
5. **Varování při zadání:** chybí / mimo normu / rozpor / AI si není jistá. Lékař je může odkliknout, ale varovné signály v podkladu pro komisi zůstanou.
6. **Hlavička:** `P03 · muž · 67 let` (místo rodného čísla), diagnóza + TNM, hlavní otázka, velké ECOG lékaře a vedle něj ECOG pacienta, velké písmeno **C** (kurativní) nebo **P** (paliativní).
7. **Checkbox „Snímek mladší než 3 měsíce“:** připomínka pro lékaře, pro každé zasedání zvlášť. Automatická kontrola stagingu zůstává na 6 týdnech (OBC-1.2).
8. **Úzké rozložení:** jeden sloupec, bloky pod sebou. Sekce odborností (min. 3 role) mají štítek a barvu odbornosti. Výchozí obsah a pořadí nastavuje předseda, ostatní si bloky jen sbalí.
9. **Postupy léčby mají semafor souladu se stavem pacienta**, ne doporučení AI: 🟢 nevylučuje · 🟠 pozor · 🔴 vylučuje · ⚪ nelze posoudit. Barvu počítají deterministická pravidla s citací, nikdy LLM. Vždy se zobrazí všechny možnosti.
10. **Podklad pokrývá celé zadání:** souhrn s časovou osou (A), sekce odborností (B), možnosti léčby, studie a otázky k diskusi (B2), závěr a akční plán (C) a úkoly po zasedání. AI nic nedomýšlí: co nemá zdroj, je „chybí“ nebo „neznámé“ a vyvolá varování.

### Soulad se zadáním

Porovnáno s prezentací zadání (13 slidů s poznámkami řečníka). Číslo v závorce je číslo slidu.

| Zadání | Jak ho návrh plní |
|---|---|
| A: diagnóza a hlavní otázka, orientace do 30 s (5) | hlavička nahoře: diagnóza, TNM, otázka; souhrn hned pod ní |
| A: ECOG podle lékaře i pacienta, rozdíl je varovný signál (5) | velké ECOG lékaře + ECOG pacienta vedle, rozdíl ≥ 1 oranžově (OBC-1.3) |
| A: časová osa nemoci a léčby (5) | blok 1 (souhrn a časová osa) |
| B: každý vidí, co potřebuje, min. 3 role (5) | pojmenované sekce odborností s obsahem podle zadání (chirurg: lze operovat, TNM; onkolog: biomarkery, léky, nežádoucí účinky; radiolog; patolog; pacient) |
| B2: AI předkládá, nevybírá; možnosti z guidelines s citací (5) | vždy všechny možnosti z dodaných guidelines; semafor = soulad se stavem, počítají ho pravidla |
| B2: vhodnost pro klinické studie, 2–3 otázky k diskusi (5) | blok 7 (možnosti, studie, otázky) |
| C: rozhodnutí, úkoly, termíny, kontrola, export PDF / FHIR (5) | blok 9 (závěr a akční plán) + úkoly po zasedání (FR-P3) |
| nastavitelnost: předseda nakliká sekce, pořadí, přítomné, podrobnost (6) | předseda = administrátor nastavuje podklad pro zasedání |
| red flags se závažností a citací obou zdrojů (6) | zůstávají v podkladu i po odkliknutí (D-019) |
| dohledatelnost: klik na zdroj, chybějící údaj AI řekne (6) | citace u každého tvrzení; přeskočený údaj = „Chybí (přeskočeno lékařem)“ |
| člověk rozhoduje, text AI je odlišený (4, 6) | lékař potvrzuje data od AI i závěr; obsah od AI má fialový okraj a štítek „AI návrh“ |
| grounding: AI pracuje jen s daty pacienta a dodanými dokumenty (6) | externí zdroje jen u pravidel semaforu, označené `EXT-…`; demo stojí na dodaných guidelines (D-016) |
| 3 fáze procesu (3) | před: zařazení s kontrolou úplnosti · během: podklad a zápis · po: úkoly a re-MDT |
| ochrana údajů, pseudonymizace (9) | bez jména a RČ; v pitchi: AI Studio jen pro prototyp na fiktivních datech, produkce přes Vertex AI v EU |

---

## 1. Role a oprávnění

| Role | Kdo | Smí | Nesmí |
|---|---|---|---|
| **Administrátor MDT** | předseda komise (D-014) | zakládá boardy (datum, čas, komise), mění termíny, **nastavuje podklad pro zasedání** (sekce, pořadí, přítomné role, podrobnost; FR-R1), přesouvá pacienty, potvrzuje závěr (FR-C3) | měnit klinická data pacienta |
| **Zadávající lékař** | ošetřující lékař, který pacienta nominuje | zařadí pacienta do boardu ([§2.2](#22-formulář-zařadit-pacienta-do-boardu)), doplní nebo přeskočí údaje, odklikne varování, zadá ECOG a záměr C/P, zaškrtne připomínku snímku, **přesouvá své pacienty mezi boardy** | měnit cizí případy, potvrzovat závěr |
| **Prohlížející** | členové komise | číst podklad, bloky si u sebe sbalit nebo přeskládat (lokálně) | měnit data a výchozí nastavení podkladu |

**Implementace** (ARCH §6.2):

- Django `Group`: `mdt_admin`, `mdt_doctor`, `mdt_viewer`.
- K uživateli `specialty`: chirurg, klinický onkolog, radiolog, patolog, radiační onkolog, pneumolog, kardiolog…
- Demo účty z ARCH §6.2 zachovat a jen jim přiřadit skupinu.

---

## 2. Data a zadání pacienta

### 2.1 Všechno ve FHIR

```
Vstup        dnes: dataset v1.1 · budoucnost: PDF, vložený text, HL7v2, CDA…
   │
   ▼
Překladač do FHIR
   ├─ dataset: sanitizace podle DATASET §6.2 + collection → transaction
   ├─ PDF / text: Gemini extrahuje FHIR resources, každý s odkazem na zdrojový DocumentReference
   └─ HL7v2: IRIS Interoperability (DTL), ARCH §4.1
   │
   ▼
Validace („syntax“)   FHIR R4 (IRIS $validate / pydantic), ID, prázdné hodnoty, jednotky UCUM, data v časové ose
   │
   ▼
Potvrzení lékařem     jen u údajů extrahovaných AI nebo zadaných ručně
   │
   ▼
IRIS for Health (FHIR R4) = jediný zdroj pravdy
   │
   ▼
Pravidla (services/rules) + AI čtou jen z IRIS
```

- **Dnes (demo):** 6 pacientů z datasetu v IRIS (T-101). Nové pacienty z PDF nebo textu řešíme později ([T-510](#11-úkoly)).
- **Ručně zadaný údaj** se taky ukládá jako FHIR (např. `Observation` ECOG, kde `performer` = lékař) a dostane `Provenance`: kdo, kdy, zda ručně nebo z extrakce AI.

### 2.2 Formulář „Zařadit pacienta do boardu“

1. **Výběr** boardu a pacienta (z IRIS).
2. **Předvyplnění z IRIS:** každý údaj z [§4](#4-povinné-a-důležité-údaje-podle-diagnózy) s citací zdroje.
3. **Co chybí:** pole s tlačítky **Doplnit** a **Přeskočit**. Přeskočené pole:
   - se dál nehlídá a nevyvolá varování;
   - v podkladu pro komisi zůstane jako **„Chybí (přeskočeno lékařem)“** (zadání: když údaj chybí, AI to řekne);
   - pravidla, která na něm závisí, ukážou „neposuzováno (přeskočeno)“;
   - AI ho **nesmí** doplnit odhadem;
   - **otázku pro MDT přeskočit nelze** (OBC-1.1: bez otázky je případ neúplný). Neúplný případ může předseda vrátit k doplnění.
4. **Lékař zadá nebo potvrdí:**
   - ECOG;
   - záměr C/P;
   - otázku pro MDT;
   - úplnost seznamu komorbidit (potřebuje pravidlo „nezaznamenáno“ v [§5.1](#51-význam-barev-a-vyhodnocení)).
5. **Varování** ([§2.3](#23-typy-varování-při-zadání)): každé jde odkliknout („Beru na vědomí“) a pokračovat.
6. **Připomínka:** checkbox **„Snímek mladší než 3 měsíce“**. Jen připomíná, nic neblokuje. Platí pro jeden případ na jednom zasedání. Automatická kontrola stagingu ≤ 6 týdnů (OBC-1.2, VS-OBC-09) běží dál nezávisle na checkboxu. Nápověda u checkboxu: „pro radikální léčbu a změnu linie musí být staging ≤ 6 týdnů (OBC-1.2), před resekcí jater ≤ 4–6 týdnů (KRC-2.4)“.
7. **Uložit** do FHIR: `ServiceRequest` + `Task` podle FR-P1, ruční údaje + `Provenance`.

**Přesun mezi boardy:** změní se `MdtCase.session` a `Task.restriction.period.start` (datum zasedání).

### 2.3 Typy varování při zadání

| Typ | Kdy | Příklad z datasetu |
|---|---|---|
| **CHYBÍ** | povinný údaj z §4 nemá hodnotu, nebo má hodnotu „nevyšetřeno / probíhá“ | MMR/MSI nevyšetřeno `P03-bm04` (KRC-1.1) |
| **MIMO NORMU / ZVLÁŠTNÍ** („přečnívá“) | hodnota mimo `referenceRange` (`interpretation` H/L), nebo hodnota nepravděpodobná či neobvyklá: skok, nesedí jednotka, datum mimo časovou osu | Na 129 mmol/l `P04-lab05-na` (norma 136–145), glykémie 11,8 mmol/l `P02-lab06-glu` |
| **ROZPOR** | dva zdroje si odporují (pravidla RF-* z ARCH §5.4) | „hmotnost stabilní“ `P04-doc05` vs. 78 → 71 kg (`P04-vaha01` → `P04-vaha03`) |
| **NEJISTOTA AI** | AI si není jistá výkladem: nejednoznačná zkratka ([§7](#7-zkratky)), rozmezí, nečitelný údaj | „ECOG 0–1“ v `P03-doc06`, strukturovaně uloženo jako 1 (`P03-ecog02`) |

- **Požadavek lékaře:** kdykoli si AI není jistá, vyhodí varování.
- **Odkliknuté varování** ([Q-4](#12-otevřené-otázky)):
  - stačí kliknout na „Beru na vědomí“, důvod se nepíše;
  - samotný problém (např. chybí MMR) v podkladu pro komisi **zůstane** jako varovný signál nebo chybějící údaj, protože je důležitý pro rozhodnutí;
  - komise nevidí, kdo a kdy varování odklikl. Systém si to jen zapíše do auditu (NFR-4).

---

## 3. Obrazovka podkladu (úzké rozložení)

### 3.1 Požadavky

- Aplikace běží v **úzkém okně prohlížeče** na kraji plochy. Vedle běží jiné programy lékaře (PACS, nemocniční systém).
- Cíl: použitelné od šířky **360 px** (číslo doladit, [Q-10](#12-otevřené-otázky)). Jeden sloupec, žádné vodorovné posouvání.
- **Bloky pod sebou.** Výchozí obsah a pořadí nastavuje předseda pro zasedání (FR-R1). Každý si bloky může u sebe sbalit nebo přeskládat.
- **Všichni se dívají na jeden projektor.** Údaje pro stejnou odbornost jsou proto v pojmenované sekci odbornosti se štítkem a barvou, aby je lékař našel na první pohled.

### 3.2 Výchozí pořadí bloků

Pořadí od lékaře je zachované a doplněné o to, co chce zadání. Souhrn je nahoře kvůli orientaci do 30 s.

| # | Blok | Obsah | Zdroj ve FHIR | Zadání |
|---|---|---|---|---|
| 0 | **Hlavička** (stále nahoře) | `P03 · muž · 67 let` · diagnóza + TNM · hlavní otázka (zkráceně, celá v bloku 8) · velké **ECOG** lékaře a vedle ECOG pacienta (při rozdílu ≥ 1 oranžově) · velké **C/P** · počet varování · board a datum | `Patient`, `Condition`, `Observation` tnm a 89247-1, `QuestionnaireResponse` `samostatnost`, `ServiceRequest` | A |
| 1 | **Souhrn a časová osa** | 3–5 bodů s citacemi, časová osa nemoci a léčby | vše | A |
| 2 | **Varovné signály** | závažnost, oba zdroje, pasáž guidelines; i varování odkliknutá při zařazení | pravidla RF-* | pravidlo 2 |
| 3 | **Anamnéza** | krátký text doslovně, dlouhý jako shrnutí AI s citacemi; lékař může přepnout | `DocumentReference`, sekce OA, FA, RA, SA, GA, NO | lékař |
| 4 | **Sekce odborností** | Chirurg, Onkolog, Radiolog, Patolog (+ Pneumolog, Kardiolog, Radiační onkolog podle diagnózy a přítomných); v každé údaje podle diagnózy ([§4](#4-povinné-a-důležité-údaje-podle-diagnózy)), posouzení role a barva odbornosti | `Observation`, `DiagnosticReport`, `Procedure` | B (min. 3 role) |
| 5 | **Hlas pacienta** | dotazník: 2 vyplnění, trend, volné texty (nové obtíže, postoj, léky navíc) | `QuestionnaireResponse` | B (pohled pacienta) |
| 6 | **Léčebné metody a odborníci** | metody pro danou diagnózu; u každé odborník, který se musí vyjádřit, a data, která má mít u sebe | [§5.2](#52-katalog-léčebných-metod-a-odborníků) | lékař |
| 7 | **Možnosti léčby, studie, otázky** | všechny možnosti z guidelines s citací a semaforem ([§5](#5-soulad-léčebného-postupu-se-stavem-pacienta-semafor)), screening studií RKT, 2–3 otázky k diskusi | pravidla §5.3, `ResearchStudy` | B2 |
| 8 | **Otázka pro MDT** (velká) | celé znění | `ServiceRequest.reasonCode.text` | A |
| 9 | **Závěr a akční plán** (po zasedání) | rozhodnutí se zdůvodněním, úkoly a termíny, potvrzení lékařem, export PDF / FHIR | `Composition`, `CarePlan`, `Task` | C |

### 3.3 Hlavička

- **Místo rodného čísla** se zobrazí `P03 · muž · 67 let`. Dataset RČ nemá a RČ nesmí do LLM (ARCH §5.7).
- **ECOG:** velká číslice. Zadává ji nebo potvrzuje lékař, předvyplní se z posledního `Observation` 89247-1.
- **ECOG pacienta** (PROMs `samostatnost`) je vždy vedle, menší. Rozdíl ≥ 1 je oranžově a je to varovný signál (zadání, OBC-1.3).
- **Diagnóza + TNM a hlavní otázka** jsou v hlavičce kvůli orientaci do 30 s. Celá otázka je ještě velkým písmem v bloku 8.
- **Písmeno záměru:** velké, vedle ECOG. Jen dvě možnosti: **C** = kurativní, **P** = paliativní.
  - Předvyplní se z poslední MDT (`CarePlan.category`): P01 P, P02 P, P03 C, P05 P, P06 P. Lékař ho potvrdí nebo změní.
  - U P04 minulá MDT rozhodnutí odložila (`odlozeno` = „doplnit diagnostiku“). V takovém případě se nic nepředvyplní a lékař vybere C, nebo P sám ([Q-2](#12-otevřené-otázky)).
  - Konečný záměr rozhoduje MDT (`Decision.sections.intent`). Po potvrzení závěru se písmeno přepíše. Když MDT rozhodnutí znovu odloží, zůstane písmeno od lékaře.

### 3.4 Tři systémy barev (nesmí se plést)

| Systém | Význam | Návrh |
|---|---|---|
| **Semafor** | soulad postupu se stavem pacienta | zelená / oranžová / červená / šedá, vždy s ikonou a textem (✓ ! ✕ ?) |
| **Odbornost** | komu údaj patří | barevný štítek s textem (Chirurg, Onkolog…). Odstíny mimo zelenou, oranžovou, červenou a mimo fialovou AI. |
| **AI vs. člověk** | odlišení obsahu od AI (zlaté pravidlo) | fialový levý okraj + štítek „AI návrh“ (ARCH §7.2) |

Barva nikdy nenese informaci sama: na projektoru se barvy zkreslují a část lidí barvy nerozliší. Vždy je u ní i text nebo ikona.

---

## 4. Povinné a důležité údaje podle diagnózy

Toto je seznam „důležitých informací“, který měl tým dohledat. Základ tvoří OBC-1.1, k němu pasáže guidelines podle diagnózy a vstupy pravidel z §5. Sloupec *Dataset* ukazuje, kde údaj u našich pacientů chybí.

### 4.1 Vždy (všechny diagnózy)

| Údaj | Kde ve FHIR | Zdroj | Dataset |
|---|---|---|---|
| Otázka pro MDT (**nelze přeskočit**) | `ServiceRequest.reasonCode.text` | OBC-1.1 | ✅ |
| Všechny nádory v nominaci (při duplicitě malignit) | `ServiceRequest.reasonReference` | OBC-1.4 | ✅ (P06 uvádí všechny tři diagnózy) |
| Zapojení paliativní péče (pokročilé onemocnění se symptomem ≥ 7/10, zhoršením ECOG nebo progresí) | `DocumentReference`, `Procedure` | OBC-2.1 | ❌ u žádného pacienta zmíněna není |
| Plán snižování kortikoidů | `MedicationRequest`, text zpráv | OBC-3.1 | ❌ P02 dexametazon bez plánu |
| Histologie + grade | `Condition` (ICD-O-3), `DiagnosticReport` SP | OBC-1.1 | ✅ |
| Aktuální staging TNM, zobrazení ≤ 6 týdnů k datu MDT | `Observation` tnm, `DiagnosticReport` RAD | OBC-1.1, OBC-1.2 | 🟨 P01 (`P01-img06`, 50 dní), P05 (`P05-img04`, 83 dní) |
| Prediktivní biomarkery podle diagnózy | `Observation` bm | OBC-1.1 | viz 4.2–4.4 |
| ECOG lékař + pacient | `Observation` 89247-1, PROMs `samostatnost` | OBC-1.3 | ✅ |
| Komorbidity | `Condition` „komorbidita“ | OBC-1.1 | ✅ |
| Dosavadní léčba | `MedicationAdministration`, `Procedure` | OBC-1.1 | ✅ |
| Preference pacienta | `ServiceRequest.note`, PROMs `priorita` a `postoj` | OBC-1.1 | ✅ |
| Léčebný záměr C/P | `CarePlan.category` / nový údaj (§10) | požadavek lékaře | 🟨 jen z předchozí MDT |
| Alergie | PROMs `alergie`, text „Alergie:“ | ARCH FR-A4 | ✅ (P06 otoky po doplňcích) |
| Medikace + léky a byliny navíc | `MedicationRequest`, PROMs `leky-mimo` | ARCH RF-MED | 🟨 P01 paracetamol, P03 hořčík a vitamin B, P05 třezalka a železo chybí v medikaci |
| Hmotnost a trend za 6 měsíců, albumin | `Observation` vaha, lab alb | OBC-2.3 | ✅ |
| G8 u věku ≥ 70 | nový údaj | OBC-2.2 | ❌ P04 (70), P06 (76) |
| Krevní obraz, kreatinin (z něj CrCl), bilirubin, ALT/AST | `Observation` lab | vstupy §5 | ✅ |
| Předchozí výkony, implantáty, radioterapie | `Procedure` | ARCH FR-A4 | ✅ |
| Snímek mladší než 3 měsíce (checkbox, připomínka) | `MdtCase` (Postgres) | požadavek lékaře; automatická kontrola stagingu ≤ 6 týdnů běží dál (OBC-1.2) | — |

### 4.2 Karcinom plic (C34): PLI

- PET-CT, MR mozku, CT hrudníku a horního břicha. Při suspektních uzlinách invazivní staging mediastina (EBUS-TBNA). PLI-1.1
- Ověření ložiska, které by změnilo stadium. PLI-1.2. U P04 jde o ložisko levé nadledviny (`P04-img03`).
- EGFR a ALK vždy před perioperační imunoterapií, dále ROS1 a PD-L1 TPS. Při nedostatku tkáně rebiopsie (EBUS) nebo tekutá biopsie. PLI-1.3. U P04 EGFR probíhá (`P04-bm05`).
- FEV1, DLCO, ppoFEV1, ppoDLCO. Při hodnotě < 60 % zátěžový test (VO2max). PLI-3.1. U P04 spiroergometrie neproběhla (`P04-doc06`).
- Dušnost (PROMs) a výkonnost (chůze). PLI-3.1
- Sodík: při nové nebo progredující hyponatrémii osmolalita séra a moči a natriurie k vyloučení SIADH, úprava před léčbou. PLI-3.2. U P04 tato vyšetření v datech nejsou.
- Kouření, balíčkoroky; odvykání před operací i radioterapií. PLI-3.3
- Složení MDT u st. III: hrudní chirurg, radiační onkolog, klinický onkolog, pneumolog, radiolog. PLI-2.1 (`RF-ROLES`)

### 4.3 Karcinom prsu (C50): PRS

- ER, PR, HER2 (IHC 0/1+/2+/3+, ISH) a Ki-67 z primárního nádoru i z metastázy. PRS-1.1, PRS-1.2
- Při progresi HR+/HER2−: ESR1 (ctDNA), PIK3CA/AKT1/PTEN, gBRCA (PRS-1.3). Výsledky NGS projde molekulární komise (PRS-1.4).
- LVEF každé 3 měsíce u anti-HER2 léčby. PRS-3.4
- Známky viscerální krize: bilirubin, rychle se zhoršující dušnost. PRS-2.4
- Mozkové metastázy: počet, symptomy, kortikoidy a jejich dávka. PRS-3.3, OBC-3.1, RKT-02/Z3
- Kostní metastázy: kalcium, stomatologické vyšetření (PRS-4.1). Nová lokalizovaná bolest (PRS-4.2).
- Menopauzální stav. PRS-2.1
- QTc (EKG) před ribociklibem (VS-PRS-05). Glykémie nebo HbA1c před PI3K inhibitorem (VS-PRS-06).
- Kumulativní dávka antracyklinů: ⚪ práh doplní lékař.
- T-DXd u HER2-low až po vyčerpání endokrinních možností nebo po chemoterapii v metastatickém stadiu, před léčbou zhodnotit riziko ILD. PRS-2.3
- Výsledek NGS projde molekulární tumor board; jeho doporučení je podklad pro MDT, ne konečné rozhodnutí. PRS-1.4 (`RF-ROLES`)

### 4.4 Kolorektální karcinom (C18–C20): KRC

- RAS (KRAS a NRAS, exony 2–4), BRAF V600E, MMR/MSI. U RAS/BRAF wild-type navíc HER2. KRC-1.1. U P03 MMR nevyšetřeno.
- Restaging ne starší než 4–6 týdnů: CT hrudníku, břicha a pánve + MR jater s hepatospecifickou kontrastní látkou. KRC-2.4. U P03 chybí CT hrudníku.
- Počet a lokalizace jaterních ložisek, postižení obou laloků, vymizelá ložiska. KRC-2.4, KRC-2.5
- FLR (budoucí jaterní remnant) v % a zda pacient prošel intenzivní chemoterapií; cévní přítok, odtok a žlučová drenáž. KRC-2.1. U P03 ložisko S8 naléhá na pravou jaterní žílu (`P03-img04`).
- Složení MDT u otázky resekability: hepatobiliární chirurg a radiolog. KRC-2.1 (`RF-ROLES`)
- Počet cyklů konverzní chemoterapie: po dosažení resekability neprodlužovat. KRC-2.2
- Datum poslední dávky bevacizumabu. KRC-2.3
- Neuropatie podle lékaře i podle pacienta. KRC-3.2
- Trend CEA a CA 19-9.
- Krevní tlak a proteinurie při bevacizumabu. VS-KRC-08
- DPD před fluoropyrimidiny (EMA 2020). V datasetu není.
- Rodinná anamnéza (Lynchův syndrom). OBC-2.4, KRC-1.2

### 4.5 Karcinom prostaty (C61): rešerše, v datasetu není

> Rešerše T-512 (17. 10. 2026) jako podklad šablony. Pacient ani guidelines s C61 v datasetu nejsou, `intake.py` tato pole zatím nemá (T-513). Zdroj: kapesní doporučení EAU-EANM-ESTRO-ESUR-ISUP-SIOG 2025, ověřeno v plném textu. Průdušnost (spirometrie) se u prostaty nesleduje, patří jen k plicím (4.2).

- PSA a jeho kinetika (PSA-DT). U M0 s PSA-DT > 12 měsíců nenabízet ADT; high-risk biochemický relaps = PSA-DT ≤ 9 měsíců a PSA ≥ 2 ng/ml nad nadirem po RT nebo ≥ 1 ng/ml po RP.
- Histologie: Gleason skóre a globální ISUP grade group (1–5).
- cTNM (cT podle DRE), MR prostaty.
- Staging: u ISUP GG 3 a u high-risk / lokálně pokročilého onemocnění PSMA-PET/CT, jinak aspoň CT/MR břicha a pánve a scintigrafie skeletu.
- Testosteron: kastrační hladina < 50 ng/dl potvrzená před diagnózou CRPC.
- mCRPC: somatické a/nebo germinální testování (HRR, BRCA2) a MMR/MSI; mCRPC projednává MDT.
- Germinální testování: více příbuzných s CaP pod 60 let nebo úmrtí na CaP v rodině, vysoce rizikové mutace v rodině, BRCA ze somatického testu; před testem genetické poradenství.
- Zdravotní stav: očekávaná délka života, komorbidity, G8 (+ mini-COG, Clinical Frailty Scale); G8 ≤ 14 → specializované geriatrické vyšetření (shodně s OBC-2.2).

### 4.6 Nádor ledviny (C64, P06 D41.0): rešerše, guidelines v datasetu nejsou

> Rešerše T-512 (17. 10. 2026). Zdroj: souhrny EAU RCC 2025 (European Urology) a IMDC; ⚠ jen ze sekundárních souhrnů, plný text EAU se nepodařilo stáhnout (HTTP 403).

- Histologie z jádrové biopsie (ne FNA); cystické léze bez solidní složky nebiopsovat.
- Funkce ledvin: eGFR; při eGFR < 45 ml/min/1,73 m² nebo riziku zhoršení nefrolog před léčbou (nefrektomie mění funkci).
- Staging: TNM, histologický podtyp (světlobuněčný / nesvětlobuněčný), grade.
- Metastatické onemocnění: rizikové skupiny IMDC: interval od diagnózy do systémové léčby < 1 rok, Hb pod dolní mezí, korigované Ca nad horní mezí, neutrofily nad horní mezí, trombocyty nad horní mezí, Karnofsky < 80 % (Heng 2009). Podle skupiny se volí 1. linie; u poor-risk se nedoporučuje cytoredukční nefrektomie.

---

## 5. Soulad léčebného postupu se stavem pacienta (semafor)

Barvy **nejsou doporučení AI**. Říkají, jestli se postup nevylučuje se stavem pacienta. Příklad lékaře: pacientovi se špatnou spirometrií nelze odebrat plíci.

### 5.1 Význam barev a vyhodnocení

| Barva | Význam | Kdy |
|---|---|---|
| 🟢 **zelená** ✓ | stav postup nevylučuje | hodnota je ověřená z dat (citace) a je v pořádku |
| 🟠 **oranžová** ! | dávej pozor | hraniční hodnota, relativní kontraindikace, nutné další vyšetření nebo rozpor ve zdrojích |
| 🔴 **červená** ✕ | stav postup vylučuje | podle **zdroje** stav postup vylučuje, nebo je nad prahem vysokého rizika |
| ⚪ **šedá** ? | nelze posoudit | údaj chybí, nebo pro kontrolu zatím nemáme práh |
| — **neposuzováno** | lékař údaj přeskočil | bez varování |

**Pravidla vyhodnocení:**

1. Barvu počítá kód (`services/rules/`), **ne LLM**. LLM jen vytáhne hodnotu z textu s citací.
2. Každá barva má citaci faktu pacienta (Evidence ID) a citaci pravidla: pasáž guidelines, kritérium studie nebo externí zdroj.
3. **Červená jen tam, kde zdroj jasně říká** „vylučuje / nepodávat / vysoké riziko“, nebo kde ji potvrdil tým (⚠, Q-7).
4. **Celková barva postupu** = nejhorší z jeho pravidel: 🔴 > 🟠 > ⚪ > 🟢.
5. **„Není v dokumentaci“** se zobrazí zeleně jen tehdy, když lékař při zadání potvrdil, že seznam komorbidit je úplný. Jinak je šedá.
6. **Text u barvy je věcný**, např. „ppoDLCO 38 % < 60 % → zátěžový test (PLI-3.1)“. Nikdy „doporučujeme“. Blok se jmenuje „Soulad se stavem pacienta“.
7. **Odvozené hodnoty** (CrCl podle Cockcrofta-Gaulta, % úbytku hmotnosti, dny od bevacizumabu) zobrazit se vzorcem a citacemi vstupů.
8. **Preference pacienta není kontraindikace.** Např. „nechce chemoterapii, po které vypadají vlasy“ se zobrazí jako štítek 💬 u postupu a barvu nemění.
9. **Rozsah:**
   - pravidla pokrývají 3 typy nádorů z datasetu (plíce, prs, kolorektum), obecná pravidla a nádor ledviny u P06;
   - další nádory se přidají jako další řádky;
   - pravidla drž jako data (např. YAML se stejnými sloupci jako tabulky níže), ne natvrdo v kódu.
10. **Vždy se zobrazí všechny možnosti** z dodaných guidelines, i červené. Červená možnost se nikdy neskryje (zadání: AI předkládá, nevybírá).
11. **Externí zdroje** (`EXT-…`) jsou v UI označené „externí zdroj“. Demo stojí hlavně na pravidlech s citací z dodaných guidelines (D-016).

### 5.2 Katalog léčebných metod a odborníků

| Metoda (`mdt-modalita`) | Kdo se musí vyjádřit | Co musí mít u sebe | Zdroj |
|---|---|---|---|
| `chirurgie` | chirurg dané oblasti (hrudní, hepatobiliární, mamární, urolog) | resekabilita, TNM, FLR / ppoFEV1, předchozí operace, kardiální riziko, výživa, G8 | KRC-2.1, PLI-2.1, PLI-3.1 |
| `rt` | radiační onkolog | předchozí RT (oblast, dávka), plicní funkce, počet mozkových metastáz | PRS-3.3, PLI-2.1, ARCH FR-B6 |
| `chemoterapie`, `cilena`, `imunoterapie`, `hormonalni`, `jina-systemova` | klinický onkolog | biomarkery, linie léčby, toxicita (lékař vs. pacient), orgánové funkce, interakce | ARCH FR-B2 |
| `diagnostika` (biopsie, EBUS) | radiolog, pneumolog, patolog | ložisko, přístup, předchozí komplikace, potřebná imunohistochemie | OBC-1.4, PLI-1.2 |
| podklad pro všechny: zobrazení | radiolog | vývoj lézí, RECIST, aktuálnost | ARCH FR-B3 |
| podklad pro všechny: patologie | patolog | histologie, grade, IHC, diskordance | ARCH FR-B4 |
| podklad: kardiologie (anti-HER2) | kardiolog | trend LVEF | PRS-3.4 |
| podklad: plicní funkce | pneumolog | spirometrie, DLCO, zátěžový test | PLI-2.1, PLI-3.1 |
| podpůrná péče | paliativní tým, nutriční terapeut, geriatr, klinický genetik | symptomy (PROMs), trend ECOG, hmotnost a albumin, G8, rodinná anamnéza a biomarkery | OBC-2.1 až 2.4 |

### 5.3 Pravidla

Sloupce: **ID · postup · co se kontroluje · 🟢 · 🟠 · 🔴 · zdroj · výskyt v datasetu**. Mapování všech 42 pasáží guidelines na pravidla je v [ARCH §5.11](../ARCHITEKTURA.md#511-pokrytí-guidelines).

#### Obecná pravidla (všechny diagnózy)

| ID | Postup | Kontrola | 🟢 | 🟠 | 🔴 | Zdroj | Dataset |
|---|---|---|---|---|---|---|---|
| VS-OBC-01 | intenzivní léčba (velká operace, radikální CHRT, kombinovaná chemoterapie) | ECOG lékaře | 0–1 | 2 | ≥ 3 ⚠ | kritéria studií RKT-01–04, 06 (ECOG 0–1), OBC-1.3 | všichni |
| VS-OBC-02 | vše | rozdíl ECOG lékař vs. pacient | 0 | ≥ 1 | — | OBC-1.3 | P01, P02, P03, P04, P06 |
| VS-OBC-03 | intenzivní léčba, věk ≥ 70 | G8 | > 14 | ≤ 14 → komplexní geriatrické hodnocení | — | OBC-2.2; práh 14: MDCalc, Frontiers 2023 | P04, P06: G8 chybí → ⚪ + varování |
| VS-OBC-04 | velká operace | úbytek hmotnosti za 6 měsíců, albumin | < 5 % | ≥ 5 % nebo pokles albuminu | — | OBC-2.3 | P03 −7 %, P04 −9 %, P06 67 → 63 kg |
| VS-OBC-05 | kortikoidy u diabetika | glykémie | ≤ 10 mmol/l | > 10 mmol/l ⚠ (práh z ARCH RF-LAB) | — | OBC-3.1 | P02 11,8 |
| VS-OBC-06 | myelotoxická léčba | neutrofily / trombocyty / Hb | ≥ 1,5 / ≥ 100 / ≥ 90 | pod kterýmkoli ⚠ | — | prahy z kritéria RKT-06/Z4; pro běžnou léčbu potvrdí lékař | P05 |
| VS-OBC-07 | systémová léčba | bilirubin | ≤ 1,5× ULN | > 1,5× ULN (úprava léčby) | screening RKT-01: vyřazení | RKT-01/V3; u prsu i známka viscerální krize (PRS-2.4) | P01 v normě |
| VS-OBC-08 | léky závislé na ledvinách | CrCl (Cockcroft-Gault, odvozeno) | ≥ 60 ml/min | 30–59 ml/min | < 30 jen u léku se zdrojem (zoledronát, VS-PRS-12) | VS-PLI-11, VS-PRS-12 | P06 ≈ 40 ml/min (odvozeno z `P06-lab07-krea` 106 µmol/l, 63 kg, 76 let) |
| VS-OBC-09 | radikální léčba, změna linie | stáří stagingu k datu MDT | ≤ 42 dní | > 42 dní | — | OBC-1.2 | P01 50 dní, P05 83 dní |
| VS-OBC-10 | radikální léčba | nejasné ložisko měnící stadium, druhý nádor bez histologie | ověřeno | neověřeno → nutné ověřit | — | OBC-1.4, PLI-1.2 | P04 nadledvina, P06 plicní ložisko + ledvina |
| VS-OBC-11 | léky metabolizované přes CYP3A | byliny a léky mimo medikaci (třezalka, grapefruit) | nic | interakce → vyřešit | — | `P05-doc03` (klinický farmaceut), ARCH RF-MED | P05 třezalka |
| VS-OBC-12 | vše | alergie | neuvedena | uvedena → info | — | ARCH FR-A4 | P06 otoky po doplňcích |
| VS-OBC-13 | radioterapie, operace | předchozí výkon nebo RT v oblasti, implantáty | ne | ano → info pro chirurga / radiačního onkologa | — | ARCH RF-PRIOR-PROC | P01 a P05 RT hrudní stěny, P03 port + koronární stent |

#### Chirurgie obecně

| ID | Postup | Kontrola | 🟢 | 🟠 | 🔴 | Zdroj | Dataset |
|---|---|---|---|---|---|---|---|
| VS-CHIR-01 | velká operace | infarkt myokardu, koronární stent | IM > 60 dní a stent > 6 měsíců | lékový stent ≤ 6 měsíců ⚠ | IM ≤ 60 dní ⚠ | ACC/AHA a ESC 2022 (sekundární souhrny) | P03 IM i stent 2019 → 🟢, užívá ASA → info |
| VS-CHIR-02 | operace, radioterapie | kouření | nekouří | aktivní kuřák → odvykání (před operací ≥ 4 týdny) | — | PLI-3.3, `P04-doc06` | P04 |
| VS-CHIR-03 | operace | interval od poslední dávky bevacizumabu | ≥ 6 týdnů | — | < 6 týdnů | KRC-2.3 (přísnější než americký příbalový text, 28 dní) | P03: poslední dávka 2026-09-07 (`P03-tx-bev-08`) → operace nejdříve 2026-10-19 |
| VS-CHIR-04 | operace | výživa, G8, ECOG | viz VS-OBC-01, 03, 04 | | | | |

#### Plíce (C34)

| ID | Postup | Kontrola | 🟢 | 🟠 | 🔴 | Zdroj | Dataset |
|---|---|---|---|---|---|---|---|
| VS-PLI-01 | lobektomie, pneumonektomie | ppoFEV1 a ppoDLCO | obě ≥ 60 % | kterákoli 30–59 % → zátěžový test | kterákoli < 30 % (vysoké riziko) | PLI-3.1 | P04 49 % / 38 % → 🟠 |
| VS-PLI-02 | lobektomie | VO2max (spiroergometrie) | > 20 ml/kg/min | 10–20 | < 10 ⚠ (vysoké riziko) | ⚠ sekundární souhrn (Springer 2016); zdroje se liší, při příležitosti ověřit v ERS/ESTS 2025 | P04 neprovedeno → ⚪ |
| VS-PLI-03 | operace | dušnost (PROMs) a chůze | dušnost < 7, chůze bez omezení | dušnost ≥ 7 nebo patro jen se zastávkou | — | PLI-3.1, OBC-1.3 | P04 dušnost 7, `1-patro-zastavka` |
| VS-PLI-04 | radikální léčba | M-kategorie, ložisko měnící stadium | ověřeno | neověřeno | — | PLI-1.2 | P04 nadledvina 14 mm, SUVmax 4,1 |
| VS-PLI-05 | radikální léčba | MR mozku, invazivní staging mediastina | provedeno | chybí | — | PLI-1.1 | P04 hotovo → 🟢 |
| VS-PLI-06 | perioperační nebo konsolidační imunoterapie | EGFR a ALK | obě negativní | neznámé → doplnit | pozitivní (imunoterapie bez přínosu) | PLI-1.3, PLI-2.3, PLI-2.4, RKT-04/V1 | P04 EGFR probíhá → 🟠 |
| VS-PLI-07 | durvalumab po CHRT | PD-L1 TPS | ≥ 1 % | neznámé | < 1 % (v EU se nepodává) | PLI-2.4 | P04 60 % → 🟢 |
| VS-PLI-08 | imunoterapie | autoimunitní onemocnění se systémovou léčbou, transplantace | ne | ano ⚠ | — | RKT-04/V2 (studie); vyřazení z registračních studií a riziko vzplanutí (PMC 2018) | — |
| VS-PLI-09 | jakákoli léčba | sodík, progredující hyponatrémie | ≥ 136 mmol/l | < 136 a klesá → vyšetřit SIADH, upravit před léčbou | — | PLI-3.2 | P04 136 → 129 |
| VS-PLI-10 | chemoradioterapie | plicní funkce pro radikální RT | — | — | — | ⚪ práh v podkladech není, doplní radiační onkolog | P04 |
| VS-PLI-11 | cisplatina | CrCl, neuropatie, sluch, ECOG, srdeční selhání | CrCl ≥ 60 a nic dalšího | CrCl < 60, neuropatie ≥ G2, ztráta sluchu ≥ G2, ECOG 2 nebo NYHA III → zvážit karboplatinu ⚠ | — | Galsky 2011 (kritéria vznikla u uroteliálního karcinomu, pro plíce potvrdí lékař) | P04 CrCl ≈ 76 ml/min (odvozeno) → 🟢 |

#### Kolorektum (C18–C20)

| ID | Postup | Kontrola | 🟢 | 🟠 | 🔴 | Zdroj | Dataset |
|---|---|---|---|---|---|---|---|
| VS-KRC-01 | resekce jater | FLR | ≥ 40 % po intenzivní chemoterapii nebo při steatóze; ≥ 30 % u zdravých jater | 30–39 % po intenzivní chemoterapii → posoudí HPB chirurg, zvážit dvoudobý postup (KRC-2.5) | < 30 % | KRC-2.1, RKT-03/V4 | P03 38 % po 8× FOLFOX → 🟠 |
| VS-KRC-02 | resekce jater | extrahepatální onemocnění, kompletní restaging (CT hrudníku, břicha a pánve + MR jater s hepatospecifickou k. l.) | vyloučeno, restaging ≤ 4–6 týdnů | část restagingu chybí nebo je starší | neresekabilní extrahepatální onemocnění | KRC-2.1, KRC-2.4 | P03: „hrudník nebyl požadován“ (`P03-img03`), poslední CT hrudníku 2026-04-28 (`P03-img01`) → 🟠 |
| VS-KRC-03 | resekce jater | postižení obou laloků, vymizelá ložiska, dosažitelnost R0, cévní přítok, odtok a žlučová drenáž | jeden lalok, bez kontaktu s cévami | oba laloky, vymizelé ložisko (plánovat podle původní lokalizace) nebo kontakt s jaterní žílou | — | KRC-2.1, KRC-2.4, KRC-2.5 | P03 ložisko S3, vymizelé S5, S8 u pravé jaterní žíly (`P03-img04`) |
| VS-KRC-04 | operace | interval od bevacizumabu | viz VS-CHIR-03 | | | | |
| VS-KRC-05 | oxaliplatina | neuropatie | G0–1 a pacient nehlásí omezení instrumentálních činností | lékař G1, ale pacient popisuje omezení (knoflíky, psaní, držení předmětů) → rozpor, odpovídá G2 | přetrvávající G2 podle lékaře | KRC-3.2 | P03: `P03-neuro01` G1 vs. `P03-prom02` → 🟠 |
| VS-KRC-06 | anti-EGFR (cetuximab, panitumumab) | RAS | RAS wild-type | RAS neznámý | RAS mutovaný | KRC-3.1 | P03 KRAS G12D (`P03-bm01`) → 🔴 |
| VS-KRC-07 | imunoterapie | MMR/MSI | dMMR / MSI-H (v 1. linii preferována) | — | — | KRC-1.2; u pMMR/MSS ⚠ podklady mlčí → ⚪ | P03 nevyšetřeno → ⚪ |
| VS-KRC-08 | bevacizumab | krevní tlak, arteriální tromboembolie, proteinurie | tlak pod kontrolou, bez arteriální tromboembolie, proteinurie < 2 g/24 h | arteriální tromboembolie nebo IM v anamnéze (opatrnost) | nekontrolovaná hypertenze (nezahajovat), proteinurie ≥ 2 g/24 h (přerušit), nefrotický syndrom (ukončit) | příbalový text Avastin (FDA), monografie Cancer Care Ontario | P03 IM 2019 → 🟠, hypertenze kompenzovaná (`P03-doc07`) |
| VS-KRC-09 | 5-FU, kapecitabin | deficit DPD | normální aktivita | částečný deficit → snížit úvodní dávku | úplný deficit | EMA 2020 | v datasetu není → ⚪ |
| VS-KRC-10 | pokračovat v konverzní chemoterapii | metastázy už resekabilní, počet cyklů | metastázy zatím neresekabilní | resekabilní po ≥ 4–8 cyklech → neprodlužovat (hepatotoxicita, riziko vymizení ložisek) | — | KRC-2.2 | P03 8 cyklů, vymizelé S5 → 🟠 |

#### Prs (C50)

| ID | Postup | Kontrola | 🟢 | 🟠 | 🔴 | Zdroj | Dataset |
|---|---|---|---|---|---|---|---|
| VS-PRS-01 | anti-HER2 (trastuzumab, pertuzumab, T-DXd) | LVEF a pokles od výchozí hodnoty | ≥ 50 % a pokles < 10 bodů | pokles ≥ 10 bodů, ale LVEF ≥ 50 % → častější kontroly; poslední echo starší než 3 měsíce | pokles ≥ 10 bodů pod 50 % nebo symptomatické srdeční selhání → přerušit | PRS-3.4 | P02 63 → 52 %, P06 65 → 55 % → 🟠 |
| VS-PRS-02 | T-DXd | ILD nebo pneumonitida v anamnéze | ne | ano ⚠ | — | PRS-2.3 (riziko ILD hodnotit před léčbou), RKT-02/V1; přesné znění SmPC ověřit | — |
| VS-PRS-03 | T-DXd (indikace HER2-low) | HER2 IHC; vyčerpaná endokrinní léčba nebo předchozí chemoterapie | 1+ nebo 2+ s negativní ISH v kterémkoli vzorku | diskordance primární nádor vs. metastáza; endokrinní možnosti ještě nevyčerpané | HER2 0 ve všech vzorcích | PRS-1.1, PRS-1.2, PRS-2.3 | P01 1+ v primáru, 0 v metastáze → 🟠; P05 1+ → 🟢 |
| VS-PRS-04 | endokrinní léčba ± CDK4/6 | viscerální krize | není (mírná elevace transamináz krizí není) | — | viscerální krize: bilirubin > 1,5× ULN bez obstrukce, rychle se zhoršující dušnost → chemoterapie nebo ADC | PRS-2.1, PRS-2.2, PRS-2.4 | P01 bilirubin v normě → 🟢 |
| VS-PRS-05 | ribociklib | QTcF | < 450 ms | — | ≥ 450 ms (nezahajovat); > 480 ms přerušit | SmPC Kisqali (UK) | P01 QTc 420 ms (`P01-doc02`, údaj z roku 2023) |
| VS-PRS-06 | PI3K inhibitor (alpelisib) | diabetes, glykémie / HbA1c | bez diabetu, glykémie v normě | diabetes → upravit glykémii před zahájením; nekompenzovaný diabetes 2. typu nebo diabetes 1. typu (bezpečnost nestanovena) ⚠ | — | PI PIQRAY (TGA), Cancer Care Ontario | — |
| VS-PRS-07 | PARP inhibitor (RKT-06) | Hb a anémie G3 | Hb ≥ 90 g/l → lze pokračovat | Hb 80–89 g/l; nejnižší úroveň dávky (200 mg 2×) | Hb < 80 g/l → přerušit; anémie G3 při 200 mg 2× → ukončit | protokol RKT-06, RKT-06/Z4 | P05 Hb 92 (`P05-lab07-hb-f`) → lze 200 mg, další G3 = konec |
| VS-PRS-08 | PARP inhibitor | MDS/AML v anamnéze, předchozí PARPi | ne | — | ano (vyřazení) | RKT-06/V1, RKT-06/V2 | P05 ne |
| VS-PRS-09 | PARP inhibitor, CDK4/6, everolimus | induktory a inhibitory CYP3A (třezalka, grapefruit) | ne | ano → vyřešit | — | `P05-doc03`; SmPC Kisqali (silné inhibitory CYP3A) | P05 třezalka → 🟠 |
| VS-PRS-10 | taxany | neuropatie | G0–1 | ≥ G2 ⚠ (v datech paklitaxel ukončen při G2, `P06-doc08`) | — | praxe z datasetu, ⚠ práh potvrdí lékař | P06 G2, P02 G1 |
| VS-PRS-11 | mozkové metastázy: RT | počet ložisek, symptomy, kortikoidy | omezený počet → stereotaktická RT (SRS) | celomozková RT (kognitivní toxicita, odkládá se) | — | PRS-3.3 | P02 2 ložiska → SRS 🟢, obava z ozařování hlavy 💬 |
| VS-PRS-12 | kyselina zoledronová | CrCl | ≥ 60 ml/min (4 mg) | 30–59 ml/min (snížit dávku na 3,0–3,5 mg) | < 30 ml/min (nedoporučeno) | SmPC Zometa (UK eMC) | P05 CrCl ≈ 72 ml/min (odvozeno) → 🟢 |
| VS-PRS-13 | denosumab, zoledronát | stomatologické vyšetření, kalcium | provedeno | chybí | — | PRS-4.1 | P01 provedeno 2023 (`P01-doc02`), P05 (`P05-doc01`) |
| VS-PRS-14 | antracykliny | kumulativní dávka, LVEF | — | — | — | ⚪ práh doplní lékař | P01 AC 4× v roce 2017 |
| VS-PRS-15 | chemoterapie s vypadáváním vlasů | preference | — | 💬 preference (barvu nemění) | — | OBC-1.1 | P01 |

#### Ledvina (P06, D41.0): guidelines v datasetu nejsou

| ID | Postup | Kontrola | 🟢 | 🟠 | 🔴 | Zdroj | Dataset |
|---|---|---|---|---|---|---|---|
| VS-URO-01 | nefrektomie | funkce ledvin | — | CKD G3a, CrCl ≈ 40 ml/min → riziko dalšího zhoršení | — | `P06-doc03` (stanovisko urologa) | P06; navíc 💬 operaci si nepřeje |

#### Diagnostické výkony

| ID | Postup | Kontrola | 🟢 | 🟠 | 🔴 | Zdroj | Dataset |
|---|---|---|---|---|---|---|---|
| VS-DG-01 | transtorakální biopsie plic | předchozí pneumotorax po biopsii, CHOPN nebo emfyzém | ne | ano → zvážit EBUS nebo VATS | — | `P06-doc02` (alternativy), `P06-proc02`; ⚠ obecný práh bez zdroje | P06 → 🟠, 💬 obava z biopsie |
| VS-DG-02 | biopsie, operace při antiagregaci | ASA, antikoagulace | — | info | — | ⚠ | P03, P06 |

### 5.4 Očekávané barvy pro demo (podklad pro dev ground truth T-013)

**P03 (kolorektum s jaterními metastázami):**

| Postup | Pravidla | Celkem |
|---|---|---|
| Resekce jater (jednodobě nebo dvoudobě) + primárního nádoru | VS-KRC-01 🟠 (FLR 38 %), VS-KRC-02 🟠 (chybí CT hrudníku), VS-KRC-03 🟠 (S3, vymizelé S5), VS-CHIR-03 🟢 (od 19. 10.), VS-CHIR-01 🟢 + info ASA, VS-OBC-04 🟠 (−7 %), VS-OBC-02 🟠 (ECOG 0 vs. 1) | 🟠 |
| Pokračovat ve FOLFOX + bevacizumab | VS-KRC-05 🟠 (neuropatie G1 vs. popis pacienta), VS-KRC-08 🟠 (IM 2019), VS-KRC-09 ⚪ (DPD), VS-KRC-10 🟠 (8 cyklů, vymizelé S5: neprodlužovat) | 🟠 |
| Anti-EGFR | VS-KRC-06 🔴 (KRAS G12D) | 🔴 |
| Imunoterapie | VS-KRC-07 ⚪ (MMR nevyšetřeno) | ⚪ |

**P04 (NSCLC st. III):**

| Postup | Pravidla | Celkem |
|---|---|---|
| Neoadjuvantní chemoimunoterapie + lobektomie (PLI-2.2) | VS-PLI-01 🟠 (49 % / 38 %), VS-PLI-02 ⚪ (VO2max chybí), VS-PLI-03 🟠 (dušnost 7), VS-PLI-06 🟠 (EGFR probíhá), VS-PLI-04 🟠 (nadledvina), VS-PLI-09 🟠 (Na 129), VS-CHIR-02 🟠 (kouří), VS-OBC-03 ⚪ (G8 chybí), VS-OBC-04 🟠 (−9 %), VS-PLI-11 🟢 (CrCl ≈ 76) | 🟠 |
| Chemoradioterapie + durvalumab (PLI-2.4) | VS-PLI-07 🟢 (TPS 60 %), VS-PLI-06 🟠 (EGFR), VS-PLI-10 ⚪ (práh plicních funkcí pro RT), VS-PLI-04 🟠, VS-OBC-04 🟠, VS-PLI-11 🟢 | 🟠 |

---

## 6. Škály

| Škála | Rozsah | V datasetu | Poznámka |
|---|---|---|---|
| ECOG | 0–4 | lékař `Observation` 89247-1, pacient PROMs `samostatnost` | rozdíl ≥ 1 → OBC-1.3 |
| PROMs MDT-PROMS-1 | 0–10 | `QuestionnaireResponse` | ≥ 7 = výrazná zátěž (OBC-1.3) |
| CTCAE | G1–G5 | `neuro`, `anem` | anémie G3 = Hb < 80 g/l (`P05-doc07`) |
| RECIST 1.1 | CR / PR / SD / PD | popisy zobrazení | PR = pokles SLD ≥ 30 % proti výchozímu, PD = nárůst ≥ 20 % proti nadiru a ≥ 5 mm. `P03-img03` −40 % = PR, `P06-img05` +16 % proti nadiru = SD |
| TNM 8 | cT/pT, cN/pN, cM, stadia | `Observation` tnm, `Condition.stage` | rozpory P04 (`P04-tnm01` vs. `P04-tnm02`) |
| BI-RADS | 0–6 | `P02-img01` 5, `P06-img01` 5, `P01-doc01` 1 | |
| Nottingham grade | skóre 3–9 → G1–G3 | `P01-pat01` 6 bodů = G2, `P02-pat01` 8 = G3 | |
| HER2 IHC | 0 / 1+ / 2+ / 3+ | `bm` | HER2-low = 1+ nebo 2+ s negativní ISH (PRS-1.2) |
| GOLD | 1–4 (FEV1 %) | `P04-kom1` GOLD 2, FEV1 58 % | |
| CKD | G1–G5 (eGFR) | `P06-kom2` G3a | |
| G8 | 0–17 | chybí | ≤ 14 abnormální (OBC-2.2) |
| další číselné | LVEF %, ppoFEV1 / ppoDLCO %, VO2max ml/kg/min, PD-L1 TPS %, Ki-67 %, FLR %, SUVmax, balíčkoroky, BBPS 0–9 (`P03-doc01` 8) | | |
| Lung-RADS, Fleischner | viz §6.1 | v datech nejsou | jen s kontrolou použitelnosti |

### 6.1 Karta Lung-RADS a Fleischner (BON-6)

Karta se zobrazí u plicního ložiska. **Nejdřív deterministicky zkontroluje, jestli se škála dá použít:**

- **Lung-RADS** platí jen pro nález ze **screeningového** nízkodávkového CT plic. V datasetu žádné screeningové CT není → „nelze použít“.
- **Fleischner 2017** platí jen pro **náhodně zjištěný** plicní uzel u dospělého ≥ 35 let **bez známého nádoru**, bez imunosuprese a mimo screening. Všech 6 pacientů má známý nádor → „nelze použít: známý nádor, Fleischner se nevztahuje“.

U našich pacientů karta ukáže jen tento důvod, žádnou kategorii. Pro budoucí pacienty:

- **Lung-RADS v2022, solidní uzel:** 2 < 6 mm · 3 6 až < 8 mm · 4A 8 až < 15 mm · 4B ≥ 15 mm · 4X = přídatné suspektní znaky. ⚠ Ověřit proti PDF ACR.
- **Fleischner:** tabulku velikostí a intervalů doplnit z originální publikace (MacMahon a kol., Radiology 2017). Do té doby ⚪.
- **Citace:** externí zdroj, Evidence ID `EXT-LUNGRADS-2022` (D-016).

---

## 7. Zkratky

### 7.1 Pravidla výkladu

1. **Zkratku vykládej podle kontextu:**
   - sekce zprávy (OA v anamnéze = osobní anamnéza);
   - oddělení (`category.text`);
   - okolní slova (PR + „%“ = receptor, PR + RECIST = odpověď);
   - orgán (S3 u jater ≠ S3 u plic).
2. **Rozmezí** („ECOG 0–1“, „ECOG 1–2“) nepřeváděj sám na jedno číslo. Zobraz rozmezí a vyhoď NEJISTOTU AI. Strukturovaná data v datasetu berou horší hodnotu: `P03-ecog02` = 1, `P06-ecog02` = 2.
3. **Neznámou zkratku nerozepisuj odhadem.** Vyhoď varování „neznámá zkratka“.
4. **Strana těla:** l. dx. = vpravo, l. sin. = vlevo. Nesoulad se stranou diagnózy = ROZPOR (RF-IDENTITY).

### 7.2 Nejednoznačné zkratky v datasetu

| Zkratka | Význam A (kde) | Význam B |
|---|---|---|
| G1 / G2 / G3 | grade nádoru (`P03-pat01` G2) | stupeň toxicity CTCAE (`P05-anem01` G3), stadium CKD G3a (`P06-kom2`), GOLD 2 (`P04-kom1`) |
| PR | progesteronový receptor (`P01-pat01`) | parciální odpověď podle RECIST |
| PD | progrese podle RECIST | PD-L1 / PD-1 (`P04-bm01`, RKT-PD1) |
| LDL | levý dolní lalok (`P06-img02`) | LDL cholesterol |
| OA / RA | osobní / rodinná anamnéza (`P03-doc02`) | osteoartróza / revmatoidní artritida |
| PA | RTG projekce zezadu dopředu (`P04-img01`) | pracovní anamnéza |
| PAD | perorální antidiabetika (`P02-doc01`) | onemocnění periferních tepen |
| CMP | cévní mozková příhoda (`P06-doc05`) | kardiomyopatie |
| S3 | jaterní segment (`P03-img02`) | plicní segment (`P02-img02`) |
| PH | pertuzumab + trastuzumab (`P02-doc06`) | plicní hypertenze (`P06-doc04` popisuje zvýšený tlak v plicnici) |

### 7.3 Slovník zkratek z datasetu

**Oddělení** (`category.text`; prefix A- = ambulance):

| Zkratka | Význam |
|---|---|
| A-ONK | Ambulance klinické onkologie |
| A-PNEU / L-PNEU | Pneumologická ambulance / pneumologické oddělení, lůžková část |
| A-HCH | Hrudně chirurgická ambulance |
| A-GAST | Gastroenterologická ambulance, endoskopie |
| A-MCH / A-MAM | Ambulance mamární chirurgie / mamární poradna |
| A-KARD | Kardiologická ambulance |
| A-URO | Urologie, uroonkologická komise |
| A-CHIR | Chirurgická ambulance, jednodenní chirurgie |
| A-KTPP | Chirurgická ambulance, cévní přístupy (rozepsání zkratky v datech není) |
| A-ST | Studijní ambulance KOC (klinická hodnocení) |
| A-KF | Klinická farmacie |
| ONK-L | Onkologická klinika, jednodenní hospitalizace |
| RDG | Radiodiagnostické oddělení |
| NM | Nukleární medicína |
| PAT-B / PAT-M | Patologie, bioptická / molekulární |
| KOC | Komplexní onkologické centrum |
| MDT | multidisciplinární tým, onkologická komise |

**Anamnéza a vyšetření:**

| Zkratka | Význam |
|---|---|
| NO | nynější onemocnění |
| OA | osobní anamnéza |
| FA | farmakologická anamnéza |
| RA | rodinná anamnéza |
| SA | sociální anamnéza |
| GA | gynekologická anamnéza |
| st. p. | stav po (status post) |
| TK | krevní tlak |
| TF | tepová frekvence |
| AS | akce srdeční |
| SpO2 | saturace kyslíkem |
| KO | krevní obraz |
| DKK / HK | dolní končetiny / horní končetina |
| k. l. | kontrastní látka |
| NH | náležitá hodnota |
| IM | infarkt myokardu |
| STEMI | infarkt s elevacemi ST |
| PCI RIA | perkutánní koronární intervence na ramus interventricularis anterior |
| CHOPN | chronická obstrukční plicní nemoc |
| DM | diabetes mellitus |
| PAD | perorální antidiabetika |
| HRT | hormonální substituční léčba |
| CMP | cévní mozková příhoda |
| CKD | chronické onemocnění ledvin |
| eGFR | odhadovaná glomerulární filtrace |
| CrCl | clearance kreatininu |
| NSA | nesteroidní antirevmatika |
| ULN | horní hranice normy |
| G8 | geriatrický screening |

**Anatomie:**

| Zkratka | Význam |
|---|---|
| HZK | horní zevní kvadrant |
| PHL / LDL | pravý horní / levý dolní plicní lalok |
| S1–S10 | plicní segmenty |
| S1–S8 | jaterní segmenty |
| B1 / B2 | segmentální bronchy |
| 4R, 4L, 7, 10R, 11R | mediastinální a hilové uzlinové stanice |
| l. dx. / l. sin. | vpravo / vlevo |
| LK | levá komora |

**Zobrazení a výkony:**

| Zkratka | Význam |
|---|---|
| CT, MR, RTG PA | zobrazovací metody; RTG PA = projekce zezadu dopředu |
| MG, UZ | mamografie, ultrazvuk |
| CC / MLO | projekce mamografie (kraniokaudální / mediolaterální šikmá) |
| PET-CT (18F-FDG) | pozitronová emisní tomografie s CT |
| SUVmax | maximální akumulace FDG |
| HU | Hounsfieldovy jednotky |
| BI-RADS | klasifikace nálezu v prsu |
| EBUS-TBNA | endobronchiální ultrazvuk s punkcí |
| ROSE | rychlé cytologické hodnocení na sále |
| BAL | bronchoalveolární laváž |
| VATS | videoasistovaná torakoskopie |
| BBPS | Boston Bowel Preparation Scale (příprava střeva) |
| R0 | resekce bez reziduálního nádoru |
| FLR | budoucí jaterní remnant |
| TU | transfuzní jednotka |
| EKG, QTc | elektrokardiogram, korigovaný interval QT |
| LVEF / EF | ejekční frakce levé komory |
| FEV1, FVC | vteřinová kapacita, usilovná vitální kapacita |
| DLCO | difuzní kapacita plic |
| ppoFEV1 / ppoDLCO | predikované pooperační hodnoty |
| VO2max | maximální spotřeba kyslíku |
| GOLD | stupeň CHOPN |

**Patologie a biomarkery:**

| Zkratka | Význam |
|---|---|
| NST | invazivní karcinom bez zvláštního typu |
| DCIS | duktální karcinom in situ |
| G1–G3 | grade nádoru |
| ICD-O-3 …/3 a …/6 | maligní primární nádor / metastáza |
| IHC, ISH | imunohistochemie, in situ hybridizace |
| NGS | sekvenování nové generace |
| ctDNA | cirkulující nádorová DNA |
| VAF | alelová frekvence varianty |
| TMB | mutační nálož |
| ER, PR, HER2, Ki-67 | receptory a proliferace |
| HER2-low / HER2 0 | IHC 1+ nebo 2+ s negativní ISH / IHC 0 |
| luminal A / B | podtyp karcinomu prsu |
| TTF-1, napsin A, p40, GATA3, CK7, CK20, AE1/AE3 | imunohistochemické markery původu |
| KRAS G12D, NRAS, BRAF V600E | mutace |
| wt | wild-type, bez mutace |
| MMR / MSI, dMMR, MSI-H, MSS | mismatch repair / mikrosatelitová nestabilita |
| PD-L1 TPS (22C3) | podíl PD-L1 pozitivních nádorových buněk |
| ALK (D5F3), ROS1 (D4D6) | přestavby genů (klon protilátky v závorce) |
| ESR1, PIK3CA, AKT1, PTEN | změny v dráze estrogenového receptoru a PI3K |
| BRCA1/2, gBRCA | varianty BRCA, zárodečná varianta |
| HRR | geny homologní rekombinace |

**Léčba:**

| Zkratka | Význam |
|---|---|
| FOLFOX / FOLFIRI / FOLFOXIRI | režimy s 5-FU, leukovorinem (LV) a oxaliplatinou / irinotekanem |
| 5-FU, LV | fluorouracil, leukovorin |
| AC | doxorubicin + cyklofosfamid |
| PH | pertuzumab + trastuzumab |
| T-DXd | trastuzumab deruxtekan |
| ADC | konjugát protilátky s léčivem |
| IA | inhibitor aromatázy |
| CDK4/6 | inhibitory cyklin-dependentních kináz 4/6 |
| SERD | selektivní degradátor estrogenového receptoru |
| PARPi | PARP inhibitor |
| IO | imunoterapie |
| RT | radioterapie |
| SRS / SBRT | stereotaktická radiochirurgie / stereotaktická RT |
| CHRT | chemoradioterapie |
| Gy / frakce | dávka záření |
| BSC | pouze podpůrná léčba |
| D1, C1D1 | den 1, cyklus 1 den 1 |
| á 3 týdny | každé 3 týdny |
| 1-0-0 | dávkování ráno-poledne-večer |
| p. o., i.v., s. c., i.m. | ústy, do žíly, pod kůži, do svalu |
| RKT-SERD, RKT-ADC2, RKT-PD1, RKT-PARPi | studijní léky (fiktivní) |

---

## 8. Pravidla proti halucinacím

Převzato ze [stop-hallucination-guard](https://github.com/wreggyy/stop-hallucination-guard-skill): fakta s důkazem, předpoklady, neznámé a zásada **„raději vynechat než vymyslet“**. Sladěno s ARCH §5.3.

1. **Každý údaj v podkladu je jednoho ze tří typů** a v UI je to vidět:
   - **z dat:** citace Evidence ID;
   - **odvozeno:** výpočet z citovaných hodnot (CrCl, % úbytku, dny od bevacizumabu) se vzorcem a vstupy;
   - **neznámé / chybí:** „Údaj chybí v podkladech“ + kde by měl být.
2. **LLM nikdy nepřiřazuje barvu semaforu** a nevymýšlí prahy.
3. **Při extrakci** (zadání pacienta) vrací LLM ke každému poli hodnotu, citaci, jistotu a důvod nejistoty. Varování NEJISTOTA AI se spustí, když:
   - jistota je pod prahem (hodnotu doladit v evalu);
   - **nebo** jde o nejednoznačnou zkratku;
   - **nebo** jde o rozmezí;
   - **nebo** si zdroje odporují;
   - **nebo** grounding validátor tvrzení neověří.

   Sebehodnocení LLM samo nestačí, protože jistotu bývá zvyklé přeceňovat.
4. **Chybějící povinný údaj** se doplní jako `missing`, i když ho LLM nezmínil (ARCH §5.3 bod 5).
5. **Externí znalost** (mimo dataset) jen s citací zdroje z [§13](#13-zdroje). Jinak ⚪.
6. **Každý podklad má souhrn:** počet tvrzení, neověřených a chybějících (ARCH `stats`).

---

## 9. Model AI

- **Rozhodnutí ([Q-1](#12-otevřené-otázky)):** `AI_MODEL=gemini-3.8-flash`. Tým chtěl nejlepší poměr ceny a výkonu při opravdu dobrém výkonu. „Gemini 3.5 Pro“ neexistuje (stránka modelů Google, ověřeno 16. 10. 2026). Volba odpovídá ARCH D-008, ARCHITEKTURA.md se nemění.
- **Proč:**
  - jde o stabilní verzi a Google ji popisuje jako nejschopnější model řady Flash;
  - proti modelům Pro je na vstupu 2,7× levnější.

  Ceník Google (aktualizovaný 15. 10. 2026, placený tier, USD za 1M textových tokenů):

  | Model | Stav | Vstup | Výstup |
  |---|---|---|---|
  | **`gemini-3.8-flash`** (vybráno) | stable | 0,75 | 3,75 |
  | `gemini-4-argon` | stable | 2,00 (od 1. 12. 2026: 4,00) | 10,00 (od 1. 12. 2026: 20,00) |
  | `gemini-3.1-pro-preview` | preview | 2,00 | 12,00 |
  | `gemini-3.5-flash-lite` | stable | 0,30 | 2,50 |

- **Hrubý odhad ceny jednoho podkladu:**
  - předpoklad: ~8 paralelních volání po ~30 000 tokenech vstupu a ~2 000 tokenech výstupu;
  - Flash cca 0,24 USD na pacienta, Argon cca 0,64 USD.
- **Další modely:**
  - `gemini-4-argon` zůstává jako `AI_MODEL_STRONG` jen pro srovnání v evalu (T-301). Kdyby Flash v evalu neobstál, přepne se v env, beze změny kódu.
  - `gemini-3.5-flash-lite` je pro levné pomocné úlohy (klasifikace, normalizace textu), ARCH §5.7.
- **Pravidla:** model drž jen v env, testy běží na `AI_PROVIDER=mock`.
- **Embeddingy:** `gemini-embedding-001` v ceníku chybí, uvádí se `gemini-embedding-2`. Před T-102 ověřit, který použít (ARCH D-007).
- **Placený tier** se zapne, až bude tento souhrn hotový (rozhodnutí týmu). Do té doby žádná data do Gemini (Q9). Změněno D-021: nad syntetickým datasetem smí free tier.
- **Rychlost:** cíl NFR-1 (< 20 s) ověřit v evalu T-301.
- **Pitch (ochrana údajů):** podle ARCH §5.7 může Google AI Studio data dočasně uložit v jakékoli zemi. V pitchi říkat: prototyp běží na fiktivních datech, produkční nasazení přes Vertex AI v EU (data residency, DPA).

---

## 10. Změny kontraktu

✅ **Zapsáno do ARCHITEKTURA.md** (⚠️ KONTRAKT v Deníku PROGRESS.md). Platí znění tam, tady je jen rozcestník:

| Co | Kde v ARCHITEKTURA.md |
|---|---|
| role `mdt_admin` / `mdt_doctor` / `mdt_viewer`, `UserProfile`, demo účty | §6.2, D-014 |
| board = `MdtSession`, pole zařazení v `MdtCase` | §6.2, §8.6 |
| API: `/api/mdt/me/`, `/patients/{pid}/intake/`, `PATCH /cases/{cid}/`, `/cases/{cid}/compatibility/` | §6.3 |
| hlavička (`display_name`, `ecog.physician.entered_by`, `intent`) | §8.2, D-018 |
| semafor (`Light`, `CompatibilityRuleResult`, `TreatmentCompatibility`) | §8.1, §8.3, §5.9, D-015 |
| zařazení (`IntakeField`, `IntakeWarning`, `IntakePrefill`, `MdtCase`) | §8.6, §5.10 |
| FHIR zápisy (ECOG, záměr, přesun, odkliknuté varování) | §4.3 |
| Evidence ID `EXT-…` | §5.2, §4.5, D-016 |
| nové `RoleId` (`pulmonologist`, `cardiologist`) a `SectionId` | §8.1 |

---

## 11. Úkoly

Jsou v [PROGRESS.md §4](../PROGRESS.md#4-task-board):

| Úkol | Sprint | Co |
|---|---|---|
| T-500 ✅ | 0 | tento dokument a zapracování do ARCHITEKTURA.md |
| T-014 | 0 | CI a oprava testovací DB |
| T-501 | 1 | role a boardy |
| T-211 | 2 | formulář zařazení pacienta |
| T-502 | 2 | kontrola úplnosti a varování |
| T-503 | 2 | semafor |
| T-504 | 2 | externí zdroje `EXT-…` |
| T-505 | 2 | úzké rozložení |
| T-506 | 2 | údaje podle diagnózy a katalog metod |
| T-511 | 2 | úkoly po zasedání |
| T-303 | 3 | readiness nad T-502 |
| T-507 | 3 | anamnéza |
| T-508 | 3 | Lung-RADS a Fleischner (BON-6) |
| T-509 | 3 | zkratky a nejistota AI |
| T-510 | 3 | vstup PDF nebo textu (BON-7) |

---

## 12. Otevřené otázky

| # | Otázka | Stav |
|---|---|---|
| Q-1 | Který model? | ✅ `gemini-3.8-flash`, `gemini-4-argon` jen pro eval |
| Q-2 | Co ukázat, když minulá MDT rozhodnutí odložila (P04)? | ✅ jen C/P: nic se nepředvyplní, lékař vybere |
| Q-3 | Chceme 4. stav šedá (nelze posoudit)? | ✅ ano |
| Q-4 | Jak se chová odkliknuté varování? | ✅ stačí kliknout; problém v podkladu zůstane; kdo odklikl, jde jen do auditu (D-019) |
| Q-5 | Kdo přesouvá pacienty mezi boardy? | výchozí: zadávající lékař své, předseda jakékoli |
| Q-6 | Je administrátor zároveň předseda? | ✅ ano (D-014) |
| Q-7 | Prahy ⚠ | ✅ potvrdil tým 16. 10. 2026 (klinicky zatím neověřil lékař) |
| Q-8 | Od kolika znaků se anamnéza zkracuje na shrnutí? | výchozí 600 znaků (`INTAKE_ANAMNESIS_MAX_CHARS`) |
| Q-9 | Checkbox snímku vs. automatická kontrola stagingu | ✅ obojí: checkbox 3 měsíce, kontrola 6 týdnů |
| Q-10 | Jak široké bude okno prohlížeče? | výchozí od 360 px |

Týmové otázky jsou v PROGRESS.md §5 (otevřená zůstává Q12: CRLF na Windows).

---

## 13. Zdroje

**Dataset:**

- guidelines `KRC`, `PRS`, `PLI`, `OBC`;
- studie `RKT-01…06`;
- pacienti `P01–P06`;
- [DATASET.md](../DATASET.md).

**Externí** (ověřeno 16. 10. 2026; u ⚠ jen ze sekundárních souhrnů):

| Téma | Odkazy |
|---|---|
| Funkční operabilita plic | [ERS/ESTS 2025 (obrázek algoritmu)](https://publications.ersnet.org/ers-lookup/tab-link/F3/714410) · [souhrn Springer 2016](https://link.springer.com/article/10.1007/s40137-016-0158-x) · [PMC 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4283874) · [Breathe](https://publications.ersnet.org/content/breathe/7/3/221) |
| G8 | [MDCalc](https://www.mdcalc.com/calc/10426/g8-geriatric-screening-tool) · [Frontiers in Oncology 2023](https://www.frontiersin.org/journals/oncology/articles/10.3389/fonc.2023.1110236/epub) |
| DPD | [EMA 2020](https://www.ema.europa.eu/en/documents/referral/fluorouracil-and-fluorouracil-related-substances-article-31-referral-new-testing-and-treatment-recommendations-fluorouracil-capecitabine-tegafur-and-flucytosine_en.pdf) · [ESMO news](https://esmo.org/oncology-news/ema-provides-new-testing-and-treatment-recommendations-for-fluorouracil-capecitabine-and-tegafur) |
| Ribociklib | [Kisqali PI (UK)](https://pro.novartis.com/uk-en/sites/pro_novartis_com_uk/files/2025-01/kisqali-pi.pdf) · [Cancer Care Ontario](https://www.cancercareontario.ca/sites/ccocancercare/files/ribociclib.pdf) |
| Bevacizumab | [Avastin label (FDA)](https://www.accessdata.fda.gov/drugsatfda_docs/label/2020/125085s337lbl.pdf) · [Cancer Care Ontario](https://www.cancercareontario.ca/system/files_force/BEVAMNT_LU_MES_P.pdf?download=1) |
| Zoledronát | [Zometa SmPC (UK eMC)](https://www.medicines.org.uk/emc/product/12754/smpc/print) |
| Kardiální riziko před operací | [JAMA Surgery](https://jamanetwork.com/journals/jamasurgery/fullarticle/2825366) · [The Hospitalist](https://blogs.the-hospitalist.org/content/reply-perioperative-interruption-dual-antiplatelet-therapy) |
| Cisplatina | [Galsky (Healio)](https://www.healio.com/news/hematology-oncology/20120325/panel-proposes-consensus-definition-of-cisplatin-ineligibility-criteria) |
| Imunoterapie a autoimunita | [PMC 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6045736) |
| T-DXd a ILD | [Swain a kol. 2022 (PubMed)](https://pubmed.ncbi.nlm.nih.gov/35430509/) |
| Alpelisib | [PI PIQRAY (TGA)](https://tga.gov.au/sites/default/files/auspar-alpelisib-200820-pi.pdf) · [Cancer Care Ontario](https://www.cancercareontario.ca/system/files_force/alpelisib.pdf?download=1) |
| Lung-RADS | [ACR Lung-RADS v2022](https://ACR.org/-/media/ACR/Files/RADS/Lung-RADS/Lung-RADS-2022-Summary-_Final.pdf) · [ctisus](https://ctisus.com/learning/journalclub/344580) |
| Fleischner | [Cleveland Clinic](https://consultqd.clevelandclinic.org/incidental-pulmonary-nodules-a-summary-of-the-2017-fleischner-society-guidelines) · [Radiopaedia](https://radiopaedia.org/articles/13541) |
| Modely Gemini | [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models) |
| Prostata (§4.5, 17. 10.) | [EAU Pocket on Prostate Cancer 2025 (PDF)](https://d56bochluxqnz.cloudfront.net/documents/pocket-guidelines/EAU-EANM-ESTRO-ESUR-ISUP-SIOG-Pocket-on-Prostate-Cancer-2025_updated.pdf) · [EAU guideline (plný text)](https://d56bochluxqnz.cloudfront.net/documents/full-guideline/EAU-EANM-ESTRO-ESUR-ISUP-SIOG-Guidelines-on-Prostate-Cancer-2025_2025-03-24-120144_rinw.pdf) |
| Ledvina (§4.6, 17. 10.) ⚠ | [EAU RCC 2025 update (European Urology)](https://www.europeanurology.com/article/S0302-2838(25)00139-3/fulltext) · [IMDC (MDCalc)](https://www.mdcalc.com/imdc-international-metastatic-rcc-database-consortium-risk-score-rcc) · [Alberta RCC guideline 2025](https://www.albertahealthservices.ca/assets/info/hp/cancer/if-hp-cancer-guide-gu003-renal-cell.pdf) |
