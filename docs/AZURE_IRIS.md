# Azure IRIS a druhá AI (T-331)

Připraveno pro syntetický dataset hackathonu. ACI má veřejné porty 1972 a 52773,
FHIR používá HTTP a úložiště není trvalé. Po znovuvytvoření kontejneru spusť
inicializaci a ingest znovu. Živý deployment a gateway vyžadují přístupy uživatele.

## Vytvoření IRIS v ACI

Vyžaduje Azure CLI (`az login` a správné předplatné), existující resource group,
Bash a Python 3. Skript vytváří placený kontejner se 2 CPU / 4 GiB.
Použij nový název; spuštění se jménem existujícího kontejneru může instanci nahradit.

```bash
export AZURE_RESOURCE_GROUP='<resource-group>'
export AZURE_LOCATION=westeurope
export AZURE_CONTAINER_NAME=mdt-iris
# IRIS_PASSWORD nastav přes správce secrets nebo skrytý vstup, nikdy jako literál do historie.
read -r -s -p 'IRIS password: ' IRIS_PASSWORD; echo
export IRIS_PASSWORD
bash WEB_Template/scripts/azure_iris.sh
unset IRIS_PASSWORD
```

Skript používá image `intersystems/irishealth-community:2026.2` (lze změnit přes
`IRIS_IMAGE`). Manifest posílá do Azure přes stdin, heslo není v argumentech
příkazů ani v lokálním souboru. Secret volume obsahuje heslo pro `--password-file`
a druhý soubor `after-start.sh`. `/iris-main -a` spustí po startu IRIS tento skript:
v `%SYS` nastaví `%Service_CallIn` na `Enabled=1`, `AutheEnabled=48` a zavolá
`Security.Users.UnExpireUserPasswords("*")`. Nahrazuje tak konfiguraci `merge.cpf`,
která v čistém ACI image chybí. Nevypisuj deployment manifest ani nezapínej shell tracing / Azure `--debug`.

Pokud bootstrap neproběhne, ruční záloha v Management Portalu:
**System Administration → Security → Services → %Service_CallIn → Enabled**,
autentizace podle hodnoty 48. Bez služby se `iris_init` přes native API nepřipojí.
Při problému s expirací zavolej v terminálu `%SYS`
`do ##class(Security.Users).UnExpireUserPasswords("*")`.

## Připojení backendu

Do ignorovaného `WEB_Template/.env` doplň vlastní údaje (placeholdery níže nejsou hodnoty pro nasazení):

```dotenv
IRIS_HOST=<PUBLIC_IP>
IRIS_PORT=1972
IRIS_NAMESPACE=FHIRSERVER
IRIS_USER=_SYSTEM
IRIS_PASSWORD=<PASSWORD_FROM_SECRET_STORE>
FHIR_BASE_URL=http://<PUBLIC_IP>:52773/fhir/r4
```

Oba Compose soubory nyní respektují tyto proměnné. Po úpravě `.env` backend
znovu vytvoř, pouhý restart nezmění prostředí. Lokální služba `iris` zůstává
v Compose jako závislost; při práci s ACI ji lze vynechat pomocí `--no-deps`
po spuštění databáze a Redis:

```bash
cd WEB_Template
docker compose -f docker-compose.dev.yml up -d db redis
docker compose -f docker-compose.dev.yml up -d --build --no-deps --force-recreate backend
docker compose -f docker-compose.dev.yml exec backend python manage.py iris_init
docker compose -f docker-compose.dev.yml exec backend python manage.py ingest_dataset
docker compose -f docker-compose.dev.yml exec backend python manage.py iris_check
```

`iris_init` idempotentně vytvoří namespace `FHIRSERVER`, endpoint `/fhir/r4`
a Device aplikace. Pro první kontrolu bez embeddingů lze ingest spustit s
`--patients P03 --skip-vectors`; před generováním podkladu je nutný plný ingest
včetně vektorů. Embeddingy dál určuje primární `AI_PROVIDER` (mock nebo Gemini).
Při spuštění Pythonu mimo Docker musíš proměnné z `.env` exportovat do procesu;
Django samo `WEB_Template/.env` nenačítá.

## Zapnutí ověřovatele

Do stejného lokálního `.env` nastav:

```dotenv
VERIFIER_PROVIDER=openai
VERIFIER_MODEL=gpt-6-astra
OPENAI_BASE_URL=https://apim-rakathon-q7146n.azure-api.net/openai/v1
OPENAI_API_KEY=<TEAM31_KEY_FROM_SECRET_STORE>
AI_REAL_PATIENT_DATA=False
```

Klíč týmu patří do hlavičky `api-key`. `Authorization: Bearer` tato gateway
nepřijímá. Provider pro uvedenou gateway přeloží `gpt-6-astra` na deployment
`gpt-6-astra-global`; explicitní deployment lze zadat také přímo. Global
deployment používej jen pro syntetická data (D-021). Gateway nabízí také
EU Data Zone deploymenty `gpt-6-luna` a `gpt-6.1-sol`.

Šablony mají `VERIFIER_PROVIDER=off`. Není-li proměnná vůbec nastavena,
klíč OpenAI zapne ověřovatele automaticky. Bez klíče či bez oprávnění pro
nesyntetická data se kontrola vypne; primární provider se nemění. Nastavení
`AI_REAL_PATIENT_DATA=True` nenahrazuje schválení endpointu pro skutečná data.
`VERIFIER_PROVIDER=gemini` vyžaduje `GEMINI_API_KEY` a vhodný `VERIFIER_MODEL`.

Vygeneruj nový podklad (offline demo/cache znovu ověřeno není). Pole
`verifier.status=ok` znamená dokončenou kontrolu, nikoli bezchybnost:
`rejected` zahrnuje nepodložená i nejistá tvrzení. `partial/error` a `unchecked`
ukazují výpadky nebo chybějící verdikty. Tvrzení zůstávají viditelná a zamítnutá
mají `verification=unverified`. Každá dávka má audit `brief.verifier`.
