# SwissTech Stock Tracker — Fresh Windows Trial Setup and Recovery Guide

This is the authoritative setup guide for the three-month environment trial. The
target is a **different Windows computer**, used by one person with the **Admin**
role. It must start with a new empty business database; nothing entered during
testing on the Mac is transferred.

After a technician completes this guide once, the Admin only double-clicks the
**SwissTech Stock Tracker** Desktop shortcut and signs in.

## Trial plan

- Platform: Windows 10/11 with Docker Desktop using Linux containers.
- Duration: approximately three months.
- Users: one local Admin.
- Address: <http://localhost:8080> on that Windows computer only.
- Data: fresh database; required locations, categories, currencies, exchange
  rates, and GST rates are seeded, but products and transactions remain empty.
- Backups: database and uploaded-file backup pairs immediately at backup-service
  startup and every 12 hours afterward while Docker is online.
- Retention: 120 days, covering the whole trial plus a margin.
- Server/AWS deployment: considered only after a stable trial.

## 1. Do not copy testing data from the Mac

The Windows installation must come from a fresh Git clone. Do **not** copy any of
these from the tested Mac:

- Docker volumes or containers
- `deployment/.env.prod`
- `data/backups/`
- `src/backend/media/`
- database dumps or uploaded-file archives

The source repository does not contain runtime business data. A fresh clone on a
new Windows machine creates new Docker volumes and therefore starts clean.

## 2. Install Windows prerequisites

Using a Windows administrator account, install:

1. [Git for Windows](https://git-scm.com/download/win).
2. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
3. Enable WSL 2 when Docker Desktop requests it, then restart Windows.
4. In Docker Desktop, enable **Settings → General → Start Docker Desktop when you
   sign in** and confirm **Use the WSL 2 based engine** is enabled.

Docker Desktop must use **Linux containers**. Keep at least 10 GB of free disk
space; uploaded invoice files may require more later.

## 3. Clone a clean copy

Open **Windows PowerShell** and run:

```powershell
New-Item -ItemType Directory -Force C:\SwissTech
Set-Location C:\SwissTech
git clone https://github.com/Maaz-Bin-Haider/Stock_Tracker.git
Set-Location C:\SwissTech\Stock_Tracker
```

Confirm `git status` does not show unexpected local changes.

## 4. Private configuration is generated automatically

Do not copy or create `.env.prod` manually. On its first run, the Windows setup
script creates `deployment\.env.prod` with a machine-specific random 64-character
Django secret and random database password, plus the confirmed localhost and
backup settings.

The generated file remains ignored by Git even though the repository is private.
Secrets committed to Git persist in history and are unnecessary here. After setup,
store one secure offline copy of `.env.prod` for disaster recovery.

## 5. Initialize the fresh application

Start Docker Desktop and wait until it says the engine is running. From
`C:\SwissTech\Stock_Tracker`, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\setup-windows.ps1
```

This setup script:

1. Generates a private `.env.prod` with random machine-specific secrets if missing.
2. Builds and starts the production Docker stack.
3. Applies all database migrations to new Docker volumes.
4. Refuses to continue if any existing user or business record is detected; it
   never deletes that data automatically.
5. Seeds required master settings only—never demo transactions.
6. Prompts for the new Admin username and password.
7. Creates the Windows Desktop shortcut.
8. Creates the first post-setup database/uploaded-file backup pair.

Use `admin` as the username. Choose the password approved for the trial; it is not
stored in Git or this guide.

## 6. Confirm it is a fresh system

Double-click **SwissTech Stock Tracker** on the Windows Desktop and sign in. Verify:

- Products: empty
- Suppliers: empty
- Customers: empty
- Purchases, refunds, shipments, sales, and stock adjustments: empty
- Stock Ledger: empty
- Settings: locations, categories, currencies, exchange rates, and GST rates exist
- Users: only the newly created Admin

If business/test transactions are visible, stop and contact the technician. Do
not enter live trial data until the cause is understood.

## 7. Daily use for the non-technical Admin

1. Double-click **SwissTech Stock Tracker** on the Desktop.
2. If Docker Desktop is closed, the shortcut starts it and waits up to two minutes.
3. The shortcut starts the application and opens the login page automatically.
4. Sign in as `admin` and make entries.
5. Sign out when finished. Docker can remain running so 12-hour backups continue.

If a command window shows an error, leave it open and send a photo to the
technician. The Admin does not need PowerShell for normal daily use.

## 8. Automatic and manual backups

Backup pairs are written to:

```text
C:\SwissTech\Stock_Tracker\data\backups\
```

Each timestamp produces:

```text
stock_tracker-YYYYmmdd-HHMMSS.sql.gz
stock_tracker-media-YYYYmmdd-HHMMSS.tar.gz
```

- The SQL archive contains users, settings, products, all business transactions,
  stock, report metadata, and audit history.
- The media archive contains uploaded invoices and attachments.
- A pair is created when the backup container starts and every 43,200 seconds
  (12 hours) while Docker is online.
- Backups older than 120 days are removed automatically.
- Report-export files are reproducible and are not included.

Create an extra backup before updates or important maintenance:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\backup-windows.ps1
```

At least weekly, the technician must copy the entire `data\backups` folder to an
encrypted USB drive or another trusted computer. Local-only backups cannot protect
against theft or disk failure.

## 9. Technical status and support

From the repository folder:

```powershell
docker compose -f deployment\docker-compose.prod.yml --env-file deployment\.env.prod ps
```

All seven services should show `Up`; PostgreSQL, Redis, and the backend should
show `healthy`.

Recent logs:

```powershell
docker compose -f deployment\docker-compose.prod.yml --env-file deployment\.env.prod logs --tail=100
```

Do not use `docker compose down -v`; `-v` permanently deletes the database and
uploaded-file volumes.

## 10. Update the application safely

Only the technician should update it. Ensure the Admin is signed out, then run:

```powershell
Set-Location C:\SwissTech\Stock_Tracker
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\backup-windows.ps1
git pull
docker compose -f deployment\docker-compose.prod.yml --env-file deployment\.env.prod up -d --build
```

Updating source code preserves Docker volumes, but the pre-update backup is
mandatory.

## 11. Recover on the same or a replacement Windows computer

1. Install Git and Docker Desktop.
2. Clone the same repository into `C:\SwissTech\Stock_Tracker`.
3. Restore the secure copy of `deployment\.env.prod`.
4. Copy one timestamp-matched SQL/media backup pair into `data\backups\`.
5. Start the stack:

   ```powershell
   docker compose -f deployment\docker-compose.prod.yml --env-file deployment\.env.prod up -d --build
   ```

6. Restore both files, substituting the actual timestamp:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\restore-windows.ps1 `
     -DatabaseFile data\backups\stock_tracker-YYYYmmdd-HHMMSS.sql.gz `
     -MediaFile data\backups\stock_tracker-media-YYYYmmdd-HHMMSS.tar.gz
   ```

7. Type `YES` only after confirming the selected files. The restore overwrites the
   current database.
8. Install the Desktop shortcut again if necessary:

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\install-desktop-launcher-windows.ps1
   ```

9. Sign in and verify products, recent transactions, stock, audit history, and
   uploaded files.

## 12. End of the three-month trial

If no blocking problem occurs:

1. Create a final manual backup pair.
2. Copy the final pair and `.env.prod` to secure offline storage.
3. Confirm report columns and the long-term backup policy.
4. Plan server/AWS deployment, HTTPS, S3-compatible uploaded-file storage, and
   off-machine cloud backups.
5. Migrate only the Windows trial database/media—not the old Mac test data—to the
   future server.
