# Účty, pozvánky a nastavení lékaře pro PVW

> Požadavek týmu z 9. 11. 2026. Navazuje na šablonu údajů lékaře (D-025, [SABLONY_LEKARE.md](SABLONY_LEKARE.md)),
> tým komise (T-319), registraci se šablonou (T-338) a okno pro projektor (T-333, T-348).
> Rozhodnutí D-027 a D-028, úkoly T-356 až T-360 v [PROGRESS.md](../PROGRESS.md).
> **Stav: hotovo** (10. 11. 2026, větev `claude/exciting-edison-bp0dl2`). Kontrakty jsou v ARCHITEKTURA.md
> §6.2, §6.3, §7.1, §8.6 a §9; jak to funguje v kódu, popisuje §5 níže.

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
- **Správce je samostatná role `mdt_manager`** (rozhodnuto 9. 11., Q29). Spravuje účty, komise a pozvánky,
  ale sám nepotvrzuje závěry. Předseda komise (`mdt_admin`, D-014) zůstává klinická role.
- **Jeden člověk může mít obě role** (správce i předseda). Role jsou Django `Group`, uživatel může být ve více skupinách.
- Dnes účty spravuje `mdt_admin` na stránce Tým komise (`/dashboard/tym`, T-319, T-338). Tato oprávnění přejdou na
  `mdt_manager`. Demo účet předsedy dostane obě role, aby demo fungovalo beze změny.

## 2. Pozvánky a lékaři z jiných nemocnic

1. Správce vyplní pozvánku: jméno, tituly, e-mail, odbornost, roli (`mdt_doctor` / `mdt_viewer`), **nemocnici**
   a komise, kterých se lékař účastní.
2. Vznikne **jednorázový odkaz** s náhodným tokenem a omezenou platností (návrh: 7 dní). Do databáze se ukládá jen
   hash tokenu. **Doručení (rozhodnuto 9. 11.): obojí.** Aplikace odkaz pošle e-mailem (v dev jen do Mailhogu)
   a správce ho zároveň může zkopírovat a poslat sám (Teams, SMS…).
3. Lékař otevře odkaz, nastaví si heslo a projde **průvodcem nastavení** (§3). Použitý nebo prošlý odkaz nefunguje,
   správce může pozvánku zrušit nebo poslat znovu.
4. **Lékař z jiné nemocnice:** správce u pozvánky vybere „externí lékař“ a jeho nemocnici
   (ve FHIR `Organization`, lékař `Practitioner` + `PractitionerRole.organization`).
   - Účastní se jen komisí, do kterých ho správce pozval. Jiné komise ani pacienty z nich nevidí.
   - **U pacientů zasedání, kam je pozvaný, vidí celý podklad** jako ostatní členové komise (podklad, PVW, závěr;
     rozhodnuto 9. 11.). Pacienty do našich komisí nezařazuje (role `mdt_viewer`). Hlavičky jsou i pro něj bez jména
     a RČ (D-018).
   - Všude, kde je vidět jméno lékaře (přítomní, úkoly, spolupráce, záznam boardu), je u něj i jeho nemocnice.
5. Samoregistrace `/register` je v pilotu a produkci vypnutá (`MDT_ALLOW_REGISTRATION`, T-355); účty vznikají
   přes pozvánku nebo je správce založí přímo. V dev zůstává registrace kvůli demu, stejně jako demo účty
   a 1-click přihlášení pro pitch.

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

### Kdo je „pozvaný na MDT“ (rozhodnuto 9. 11.)

Platí **obojí**:

- **stálý člen komise:** správce lékaře přiřadí ke komisi (např. plicní). Lékař je pozvaný na všechna její zasedání.
  U jednoho zasedání ho jde vyřadit (nepřijde);
- **přizvaný na zasedání:** předseda nebo správce může k jednomu zasedání přizvat lékaře, který členem komise není
  (např. kardiolog jen na jeden termín).

Podle toho se ukazují požadavky lékaře (krok 3) a jeho normy na PVW (krok 4).

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
- Norma je **strukturovaná** (rozhodnuto 9. 11.), ne volný text: údaj z katalogu, operátor, hodnota a jednotka, ke kterému postupu nebo
  oblasti patří, poznámka a nepovinně zdroj (Evidence ID guidelines nebo `EXT-MK-…`).
- **Na PVW:** u pacienta, kde je lékař pozvaný, se norma ukáže jako řádek s autorem a hodnotou pacienta, například
  „Norma MUDr. Novák: FLR ≥ 30 % · pacient 28 % (P03-img03)“.
- **Pravidla (platí pro všechny AI agenty):**
  - normu vyhodnocuje **kód**, ne LLM, a vždy s citací faktu pacienta;
  - chybějící údaj se ukáže jako `missing`, nikdy se nedomýšlí;
  - norma lékaře je **osobní kritérium**, ne pravidlo semaforu: barvu semaforu nemění (D-015) a nikdy se nepíše
    „doporučujeme“;
  - je vždy vidět, čí norma to je.
- **Požadavky i normy mění jen lékař sám** (rozhodnuto 9. 11.) v průvodci nebo v Nastavení. Správce je vidí, ale nemění.

## 4. Co přibylo (T-356 až T-360)

| Co | Kde |
|---|---|
| role správce `mdt_manager` (samostatná skupina, demo předseda má obě role); účty, pozvánky a komise spravuje jen správce | `apps/mdt/roles.py`, `accounts.py`, `/dashboard/tym` |
| pozvánka s jednorázovým odkazem (hash tokenu, 7 dní, e-mail i kopie, nový odkaz, zrušení) → stránka `/pozvanka/[token]` | `Invitation`, `apps/mdt/accounts.py` |
| komise se stálými členy; u zasedání komise, přizvaní a vyřazení | `Committee`, `MdtSession.committee/invited/excluded`, `SessionInvitedDialog` (jednání → ⋯ → Pozvaní lékaři) |
| lékař z jiné nemocnice: vidí jen své komise a zasedání, kam je pozvaný; v IRIS `Organization` + `PractitionerRole` | `apps/mdt/scope.py` (middleware deny by default), `services/practitioners.py` |
| průvodce po prvním přihlášení: profil → můj PVW s náhledem → požadavky → normy | `/dashboard/vitejte`, `PvwSketch`, `MyRulesEditor`, `OnboardingBanner` |
| požadavky lékaře → upozornění zadávajícímu lékaři při zařazení, v kontrole před zasedáním a v detailu případu; rozhodnutí „potřebuji / nepotřebuji / chybějící do úkolů“ | `DoctorRequirement`, `MdtCase.requirement_decisions`, `RequirementsPanel` |
| normy lékaře na PVW (karta „Normy lékařů“), vyhodnocení kódem s citací | `DoctorNorm`, `services/rules/doctor_rules.py`, blok `norms` v `quick-view.tsx` |

## 5. Jak to funguje v kódu

- **Pozvaní na zasedání** = `members` komise − `excluded` + `invited` (`scope.invited_users`). Podle nich se
  ukazují požadavky (bez zadávajícího lékaře) a normy na PVW. Seed zakládá komise podle názvů zasedání.
- **Externí lékař:** `ExternalScopeMiddleware` mu povolí jen vyjmenovaná API (`scope.ALWAYS`, API podle zasedání,
  případu a pacienta z jeho zasedání); nové API je pro něj zavřené, dokud ho někdo vědomě nepřidá.
- **Vyhodnocení normy** (`doctor_rules.evaluate_norm`): údaj chybí / přeskočený → `missing`; v hodnotě rozmezí,
  nerovnost, víc čísel nebo jiná jednotka → `not_evaluable` s důvodem; jinak porovnání → `met` / `not_met`.
  Z textu bere jen jednoznačné číslo v jednotce normy (např. „1,9 l (58 % náležité)“ + „%“ → 58).
- **Rozhodnutí zadávajícího lékaře** se jen přidává do `MdtCase.requirement_decisions` (platí poslední, historie
  zůstává, D-019). „Chybějící do úkolů“ založí `Task` v IRIS stejně jako příprava na MDT (T-350).
