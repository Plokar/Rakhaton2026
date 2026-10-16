# Dev ground truth (T-013)

Vývojová evaluační sada pro `eval_ground_truth` (T-301, ARCHITEKTURA §5.8): `P01.json` … `P06.json`.

> ⚠️ **Není to oficiální ground truth.** Organizátor ho zveřejní až po odevzdání. Sada vznikla ručně z dat datasetu a z hypotéz v [DATASET.md §9](../../DATASET.md#9-vložené-nesrovnalosti--pracovní-hypotézy-týmu). Barvy semaforu jsou převzaté z [docs/POZADAVKY_LEKARE.md §5.4](../../docs/POZADAVKY_LEKARE.md#54-očekávané-barvy-pro-demo-podklad-pro-dev-ground-truth-t-013). **Nesmí se odvozovat z výstupu aplikace** (pravidel ani LLM), jinak by eval měřil sám sebe.

## Formát

Model, načtení a validace jsou v `WEB_Template/backend/services/eval/ground_truth.py` (`load()`, pydantic `PatientGroundTruth`). Struktura odpovídá ohlášenému oficiálnímu ground truth (README datasetu): kdyby přišel, stačí přepnout `--gt`.

| Klíč | Obsah |
|---|---|
| `mdt_question`, `mdt_date` | otázka pro MDT (`ServiceRequest`) a datum zasedání |
| `timeline` | klíčové události s citacemi |
| `key_facts` | fakta, která má podklad obsahovat (pokrytí faktů) |
| `red_flags` | pravidlo `RF-*` (ARCH §5.4), závažnost, `importance` (`key` = hlavní nález datasetu, `secondary` = konvence týmu nebo vedlejší), ≥ 2 citace, pasáž guidelines (nebo `basis`, když pasáž není) |
| `missing_data` | co chybí, `field` = `IntakeField.id` (ARCH §8.6), `required_by`, očekávaná reakce AI („Údaj chybí…“) |
| `ai_uncertainty` | NEJISTOTA AI (FR-R5), např. rozmezí ECOG |
| `discussion_questions` | 2–3 otázky k diskusi |
| `recist` | výchozí, nadir, aktuální součet, změna v %, nové léze, odpověď (nebo `recist_note`, když hodnotit nelze) |
| `trials` | všech 6 studií; u relevantních (diagnóza + RKT-05 + RKT-06, ARCH §5.5) kritéria `met` / `not_met` / `unknown` s citací, u `unknown` co dodat |
| `guideline_passages` | relevantní pasáže guidelines |
| `compatibility` | celé možnosti léčby se semaforem (P03, P04 podle POZADAVKY §5.4) |
| `compatibility_rules` | jednotlivá pravidla semaforu, kde katalog (POZADAVKY §5.3, sloupec Dataset) uvádí barvu |
| `new_findings` | nálezy nad rámec DATASET §9 |

## Pravidla pro eval (T-301)

- **Citace se porovnávají na úrovni zdroje:** `P03-img03#2` = `P03-img03` (`ground_truth.same_source`). Ground truth cituje celé resources.
- **Red flag je nalezený**, když sedí pravidlo (`rule`, nebo některé z `also_rules`) a aspoň jeden citovaný zdroj.
- **`also_acceptable`** u kritérií studií a celkového stavu je obhajitelná alternativa (např. nevyšetřené = `unknown` i `not_met`). Počítá se jako shoda.
- **Recall red flags** měřit zvlášť pro `key` (hlavní metrika) a pro všechny.
- Kritéria vyřazení: `met` = kritérium platí, pacient je vyřazen.

## Kontrola sady

```bash
cd WEB_Template/backend && pytest services/eval      # každé ID existuje v datasetu, pasáže, kritéria, pravidla VS-*, RECIST
```

## Orientační výsledek (16. 10., jen deterministická pravidla `services/rules/red_flags.py`, bez LLM)

Klíčové red flags: **42 / 48**. Chybí rozpory mezi texty dokumentů, které má najít `RF-LLM`:

- P02: „EF v normě“ vs. LVEF 52 %;
- P02: TNM cN2 v záznamu MDT vs. cN1;
- P05: „únava mírná“ vs. 8/10.

A dvě mezery v pravidlech:

- `RF-GENETIC` u P03 (karcinom Lynchova spektra v rodině, OBC-2.4);
- `RF-MISSING` u doporučeného kontrolního echa (P02-doc08, P06-doc10).
