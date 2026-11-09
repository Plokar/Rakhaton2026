# Účty, pozvánky a nastavení lékaře pro PVW

> Požadavek týmu z 9. 11. 2026. Navazuje na šablonu údajů lékaře (D-025, [SABLONY_LEKARE.md](SABLONY_LEKARE.md)),
> tým komise (T-319), registraci se šablonou (T-338) a okno pro projektor (T-333, T-348).
> Rozhodnutí D-027 a D-028, úkoly T-355 až T-359 v [PROGRESS.md](../PROGRESS.md).
> Tento dokument je **návrh**. Kontrakty (API §6.3, JSON §8) se mění až v PR s kódem, podle AGENTS.md.

## 0. Slovník

| Zkratka | Význam |
|---|---|
| **PVW** | **projektor view** = okno pro projektor, tedy panel, který se při zasedání MDT promítá na projektoru celé komisi. Route `/projector` (T-512), slidy bez posouvání (T-348), rozložení u případu `MdtCase.projector_layout` (T-333), jinak šablona zadávajícího lékaře (D-025). Když tým nebo lékař řekne „PVW“, myslí tohle. |
| **Správce MDT** | jeden člověk, který spravuje všechny komise a všechny účty (§1). |
| **Must-have PVW** | osobní šablona lékaře: co a v jakém pořadí chce na PVW vidět vždy (§3, krok 2). |
| **Požadavek lékaře** | údaje, které lékař jako člen komise u pacienta vyžaduje (§3, krok 3). |
| **Norma lékaře** | práh nebo kritérium pro rozhodnutí, za které lékař odpovídá (§3, krok 4). |

## 1. Správce MDT

- Je **jeden správce všech MDT** (všech komisí a zasedání nemocnice).
- Má na starosti **všechny účty**: zakládá je, posílá pozvánky, mění roli, odbornost a komise, blokuje účty a obnovuje přístup.
- Lékaři se sami neregistrují. Do aplikace se dostanou jen přes **pozvánku od správce** (§2).
- Dnes tuto práci dělá role `mdt_admin` (předseda, D-014) na stránce Tým komise (`/dashboard/tym`, T-319, T-338).
  Jestli správce zůstane totožný s předsedou, nebo bude samostatná role (`mdt_manager`), je otevřená otázka Q29.
  Do rozhodnutí platí: **správce = `mdt_admin`**.

## 2. Pozvánky a lékaři z jiných nemocnic

1. Správce vyplní pozvánku: jméno, tituly, e-mail, odbornost, roli (`mdt_doctor` / `mdt_viewer`), **nemocnici**
   a komise, kterých se lékař účastní.
2. Vznikne **jednorázový odkaz** s náhodným tokenem a omezenou platností (návrh: 7 dní). Správce ho lékaři pošle
   (zkopíruje, nebo e-mailem; v dev jde e-mail jen do Mailhogu). Do databáze se ukládá jen hash tokenu.
3. Lékař otevře odkaz, nastaví si heslo a projde **průvodcem nastavení** (§3). Použitý nebo prošlý odkaz nefunguje,
   správce může pozvánku zrušit nebo poslat znovu.
4. **Lékař z jiné nemocnice:** správce u pozvánky vybere „externí lékař“ a jeho nemocnici
   (ve FHIR `Organization`, lékař `Practitioner` + `PractitionerRole.organization`).
   - Účastní se jen komisí, do kterých ho správce pozval. Jiné komise ani pacienty z nich nevidí.
   - Všude, kde je vidět jméno lékaře (přítomní, úkoly, spolupráce, záznam boardu), je u něj i jeho nemocnice.
5. Veřejná registrace `/register` se vypne, nebo bude fungovat jen s platným tokenem pozvánky.
   Demo účty a 1-click přihlášení pro pitch zůstávají.

## 3. Průvodce nastavením lékaře (při prvním přihlášení)

Kroky jdou přeskočit a kdykoli později změnit v Nastavení. Nic z nastavení nemění podklad, export ani
kontrolu úplnosti (D-019).

### Krok 1: Profil

Jméno, tituly, odbornost a nemocnice předvyplněné z pozvánky. Lékař je zkontroluje.

### Krok 2: Můj PVW (must-have)

- Lékař si **jako první** nastaví, jak má PVW vypadat: které kategorie a údaje jsou pro něj „must have“
  a v jakém pořadí. Rovnou vidí **živý náhled PVW** na demo pacientovi.
- Výchozí stav je preset podle odbornosti (`template_presets.yaml`, D-025).
- Technicky je to stávající šablona údajů lékaře (`FactTemplate`, po oblastech diagnózy). Platí pravidla D-024 a D-025:
  kategorie určuje systém, závažný údaj se ukáže i skrytý, skryté se jen sbalí.

### Krok 3: Moje požadavky na podklad

- Lékař vybere údaje, které **vyžaduje**, když je na MDT pozvaný. Vybírá z katalogu údajů (klíče `bm.egfr`,
  `spiro.fev1`, `liver.flr`, `lab:718-7`…), po oblastech diagnózy. Ke každému může připsat krátkou poznámku.
- **Co se stane:** když zadávající lékař připravuje pacienta na zasedání, kde je tento lékař pozvaný (přítomný
  nebo člen komise), dostane upozornění:
  „MUDr. Petr Novák (radiační onkolog) u pacientů s karcinomem plic vyžaduje: FEV1, DLCO, předchozí RT. U pacienta chybí: DLCO.“
- **Rozhoduje zadávající lékař:**
  - *lékaře u pacienta potřebuji* → chybějící údaje doplní, nebo je dá do úkolů (stávající `prep_tasks`, T-350);
  - *u tohoto pacienta ho nepotřebuji* → upozornění odklikne. Odkliknutí se zapíše (kdo, kdy) a z podkladu nezmizí (D-019).
- Požadavek lékaře je **upozornění, ne blokace**. Pacienta jde zařadit i bez vyžadovaných údajů.

### Krok 4: Moje normy pro řešení

- Lékař nastaví normy, které **závisí na něm**: prahy a kritéria, podle kterých se jeho odbornost rozhoduje.
  Například chirurg: FLR ≥ 30 %, ECOG ≤ 1 pro resekci; radiační onkolog: FEV1 ≥ 40 % pro radikální RT.
- Norma je **strukturovaná**, ne volný text: údaj z katalogu, operátor, hodnota a jednotka, ke kterému postupu nebo
  oblasti patří, poznámka a nepovinně zdroj (Evidence ID guidelines nebo `EXT-MK-…`).
- **Na PVW:** u pacienta, kde je lékař pozvaný, se norma ukáže jako řádek s autorem a hodnotou pacienta, například
  „Norma MUDr. Novák: FLR ≥ 30 % · pacient 28 % (P03-img03)“.
- **Pravidla (platí pro všechny AI agenty):**
  - normu vyhodnocuje **kód**, ne LLM, a vždy s citací faktu pacienta;
  - chybějící údaj se ukáže jako `missing`, nikdy se nedomýšlí;
  - norma lékaře je **osobní kritérium**, ne pravidlo semaforu: barvu semaforu nemění (D-015) a nikdy se nepíše
    „doporučujeme“;
  - je vždy vidět, čí norma to je.

## 4. Co už existuje a co je nové

| Už je | Kde |
|---|---|
| předseda zakládá lékaře ve dvou krocích (profil → šablona údajů) | `/dashboard/tym`, `POST /api/mdt/users/` (T-319, T-338) |
| registrace s odborností a šablonou | `/register`, `POST /api/auth/register/` (T-338) |
| šablona údajů lékaře po oblastech, presety podle odbornosti | `FactTemplate`, D-025 |
| rozložení PVW u případu, „Uložit také jako moji šablonu“ | `MdtCase.projector_layout` (T-333) |
| lékaři nemocnice z IRIS | `GET /api/mdt/practitioners/` (T-328) |
| úkoly z chybějících údajů při zařazení | `prep_tasks` (T-350) |

| Nové | Úkol |
|---|---|
| pozvánky s jednorázovým odkazem, registrace jen přes pozvánku | T-355 |
| lékaři z jiných nemocnic a omezení na jejich komise | T-356 |
| průvodce nastavením po prvním přihlášení (kroky 1–4) | T-357 |
| požadavky lékaře → upozornění zadávajícímu lékaři | T-358 |
| normy lékaře na PVW | T-359 |

## 5. Návrh datového modelu (upřesní se v PR s kódem)

- `Invitation`: `token_hash`, `email`, jméno a tituly, `role`, `specialty`, `organization` (nemocnice), `is_external`,
  `committees` (komise), `expires_at`, `used_at`, `revoked_at`, `created_by`.
- `UserProfile`: + `organization`, `is_external`, `committees`, `onboarding_done`.
- **Komise** dnes nemá vlastní model (zasedání `MdtSession` mají jen `title`). Pro omezení externích lékařů a pro
  „pozvaný na MDT“ bude potřeba buď model komise s členy, nebo pozvaní u zasedání. Rozhodne T-356.
- `DoctorRequirement`: `user`, `area` (`PLI` / `PRS` / `KRC` / `OBC`…), `fields` (klíče katalogu údajů), `note`.
- `DoctorNorm`: `user`, `area`, `field`, `op`, `value`, `unit`, `procedure` (postup ze semaforu, nepovinně), `note`, `source`.
