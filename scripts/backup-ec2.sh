#!/usr/bin/env bash
# Create and validate a matched EC2 PostgreSQL/uploaded-media backup pair.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker-compose.ec2.yml"
ENV_FILE="$REPO_ROOT/deployment/.env.ec2"
BACKUP_DIR="$REPO_ROOT/data/backups"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing $ENV_FILE" >&2
  exit 1
fi

env_value() {
  local name="$1" default="$2" value
  value="$(awk -F= -v key="$name" '$1 == key {sub(/^[^=]*=/, ""); print}' "$ENV_FILE" | tail -n 1 | tr -d '\r')"
  printf '%s' "${value:-$default}"
}

DB_NAME="$(env_value POSTGRES_DB stock_tracker)"
DB_USER="$(env_value POSTGRES_USER stock_tracker)"
RETENTION_DAYS="$(env_value BACKUP_RETENTION_DAYS 120)"

mkdir -p "$BACKUP_DIR"
umask 077

stamp="$(date +%Y%m%d-%H%M%S)"
container_sql="/tmp/stock_tracker-$stamp.sql"
container_gzip="$container_sql.gz"
container_media="/tmp/stock_tracker-media-$stamp.tar.gz"
database_output="$BACKUP_DIR/stock_tracker-$stamp.sql.gz"
media_output="$BACKUP_DIR/stock_tracker-media-$stamp.tar.gz"
pair_complete=0

cleanup() {
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
    rm -f "$container_sql" "$container_gzip" >/dev/null 2>&1 || true
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
    rm -f "$container_media" >/dev/null 2>&1 || true
  if [ "$pair_complete" -ne 1 ]; then
    rm -f "$database_output" "$media_output"
  fi
}
trap cleanup EXIT

echo "[backup] creating database archive"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
  pg_dump --clean --if-exists -U "$DB_USER" "$DB_NAME" --file="$container_sql"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
  gzip -f "$container_sql"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
  gzip -t "$container_gzip"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" cp \
  "postgres:$container_gzip" "$database_output"
gzip -t "$database_output"

echo "[backup] creating uploaded-media archive"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
  tar -czf "$container_media" -C /app/media .
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
  tar -tzf "$container_media" >/dev/null
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" cp \
  "backend:$container_media" "$media_output"

if ! tar -tzf "$media_output" >/dev/null; then
  echo "ERROR: media validation failed; removing the incomplete backup pair." >&2
  rm -f "$database_output" "$media_output"
  exit 1
fi

chmod 600 "$database_output" "$media_output"
if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ] && id "$SUDO_USER" >/dev/null 2>&1; then
  chown "$SUDO_USER:$SUDO_USER" "$database_output" "$media_output"
fi
pair_complete=1
find "$BACKUP_DIR" -name 'stock_tracker-*.sql.gz' -type f -mtime "+$RETENTION_DAYS" -delete
find "$BACKUP_DIR" -name 'stock_tracker-media-*.tar.gz' -type f -mtime "+$RETENTION_DAYS" -delete

echo "[backup] complete"
echo "$database_output"
echo "$media_output"
