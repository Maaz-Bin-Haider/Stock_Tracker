# Purchase search production deployment

Date: 2026-10-22. The user explicitly requested a backup followed by deployment of
the modern Purchases search enhancement. Status: deployed successfully at **15:51:01 UTC / 20:51:01 Pakistan time**.
Production now serves the modern Purchases search release.

## Backup and recovery preparation

- Initial backup pair `20261022-153010` UTC was created and validated on EC2 before
  source transfer. Its approved Mac copy is under
  `/Users/swisstech/Development/Stock_Tracker/data/backups/ec2-2026-10-22/`.
  The prior explicit approval of this destination remains applicable; both SHA256
  checksums match EC2 and gzip/tar integrity checks passed. Folder mode 700;
  archives/checksum manifest mode 600; backup payloads remain gitignored.
- Initial database SHA256:
  `66e22fe66e83f2f4374de709906fffefc957cdb615b62d1e0f53ac10c9fce81a`.
- Initial media SHA256:
  `36d327ab0a251e9adee885696483ae4fb4b97010151cec26a67299a6afacb6dd`.
- Existing source/images retained in
  `/home/ubuntu/stock-tracker-releases/search-20261022-1530/` and tags
  `stock-tracker-ec2-{backend,worker,frontend}:before-search-20261022`.
- Production environment remains on EC2 at mode 600; its hash is checked before
  and after deployment. No local sample data, environment files, credentials,
  database, or uploaded files are sent to production.

## Release validation

The earlier deployed correction release manifest was the comparison baseline,
since Git HEAD at deployment time predated that working-tree change. All 179 existing source/build files
matched it (the intentionally omitted empty media marker is excluded). The new
release contains 184 clean source/build files. Final source archive SHA256:
`db17040e5a8988e3665e816251393ede1b587fb757d3f2186e1a61cfbb75d076`.

- Frontend security gate and local/native EC2 ARM64 production build pass on
  Next.js 15.5.28. Current npm production audit contains only the documented
  internal build-time PostCSS exception and inherited Next finding; it is not a
  zero-finding audit. No dependency or major framework upgrade is part of this release.
- Backend/worker reuse the previous tested Python runtime/dependency image and
  copy the new source onto it. The private release directory retains
  `Dockerfile.backend` and `runtime-build.yml` as the exact build recipe.
- Django configuration and `migrate --check` pass; no schema change is required.
- Local frontend: 30 tests, TypeScript, ESLint, production build pass. Backend
  search regressions: 21 pass, including after the performance refinement.
- Local phone/tablet visual acceptance uses real 375/768 px iframe viewports with
  synthetic data. Desktop light/dark filter behavior was verified earlier.

### Status-query performance refinement

The production-sized SELECT-only preflight found a fully-collected filter request
at 5.919 seconds. The original nested line/invoice CASE expressions repeated the
quantity subqueries. Replacing them with status-specific Exists predicates reduced
that request to 2.656 seconds while preserving all model statuses and totals.

Full-page timings under concurrent synthetic test load (request handling and
serialization, excluding browser/network transport):

| Request | Initial candidate | Final candidate |
| --- | ---: | ---: |
| All invoices | 2.194 s | 2.129 s |
| Fully collected | 5.919 s | 2.656 s |
| Product text search | 2.142 s | 1.745 s |

These are diagnostic samples, not an SLA. Final read-only checks match all five
computed status counts, combined supplier/location/product/date filters, product
text scope, no-match results, and all five whole-result totals against Python
model calculations. No production invoice or balance was edited for testing.

## Switch and acceptance

The exact final ARM64 backend image passed **308 tests in 349.12 seconds** against
an isolated synthetic PostgreSQL container/network, with no production credentials
or volume mounts. One pytest cache warning came from the read-only test-source
mount; no test failed. Temporary test containers/network were removed afterward.
The earlier candidate test run was intentionally stopped when the measured query
performance warranted refinement; the complete passing run covers the final code.

Nginx and the worker were paused, then final backup pair **20261022-155019 UTC**
was created and validated before the switch:

- `/home/ubuntu/Stock_Tracker/data/backups/stock_tracker-20261022-155019.sql.gz`
- `/home/ubuntu/Stock_Tracker/data/backups/stock_tracker-media-20261022-155019.tar.gz`

Both final archives are also verified in the approved private Mac backup folder.
Final database SHA256:
`16e581e07ef7e8ff665cb8dd8f8e7118b921d30ffad1b83105208087912cae97`.
The media SHA256 matches the initial archive above. Originals remain on EC2.

Backend and frontend were recreated from the tested images. SELECT-only
repeatable-read snapshots confirmed unchanged application-table counts/hashes
(sessions excluded), zero ledger/balance discrepancies, and matching new search
results/totals. The worker stayed paused until these checks passed; it was then
recreated and nginx restarted to resolve the new application container addresses.
No production invoice was edited, sample inserted, balance repaired, or migration
applied. Startup found no pending migrations and refreshed static files.

The final production environment hash is unchanged at mode 600. Existing Admin,
Purchase, and Sale users passed read-only API checks, including correction
eligibility fields. No Viewer account exists in production; none was created.
Synthetic tests cover the Viewer role. All five status filters, combined
reference/date filters, product text scope, no-match behavior, and whole-result
quantity/pending/collected/AED/GST totals match Python model calculations.

Acceptance passed for all seven services, HTTPS health/login, HTTP redirect,
anonymous API denial, valid TLS/renewal timer, Ubuntu update timer, Django and
migration checks, worker pong, critical source hashes, and the actual public
purchase-page JavaScript bundle hash/feature markers. The standard repairing
reconciliation command is not used.

Final image digests:

- Backend: `sha256:ebaf27dcac3ade61ade60e681c6237c571abd0a140fd71deb57fe42fbe4bfa54`
- Worker: `sha256:8167cddce81858eddfd3a4375337c9927557a260b0e29f22388b069637b92e4e`
- Frontend: `sha256:eba5fb65169c3f572b79fd48f4e41db6af5d3626f669fffdc959de5d4aceb325`


## Evidence and recovery

Source-only local evidence is gitignored under
`data/exports/purchase-search-release-2026-10-22/`; runtime logs and data hashes
remain under the private EC2 release directory. This includes the build, isolated
synthetic test run, SELECT-only preflight/timing scripts, before/after fingerprints,
backup logs, and guarded deployment/check scripts.

The release adds read-only list filtering with no migration. Keep the earlier
purchase correction implementation when rolling back search; reverting to a
backend before purchase corrections can mishandle corrected collection undo.
No production data restore is authorized by this deployment request.
