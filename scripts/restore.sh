#!/usr/bin/env bash
# Restore the offline/local production database from a backup produced by
# scripts/backup.sh or the backup sidecar (Phase M9).
#
# DESTRUCTIVE: this overwrites the current database with the contents of the dump
# (the dumps are taken with --clean --if-exists, so existing objects are dropped
# and recreated). You are asked to confirm before anything happens.
#
# Usage:  scripts/restore.sh data/backups/stock_tracker-YYYYmmdd-HHMMSS.sql.gz
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker-compose.prod.yml"
ENV_FILE="$REPO_ROOT/deployment/.env.prod"

if [ "$#" -ne 1 ]; then
  echo "Usage: scripts/restore.sh <path-to-backup.sql.gz>" >&2
  echo "Available backups:" >&2
  ls -1t "$REPO_ROOT"/data/backups/stock_tracker-*.sql.gz 2>/dev/null >&2 || echo "  (none found)" >&2
  exit 2
fi

BACKUP_FILE="$1"
if [ ! -f "$BACKUP_FILE" ]; then
  echo "[restore] ERROR: file not found: $BACKUP_FILE" >&2
  exit 1
fi

DB="${POSTGRES_DB:-stock_tracker}"
USER="${POSTGRES_USER:-stock_tracker}"

echo "About to RESTORE '$BACKUP_FILE' into database '$DB'."
echo "This OVERWRITES all current data. This cannot be undone."
printf "Type 'yes' to continue: "
read -r reply
if [ "$reply" != "yes" ]; then
  echo "[restore] aborted."
  exit 1
fi

echo "[restore] stopping app services (backend, worker) to drop live connections"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop backend worker

echo "[restore] loading dump into '$DB'"
gunzip -c "$BACKUP_FILE" \
  | docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
      psql -v ON_ERROR_STOP=1 -U "$USER" "$DB"

echo "[restore] restarting app services"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" start backend worker

echo "[restore] done. Verify the app, then confirm the data looks correct."
