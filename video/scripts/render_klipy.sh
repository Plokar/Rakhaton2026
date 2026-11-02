#!/usr/bin/env bash
# Klipy do prezentace: každá scéna = jedno video (bez hudby, se zvukovými efekty).
set -e
cd "$(dirname "$0")/.."
npx remotion render src/index.ts KlipProjektor out/klipy/04_okno_projektoru.mp4 --log=error
npx remotion render src/index.ts KlipProjektorSvetly out/klipy/04_okno_projektoru_svetly.mp4 --log=error
# ostatní scény vyříznuté z průchodu (snímky podle CHAPTERS v src/walk/timeline.ts)
while read -r name range; do
  npx remotion render src/index.ts MedTeamWalkthrough "out/klipy/${name}.mp4" --frames="$range" --props=props-nobgm.json --log=error
done <<'LIST'
01_rychly_prehled 120-419
02_podklad_podle_odbornosti 420-709
03_otazka_nad_pripadem 710-979
05_jednani_a_platno 1255-1484
06_zdroj_tvrzeni 1485-1724
07_chat_komise 1725-1984
08_ai_zapisovatel 1985-2254
09_zapis_do_iris 2255-2529
LIST
ls -la out/klipy
