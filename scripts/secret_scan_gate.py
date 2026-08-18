#!/usr/bin/env python3
"""Hive secret-scan gate.

Runs from repo root. Exits non-zero if any literal private-key or high-risk
secret marker is found in the current tree. Audit evidence is allowed to
reference the historical finding using a redacted placeholder.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SECRET_MARKERS = [
    r"-----BEGIN\s+RSA\s+PRIVATE\s+KEY-----",
    r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----",
    r"-----BEGIN\s+EC\s+PRIVATE\s+KEY-----",
    r"-----BEGIN\s+DSA\s+PRIVATE\s+KEY-----",
    r"-----BEGIN\s+PRIVATE\s+KEY-----",
    r"-----BEGIN\s+ENCRYPTED\s+PRIVATE\s+KEY-----",
]

ALLOWED_PATHS = {
    "blueprints/audits/HERMES_AUDIT_FINDINGS.json",
    "blueprints/audits/HERMES_FULL_REPO_AUDIT.md",
}


def main() -> int:
    try:
        result = subprocess.run(
            ["git", "grep", "-I", "-n", "-E", "|".join(SECRET_MARKERS), "--", "."],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("secret-scan: git not found", file=sys.stderr)
        return 2
    if result.returncode != 0:
        print("secret-scan: no secret markers found")
        return 0
    hits = []
    for line in result.stdout.splitlines():
        path = line.split(":", 1)[0]
        if path in ALLOWED_PATHS and "[REDACTED_KEY_MARKER]" in line:
            continue
        hits.append(line)
    if not hits:
        print("secret-scan: no secret markers found")
        return 0
    print("secret-scan: found secret markers", file=sys.stderr)
    for hit in hits:
        print(hit, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
