#!/usr/bin/env bash
# One-shot database backup for the offline/local production stack (Phase M9).
# Dumps the running Postgres container to data/backups/ as a gzipped SQL file and
# prunes dumps older than the retention window. Safe to run any time; also the
# thing to wire into host cron if you prefer scheduling on the host over the
# built-in backup sidecar.
#
# Usage:  scripts/backup.sh
# Cron (daily at 02:00), from the repo root:
#   0 2 * * * cd /path/to/Stock_Tracker && scripts/backup.sh >> data/backups/backup.log 2>&1
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker-compose.prod.yml"
ENV_FILE="$REPO_ROOT/deployment/.env.prod"
BACKUP_DIR="$REPO_ROOT/data/backups"
configured_retention="$(awk -F= '$1 == "BACKUP_RETENTION_DAYS" {print $2}' "$ENV_FILE" | tail -n 1 | tr -d '[:space:]\"')"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-${configured_retention:-120}}"

mkdir -p "$BACKUP_DIR"

ts="$(date +%Y%m%d-%H%M%S)"
out="$BACKUP_DIR/stock_tracker-$ts.sql.gz"
media_out="$BACKUP_DIR/stock_tracker-media-$ts.tar.gz"

echo "[backup] dumping database -> $out"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
  pg_dump --clean --if-exists -U "${POSTGRES_USER:-stock_tracker}" "${POSTGRES_DB:-stock_tracker}" \
  | gzip > "$out"

# Fail loudly on an empty/truncated dump rather than keeping a useless file.
if [ ! -s "$out" ]; then
  echo "[backup] ERROR: dump is empty, removing $out" >&2
  rm -f "$out"
  exit 1
fi

echo "[backup] ok ($(du -h "$out" | cut -f1)): $out"
echo "[backup] archiving uploaded files -> $media_out"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
  tar -czf - -C /app/media . > "$media_out"
if ! tar -tzf "$media_out" >/dev/null; then
  echo "[backup] ERROR: media archive is invalid, removing $media_out" >&2
  rm -f "$media_out"
  exit 1
fi
echo "[backup] media ok ($(du -h "$media_out" | cut -f1)): $media_out"
echo "[backup] pruning dumps older than ${RETENTION_DAYS} days"
find "$BACKUP_DIR" -name 'stock_tracker-*.sql.gz' -type f -mtime "+${RETENTION_DAYS}" -delete
find "$BACKUP_DIR" -name 'stock_tracker-media-*.tar.gz' -type f -mtime "+${RETENTION_DAYS}" -delete
echo "[backup] done"
