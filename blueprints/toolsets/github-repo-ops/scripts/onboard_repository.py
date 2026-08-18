#!/usr/bin/env python3
"""Generate a portable connector kit for another repository."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


def check(repo_id: str, full_name: str, url: str) -> list[str]:
    errors = []
    if not ID_RE.fullmatch(repo_id):
        errors.append("invalid repo-id")
    if full_name.count("/") != 1 or any(not x for x in full_name.split("/")):
        errors.append("full-name must be OWNER/REPOSITORY")
    parsed = urlparse(url)
    if parsed.scheme != "https":
        errors.append("snapshot-url must use https")
    host = parsed.hostname or ""
    if host != "raw.githubusercontent.com" and not host.endswith(".github.io"):
        errors.append("snapshot-url host is not approved")
    return errors


def dump(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Generate GitHub Command Site connector kit")
    p.add_argument("--repo-id", required=True)
    p.add_argument("--full-name", required=True)
    p.add_argument("--snapshot-url", required=True)
    p.add_argument("--output")
    a = p.parse_args()
    errors = check(a.repo_id, a.full_name, a.snapshot_url)
    if errors:
        print("; ".join(errors))
        return 1
    out = Path(a.output) if a.output else ROOT / "onboarding" / a.repo_id
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "connectors" / "export_repo_snapshot.py", out / "export_repo_snapshot.py")
    owner, repo = a.full_name.split("/", 1)
    dump(out / "command-site.config.json", {
        "schema_version": 1, "repo_id": a.repo_id, "full_name": a.full_name,
        "snapshot_url": a.snapshot_url,
        "notes": "Adapt mappings to canonical repository state; do not create a parallel database."
    })
    dump(out / "registry-entry.json", {
        "id": a.repo_id, "snapshot_url": a.snapshot_url, "enabled": True,
        "owner": owner, "repository": repo
    })
    (out / "README.md").write_text(
        f"# Command Site connector kit — {a.full_name}\n\n"
        "Read the target repo governance first. Copy/adapt the exporter, generate a bounded metadata snapshot, "
        "publish it at the configured HTTPS URL, then add registry-entry.json to the hub through normal review.\n\n"
        f"Example: `python export_repo_snapshot.py --repo-id {a.repo_id} --full-name {a.full_name}`\n\n"
        "Never export credentials, secrets, private keys, wallet seeds, private user data, or unbounded file bodies.\n",
        encoding="utf-8"
    )
    print(json.dumps({"output": str(out), "files": sorted(x.name for x in out.iterdir())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
