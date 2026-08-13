#!/usr/bin/env bash
set -euo pipefail

umask 077

profile_env="${TUVOK_ENV_FILE:-/home/jeffersonpasserini/.hermes/profiles/tuvok/.env}"
data_dir="${DEPENDENCY_CHECK_DATA_DIR:-/home/jeffersonpasserini/.hermes/data/dependency-check}"
dependency_check_bin="${DEPENDENCY_CHECK_BIN:-/home/jeffersonpasserini/.local/bin/dependency-check}"
timeout_seconds="${NVD_UPDATE_TIMEOUT_SECONDS:-1800}"

fail() {
  printf 'NVD update failed: %s\n' "$1" >&2
  exit 1
}

[[ -r "$profile_env" ]] || fail "profile environment is not readable"
[[ -x "$dependency_check_bin" ]] || fail "Dependency-Check is not executable"
[[ "$timeout_seconds" =~ ^[1-9][0-9]*$ ]] || fail "timeout must be a positive integer"

mkdir -p "$data_dir"

set -a
# shellcheck disable=SC1090 -- the profile environment is selected by configuration.
source "$profile_env"
set +a

[[ -n "${NVD_API_KEY:-}" ]] || fail "NVD_API_KEY is not configured"

if timeout --signal=TERM --kill-after=30s "${timeout_seconds}s" \
  "$dependency_check_bin" \
  --updateonly \
  --data "$data_dir" \
  --disableKnownExploited \
  --disableRetireJs; then
  :
else
  status=$?
  if [[ $status -eq 124 || $status -eq 137 ]]; then
    fail "Dependency-Check exceeded ${timeout_seconds}s"
  fi
  fail "Dependency-Check exited with status $status"
fi

printf 'NVD local database update completed successfully\n'
