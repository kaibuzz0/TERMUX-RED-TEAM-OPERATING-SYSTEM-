"""Documentation hygiene: no new hardcoded absolute paths in production docs.

Historical/reference markdown under Hive Ops DevAI/, Hive Ops Final/, and
MILESTONE*_REPORT.md are allowed to keep their original host-specific paths for
audit continuity. Production-facing docs (README.md, website/, docs/, blueprints/)
must not introduce new hardcoded absolute paths.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_DOC_GLOBS = [
    "README.md",
    "website/**/*.md",
    "docs/**/*.md",
    "blueprints/remediation/**/*.md",
    "evidence/**/*.md",
]
EXCLUDED_PATHS = {
    REPO_ROOT / "docs" / "ORIGINAL_RUNTIME_PARITY.md",
    REPO_ROOT / "docs" / "PATH_MODEL.md",
    REPO_ROOT / "docs" / "RUNTIME_ENVIRONMENT.md",
    REPO_ROOT / "docs" / "COMPATIBILITY_LAUNCHERS.md",
}


def _is_placeholder(match: str) -> bool:
    """Ignore ellipsis placeholders like /home/... or /root/..."""
    return "..." in match

# Raw regex strings: do not over-escape.
ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"/home/[^/\s/`]+/?[^\s`.,]*"),
    re.compile(r"/root/[^\s`]*"),
    re.compile(r"[A-Za-z]:\\[^\s`]*"),
    re.compile(r"/Users/[^/\s/`]+/?[^\s`]*"),
]


def _is_marked_example(line: str, start: int) -> bool:
    prefix = line[:start].lower()
    return "example" in prefix or "e.g." in prefix


@pytest.mark.parametrize("glob", PRODUCTION_DOC_GLOBS)
def test_no_new_absolute_paths_in_production_docs(glob: str) -> None:
    bad = []
    for path in REPO_ROOT.glob(glob):
        if not path.is_file() or path in EXCLUDED_PATHS:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            for pat in ABSOLUTE_PATH_PATTERNS:
                for m in pat.finditer(line):
                    if _is_marked_example(line, m.start()) or _is_placeholder(m.group()):
                        continue
                    bad.append((path, m.group(), lineno))

    lines = [
        f"  {p.relative_to(REPO_ROOT)}:{line}: {match!r}"
        for p, match, line in bad[:50]
    ]
    if bad:
        msg = (
            "Production docs contain absolute host-specific paths:\n"
            + "\n".join(lines)
        )
        raise AssertionError(msg)
