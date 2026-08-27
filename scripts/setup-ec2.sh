#!/usr/bin/env bash
# One-time guarded setup for Ubuntu 24.04 ARM64 on AWS EC2.
# Run from the repository: sudo scripts/setup-ec2.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/deployment/docker-compose.ec2.yml"
ENV_FILE="$REPO_ROOT/deployment/.env.ec2"
ADMIN_USER="${SUDO_USER:-ubuntu}"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run with sudo: sudo scripts/setup-ec2.sh" >&2
  exit 1
fi
if [ "$ADMIN_USER" = "root" ] || ! id "$ADMIN_USER" >/dev/null 2>&1; then
  echo "ERROR: run this script through sudo from the Ubuntu administration account." >&2
  exit 1
fi
if [ "$(uname -m)" != "aarch64" ]; then
  echo "ERROR: this deployment is approved for ARM64 t4g; found $(uname -m)." >&2
  exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: generate $ENV_FILE first:" >&2
  echo "  scripts/generate-ec2-env.sh ELASTIC_IP LETSENCRYPT_EMAIL" >&2
  exit 1
fi
"$REPO_ROOT/scripts/check-ec2-frontend-security.sh"
if [ ! -s "/home/$ADMIN_USER/.ssh/authorized_keys" ]; then
  echo "ERROR: /home/$ADMIN_USER/.ssh/authorized_keys is empty; refusing to harden SSH and risk lockout." >&2
  exit 1
fi

env_value() {
  local name="$1" value
  value="$(awk -F= -v key="$name" '$1 == key {sub(/^[^=]*=/, ""); print}' "$ENV_FILE" | tail -n 1 | tr -d '\r')"
  printf '%s' "$value"
}

ELASTIC_IP="$(env_value ELASTIC_IP)"
LETSENCRYPT_EMAIL="$(env_value LETSENCRYPT_EMAIL)"
if [ -z "$ELASTIC_IP" ] || [ -z "$LETSENCRYPT_EMAIL" ]; then
  echo "ERROR: ELASTIC_IP and LETSENCRYPT_EMAIL are required in $ENV_FILE." >&2
  exit 1
fi

echo "[host] installing Docker Engine, Compose, Fail2ban, and certificate tooling"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl fail2ban openssl python3-venv unattended-upgrades
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' \
  "$(dpkg --print-architecture)" "$VERSION_CODENAME" > /etc/apt/sources.list.d/docker.list
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
usermod -aG docker "$ADMIN_USER"

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
systemctl enable --now apt-daily.timer apt-daily-upgrade.timer

# A small swap file keeps a native ARM Next.js production build from exhausting
# the t4g.medium's 4 GB RAM. Runtime data remains on the encrypted EBS volume.
if [ "$(swapon --show --noheadings | wc -l)" -eq 0 ]; then
  echo "[host] creating a 2 GB swap file for build headroom"
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  printf '/swapfile none swap sw 0 0\n' >> /etc/fstab
fi

echo "[security] enforcing key-only public SSH and verbose authentication logging"
cat > /etc/ssh/sshd_config.d/99-stock-tracker-hardening.conf <<EOF
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
AuthenticationMethods publickey
AllowUsers $ADMIN_USER
MaxAuthTries 3
LoginGraceTime 30
AllowAgentForwarding no
AllowTcpForwarding no
X11Forwarding no
PermitTunnel no
LogLevel VERBOSE
SyslogFacility AUTH
EOF
/usr/sbin/sshd -t
systemctl reload ssh

cat > /etc/fail2ban/jail.d/stock-tracker-ssh.local <<'EOF'
[sshd]
enabled = true
backend = systemd
port = ssh
maxretry = 5
findtime = 10m
bantime = 1h
EOF
systemctl enable --now fail2ban
fail2ban-client reload

echo "[tls] installing Certbot 5.4+ in an isolated environment"
if [ ! -x /opt/certbot/bin/certbot ]; then
  python3 -m venv /opt/certbot
fi
/opt/certbot/bin/pip install --upgrade pip
/opt/certbot/bin/pip install --upgrade 'certbot>=5.4,<6'
install -d -m 0755 /var/www/stock-tracker-certbot /etc/letsencrypt

echo "[application] building services sequentially for predictable memory use"
export COMPOSE_PARALLEL_LIMIT=1
NGINX_CONFIG_FILE=ec2-bootstrap.conf docker compose \
  -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

echo "[application] waiting for Django migrations and health"
backend_ready=0
for _attempt in $(seq 1 90); do
  if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
    python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health/', timeout=3)" \
    >/dev/null 2>&1; then
    backend_ready=1
    break
  fi
  sleep 2
done
if [ "$backend_ready" -ne 1 ]; then
  echo "ERROR: backend did not become healthy within three minutes." >&2
  docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps >&2
  exit 1
fi

echo "[freshness] refusing setup if users or business data already exist"
fresh_check="from apps.accounts.models import User; from apps.attachments.models import FileAttachment; from apps.inventory.models import StockLedgerEntry; from apps.masterdata.models import Customer, Supplier; from apps.products.models import Product; from apps.purchases.models import Purchase; from apps.sales.models import Sale; from apps.shipments.models import Shipment; print(sum(model.objects.count() for model in [User, Product, Supplier, Customer, Purchase, Shipment, Sale, StockLedgerEntry, FileAttachment]))"
fresh_count="$(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
  python manage.py shell -c "$fresh_check" | tail -n 1 | tr -d '[:space:]')"
if ! [[ "$fresh_count" =~ ^[0-9]+$ ]] || [ "$fresh_count" -ne 0 ]; then
  echo "ERROR: database freshness check returned '$fresh_count'. No data was deleted." >&2
  exit 1
fi

echo "[tls] requesting a trusted short-lived certificate for $ELASTIC_IP"
/opt/certbot/bin/certbot certonly \
  --preferred-profile shortlived \
  --webroot \
  --webroot-path /var/www/stock-tracker-certbot \
  --ip-address "$ELASTIC_IP" \
  --cert-name stock-tracker \
  --non-interactive \
  --agree-tos \
  --email "$LETSENCRYPT_EMAIL"

if grep -q '^NGINX_CONFIG_FILE=' "$ENV_FILE"; then
  sed -i 's/^NGINX_CONFIG_FILE=.*/NGINX_CONFIG_FILE=ec2-https.conf/' "$ENV_FILE"
else
  printf '\nNGINX_CONFIG_FILE=ec2-https.conf\n' >> "$ENV_FILE"
fi
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --force-recreate nginx

echo "[tls] installing four-times-daily certificate renewal"
cat > /etc/systemd/system/stock-tracker-cert-renew.service <<EOF
[Unit]
Description=Renew SwissTech Elastic-IP TLS certificate
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/opt/certbot/bin/certbot renew --quiet
ExecStartPost=-/usr/bin/docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T nginx nginx -s reload
EOF

cat > /etc/systemd/system/stock-tracker-cert-renew.timer <<'EOF'
[Unit]
Description=Check SwissTech Elastic-IP TLS certificate four times daily

[Timer]
OnCalendar=*-*-* 00,06,12,18:17:00
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now stock-tracker-cert-renew.timer

echo "[freshness] seeding required master settings only (never demo transactions)"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend python manage.py seed

echo "[admin] create the new production Admin account"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec backend python manage.py create_admin

echo "[backup] creating the first post-Admin backup pair"
"$REPO_ROOT/scripts/backup-ec2.sh"

echo "[verify] running infrastructure checks"
"$REPO_ROOT/scripts/verify-ec2.sh"

echo
echo "EC2 setup complete: https://$ELASTIC_IP"
echo "Sign in as the new Admin, review seeded rates, and create the real users."
echo "Log out and reconnect before using Docker without sudo (group membership changed)."
