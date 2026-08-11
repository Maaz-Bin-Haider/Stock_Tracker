#!/usr/bin/env bash
# Restore uploaded invoice/attachment files from a paired media backup.
# This overlays the archive onto the persistent media volume; it does not delete
# unrelated files already present. Use the archive with the same timestamp as the
# database backup restored by scripts/restore.sh.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker-compose.prod.yml"
ENV_FILE="$REPO_ROOT/deployment/.env.prod"

if [ "$#" -ne 1 ]; then
  echo "Usage: scripts/restore-media.sh <path-to-stock_tracker-media-*.tar.gz>" >&2
  exit 2
fi

MEDIA_BACKUP="$1"
if [ ! -f "$MEDIA_BACKUP" ]; then
  echo "[restore-media] ERROR: file not found: $MEDIA_BACKUP" >&2
  exit 1
fi

if ! tar -tzf "$MEDIA_BACKUP" >/dev/null; then
  echo "[restore-media] ERROR: archive is invalid: $MEDIA_BACKUP" >&2
  exit 1
fi

echo "About to restore uploaded files from '$MEDIA_BACKUP'."
printf "Type 'yes' to continue: "
read -r reply
if [ "$reply" != "yes" ]; then
  echo "[restore-media] aborted."
  exit 1
fi

echo "[restore-media] extracting into the persistent media volume"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
  tar -xzf - -C /app/media < "$MEDIA_BACKUP"
echo "[restore-media] done. Reload the app and verify uploaded files."
