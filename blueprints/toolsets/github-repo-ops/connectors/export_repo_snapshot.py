#!/usr/bin/env python3
"""Portable bounded exporter for GitHub Command Site connected repositories."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

MAX_JSON_BYTES = 2_000_000
MAX_ITEMS = 500
MAX_REPOSITORY_FILES = 5000
MAX_REPOSITORY_DIRECTORIES = 2500


def git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def doc(path: Path) -> dict:
    if not path.exists() or path.stat().st_size > MAX_JSON_BYTES:
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def collection(path: Path, *keys: str) -> list:
    data = doc(path)
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value[:MAX_ITEMS]
    return []


def tracked_files() -> list[str]:
    raw = git("ls-files", "-z")
    return sorted(x for x in raw.split("\0") if x)


def recent_activity(full_name: str, limit: int = 10) -> list[dict]:
    raw = git("log", f"-{limit}", "--pretty=format:%H%x1f%aI%x1f%s")
    rows = []
    for line in raw.splitlines() if raw else []:
        parts = line.split("\x1f", 2)
        if len(parts) == 3:
            sha, stamp, title = parts
            rows.append({"id": sha, "type": "commit", "title": title, "timestamp": stamp,
                         "url": f"https://github.com/{full_name}/commit/{sha}"})
    return rows


def generic_stats(files: list[str]) -> dict:
    lower = [x.lower() for x in files]
    return {
        "tracked_files": len(files),
        "python_files": sum(x.endswith(".py") for x in lower),
        "javascript_typescript_files": sum(x.endswith((".js", ".mjs", ".cjs", ".ts", ".tsx")) for x in lower),
        "workflow_files": sum(x.startswith(".github/workflows/") for x in lower),
        "test_files": sum("test" in PurePosixPath(x).name.lower() for x in files),
    }


def repository_inventory(files: list[str]) -> dict:
    directory_counts: dict[str, int] = {}
    for file_path in files:
        parts = PurePosixPath(file_path).parts
        for index in range(1, len(parts)):
            directory = "/".join(parts[:index])
            directory_counts[directory] = directory_counts.get(directory, 0) + 1
    directories = [{"path": path, "name": PurePosixPath(path).name,
                    "depth": len(PurePosixPath(path).parts), "file_count": count}
                   for path, count in sorted(directory_counts.items())[:MAX_REPOSITORY_DIRECTORIES]]
    exported_files = [{"path": path, "name": PurePosixPath(path).name,
                       "extension": PurePosixPath(path).suffix.lower()}
                      for path in files[:MAX_REPOSITORY_FILES]]
    top_level = sorted({PurePosixPath(path).parts[0] for path in files if PurePosixPath(path).parts})
    return {"total_files": len(files), "total_directories": len(directory_counts),
            "files_truncated": len(files) > len(exported_files),
            "directories_truncated": len(directory_counts) > len(directories),
            "top_level": top_level, "directories": directories, "files": exported_files}


def identity(repo_id: str | None, full_name: str | None, default_branch: str | None) -> tuple[str, str, str]:
    full = full_name or os.getenv("GITHUB_REPOSITORY") or "unknown/unknown"
    name = full.split("/", 1)[-1]
    rid = repo_id or name.lower()
    branch = default_branch or os.getenv("COMMAND_SITE_DEFAULT_BRANCH") or git("branch", "--show-current") or "main"
    return rid, full, branch


def build(repo_id: str | None, full_name: str | None, default_branch: str | None) -> dict:
    root = Path.cwd()
    rid, full, branch = identity(repo_id, full_name, default_branch)
    commit = git("rev-parse", "HEAD") or "unknown-commit"
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    site, data = root / "site-data", root / "data"
    files = tracked_files()
    stats = generic_stats(files)
    status = doc(site / "status.json")
    if status:
        stats["project_status"] = status
    return {
        "schema_version": 1,
        "generated_at": now,
        "source_commit": commit,
        "repo": {"id": rid, "full_name": full, "url": f"https://github.com/{full}", "default_branch": branch},
        "stats": stats,
        "repository_tree": repository_inventory(files),
        "tools": collection(data / "tools.json", "items", "tools"),
        "toolsets": collection(site / "toolsets.json", "items", "toolsets"),
        "cases": collection(site / "cases.json", "items", "cases"),
        "opportunities": collection(data / "opportunities.json", "items", "opportunities"),
        "intelligence": collection(data / "intelligence.json", "items", "intelligence"),
        "sources": collection(site / "sources.json", "sources", "items") or collection(data / "intelligence_sources.json", "sources", "items"),
        "prompts": collection(data / "prompts.json", "prompts", "items"),
        "evidence": collection(site / "artifacts.json", "items", "artifacts"),
        "agent_ops": doc(site / "agent-ops.json"),
        "activity": recent_activity(full),
        "links": [
            {"id": "github", "name": "GitHub repository", "url": f"https://github.com/{full}"},
            {"id": "actions", "name": "GitHub Actions", "url": f"https://github.com/{full}/actions"},
            {"id": "issues", "name": "Issues", "url": f"https://github.com/{full}/issues"},
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id")
    parser.add_argument("--full-name")
    parser.add_argument("--default-branch")
    parser.add_argument("--output", default=".command-site/repo-snapshot.json")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build(args.repo_id, args.full_name, args.default_branch)
    output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
