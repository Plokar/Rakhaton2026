#!/usr/bin/env bash
# Záloha pilotu MDTcore (T-355, docs/PILOT.md): Postgres (účty, zasedání, závěry, chat) + IRIS (FHIR, vektory,
# zapsané závěry a úkoly). Spouští cron na VPS jednou denně, drží posledních BACKUP_KEEP_DAYS dní.
#
#   WEB_Template/scripts/backup.sh                 # záloha do /var/backups/mdtcore
#   BACKUP_DIR=/mnt/zalohy scripts/backup.sh
#   COMPOSE_FILE=docker-compose.dev.yml scripts/backup.sh   # vyzkoušení na dev stacku
#
# Obnova: viz docs/PILOT.md, „Obnova ze zálohy“.
set -euo pipefail

cd "$(dirname "$0")/.."                                   # WEB_Template (docker-compose.yml, .env)
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/mdtcore}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
STAMP="$(date +%Y-%m-%d_%H%M)"
DEST="$BACKUP_DIR/$STAMP"
dc() { docker compose -f "$COMPOSE_FILE" "$@"; }

mkdir -p "$DEST"
chmod 700 "$BACKUP_DIR"
echo "▶ Záloha MDTcore do $DEST"

# 1) Postgres: logický dump (obnova: pg_restore). Uživatel a DB z .env služby db.
dc exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner' > "$DEST/postgres.dump"
echo "  ✓ Postgres ($(du -h "$DEST/postgres.dump" | cut -f1))"

# 2) IRIS: ExternalFreeze → kopie /durable → ExternalThaw. Zmrazení drží zápisy (sekundy), nic se neztratí.
IRIS_CONTAINER="$(dc ps -q iris)"
freeze() {
  printf 'write ##class(Backup.General).%s()\nhalt\n' "$1" | dc exec -T iris iris session IRIS -U%SYS
}
thaw() { freeze ExternalThaw >/dev/null || true; }
trap thaw EXIT
if ! freeze ExternalFreeze | grep -q '^1'; then
  echo "  ✗ IRIS ExternalFreeze selhal, záloha IRIS se nedělá" >&2
  exit 1
fi
docker run --rm --volumes-from "$IRIS_CONTAINER" -v "$DEST:/backup" alpine \
  tar czf /backup/iris_durable.tgz -C / durable
thaw
trap - EXIT
echo "  ✓ IRIS ($(du -h "$DEST/iris_durable.tgz" | cut -f1))"

# 3) Kontrolní součty a úklid starých záloh
( cd "$DEST" && sha256sum ./* > SHA256SUMS )
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$BACKUP_KEEP_DAYS" -exec rm -rf {} +
echo "✔ Hotovo: $DEST"
