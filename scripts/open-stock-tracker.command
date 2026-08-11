#!/usr/bin/env bash
# Double-click launcher for the non-technical macOS operator.
# Starts Docker Desktop and the local production stack when needed, waits for the
# health endpoint, then opens the Stock Tracker in the default browser.
set -uo pipefail

script_source="${BASH_SOURCE[0]}"
while [ -h "$script_source" ]; do
  script_dir="$(cd -P "$(dirname "$script_source")" && pwd)"
  link_target="$(readlink "$script_source")"
  if [[ "$link_target" = /* ]]; then
    script_source="$link_target"
  else
    script_source="$script_dir/$link_target"
  fi
done

script_dir="$(cd -P "$(dirname "$script_source")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
compose_file="$repo_root/deployment/docker-compose.prod.yml"
env_file="$repo_root/deployment/.env.prod"

show_error() {
  local message="$1"
  echo
  echo "ERROR: $message"
  /usr/bin/osascript -e "display alert \"SwissTech Stock Tracker\" message \"$message\" as critical" >/dev/null 2>&1 || true
}

if [ ! -f "$env_file" ]; then
  show_error "Setup is incomplete: deployment/.env.prod is missing. Ask the system administrator to complete LOCAL_SETUP_GUIDE.md."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  show_error "Docker Desktop is not installed. Ask the system administrator to install it."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Starting Docker Desktop..."
  /usr/bin/open -a Docker >/dev/null 2>&1 || true
  for _ in {1..60}; do
    if docker info >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi

if ! docker info >/dev/null 2>&1; then
  show_error "Docker Desktop did not start. Open Docker Desktop manually and try the icon again."
  exit 1
fi

echo "Starting SwissTech Stock Tracker..."
if ! docker compose -f "$compose_file" --env-file "$env_file" up -d; then
  show_error "The application could not start. Ask the system administrator to check the Docker logs."
  exit 1
fi

http_port="$(awk -F= '$1 == "HTTP_PORT" {print $2}' "$env_file" | tail -n 1 | tr -d '[:space:]\"')"
http_port="${http_port:-8080}"
app_url="http://localhost:$http_port"

echo "Waiting for the application..."
for _ in {1..60}; do
  if curl -fsS "$app_url/api/v1/health/" >/dev/null 2>&1; then
    echo "Opening $app_url"
    /usr/bin/open "$app_url"
    exit 0
  fi
  sleep 2
done

show_error "The application started but did not become ready. Ask the system administrator to check the Docker logs."
exit 1
