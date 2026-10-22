# Purchase correction production deployment

Date: 2026-10-22. The user explicitly authorized connecting to EC2, taking a backup
first, then deploying the locally verified purchase correction fix.

Status: deployed successfully at **2026-10-22 11:53:47 UTC (16:53:47 Pakistan time)**.
All seven services are running; HTTPS health and login are available.

## Recovery preparation

- Host: existing ARM64 Ubuntu EC2 at `15.206.30.171`; existing Compose project
  `stock-tracker-ec2` under `/home/ubuntu/Stock_Tracker`.
- Initial database/media backup: `20261022-114012` (UTC), validated on EC2 with
  `gzip -t` and `tar -tzf`. Backup files remain private at mode 600.
- Initial database archive SHA256:
  `a7561af39b8abd66c8b74fab26eab4aef3e209cf8bbf8b0f066b0402bba5c55a`.
- Initial media archive SHA256:
  `36d327ab0a251e9adee885696483ae4fb4b97010151cec26a67299a6afacb6dd`.
- Prior source archive and images retained in
  `/home/ubuntu/stock-tracker-releases/corrections-20261022-1140/` and Docker tags
  `stock-tracker-ec2-{backend,worker,frontend}:before-corrections-20261022`.
  The previous frontend image metadata had been pruned; its running filesystem
  was captured without pausing service to retain a recoverable image.
- The production environment file stays on EC2 at mode 600 and is checked by hash
  before/after deployment. No local environment files, sample data, or credentials
  are transferred into production.
- The user explicitly approved the protected Mac destination after automatic
  approval review initially blocked the export. Final pre-deployment pair
  `20261022-115313` was then copied to
  `/Users/swisstech/Development/Stock_Tracker/data/backups/ec2-2026-10-22/`.
  Both local SHA256 checksums match EC2; gzip/tar integrity checks passed.
  The folder is mode 700 and archives/checksum manifest mode 600, with archives
  gitignored. No backup payload was opened or restored; EC2 originals remain.
- Final database SHA256:
  `5dc0bd47f4a287d261a453a2670c767b7f844ab64b4f7bc47b7ea65192151e04`.
  Final media SHA256 matches the initial media archive listed above.

## Release checks

Source payload: 180 application/build files with a SHA256 manifest. Every existing
application source file matched the known repository baseline (174 files, ignoring
an intentionally omitted empty media-directory marker). Source archive SHA256:
`fe4d2779781771a0c62942975ae2bdbe546647bd87b25c59088841f09d4ff676`.

The current npm audit required moving Next.js from 15.5.24 to 15.5.28 in the
maintained 15.5 line. The updated lock also resolves sharp to 0.35.5 and
source-map-js to 1.2.2. Production audit findings are now limited to Next.js's
internal PostCSS 8.4.31 and the inherited Next advisory. The existing runbook
exception applies: only repository-owned CSS is compiled at build time; users
cannot submit CSS/source maps and the production server does not compile them.
No major Next.js upgrade or forced audit fix was used. The security-version guard
now requires at least 15.5.28. This is not a zero-finding audit.

Sources checked: [Next.js advisory](https://github.com/advisories/GHSA-4jqv-mc3x-m676),
[sharp advisory](https://github.com/advisories/GHSA-wq5f-xc86-pv6w), and official npm
package metadata. The source dependency versions are recorded in the lockfile.
Frontend tests (27), TypeScript, ESLint, and the patched ARM64 production build
passed locally. Backend/worker/frontend also built natively on EC2 in a separate
staging directory while the old services continued running. Django configuration
check passed and `migrate --check` confirmed no pending migration.

The exact new backend image passed **287 tests in 331.58 seconds** against an
isolated synthetic PostgreSQL container/network without production credentials,
ports, or volume mounts. This also checks the runtime dependencies resolved by
the production image build. The single warning was a pytest cache write attempt
on a read-only test-source mount; no behavior test failed. The synthetic test
container and network were removed afterward.

## Completed switch and verification

Nginx and the worker were paused. Final backup pair **20261022-115313 UTC** was
created and validated before source replacement or service recreation:

- `/home/ubuntu/Stock_Tracker/data/backups/stock_tracker-20261022-115313.sql.gz`
- `/home/ubuntu/Stock_Tracker/data/backups/stock_tracker-media-20261022-115313.tar.gz`

Backend, worker, and frontend were recreated from the already-tested images.
Before reopening nginx, SELECT-only repeatable-read snapshots confirmed every
application table's count/hash unchanged (sessions excluded), with zero
ledger/balance discrepancies. Production environment hash and mode 600 remained
unchanged. No invoice edit, sample insert, migration application, or balance repair
was performed. Startup found no pending migrations; static assets were refreshed.

The first guarded switch stopped before source replacement because the verifier's
request factory used `testserver`, which production correctly rejected. The guard
restored the previous nginx/worker immediately. The verifier was corrected to use
the existing real host without relaxing allowed-host security, then preflighted
read-only before the successful second switch. An additional valid backup pair
`20261022-115219` was retained from that first attempt.

Acceptance checks passed:

- All seven services running; PostgreSQL, Redis, backend, and nginx healthy.
- HTTPS `/api/v1/health/` returned 200/ok; production login page returned 200 and
  rendered in the browser; HTTP redirected with 301 to HTTPS.
- Anonymous purchase access returned 403. Existing Admin, Purchase, and Sale users
  each read 240 purchase lines on the first page with the new eligibility fields.
  No Viewer account exists in production; no account was created for testing.
  The full synthetic suite covers Viewer restrictions.
- Django check passed; `migrate --check` passed; Celery worker returned pong.
- Next.js running version 15.5.28; critical backend/frontend source hashes match
  the release manifest. All release images are ARM64.
- TLS certificate valid beyond 24 hours; renewal timer active; Ubuntu security
  update timer enabled. Final backup archives passed integrity checks.

The normal `verify-ec2.sh` invokes a repairing balance rebuild. This deployment
used equivalent infrastructure checks plus SELECT-only ledger reconciliation.
No production correction was saved as a smoke test; the write flows were tested
in the isolated environment before release.

Release image digests:

- Backend: `sha256:eee070ed94ef107e1fb156335d85e9f389ba7b8c6c60b27d4904c78b19026e9f`
- Worker: `sha256:90cb632cd230440083f8e49efa16c9479cbd59c476c7f0c2cae1894fee1e0e1b`
- Frontend: `sha256:b4c862e23b65bdd792f9bc0ed5d53b77d444aa0948eab24f348fe38e47f541e7`

Local source-only deployment scripts and manifests are gitignored under
`data/exports/ec2-release-2026-10-22/`. Recovery artifacts and verification logs
remain under the private release directory on EC2. Once corrected ledger events
exist, do not revert application code alone without reviewing collection undo
compatibility; no database restoration is authorized by this deployment request.
