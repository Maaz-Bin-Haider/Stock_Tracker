#!/usr/bin/env bash
# Generate the private EC2 environment file with machine-specific secrets.
# Usage: scripts/generate-ec2-env.sh ELASTIC_IP LETSENCRYPT_EMAIL
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/deployment/.env.ec2"

if [ "$#" -ne 2 ]; then
  echo "Usage: scripts/generate-ec2-env.sh <elastic-ip> <letsencrypt-email>" >&2
  exit 2
fi

ELASTIC_IP="$1"
LETSENCRYPT_EMAIL="$2"

if ! [[ "$ELASTIC_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
  echo "ERROR: '$ELASTIC_IP' is not an IPv4 address." >&2
  exit 1
fi

IFS=. read -r octet1 octet2 octet3 octet4 <<< "$ELASTIC_IP"
for octet in "$octet1" "$octet2" "$octet3" "$octet4"; do
  if ((10#$octet > 255)); then
    echo "ERROR: '$ELASTIC_IP' is not a valid IPv4 address." >&2
    exit 1
  fi
done

if ! [[ "$LETSENCRYPT_EMAIL" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]; then
  echo "ERROR: '$LETSENCRYPT_EMAIL' is not a valid email address." >&2
  exit 1
fi

if [ -e "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE already exists; refusing to overwrite production secrets." >&2
  exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "ERROR: openssl is required to generate secrets." >&2
  exit 1
fi

umask 077
DJANGO_SECRET="$(openssl rand -hex 48)"
DATABASE_PASSWORD="$(openssl rand -hex 32)"
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"

cat > "$ENV_FILE" <<EOF
ELASTIC_IP=$ELASTIC_IP
LETSENCRYPT_EMAIL=$LETSENCRYPT_EMAIL
NGINX_CONFIG_FILE=ec2-bootstrap.conf

DJANGO_SECRET_KEY=$DJANGO_SECRET
DJANGO_ALLOWED_HOSTS=$ELASTIC_IP,localhost,127.0.0.1,backend
DJANGO_CSRF_TRUSTED_ORIGINS=https://$ELASTIC_IP

POSTGRES_DB=stock_tracker
POSTGRES_USER=stock_tracker
POSTGRES_PASSWORD=$DATABASE_PASSWORD

HOST_UID=$HOST_UID
HOST_GID=$HOST_GID
BACKUP_INTERVAL_SECONDS=43200
BACKUP_RETENTION_DAYS=120
EOF

chmod 600 "$ENV_FILE"
echo "Created $ENV_FILE with new EC2-only secrets."
echo "Keep a secure offline copy; never commit this file."
