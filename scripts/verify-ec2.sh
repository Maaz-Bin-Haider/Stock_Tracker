#!/usr/bin/env bash
# Read-only operational checks plus ledger reconciliation. The reconciliation
# command repairs drift if found and reports it visibly.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker-compose.ec2.yml"
ENV_FILE="$REPO_ROOT/deployment/.env.ec2"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: missing $ENV_FILE" >&2
  exit 1
fi

env_value() {
  local name="$1" value
  value="$(awk -F= -v key="$name" '$1 == key {sub(/^[^=]*=/, ""); print}' "$ENV_FILE" | tail -n 1 | tr -d '\r')"
  printf '%s' "$value"
}

ELASTIC_IP="$(env_value ELASTIC_IP)"
if [ -z "$ELASTIC_IP" ]; then
  echo "ERROR: ELASTIC_IP is missing from $ENV_FILE" >&2
  exit 1
fi

compose=(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE")

echo "[verify] container state"
"${compose[@]}" ps

expected_services=(postgres redis backend worker frontend nginx backup)
for service in "${expected_services[@]}"; do
  container_id="$("${compose[@]}" ps -q "$service")"
  if [ -z "$container_id" ] || [ "$(docker inspect -f '{{.State.Running}}' "$container_id")" != "true" ]; then
    echo "ERROR: $service is not running." >&2
    exit 1
  fi
done

echo "[verify] HTTPS application health"
curl --fail --silent --show-error "https://$ELASTIC_IP/api/v1/health/"
echo

echo "[verify] HTTP redirects to HTTPS"
redirect="$(curl --silent --output /dev/null --write-out '%{http_code}' "http://$ELASTIC_IP/")"
if [ "$redirect" != "301" ]; then
  echo "ERROR: expected HTTP 301, received $redirect." >&2
  exit 1
fi

echo "[verify] certificate is valid for more than 24 hours"
openssl s_client -connect "$ELASTIC_IP:443" -servername "$ELASTIC_IP" </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -checkend 86400

echo "[verify] Django configuration and migrations"
"${compose[@]}" exec -T backend python manage.py check
if "${compose[@]}" exec -T backend python manage.py showmigrations --plan | grep -q '\[ \]'; then
  echo "ERROR: unapplied database migrations found." >&2
  exit 1
fi

echo "[verify] stock ledger reconciliation"
"${compose[@]}" exec -T backend python manage.py rebuild_stock_balances

echo "[verify] certificate renewal timer"
systemctl --no-pager status stock-tracker-cert-renew.timer

echo "[verify] Ubuntu security-update timer"
systemctl is-enabled --quiet apt-daily-upgrade.timer

echo "[verify] latest local backup pair"
latest_database="$(find "$REPO_ROOT/data/backups" -maxdepth 1 -name 'stock_tracker-*.sql.gz' -type f -printf '%f\n' | sort | tail -n 1)"
if [ -z "$latest_database" ]; then
  echo "ERROR: no database backup exists." >&2
  exit 1
fi
stamp="${latest_database#stock_tracker-}"
stamp="${stamp%.sql.gz}"
latest_media="$REPO_ROOT/data/backups/stock_tracker-media-$stamp.tar.gz"
gzip -t "$REPO_ROOT/data/backups/$latest_database"
tar -tzf "$latest_media" >/dev/null
echo "$latest_database"
echo "$(basename "$latest_media")"

echo "[verify] all automated infrastructure checks passed."
echo "Complete the four-role browser/API acceptance checklist in deployment/AWS_EC2_GUIDE.md."
