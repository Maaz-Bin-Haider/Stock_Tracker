# Offline / Local Production Deployment (Phase M9)

Run the SwissTech Stock Tracker in **production mode on a single machine or office
LAN**, with no cloud dependency. The immediate plan is a three-month trial on a
separate Windows machine with a fresh database and one Admin operator before deciding
on AWS (Phase M8). It runs gunicorn + a Next.js production build
behind nginx, keeps all data in persistent Docker volumes, survives reboots, and
takes automatic local database backups.

> Difference from `make up`: that command is the Mac/developer stack. The Windows
> trial uses `docker-compose.prod.yml` through the PowerShell tools documented in
> root `LOCAL_SETUP_GUIDE.md`.

## What you need

- The target Windows machine with **Git for Windows** and **Docker Desktop** using Linux containers.
- A new Git clone and new Docker volumes; do not transfer Mac testing data.

## First-time setup

The full authoritative process is in root `LOCAL_SETUP_GUIDE.md`. In summary:

1. Clone the repository into `C:\SwissTech\Stock_Tracker`.
2. **Run the guarded fresh-Windows initializer:**

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\setup-windows.ps1
   ```

   It generates a gitignored `.env.prod` with random machine-specific secrets,
   refuses to initialize if user/business records already exist, seeds master
   settings only, creates the Admin, installs the Windows shortcut, and takes the
   first backup. After setup, verify all business pages are empty.

## Day-to-day operation

| Task | Command |
| --- | --- |
| Start and open in browser (Windows) | Double-click **SwissTech Stock Tracker** on the Desktop |
| Reinstall Windows shortcut | `powershell.exe -ExecutionPolicy Bypass -File scripts\install-desktop-launcher-windows.ps1` |
| Extra manual backup (Windows) | `powershell.exe -ExecutionPolicy Bypass -File scripts\backup-windows.ps1` |
| Follow logs | `docker compose -f deployment\docker-compose.prod.yml --env-file deployment\.env.prod logs --tail=100` |
| Restore matching backup pair | `powershell.exe -ExecutionPolicy Bypass -File scripts\restore-windows.ps1 ...` (see root guide) |

Because every service is set to `restart: unless-stopped`, the whole stack comes
back automatically after a machine reboot (as long as Docker starts on boot).

## Backups

- A hardened **backup sidecar** creates a PostgreSQL dump and uploaded-media
  archive in `data/backups/` immediately on startup and every 12 hours while the
  stack is online (`BACKUP_INTERVAL_SECONDS=43200`).
- Matching `stock_tracker-*.sql.gz` and `stock_tracker-media-*.tar.gz` files are
  retained for 120 days, covering the three-month trial plus a margin.
- Run an immediate backup with `scripts\backup-windows.ps1` as shown above.
- **Copy `data/backups/` off this machine regularly** (USB drive, network share) —
  a local backup does not protect against the machine itself failing.
### Restore drill (do this once before going live)

1. Note some current data (e.g. a product name).
2. Run `scripts\backup-windows.ps1` through PowerShell.
3. Run `scripts\restore-windows.ps1` with the matching SQL and media files.
4. Type `YES`, then reload the app and confirm the data and uploads.

Restoring is destructive — it overwrites the current database — so the script
stops the app services, asks for `YES`, reloads the dump/media, and restarts.

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
