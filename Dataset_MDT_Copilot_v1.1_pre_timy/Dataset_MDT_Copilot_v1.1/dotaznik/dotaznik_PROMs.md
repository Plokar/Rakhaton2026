# Dotazník pacienta MDT-PROMS-1 (ilustrační)

Vlastní krátký dotazník vytvořený pro Rakathon 2026. Tematicky vychází z oblastí standardizovaných nástrojů (EORTC QLQ-C30, PRO-CTCAE, Distress Thermometer), jejich znění ale **nepřebírá** – ta jsou chráněná licencí. V produkčním řešení by se použil licencovaný standardizovaný nástroj.

Škály 0–10: **0 = žádné potíže, 10 = nejhorší představitelné**. Otázka „Jak zvládáte běžný den?“ je laická obdoba škály ECOG (možnost 0–4 odpovídá ECOG 0–4), takže lze porovnat výkonnostní stav podle pacienta a podle lékaře.

FHIR: `Questionnaire/MDT-PROMS-1` (soubor `dotaznik_PROMs_Questionnaire.json`), odpovědi pacientů jsou `QuestionnaireResponse` v bundlu pacienta.

| linkId | Otázka | Typ | Možnosti |
|---|---|---|---|
| `bolest` | Bolest za poslední týden (0–10) | integer |  |
| `bolest-misto` | Kde vás bolí? (vlastními slovy) | string |  |
| `unava` | Únava za poslední týden (0–10) | integer |  |
| `nevolnost` | Nevolnost nebo zvracení (0–10) | integer |  |
| `dusnost` | Dušnost (0–10) | integer |  |
| `chut` | Nechutenství (0–10) | integer |  |
| `brneni` | Brnění, mravenčení nebo necitlivost rukou či nohou (0–10) | integer |  |
| `prujem` | Průjem (0–10) | integer |  |
| `psychika` | Psychická zátěž – úzkost, smutek, starosti (0–10) | integer |  |
| `spanek` | Potíže se spánkem (0–10) | integer |  |
| `samostatnost` | Jak zvládáte běžný den? | choice | `0` Zvládám vše jako před nemocí, i fyzicky náročné věci<br>`1` Těžší fyzickou práci nezvládám, lehčí činnosti a domácnost ano<br>`2` Postarám se o sebe, ale pracovat nemohu; přes den odpočívám méně než polovinu času<br>`3` Postarám se o sebe jen částečně; víc než polovinu dne ležím nebo sedím<br>`4` Jsem odkázán(a) na pomoc druhých, většinu dne ležím |
| `chuze` | Kolik zvládnete ujít? | choice | `bez-omezeni` Ujdu bez potíží delší vzdálenost i do schodů<br>`1-patro` Vyjdu jedno patro bez zastavení<br>`1-patro-zastavka` Jedno patro vyjdu jen se zastávkou<br>`rovina` Zvládnu jen chůzi po rovině<br>`byt` Pohybuji se jen po bytě |
| `hmotnost` | Vaše současná hmotnost (kg) | decimal |  |
| `hmotnost-zmena` | Změna hmotnosti za poslední 3 měsíce (kg, minus = úbytek) | decimal |  |
| `nove-obtize` | Objevily se od minulé návštěvy nové obtíže? Jaké? | string |  |
| `alergie` | Alergie nebo nesnášenlivost léků | string |  |
| `leky-mimo` | Léky, doplňky stravy nebo bylinky, které užíváte navíc | string |  |
| `priorita` | Co je pro vás v léčbě nejdůležitější? | choice | `delka` Nejdůležitější je pro mě co nejdelší život, i za cenu náročnější léčby<br>`kvalita` Nejdůležitější je pro mě kvalita života, i kdyby léčba byla méně účinná<br>`oboji` Obojí je pro mě stejně důležité<br>`nevim` Nevím / chci to probrat s lékařem |
| `postoj` | Co si přejete, aby lékaři při rozhodování věděli? (např. postoj k operaci, cestování, práce, rodina) | string |  |
| `podpora` | Podpora v domácnosti | choice | `dostatecna` Mám dostatečnou podporu blízkých<br>`castecna` Podporu mám jen částečně<br>`zadna` Podporu nemám, žiji sám/sama bez pomoci |
