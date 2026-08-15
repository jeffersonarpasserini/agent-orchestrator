#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
orchestrator_env_file=${ORCHESTRATOR_ENV_FILE:-"$project_dir/.env"}
test -f "$orchestrator_env_file"
export ORCHESTRATOR_ENV_FILE="$orchestrator_env_file"
compose() {
  docker compose --env-file "$orchestrator_env_file" \
    -p agent-orchestrator -f "$project_dir/compose.yaml" "$@"
}
backup_dir=${1:-"$project_dir/backups/openobserve"}
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
archive="$backup_dir/openobserve-$timestamp.tar.gz"
host_uid=$(id -u)
host_gid=$(id -g)

mkdir -p "$backup_dir"
cd "$project_dir"
compose stop otel-collector openobserve
trap 'compose up -d openobserve otel-collector >/dev/null 2>&1 || true' EXIT
docker run --rm \
  -v agent-orchestrator_openobserve-data:/source:ro \
  -v "$backup_dir:/backup" \
  busybox:1.37.0 \
  tar -C /source -czf "/backup/$(basename "$archive")" .
docker run --rm -v "$backup_dir:/backup" busybox:1.37.0 \
  chown "$host_uid:$host_gid" "/backup/$(basename "$archive")"
sha256sum "$archive" >"$archive.sha256"
chmod 600 "$archive" "$archive.sha256"
compose up -d openobserve otel-collector
trap - EXIT
printf '%s\n' "$archive"
