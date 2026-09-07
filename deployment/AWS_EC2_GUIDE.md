# AWS EC2 deployment guide — Elastic IP, no domain

This is the authoritative production runbook for the approved first AWS
deployment. It preserves the tested application and role model in a fresh system:

- Region: **Asia Pacific (Mumbai), `ap-south-1`**
- Instance: **`t4g.medium`** (ARM64, 2 vCPU, 4 GiB RAM)
- Operating system: **Ubuntu Server 24.04 LTS ARM64**
- Storage: **50 GB encrypted gp3 EBS** plus a 2 GB host swap file
- Address: one manually allocated and associated **Elastic IPv4 address**
- Public URL: `https://ELASTIC_IP` — no domain
- Administration: public SSH with keys only; passwords/root login disabled;
  Fail2ban and verbose SSH logging enabled
- Data: new database, new Admin, and new users; no Windows/Mac testing data
- Backups now: matched database/media pairs on EC2 every 12 hours, copied to the
  technician's Mac regularly
- Backups later: private encrypted S3 backup storage is the next durability upgrade

The EC2 stack is separate from `docker-compose.yml` (development) and
`docker-compose.prod.yml` (local Windows production). It uses
`docker-compose.ec2.yml` and `deployment/.env.ec2`.

## 1. Before creating the instance

You need:

- An AWS account with access to EC2 in `ap-south-1`.
- A Mac copy of this repository containing the EC2 deployment files.
- An email address for Let's Encrypt certificate notices.
- A secure location for the downloaded EC2 private key (`.pem`).

Do not create `deployment/.env.ec2` on the Mac and do not copy local `.env`
files, databases, Docker volumes, media, exports, or backups to AWS.

### Required frontend security gate

Do not expose the production instance unless this gate passes. The August 2026
Next.js security release moved forward to **2026-08-25** and requires 15.5.24 for
projects remaining on the maintained 15.5 line. This repository is locked to
Next.js 15.5.24. Before transferring the source to EC2, run:

```bash
cd src/frontend
npm ci
npm audit --omit=dev
cd ../..
docker compose -f deployment/docker-compose.ec2.yml \
  --env-file deployment/env.ec2.example build frontend
```

The current audit can report Next.js's internal PostCSS 8.4.31. In this application,
PostCSS only compiles repository-owned CSS during the image build; users cannot
submit CSS or source maps and the production server does not compile them. Keep
reviewing this transitive finding when a newer 15.5 patch is released. Do not use
`npm audit fix --force`: it moves the application to Next.js 16, whose breaking
changes require a separate migration. Track official releases at
<https://nextjs.org/blog>.

## 2. Create the EC2 instance in the AWS Console

Open **AWS Console → EC2** and select **Asia Pacific (Mumbai) `ap-south-1`**.

Choose **Launch instance** and use:

| Setting | Approved value |
| --- | --- |
| Name | `swisstech-stock-tracker-production` |
| AMI | Canonical Ubuntu Server 24.04 LTS, 64-bit Arm |
| Instance type | `t4g.medium` |
| Key pair | New ED25519 or RSA key pair; download the `.pem` once |
| Network | Default VPC/public subnet, auto-assign public IP enabled for launch |
| Root volume | 50 GiB, gp3, encrypted |
| Delete on termination | Disable, so accidental instance termination does not immediately delete data |

Enable **termination protection** after launch under **Instance settings → Change
termination protection**.

Confirm the AMI architecture says `arm64`. Do not select an x86_64 image for the
approved `t4g.medium` instance.

## 3. Security group

Create a dedicated security group such as `swisstech-stock-tracker-production`.

Inbound rules:

| Type | Port | Source | Purpose |
| --- | ---: | --- | --- |
| SSH | 22 | `0.0.0.0/0` | Administration from changing locations |
| HTTP | 80 | `0.0.0.0/0` | Let's Encrypt IP validation and HTTPS redirect |
| HTTPS | 443 | `0.0.0.0/0` | Application access |

Do **not** add public rules for PostgreSQL `5432`, Redis `6379`, Django `8000`,
Next.js `3000`, or any Docker-internal network. Do not add IPv6 inbound rules
unless IPv6 is deliberately introduced and separately reviewed.

Port 22 is intentionally global because the administrator changes locations.
The host setup compensates with public-key-only authentication, disabled root and
password login, three-attempt limits, disabled SSH forwarding/tunneling, Fail2ban,
and verbose authentication logs.
The private key is therefore critical: never email it or store it in the repository.

## 4. Allocate and associate the Elastic IP

After the instance is running:

1. Open **EC2 → Network & Security → Elastic IP addresses**.
2. Select **Allocate Elastic IP address** in `ap-south-1`.
3. Select the new address and choose **Actions → Associate Elastic IP address**.
4. Associate it with the production instance and its primary private IP.
5. Record the Elastic IP. It becomes the permanent application address and must
   stay associated for the short-lived IP certificate to renew.

Wait until this works from the Mac, substituting the key and address:

```bash
chmod 400 /path/to/swisstech-production.pem
ssh -i /path/to/swisstech-production.pem ubuntu@ELASTIC_IP
```

## 5. Transfer the clean source from the Mac

The following approach does not put a GitHub password or token on EC2.

First install `rsync` on the fresh instance:

```bash
sudo apt-get update
sudo apt-get install -y rsync
exit
```

From the repository root on the Mac:

```bash
rsync -az \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'node_modules/' \
  --exclude '.next/' \
  --exclude 'deployment/.env.*' \
  --exclude 'data/backups/*' \
  --exclude 'src/backend/media/*' \
  -e 'ssh -i /path/to/swisstech-production.pem' \
  ./ ubuntu@ELASTIC_IP:/home/ubuntu/Stock_Tracker/
```

The exclusion intentionally leaves out every environment secret and all local
runtime/test data. It still transfers the committed environment examples.

Reconnect and confirm the expected commit/source is present:

```bash
ssh -i /path/to/swisstech-production.pem ubuntu@ELASTIC_IP
cd /home/ubuntu/Stock_Tracker
ls deployment/docker-compose.ec2.yml scripts/setup-ec2.sh
```

## 6. Generate EC2-only secrets

On EC2, substitute the real Elastic IP and certificate email:

```bash
cd /home/ubuntu/Stock_Tracker
scripts/generate-ec2-env.sh ELASTIC_IP admin@example.com
```

This creates the gitignored `deployment/.env.ec2` with:

- a random 96-character Django secret
- a random 64-character PostgreSQL password
- the Elastic IP in Django allowed hosts
- `https://ELASTIC_IP` as the trusted CSRF origin
- the Ubuntu administrator's UID/GID for private, non-root backup ownership
- the bootstrap nginx configuration
- 12-hour backups and 120-day retention

Verify permissions without displaying the secrets:

```bash
stat -c '%a %n' deployment/.env.ec2
```

The result must be `600`. Save one encrypted/offline copy of this file. Do not
paste its contents into support messages.

## 7. Run the guarded one-time setup

Confirm ports 80 and 443 are reachable through the security group and the Elastic
IP is already associated. Then run:

```bash
sudo scripts/setup-ec2.sh
```

The script:

1. Refuses non-ARM64 machines, missing EC2 secrets, and any Next.js lockfile older
   than patched 15.5.24 or outside the approved 15.5 maintenance line.
2. Refuses to harden SSH unless the Ubuntu account already has an authorized key.
3. Installs Docker Engine/Compose and enables Ubuntu unattended security updates.
4. Creates 2 GB swap for build headroom on the 4 GiB instance.
5. Disables SSH password, keyboard-interactive, and root login.
6. Enables verbose SSH logs and Fail2ban.
7. Installs Certbot 5.4+ in `/opt/certbot`.
8. Builds the ARM64 backend/frontend images directly on EC2.
9. Starts nginx in certificate-bootstrap mode.
10. Applies migrations, then refuses to continue if any user or business record
    exists. It never deletes unexpected data.
11. Requests a trusted short-lived certificate for the Elastic IP.
12. Switches nginx to HTTPS and installs a four-times-daily renewal timer.
13. Seeds locations, currencies, exchange rates, GST rates, and categories only.
14. Prompts for the new Admin username/password.
15. Creates and validates the first database/media backup pair.
16. Runs the infrastructure verification script.

On EC2, nginx rejects direct `/media/` paths. Invoice and bill attachments are
downloaded only through Django's authenticated API, so the application's user
rights cannot be bypassed by guessing a storage filename.

Use a unique production Admin password. The command validates it with Django's
password rules and does not store it in the repository.

If certificate issuance fails, leave nginx in bootstrap mode, inspect the error,
and confirm that the Elastic IP points to this instance and port 80 is public.
Do not weaken HTTPS or switch the application to public plain HTTP.

## 8. First login and fresh-system check

Open:

```text
https://ELASTIC_IP
```

The browser must show a trusted connection without a certificate warning.

Sign in as the new Admin and verify:

- Products, suppliers, customers: empty
- Purchases, refunds, shipments, sales, adjustments: empty
- Stock ledger and balances: empty
- Users: only the new Admin
- Settings: seeded locations, categories, currencies, exchange rates, GST rates

The seed contains placeholder exchange rates effective 2026-01-01. The Admin must
review/update current production exchange and GST rates before entering purchases.
Do not run `manage.py seed --demo` in production.

## 9. Create production users and verify rights

Use **Users → Add** as Admin. Create each person with the correct role; never share
one account between people because audit records identify the signed-in user.

Complete this acceptance matrix with four test accounts before live entries:

| Check | Admin | Purchase | Sale | Viewer |
| --- | --- | --- | --- | --- |
| View dashboard/general data | Yes | Yes | Yes | Yes |
| Manage products | Yes | Yes | No | No |
| Manage purchases/collection/refunds | Yes | Yes | No | No |
| Manage shipments/receiving | Yes | Yes | No | No |
| Manage suppliers | Yes | Yes | No | No |
| Manage sales/customers | Yes | No | Yes | No |
| Manage stock adjustments | Yes | No | No | No |
| View/export stock valuation | Yes | No | No | No |
| Manage users/locations/currencies | Yes | No | No | No |
| View reports, stock ledger, audit | Yes | Yes | Yes | Yes |

Check both the visible buttons and direct API rejection. Hiding a button is not a
security boundary; Django permissions are authoritative.

## 10. Routine operations

Set reusable shell variables after connecting:

```bash
cd /home/ubuntu/Stock_Tracker
COMPOSE='docker compose -f deployment/docker-compose.ec2.yml --env-file deployment/.env.ec2'
```

After the first logout/reconnect, the `ubuntu` account belongs to the Docker group.

```bash
$COMPOSE ps
$COMPOSE logs --tail=100
$COMPOSE logs -f backend worker nginx
scripts/verify-ec2.sh
df -h /
du -sh data/backups
```

Restart without deleting data:

```bash
$COMPOSE down
$COMPOSE up -d
```

Never use `down -v`; `-v` deletes PostgreSQL, media, export, and static volumes.

Inspect SSH protection:

```bash
sudo fail2ban-client status sshd
sudo journalctl -u ssh --since today
```

## 11. TLS certificate renewal

Elastic-IP certificates are short-lived, so renewal automation is mandatory.
The setup timer checks four times daily and nginx continues serving the ACME
challenge on port 80.

```bash
systemctl list-timers stock-tracker-cert-renew.timer
sudo systemctl start stock-tracker-cert-renew.service
sudo systemctl status stock-tracker-cert-renew.service --no-pager
sudo /opt/certbot/bin/certbot certificates
```

Do not release or replace the Elastic IP without issuing a replacement certificate
and updating `deployment/.env.ec2`.

## 12. Backups now and copying them to the Mac

The backup container creates a matched pair on startup and every 12 hours:

```text
data/backups/stock_tracker-YYYYmmdd-HHMMSS.sql.gz
data/backups/stock_tracker-media-YYYYmmdd-HHMMSS.tar.gz
```

Each file is mode `600` and owned by the Ubuntu administrator. If either archive
fails validation, the incomplete pair is removed.

Create an extra pair before maintenance:

```bash
cd /home/ubuntu/Stock_Tracker
scripts/backup-ec2.sh
```

At least weekly, copy the entire backup folder to a protected Mac folder:

```bash
mkdir -p /path/to/swisstech-aws-backups
rsync -az \
  -e 'ssh -i /path/to/swisstech-production.pem' \
  ubuntu@ELASTIC_IP:/home/ubuntu/Stock_Tracker/data/backups/ \
  /path/to/swisstech-aws-backups/
```

Backups on the EC2 disk do not protect against loss of the instance and EBS
volume. The planned next durability phase is automatic upload of encrypted,
versioned backup pairs to a private S3 bucket with lifecycle retention. Application
uploads can remain on EBS initially; S3 backup does not require changing user rights.

## 13. Restore drill

Before accepting live data, create a backup pair and run one controlled restore:

```bash
scripts/restore-ec2.sh \
  data/backups/stock_tracker-YYYYmmdd-HHMMSS.sql.gz \
  data/backups/stock_tracker-media-YYYYmmdd-HHMMSS.tar.gz
```

The script validates both archives, requires typing `RESTORE`, stops application
writers, replaces the database and media, restarts the stack, and directs you to
run verification. A restore overwrites current production data.

## 14. Safe application updates

1. Have users sign out and pause entries.
2. Create a backup and copy it to the Mac.
3. Transfer the updated clean source using the same `rsync` exclusions. Never
   overwrite `deployment/.env.ec2` or `data/backups/`.
4. On EC2:

   ```bash
   cd /home/ubuntu/Stock_Tracker
   docker compose -f deployment/docker-compose.ec2.yml \
     --env-file deployment/.env.ec2 up -d --build
   docker compose -f deployment/docker-compose.ec2.yml \
     --env-file deployment/.env.ec2 restart nginx
   scripts/verify-ec2.sh
   ```

   The nginx restart is not optional. nginx resolves `backend` and `frontend`
   once, when it loads its configuration. Recreating those containers gives them
   new addresses, and if nginx itself was not recreated it keeps proxying to the
   old ones — every request returns **502** until it is restarted. This bites
   exactly when the compose file is unchanged and only application code moved.

5. Application code is baked into the images, not mounted. A file transferred to
   the host is invisible to a running container until `--build` recreates it, so
   never run `manage.py migrate` before the rebuild and expect a new migration to
   be found.

6. Complete a role-sensitive smoke test before users resume.

## 15. Recovery if the instance fails

If the EBS volume survives, attach it only through a reviewed recovery procedure;
Docker named volumes and secrets must remain consistent. If the instance and EBS
are lost, recovery is possible only from the most recent backup pair copied to the
Mac plus the saved `deployment/.env.ec2`.

Create a new approved ARM64 instance and Elastic IP, transfer the clean source,
restore `.env.ec2`, start the stack, copy the selected backup pair to
`data/backups/`, run `scripts/restore-ec2.sh`, then issue a certificate for the new
Elastic IP if the address changed.

This limitation is why private S3 backup is the next recommended infrastructure
improvement after the initial EC2 deployment stabilizes.
