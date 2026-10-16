# Simulovaná diskuse MDT (T-314, pro AI zapisovatele BON-3 / T-305)

Dataset přepis diskuse neobsahuje, proto je tu vlastní simulovaná diskuse komise k demo pacientovi P03 (re-MDT 21. 10. 2026).

| Soubor | Obsah |
|---|---|
| `P03_mdt02_script.json` | **scénář (zdroj pravdy):** mluvčí podle rolí, text, hlasy pro TTS a `expected_decision` (záměr, doporučení, úkoly s vlastníkem a termínem, re-MDT, studie) |
| `P03_mdt02.m4a` | nahrávka 3:01, AAC mono, 1,2 MB (inline do Gemini, limit 20 MB) |
| `P03_mdt02_transcript.json` | referenční přepis ve schématu `Transcript` (`services/ai_service.py`): `speaker`, `start` `MM:SS`, `text`. Časy odpovídají nahrávce. |
| `P03_mdt02.md` | čitelný přepis |
| `tts_generate.py` | generátor (macOS `say` + `afconvert`, jinak stdlib) |

- **Obsah odpovídá datům P03** a `data/dev_ground_truth/P03.json`:
  - PR 83 → 50 mm;
  - chybí CT hrudníku;
  - FLR 38 %, S3, vymizelé S5, S8 u pravé jaterní žíly;
  - bevacizumab 7. 9. (operace od 19. 10.);
  - neuropatie G1 vs. popis pacienta;
  - MMR/MSI nevyšetřeno, otec s karcinomem tlustého střeva;
  - RKT-03.
- **Rozhodnutí v nahrávce je simulace komise (lidé), ne výstup AI.** AI zapisovatel z ní má udělat jen draft `Decision`, který předseda edituje a potvrzuje (ARCH §5.6).
- **Nahrávka je záložní TTS:**
  - hlasy Zuzana (cs) a Laura (sk) se střídají podle mluvčích, role jdou poznat i z obsahu;
  - pro finále je lepší nahrát diskusi lidmi podle `P03_mdt02.md` (2–3 min, každý svou roli);
  - po novém nahrání přepsat `P03_mdt02.m4a` a časy v `P03_mdt02_transcript.json`.
- Po úpravě scénáře přegenerovat: `python3 data/audio/tts_generate.py data/audio/P03_mdt02_script.json`.
- Kontrola (schéma, mluvčí, délka, termíny v pracovní dny, závěr opravdu zazní): `cd WEB_Template/backend && pytest services/eval/test_mdt_audio.py`.
- **Pro T-305:**
  - očekávaný výstup zapisovatele je `expected_decision`;
  - citace segmentů mají tvar `P03-mdt02-prepis#n`, kde n je pořadí úseku od 1;
  - v testech lze referenční přepis zaregistrovat jako odpověď mocku: `MockAIProvider(responses={"Transcript": …})`.
