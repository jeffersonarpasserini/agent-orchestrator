#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 BACKUP.tar.gz" >&2
  exit 2
fi

archive=$1
test -f "$archive"
test -f "$archive.sha256"
archive_dir=$(CDPATH= cd -- "$(dirname -- "$archive")" && pwd)
archive_name=$(basename "$archive")
(cd "$archive_dir" && sha256sum -c "$archive_name.sha256")

volume="agent-orchestrator-openobserve-restore-verify-$(date -u +%Y%m%d%H%M%S)"
docker volume create "$volume" >/dev/null
cleanup() { docker volume rm "$volume" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker run --rm \
  -v "$volume:/restore" \
  -v "$archive_dir:/backup:ro" \
  busybox:1.37.0 \
  tar -C /restore -xzf "/backup/$archive_name"
docker run --rm -v "$volume:/restore:ro" busybox:1.37.0 \
  sh -c 'test -d /restore && test "$(find /restore -mindepth 1 | head -1)"'
printf '%s\n' "restore verification passed"
