# PowerPoint verze prezentace

- `MDTcore_vlada.pptx`: 8 slidů, 16:9, poznámky řečníka, prolínací přechody a automatické animace.
- `fonty_MDTcore.zip` (nebo složka `fonty/`): Montserrat, Montserrat ExtraBold a Inter. **Před otevřením nainstalujte na počítač, ze kterého se bude promítat** (Windows: rozbalit, označit všechny .ttf → pravé tlačítko → Instalovat pro všechny uživatele; Mac: dvojklik → Instalovat). Bez nich PowerPoint použije náhradní písmo.
- Licence fontů: SIL Open Font License (Google Fonts).

## Animace (spouštějí se samy po zobrazení slidu, není potřeba klikat)
1. Logo, podtitul, štítek a loga partnerů postupně naskočí.
2. Číslo 65 242 vyskočí, pak text a karty.
3. Nadpis vyjede, karty 12 a 4,1 h naskočí.
4. Screenshot naskočí, body 01–04 vyjíždějí po sobě.
5. Tři řádky s čísly naskočí po sobě.
6. 200–500 vyskočí, pak věta a výpočet po částech.
7. Ikonky oborů naskakují a poskočí, číslo vlevo se mění 65 242 → 88 363 → 95 935 → 96 887 → 1 296 397 (asi 7 s).
8. Nadpis, text, tagline a loga.

V editoru se na slidu 7 čísla kreslí přes sebe, protože se při promítání střídají. Úprava: Animace → Podokno animací.

## Sestavení znovu
`build/`: `node icons.js`, `node build.js`, `python3 animate.py MDTcore_vlada_raw.pptx MDTcore_vlada.pptx` (potřebuje pptxgenjs, sharp a obrázky v `img/`).
