#!/usr/bin/env python3
"""Export the repo-factory toolset into a target repository."""
from __future__ import annotations
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
TOKEN = "{{PROJECT_NAME}}"


def files():
    return [p for p in TEMPLATES.rglob("*") if p.is_file()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path)
    ap.add_argument("--project-name", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    target = args.target.expanduser().resolve()
    planned = []
    for src in files():
        rel = src.relative_to(TEMPLATES)
        dst = target / rel
        if dst.exists() and not args.force:
            raise SystemExit(f"refusing to overwrite existing file: {rel}")
        planned.append((src, dst, rel))
    for src, dst, rel in planned:
        print(rel)
        if args.dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8").replace(TOKEN, args.project_name)
        dst.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
