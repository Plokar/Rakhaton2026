# Ukázkové soubory pro „Nový pacient“ z FHIR JSON (T-335)

Fiktivní data, jen pro vyzkoušení importu. V aplikaci: zasedání → **Zařadit** → **Nový pacient** →
**Nahrát FHIR JSON** (lze vybrat víc souborů najednou, k bundlu i přepis `.md`).

| Soubor | Co ukazuje |
|---|---|
| `../dataset_test/pacienti/P07/P07_bundle.json` … `P12` | bundle jednoho pacienta ve formátu datasetu (bez RČ, RČ je při importu nepovinné) |
| `dva_pacienti_P10_P11.json` | jeden soubor se dvěma pacienty → návrh pro každého, sdílená organizace a lékaři u obou |
| `obecny_export_uuid.json` | export mimo konvenci datasetu (UUID, reference `urn:uuid:`) → ID se přečíslují podle konvence (`Pnn-dg1`, `Pnn-ecog01`…) |
| `../../Dataset_MDT_Copilot_v1.1_pre_timy/Dataset_MDT_Copilot_v1.1/pacienti/P01/P01_bundle.json` + `P01_pacient.md` | bundle s přepisem: přepis se zkontroluje proti bundlu (pohlaví, rok narození, diagnózy, otázka); řádek `**RČ:** …` v přepisu doplní RČ |

Co import dělá: sanitizace jako ingest datasetu (`_` v ID → `-`, prázdné hodnoty pryč), přečíslování na volné
`Pnn`, kontrola referencí (odkaz mimo soubor musí být v IRIS), RČ proti pohlaví a roku narození, nominace
předvyplněná ze strukturovaných dat s citací ID resource. Diagnózy, TNM a ECOG ze souboru se v aplikaci jen
zobrazí (opravují se v souboru), otázku pro MDT jde upravit. Do IRIS se nic nezapíše, dokud lékař návrh nepotvrdí.
