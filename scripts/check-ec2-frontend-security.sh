#!/usr/bin/env bash
# Refuse the package set covered by the announced 2026-08-26 Next.js release.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_LOCK_FILE="$REPO_ROOT/src/frontend/package-lock.json"

if [ ! -f "$FRONTEND_LOCK_FILE" ]; then
  echo "ERROR: missing $FRONTEND_LOCK_FILE; refusing an unpinned production build." >&2
  exit 1
fi

NEXT_LOCK_VERSION="$(awk '
  /"node_modules\/next":/ { in_next = 1; next }
  in_next && /"version":/ {
    value = $0
    sub(/^[^:]*:[[:space:]]*"/, "", value)
    sub(/".*/, "", value)
    print value
    exit
  }
' "$FRONTEND_LOCK_FILE")"

if [ -z "$NEXT_LOCK_VERSION" ]; then
  echo "ERROR: could not determine the locked Next.js version." >&2
  exit 1
fi
if [ "$NEXT_LOCK_VERSION" = "15.5.21" ]; then
  echo "ERROR: Next.js 15.5.21 is blocked from public production deployment." >&2
  echo "Apply the 2026-08-26 patched 15.5.x release and repeat the audit/build gate in deployment/AWS_EC2_GUIDE.md." >&2
  exit 1
fi

echo "Frontend security version gate passed (Next.js $NEXT_LOCK_VERSION)."
