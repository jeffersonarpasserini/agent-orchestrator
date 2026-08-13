#!/usr/bin/env python3
"""Emit a stable snapshot of open PR checks for the Spock cron monitor."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


DEFAULT_REPOSITORY = "jeffersonarpasserini/agent-orchestrator"
EXPECTED_CHECKS = (
    "Change hygiene",
    "Python 3.12 tests",
    "Python security",
    "Validate Docker Compose",
)
FAILURE_CONCLUSIONS = {
    "ACTION_REQUIRED",
    "CANCELLED",
    "FAILURE",
    "STARTUP_FAILURE",
    "STALE",
    "TIMED_OUT",
}
SUCCESS_CONCLUSIONS = {"NEUTRAL", "SKIPPED", "SUCCESS"}


def _check_snapshot(check: dict[str, Any]) -> dict[str, str]:
    return {
        "name": str(check.get("name") or "unknown"),
        "status": str(check.get("status") or "UNKNOWN"),
        "conclusion": str(check.get("conclusion") or ""),
        "url": str(check.get("detailsUrl") or ""),
    }


def _overall(checks: list[dict[str, str]]) -> tuple[str, list[str]]:
    names = {check["name"] for check in checks}
    missing = sorted(set(EXPECTED_CHECKS) - names)
    conclusions = {check["conclusion"] for check in checks if check["conclusion"]}
    statuses = {check["status"] for check in checks}
    if conclusions & FAILURE_CONCLUSIONS:
        return "failure", missing
    if missing or not checks or statuses - {"COMPLETED"}:
        return "pending", missing
    if conclusions <= SUCCESS_CONCLUSIONS:
        return "success", missing
    return "pending", missing


def normalize(prs: list[dict[str, Any]], repository: str) -> dict[str, Any]:
    normalized = []
    for pr in sorted(prs, key=lambda item: int(item["number"])):
        checks = sorted(
            (_check_snapshot(check) for check in pr.get("statusCheckRollup") or []),
            key=lambda item: item["name"],
        )
        overall, missing = _overall(checks)
        normalized.append(
            {
                "number": int(pr["number"]),
                "title": str(pr.get("title") or ""),
                "url": str(pr.get("url") or ""),
                "head_branch": str(pr.get("headRefName") or ""),
                "head_sha": str(pr.get("headRefOid") or ""),
                "draft": bool(pr.get("isDraft")),
                "merge_state": str(pr.get("mergeStateStatus") or "UNKNOWN"),
                "overall": overall,
                "missing_expected_checks": missing,
                "checks": checks,
            }
        )
    return {"repository": repository, "expected_checks": list(EXPECTED_CHECKS), "prs": normalized}


def main() -> int:
    repository = os.environ.get("SPOCK_GITHUB_REPOSITORY", DEFAULT_REPOSITORY)
    command = [
        "gh", "pr", "list", "--repo", repository, "--state", "open",
        "--json", "number,title,url,headRefName,headRefOid,isDraft,mergeStateStatus,statusCheckRollup",
        "--limit", "100",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)  # nosec B603
        payload = normalize(json.loads(result.stdout), repository)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        payload = {"repository": repository, "monitor_error": type(exc).__name__}
    json.dump(payload, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
