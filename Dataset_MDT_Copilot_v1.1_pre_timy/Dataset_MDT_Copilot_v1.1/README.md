# Dataset MDT Copilot – Rakathon 2026

Dataset k soutěžnímu zadání **MDT Copilot – asistovaná interpretace pro multidisciplinární onkologické konzilium**
(Asseco Central Europe). Slouží jako podklad pro návrh a prototyp řešení.

> **Všechna data jsou fiktivní.** Pacienti, lékaři, nálezy i klinické studie byly vytvořeny pro hackathon a neodpovídají
> žádné skutečné osobě ani studii. Data **nebyla klinicky ověřena** a nesmí se použít pro péči o pacienty.
> Výtahy z doporučených postupů jsou zjednodušené parafráze, ne oficiální doporučení.

## Pacienti

| ID | Diagnóza | Otázka pro MDT (zkráceně) | Datum MDT |
|---|---|---|---|
| **P01** | Karcinom levého prsu HR+/HER2-low, jaterní a kostní metastázy | Progrese po 1. linii IA + CDK4/6 – jaká další linie, vhodnost pro studii? | 2026-10-21 |
| **P02** | Karcinom pravého prsu HER2+, plicní metastázy, nově mozkové metastázy | Lokální léčba mozkových metastáz a pokračování anti-HER2, nebo změna linie? | 2026-10-14 |
| **P03** | Karcinom sigmatu s jaterními metastázami | Resekabilita jaterních metastáz po konverzní chemoterapii | 2026-10-21 |
| **P04** | Adenokarcinom plic, stadium III (single-station N2) | Resekce po neoadjuvantní chemoimunoterapii, nebo chemoradioterapie? Operabilita? | 2026-10-21 |
| **P05** | Karcinom pravého prsu HR+/HER2-low, mnohočetné metastázy, varianta BRCA2 v nádoru | Ve studii s PARP inhibitorem parciální odpověď, ale opakovaná anémie G3 – pokračovat se sníženou dávkou, nebo změnit léčbu? Germinální BRCA2? | 2026-10-21 |
| **P06** | Karcinom levého prsu HER2+, plicní ložiska nejasného původu, nádor pravé ledviny | Smíšená odpověď – je rostoucí plicní ložisko metastáza, nebo druhý nádor? Rebiopsie, pokračování anti-HER2 léčby, pořadí řešení ledviny | 2026-10-21 |

Každý pacient má nominaci na MDT s konkrétní otázkou, předchozí záznam MDT, lékařské zprávy, patologii, popisy CT/MR/PET
s rozměry lézí, laboratoř s trendem nádorových markerů, výkonnostní stav, biomarkery, medikaci a dvě vyplnění
pacientského dotazníku. **Do dat jsou záměrně vloženy nesrovnalosti a chybějící údaje** – jejich nalezení je součástí úlohy.

## Struktura

```
README.md                                tento soubor
pacienti/Pxx/Pxx_bundle.json             FHIR R4 Bundle (collection) – kompletní pacient
pacienti/Pxx/Pxx_pacient.md              tentýž pacient jako čitelný text (s ID zdrojů)
fhir/bundles.ndjson                      všechny bundly pacientů, jeden na řádek (hromadný import)
dotaznik/dotaznik_PROMs.md               pacientský dotazník – popis otázek a škál
dotaznik/dotaznik_PROMs_Questionnaire.json   FHIR Questionnaire
guidelines/*.md                          výtahy z doporučených postupů s číslovanými pasážemi (pro RAG)
studie/studie.md | studie.json           6 fiktivních otevřených klinických studií s kritérii
studie/studie_ResearchStudy_bundle.json  totéž jako FHIR ResearchStudy + Group
ground_truth/Pxx_ground_truth.json       referenční řešení – klíčová fakta, red flags, chybějící údaje, RECIST, studie
ground_truth/PREHLED.md                  přehled referenčního řešení
```

`Pxx_pacient.md` a `Pxx_bundle.json` mají stejný obsah. Pro čtení a orientaci použijte `.md`, strojově pracujte s FHIR.
Každý záznam v `.md` nese ID zdroje v hranatých závorkách (např. `[P03-img02]`), které odpovídá `id` zdroje ve FHIR –
to je klíč pro dohledatelnost (citace) tvrzení AI.

## Pokrytí zadání (kap. 4 „Dodaná data“)

| Položka zadání | Kde v datasetu |
|---|---|
| Mock data eZdraví (zprávy, laboratoř s trendy onkomarkerů, popisy CT/MRI, léky) | FHIR `DocumentReference`, `DiagnosticReport`, `ImagingStudy`, `Observation`, `MedicationRequest`, `MedicationAdministration`, `Procedure` |
| Pacientský dotazník (PROMs), ≥ 2 vyplnění v čase | `QuestionnaireResponse` (2× na pacienta), definice v `dotaznik/` |
| Nominace na MDT (odesílající lékař, otázka, důvod, předchozí závěry) | `ServiceRequest` + `Task` (stav žádanky), předchozí `Composition` „Záznam MDT“ + `CarePlan` + `CareTeam` |
| Výtah z doporučených postupů s číslovanými pasážemi | `guidelines/` |
| 3–5 fiktivních klinických studií s kritérii | `studie/` (6 studií) |
| 3–5 scénářů s různými nádory, záměrné nesrovnalosti, ground truth | 6 pacientů, `ground_truth/` |
| Kódování podle standardů | MKN-10, ICD-O-3, LOINC (laboratoř, typy dokumentů, ECOG), ATC (léky), DICOM modality |
| BONUS: přepis diskuse MDT | není součástí datasetu |

## FHIR – co kde najdete

| Zdroj | Obsah |
|---|---|
| `Patient` | fiktivní pacient, jen rok narození, věk k datu MDT v extension |
| `Condition` | diagnózy (MKN-10), morfologie a topografie ICD-O-3 v extension, TNM v `stage`; komorbidity s `category` „komorbidita“ |
| `DocumentReference` | lékařské zprávy; plný text v `content.attachment.data` (base64, UTF-8); oddělení v `category` |
| `DiagnosticReport` | patologie (`category` SP), zobrazení (`category` RAD, vazba na `ImagingStudy`), laboratorní panel (`category` LAB); text v `presentedForm` |
| `Observation` | laboratoř (LOINC, jednotky UCUM, referenční meze), ECOG hodnocený lékařem (LOINC 89247-1), hmotnost, biomarkery, TNM, toxicita |
| `MedicationRequest` | chronická medikace (ATC) |
| `MedicationAdministration` | jednotlivá podání protinádorové léčby |
| `Procedure` | výkony, radioterapie |
| `QuestionnaireResponse` | odpovědi pacienta na dotazník `MDT-PROMS-1` |
| `ServiceRequest` + `Task` | nominace (žádanka) na MDT – otázka v `reasonCode.text`, typ projednání v `code`, podklady v `supportingInfo`, stav žádanky v `Task.businessStatus`, plánovaný termín v `Task.restriction.period` |
| `Composition` „Záznam MDT“ | předchozí zasedání MDT – sekce Projednaná otázka, Klinické zhodnocení, Doporučený postup, Závěr…; `CarePlan` (doporučení), `CareTeam` (účastníci/odbornosti) |
| `Composition` „Rozhodnutí o léčbě“ | rozhodnutí ošetřujícího lékaře navazující na MDT vč. stanoviska pacienta |

Lokální číselníky (typ projednání, typ klinické otázky, léčebný záměr, modalita, stav žádanky) mají systém
`https://rakathon.example.org/fhir/CodeSystem/...` – jde o ilustrační číselníky pro hackathon.

**Adresy `https://rakathon.example.org/...` nejsou odkazy ke stažení.** FHIR vyžaduje, aby kódy, identifikátory,
rozšíření (`extension`) a záznamy v bundlu měly jednoznačné jméno ve tvaru URI (`system`, `url`, `fullUrl`).
Tyto adresy slouží jen jako takové jméno – stejně jako `http://loinc.org` u kódů LOINC. Na adrese nic není a nic se z ní
nenačítá; doména `example.org` je vyhrazená pro příklady. Všechna data jsou v souborech datasetu a odkazy mezi záznamy
(např. `Patient/P03`) se dohledávají uvnitř bundlu.

Text zprávy z bundlu:

```python
import json, base64
b = json.load(open("pacienti/P03/P03_bundle.json", encoding="utf-8"))
for e in b["entry"]:
    r = e["resource"]
    for a in [c["attachment"] for c in r.get("content", [])] + r.get("presentedForm", []):
        print(r["id"], r.get("date") or r.get("effectiveDateTime"), base64.b64decode(a["data"]).decode("utf-8")[:200])
```

## Co dataset neobsahuje

- **Obrazová data (DICOM).** Jen textové popisy vyšetření s rozměry lézí.
- **Jména a identifikátory.** Lékaři jsou uvedeni kódem (`LEK-P03-01`) a odborností, pacienti jen ID.
- **Standardizované dotazníky v originálním znění** (EORTC QLQ-C30, PRO-CTCAE) – jsou chráněné licencí; dataset používá vlastní krátký
  dotazník se stejnými tematickými oblastmi.
- **Přepis diskuse MDT** (bonus zadání).

## Ground truth

Referenční řešení pro hodnocení a pro vlastní evaluaci týmů (kontrolní sada). Obsahuje u každého pacienta:
časovou osu, klíčová fakta, očekávané red flags se závažností, chybějící údaje a očekávanou reakci AI,
otázky k diskusi, výpočet RECIST, vyhodnocení všech studií po kritériích a relevantní pasáže guidelines.
Každá položka odkazuje na ID zdrojů ve FHIR.

*Organizátor může ground truth soutěžícím zpřístupnit až po odevzdání řešení.*

## Kontakt

Dotazy k datům a zadání: monitor zadání a mentoři Rakathonu. Najdete-li v datech cokoli, co působí jako skutečný osobní údaj,
nahlaste to organizátorům.
