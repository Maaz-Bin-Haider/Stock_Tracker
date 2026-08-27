#!/usr/bin/env bash
# Restore a matched EC2 database/media pair. Destructive and explicitly guarded.
# Usage: scripts/restore-ec2.sh DB_BACKUP.sql.gz MEDIA_BACKUP.tar.gz
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker-compose.ec2.yml"
ENV_FILE="$REPO_ROOT/deployment/.env.ec2"

if [ "$#" -ne 2 ]; then
  echo "Usage: scripts/restore-ec2.sh <database.sql.gz> <media.tar.gz>" >&2
  exit 2
fi

DATABASE_BACKUP="$1"
MEDIA_BACKUP="$2"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing $ENV_FILE" >&2
  exit 1
fi
if [ ! -f "$DATABASE_BACKUP" ] || ! gzip -t "$DATABASE_BACKUP"; then
  echo "ERROR: missing or invalid database archive: $DATABASE_BACKUP" >&2
  exit 1
fi
if [ ! -f "$MEDIA_BACKUP" ] || ! tar -tzf "$MEDIA_BACKUP" >/dev/null; then
  echo "ERROR: missing or invalid media archive: $MEDIA_BACKUP" >&2
  exit 1
fi

env_value() {
  local name="$1" default="$2" value
  value="$(awk -F= -v key="$name" '$1 == key {sub(/^[^=]*=/, ""); print}' "$ENV_FILE" | tail -n 1 | tr -d '\r')"
  printf '%s' "${value:-$default}"
}

DB_NAME="$(env_value POSTGRES_DB stock_tracker)"
DB_USER="$(env_value POSTGRES_USER stock_tracker)"

echo "Database: $DATABASE_BACKUP"
echo "Media:    $MEDIA_BACKUP"
echo "This will overwrite the current database and uploaded files."
printf "Type RESTORE to continue: "
read -r confirmation
if [ "$confirmation" != "RESTORE" ]; then
  echo "[restore] aborted."
  exit 1
fi

echo "[restore] stopping application and backup writers"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop nginx backend worker backup

echo "[restore] loading PostgreSQL dump"
gunzip -c "$DATABASE_BACKUP" | \
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
    psql -v ON_ERROR_STOP=1 -U "$DB_USER" "$DB_NAME"

echo "[restore] replacing uploaded media with the paired archive"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm --no-deps -T backend \
  sh -c 'find /app/media -mindepth 1 -delete && tar -xzf - -C /app/media' \
  < "$MEDIA_BACKUP"

echo "[restore] restarting the full stack"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
echo "[restore] complete; run scripts/verify-ec2.sh and inspect the application."
