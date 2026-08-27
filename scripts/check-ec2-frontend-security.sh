#!/usr/bin/env bash
# Require the patched Next.js 15.5 maintenance line approved for this deployment.
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
if [[ ! "$NEXT_LOCK_VERSION" =~ ^15\.5\.([0-9]+)$ ]]; then
  echo "ERROR: Next.js $NEXT_LOCK_VERSION is outside the approved 15.5 maintenance line." >&2
  echo "Use a stable patched 15.5.x release; major upgrades require a separate migration." >&2
  exit 1
fi

NEXT_PATCH="${BASH_REMATCH[1]}"
if (( NEXT_PATCH < 24 )); then
  echo "ERROR: Next.js $NEXT_LOCK_VERSION is older than the required patched 15.5.24 release." >&2
  echo "Update the package and lockfile, then repeat the audit/build gate in deployment/AWS_EC2_GUIDE.md." >&2
  exit 1
fi

echo "Frontend security version gate passed (Next.js $NEXT_LOCK_VERSION)."
