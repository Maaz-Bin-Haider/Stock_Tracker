# Offline / Local Production Deployment (Phase M9)

Run the SwissTech Stock Tracker in **production mode on a single machine or office
LAN**, with no cloud dependency. This is the trial deployment the business uses
before deciding on AWS (Phase M8). It runs gunicorn + a Next.js production build
behind nginx, keeps all data in persistent Docker volumes, survives reboots, and
takes automatic local database backups.

> Difference from `make up`: that command is the **development** stack
> (`docker-compose.yml`, `runserver` + `next dev`, source live-reload). Everything
> here uses `docker-compose.prod.yml` and the `make prod-*` targets instead.

## What you need

- A machine (Linux/macOS/Windows) with **Docker** and **Docker Compose** installed.
- The machine's **LAN IP address** (e.g. `192.168.1.50`) so other office
  computers can reach it. Find it with `ipconfig` (Windows) or `ip addr` / `ifconfig`.

## First-time setup

1. **Create the config file** from the template and edit it:

   ```bash
   cp deployment/env.prod.example deployment/.env.prod
   ```

   Open `deployment/.env.prod` and set at least:
   - `DJANGO_SECRET_KEY` — a random key. Generate one with:
     `python -c "import secrets; print(secrets.token_urlsafe(50))"`
   - `POSTGRES_PASSWORD` — a strong database password.
   - `DJANGO_ALLOWED_HOSTS` — add the machine's LAN IP, e.g.
     `localhost,127.0.0.1,backend,192.168.1.50`
   - `DJANGO_CSRF_TRUSTED_ORIGINS` — the exact address users type in the browser,
     **with** `http://` and the port, e.g. `http://192.168.1.50:8080`
   - `HTTP_PORT` — leave `8080`, or set `80` to serve at `http://<ip>/`.

   `deployment/.env.prod` is gitignored — it holds secrets and is never committed.

2. **Start the stack** (builds images the first time — a few minutes):

   ```bash
   make prod-up
   ```

3. **Seed master data** (locations, currencies, GST rates — **no** demo data in
   production) and **create the admin user**:

   ```bash
   make prod-seed
   make prod-superuser   # creates an ADMIN-role superuser (prompts for username/password)
   ```

   > `make prod-superuser` runs `create_admin`, not Django's `createsuperuser`:
   > the app grants access by **role**, and a plain superuser would default to the
   > read-only Viewer role. `create_admin` sets the role to Admin.

4. **Open the app** from any machine on the LAN:
   `http://<machine-lan-ip>:8080` (or `:80` if you set `HTTP_PORT=80`).

## Day-to-day operation

| Task | Command |
| --- | --- |
| Start / update the stack | `make prod-up` |
| Stop the stack | `make prod-down` |
| Follow logs | `make prod-logs` |
| Back up the database now | `make backup` |
| Restore from a backup | `make restore FILE=data/backups/stock_tracker-YYYYmmdd-HHMMSS.sql.gz` |

Because every service is set to `restart: unless-stopped`, the whole stack comes
back automatically after a machine reboot (as long as Docker starts on boot).

## Backups

- A **backup sidecar** runs `pg_dump` automatically into `data/backups/` — daily
  by default (`BACKUP_INTERVAL_SECONDS`), keeping 30 days (`BACKUP_RETENTION_DAYS`).
- Run an immediate backup any time with `make backup`.
- **Copy `data/backups/` off this machine regularly** (USB drive, network share) —
  a local backup does not protect against the machine itself failing.
- Prefer host scheduling over the sidecar? Add a cron entry (repo root):

  ```cron
  0 2 * * * cd /path/to/Stock_Tracker && scripts/backup.sh >> data/backups/backup.log 2>&1
  ```

### Restore drill (do this once before going live)

1. Note some current data (e.g. a product name).
2. `make backup`
3. `make restore FILE=data/backups/<the-file>.sql.gz` and confirm with `yes`.
4. Reload the app and confirm the data is intact.

Restoring is destructive — it overwrites the current database — so the script
stops the app services, asks you to type `yes`, then reloads the dump and restarts.

## Data & persistence

All state lives in Docker **named volumes** so nothing is lost across restarts or
`prod-down`/`prod-up`:

- `postgres_data` — the database
- `media_files` — uploaded invoices/attachments
- `exports_data` — generated report exports (private; downloaded only via the API)
- `static_files` — collected Django admin/DRF static assets

Database backups are written to the host folder `data/backups/` (a bind mount) so
they are easy to find and copy off the machine.

> **`make prod-down` keeps your data** (volumes persist). Do **not** run
> `docker compose ... down -v` — the `-v` flag deletes the volumes, including the
> database.

## Enabling HTTPS later (optional)

The default is plain HTTP on a trusted LAN. If you put a TLS-terminating proxy in
front of nginx, set `DJANGO_SECURE_COOKIES=1` in `.env.prod` and switch the
browser origin(s) in `DJANGO_CSRF_TRUSTED_ORIGINS` to `https://…`. Do **not** set
that flag while still on plain HTTP, or cookies stop flowing and login breaks.

## Moving to AWS later (Phase M8)

Most of this carries over. The deltas are: swap local storage for S3-compatible
object storage (`django-storages`), run on an EC2 instance with a domain + TLS
certificates (then use `config.settings.prod` with `DJANGO_SECURE_COOKIES`
behaviour built in), and move backups from local disk to `pg_dump` → S3.
