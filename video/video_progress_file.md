# Video progress

> Průběžný stav výroby filmů podle [FILM_SCENAR.md](FILM_SCENAR.md). Nejnovější záznam je nahoře v Deníku.
> Stav: ⬜ nezačato · 🔄 rozpracováno · ✅ hotovo · ⚠️ blokováno

## Úkoly

| # | Úkol | Stav | Poznámka |
|---|---|---|---|
| V-01 | Průzkum: Rakathon, zadání Asseco, aplikace (repo + živá doména) | ✅ | rakathon.cz, docs/PITCH.md, docs/DEMO.md, snímky živé aplikace |
| V-02 | Výběr skillů: video-shotcraft + remotion-dev/skills | ✅ | staženo do `~/video-skills-src`, nainstalováno do `~/.claude/skills` |
| V-03 | Scénář obou filmů, VO text, hudební prompty | ✅ | FILM_SCENAR.md |
| V-04 | Výběr a analýza hudby (onsety, offset dropu) | ✅ | Mixkit #598 od 41,92 s (drop f330), #184 pod průchod |
| V-05 | Projekt Remotion (4.0.532), knihovny ze skillu | ✅ | `video/` |
| V-06 | Snímání aplikace: `scripts/capture.mjs` (tmavý režim, 2×) | ✅ | 8 obrazovek + layout.json, jen čtení |
| V-07 | Film A: scény A1–A8 | ✅ | QA statické snímky, 2 kola oprav |
| V-08 | Film A: zvuk (hudba, SFX, VO sloty, ducking) | ✅ | zpětná vazba uživatele zapracována, bez přebuzení |
| V-09 | Film B: kapitoly B0–B9 | ✅ | B3 prodloužena na 11 s, B6 zkrácena na 7 s |
| V-10 | Film B: zvuk (podkres, SFX) | ✅ | podkres 0,16, zdrženlivé SFX |
| V-11 | QA: statické snímky, celý render, kontrola snímků | ✅ | out/qa/ |
| V-12 | Nezávislá kontrola (subagent, final-review + aesthetic-rules) | ⬜ | na vyžádání (subagent jen se souhlasem uživatele) |
| V-13 | Finální render: hook a průchod, s hudbou i bez | ✅ | out/*.mp4: 30,0 s a 90,0 s, bez přebuzení (špička −0,2 dBFS) |
| V-14 | Průchod v2: nový návrh scén (sdělení, selling point, napojení) | ✅ | FILM_SCENAR §5, zpětná vazba 17. 10. |
| V-15 | Průchod v2: nové snímky interakcí (`scripts/capture2.mjs`) | ✅ | menu, boční panel, dotaz s odpovědí AI, editor projektoru, chat, zdroj; jen čtení |
| V-16 | Průchod v2: souvislý záběr, kamera za myší, přechody aplikace | ✅ | `src/walk/Stage.tsx` (pružina, náklon, vrstvy) |
| V-17 | Průchod v2: logo jako v hooku, přirozený klik, QR kód | ✅ | `common/LogoReveal.tsx`, Mixkit 1113/2997, `public/qr.svg` |
| V-18 | Průchod v2: render s hudbou i bez | ✅ | 90,0 s, bez přebuzení (špička −0,6 dBFS) |
| V-19 | Průchod v2.1: gramatika kamery (navigace × čtení), pomalejší tempo, závěr 5,5 s | ✅ | render s hudbou hotový; verze bez hudby zůstala z v2 (na přání uživatele nerenderováno) |
| V-21 | Klip 04: okno projektoru s výbuchem skrytých údajů (preset pneumologa) | ✅ | v2: vertikální úzký náhled, 5 s, tmavá + světlá (`src/clips/ProjectorPreset.tsx`) |
| V-22 | Klipy po scénách (výřezy z průchodu) | ✅ | `scripts/render_klipy.sh` → `out/klipy/` |
| V-20 | Prezentace 13 slidů (.pptx) ve stylu videí | ✅ | `prezentace/MedTeam_Prezentace.pptx`, validace prošla, kontrola exportem z PowerPointu |

## Klíčová rozhodnutí

- **D1 · Dva filmy místo jednoho** (zadání uživatele 17. 10.): hook 30 s na 1. slide a průchod 1:30, který řečník komentuje živě. Průchod je proto bez VO, s štítky kapitol a tempem na mluvení.
- **D2 · Tmavý režim aplikace** (režim projektoru): filmový vzhled, aplikace ho reálně má a v sále se lépe promítá.
- **D3 · Režim skillu „autonomní tvorba“** (pipeline.md): uživatel chce, aby video vytvořil agent.
- **D4 · Hudba je navázaná na drop**, ne na pevný beat grid: skladba 598 má hlavní údery po ~1,55 s a jsou změřené (onsets.py).
- **D5 · Logo jako SVG** místo JPG: logo v repu je JPG se zapečeným šachovnicovým pozadím, proto je překreslené a animované po částech.
- **D7 · Průchod v2 jako jeden záběr** (zpětná vazba 17. 10.): bez střihů mezi kapitolami, myš otevírá menu a panely jako v aplikaci a kamera ji sleduje (kriticky tlumená pružina, deterministicky od snímku 0).
- **D8 · Chat a nahrávání dokreslené:** na živé instanci jsou v chatu testovací zprávy týmu, proto je nahrazujeme jen v DOM prohlížeče. Nahrávání by poslalo audio na server, proto je jeho stav dokreslený. Nic se na server neposílá.
- **D9 · Bez AI podkladu na produkci:** P03 tam nemá vygenerovaný podklad (varovné signály, druhá AI, podobné případy). Generovat ho by změnilo sdílenou instanci, proto průchod ukazuje funkce, které fungují bez něj.
- **D6 · VO je volitelný:** soubory `public/audio/vo/A_0x.mp3` se načtou automaticky, když existují (`getStaticFiles`).

## Deník

- **18. 10. 2026:** klip 04 předělán na vertikální úzký náhled okna projektoru (jako vyskakovací okno), 5 s, jen výbuchy a dosednutí; tmavá a světlá varianta.

- **18. 10. 2026 (odpoledne):** 1:30 video rozděleno na klipy po scénách. Nová scéna 04: okno projektoru P04, 17 údajů vybuchne na skleněné střepy (preset pneumologa ze schůzky 17. 10.), zbylé přeletí na svá místa, končí skutečným stavem aplikace „skryto 17“.

- **18. 10. 2026:** průchod v2.1. Kamera už nemíchá sledování myši se zvýrazněním: buď navigace (za myší), nebo čtení (stojí 2,5–3,5 s, myš zmizí, reflektor až po zastavení). Pomalejší pružina, méně zvýraznění, závěr zkrácen z 11 na 5,5 s.

- **17. 10. 2026 (noc):** průchod v2: nový návrh 9 kapitol podle workflow předsedy, kamera za myší, logo a SFX jako v hooku, přirozený klik, QR kód, srozumitelné plátno (notebook + plátno s panelem vedle PACS).

- **17. 10. 2026 (večer):** hook hotový a upravený podle zpětné vazby (0:05 a 0:07 bez SFX, „switch“ na dosednutí kříže), průchod hotový (10 kapitol). Písma lokálně kvůli výpadkům sítě. Finální render obou filmů s hudbou i bez.

- **17. 10. 2026:** průzkum hotový, scénář sepsaný, hudba vybraná a změřená, projekt Remotion založený. Další krok: snímání aplikace a scény hooku.
