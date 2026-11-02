# Prezentace MDTcore pro vládu (1 minuta)

Publikovaná verze: https://claude.ai/artifact/WGEfKPE5QQxcHRAWFw1qDM (soukromá, sdílení přes menu Share).

- `deck/`: zdroj slidů (formát Artifact Slides). Obrázky jsou na serveru jako `/_blob/…`, lokální kopie jsou v `images/`.
- Fonty: Montserrat (nadpisy) a Inter (text), stejné jako v aplikaci a ve videu.
- Tagline: „Designed by Doctor, Made by Students“ (úvodní a závěrečný slide).

## Slidy a projev (~60 s, text je i v poznámkách řečníka)

| # | Slide | Co říct |
|---|---|---|
| 1 | Nový standard onkologických komisí | Vážený pane premiére, vážený pane ministře. Jsme tým MDTcore z Rakathonu 2026. Ukážeme vám, jak může každý onkologický pacient dostat rozhodnutí o léčbě dříve. |
| 2 | 65 242 | Každý rok slyší v Česku diagnózu rakovina přes 65 tisíc lidí. O léčbě každého rozhoduje onkologická komise. |
| 3 | Hory papírů | Háček: onkolog musí předtím projít hory papírů, dvanáct normostran na pacienta. Hodiny přípravy místo péče. |
| 4 | Řešení | MDTcore přečte zprávy za lékaře a do minuty připraví přehled. Každý údaj má odkaz na zdroj. Rozhoduje vždy lékař. |
| 5 | Nový standard | Lékařům vrátíme 50 000 hodin ročně, jako 30 onkologů navíc. Dřívější léčba je levnější. |
| 6 | 200–500 životů | Každý měsíc čekání zvyšuje riziko úmrtí o 6–8 %. O týden dřívější komise zachrání podle modelu 200–500 životů ročně. |
| 7 | Pilot | Žádáme o pilot na jedné komisi. Pak nový standard pro celé Česko. |

## Zdroje a výpočty

| Číslo | Zdroj / výpočet | Stav |
|---|---|---|
| 65 242 nových případů (2023), ≈ 180 denně | ČSÚ, Zdravotní stav obyvatelstva (data ÚZIS), C00–C97 bez C44. https://csu.gov.cz/zdravotni-stav-obyvatelstva | Z vyhledávání, tabulka ČSÚ |
| 5 specialistů, 3–5 min na pacienta | Zadání Rakathon 2026 | Ověřeno |
| 12 normostran | Pacient P04 z datasetu: 22 374 znaků / 1 800 | Ověřeno lokálně |
| 4,1 h lékaře na komisi, 84 % nákladů = čas lékařů, 8,2 lékaře a 12,6 případu na komisi | Alexandersson a kol., Acta Oncologica 2018 (50 komisí, Švédsko). https://medicaljournalssweden.se/actaoncologica/article/view/24744 | Z abstraktu |
| Příprava 1,4× delší než jednání | Studie radiologů terciárního centra 2024 (výsledek vyhledávání) | Plný text nečten, ověřit |
| 6–8 % vyšší riziko úmrtí za 4 týdny odkladu | Hanna a kol., BMJ 2020 (34 studií, 1,27 mil. pacientů, chirurgie HR 1,06–1,08). https://www.bmj.com/content/371/bmj.m4087 | Z abstraktu |
| 3,7× dražší léčba pokročilého nádoru | Incisive Health / Cancer Research UK 2014: tlusté střevo, stadium 1 £3 373 vs. stadium 4 £12 519 | Starší údaj z Anglie |
| 50 000 hodin, ≈ 30 úvazků | **Model:** 4,1 h × 8,2 lékaře / 12,6 případu = 2,7 h na případ; × 65 242 = 174 000 h; podíl přípravy 1,4/2,4 = 58 %; příprava zkrácená na polovinu → ≈ 50 000 h; / 1 650 h na úvazek ≈ 30 | Modelový odhad |
| 200–500 životů ročně | **Model:** 1 týden = HR 1,06–1,08^(1/4) = 1,015–1,019 → 27 000 × (1 − 1/HR) ≈ 390–510; dolní mez při zrychlení jen u poloviny pacientů ≈ 200–250 | Modelový odhad |
| ≈ 27 000 úmrtí na rakovinu ročně | ≈ 24 % ze 112 800 zemřelých v ČR 2023 (ČSÚ; podíl zhoubných novotvarů na úmrtích podle ÚZIS za 2014–2018) | Odvozeno, ověřit v ÚZIS |

Na slidech jsou modelové odhady výslovně označené. Pilot je má změřit.

## Prompty na světlé fotky (nahradí tmavé fotky ze staré prezentace)

1. **Úvod (pravá polovina, na výšku 3:4):** „Bright, airy hospital meeting room in daylight, five doctors of different specialties (white coats, scrubs) discussing a case around a round light-wood table with a laptop and a large wall screen showing CT scans, large windows, white and pale blue tones, soft natural light, calm and optimistic, editorial photography, shallow depth of field, no visible text, no logos.“
2. **Hory papírů (na výšku 1:1):** „Tired oncologist in a white coat at a bright white desk buried under tall stacks of paper medical records and folders, daylight from a window, clean minimalist hospital office, white and light grey palette with a hint of blue, realistic editorial photography, no readable text.“
3. **Závěr (pravá třetina, na výšku 3:4):** „Bright minimalist desk split in two: left side a messy pile of paper medical files, right side a clean empty desk with a single tablet showing a simple patient overview, morning sunlight, white and pale blue tones, high-key photography, no readable text, no logos.“

## Slide 7: kolika lidem můžeme pomoci (propočet)

| Obor | Pacientů ročně | Zdroj | Stav |
|---|---|---|---|
| Onkologie (MDT) | 65 242 | ČSÚ 2023, nové zhoubné novotvary bez C44 | Z vyhledávání |
| Cévní mozkové příhody | 23 121 | ÚZIS, hospitalizace s CMP 2021 (via České noviny) | Starší rok, ověřit |
| Kardiochirurgie (Heart Team) | 7 572 | ÚZIS, Národní kardiochirurgický registr 2021 | Starší rok |
| Transplantace | 952 | KST, rekordní rok (datum nejasné, 2019 nebo později) | Ověřit na kst.cz |
| **Součet: rozhodnutí týmu lékařů** | **96 887** | součet | Konzervativní, bez TAVI, PCI, pediatrie aj. |
| Celá nemocnice | 1 296 397 | ČSÚ 2024: 703 503 žen + 592 894 mužů hospitalizovaných v akutní péči | Z vyhledávání |

Animace (x-embed): počítadlo roste po krocích 65 242 → 88 363 → 95 935 → 96 887 → 1 296 397, s každým krokem naskočí ikonka oboru. Export do PPTX/PDF ukáže konečný stav.
