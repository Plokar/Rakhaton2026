# Podklady k číslům v prezentaci

Každé číslo na slidech, odkud je máme a jak jsme ho spočítali. Čísla bez zdroje do prezentace nepatří.

| Číslo na slidu | Hodnota | Zdroj | Stav ověření |
|---|---|---|---|
| Komise má na pacienta 3–5 minut | 3–5 min | Zadání Rakathon 2026 (Asseco CE) | Ověřeno ze zadání |
| 5 specialistů u stolu | 5 | Zadání (onkolog, chirurg, radiolog, radiační onkolog, patolog) | Ověřeno ze zadání |
| Cíl orientace do 30 sekund | 30 s | Zadání, blok A (orientace v pacientovi) | Ověřeno ze zadání |
| Lékařské minuty na pacienta | 15–25 min | Výpočet: 5 specialistů × 3–5 min | Výpočet z údajů výše |
| 25–42 hodin na 100 případů | 25–42 h | Výpočet: 15–25 min × 100 / 60 | Výpočet |
| Cena hodiny lékaře | 500–680 Kč | ČSÚ 2022: průměrná hrubá mzda lékaře 84 810 Kč/měsíc. 84 810 / 168 h = 505 Kč. Plus odvody zaměstnavatele ~33,8 % (zákonná sazba, náš předpoklad) = 675 Kč | Mzdový údaj z výsledků vyhledávání, tabulku ČSÚ jsme neotevřeli. Ověřit v publikaci ČSÚ |
| Cena času na 100 případů | 12–29 tis. Kč | 25 h × 500 Kč = 12 500; 42 h × 680 Kč = 28 560 | Výpočet z výše uvedených hodnot |
| Nových případů zhoubných novotvarů v ČR (2023) | 65 242 | ČSÚ, Zdravotní stav obyvatelstva (tabulka, zdroj ÚZIS). https://csu.gov.cz/zdravotni-stav-obyvatelstva | Z výsledků vyhledávání. Nevíme, zda zahrnuje nemelanomové kožní nádory a in situ |
| Nových případů měsíčně | cca 5 400 | 65 242 / 12 = 5 437 | Výpočet |
| Incidence ČR 2023 | 599,3 na 100 tis. obyvatel | ČSÚ (tabulka) | Z výsledků vyhledávání |
| Starší celostátní počet (2014) | 82 505 | ÚZIS | Nepoužito, stará metodika |
| Žádanka P04 má 22 374 znaků, 3 477 slov | 22 374 / 3 477 | Syntetický dataset, soubor P04_pacient.md (počítáno lokálně) | Ověřeno |
| Tučných zvýraznění v textu P04 | 25 | Počet dvojic ** v P04_pacient.md (včetně tabulky) | Ověřeno, počítáno přibližně |
| 14 upozornění k údajům | 14 | Screen aplikace (syntetický pacient P04), hlavička | Ověřeno ze screenu |
| 16 údajů na obrazovce | 16 | Screen aplikace. POZOR: jiný screen ukazuje u téže sekce 21 položek | Nejasné. Před použitím ověřit |
| Metaanalýza BMJ 2020: 34 studií, 1,27 mil. pacientů, 13 ze 17 diagnóz | 13 ze 17 | BMJ 2020, https://www.bmj.com/content/371/bmj.m4087 | Z úryvku vyhledávání, článek jsme celý nečetli |
| Přehled MDT (BMC HSR 2020) | — | https://doaj.org/article/8eeaefdf89454fbaada0068cad78c2d8 | Z úryvku |
| UK urologické MDT: 2,6–7,6 min na případ, 10–90 případů týdně | 2,6–7,6 min | https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10705031/ | Z úryvku |
| Indikátory MZ (březen 2026) | — | https://www.mzd.gov.cz/tiskove-centrum-mz/kdyz-data-zachranuji-zivoty-cesko-otevira-prvni-data-o-organizaci-onkologicke-pece-v-oblasti-karcinomu-plic-prsu-a-pankreatu/ | Z tiskové zprávy (úryvek). Obsah indikátorů ověřit |

## Co na slidech NENÍ a proč
- Počet zachráněných životů: nemáme data ani metodu. Na slidech je to výslovně označeno.
- Úspora v korunách za komisi: závisí na datech z pilotu.
- Kontakty, QR kód dema, jména lékařů: nejsou k dispozici.

## Zdroje, které nešly otevřít
Prostředí blokuje tyto domény. Povolit je lze v nastavení prostředí (Allowed domains):
bmjopenrespres.bmj.com, pmc.ncbi.nlm.nih.gov, www.tribune.cz, www.medrxiv.org, czechhta.cz
