#!/usr/bin/env bash
# One-time macOS setup helper. Creates a Desktop symlink to the double-click
# launcher while keeping the real script inside the cloned repository.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
source_launcher="$repo_root/scripts/open-stock-tracker.command"
desktop_dir="$HOME/Desktop"
desktop_launcher="$desktop_dir/SwissTech Stock Tracker.command"

if [ ! -d "$desktop_dir" ]; then
  echo "Desktop folder not found: $desktop_dir" >&2
  exit 1
fi

chmod +x "$source_launcher"

if [ -e "$desktop_launcher" ] || [ -L "$desktop_launcher" ]; then
  echo "Desktop launcher already exists: $desktop_launcher"
  exit 0
fi

ln -s "$source_launcher" "$desktop_launcher"
echo "Created desktop launcher: $desktop_launcher"
echo "The operator can now double-click it to start and open Stock Tracker."
