#!/usr/bin/env python3
"""Fail CI when GitHub workflows use floating external action refs.

This is intentionally offline and deterministic: it verifies repository policy
(format and version annotations), while upstream existence is checked during
maintenance/review when pins are changed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

WORKFLOW_DIR = Path('.github/workflows')
USES_RE = re.compile(r'^\s*-?\s*uses:\s*([^\s#]+)(?:\s+#\s*(.+))?\s*$')
PIN_RE = re.compile(r'^(?P<action>[^@]+)@(?P<ref>[0-9a-fA-F]{40})$')
VERSION_RE = re.compile(r'\bv\d+(?:\.\d+){0,2}\b')


def main() -> int:
    failures: list[str] = []
    if not WORKFLOW_DIR.is_dir():
        print('workflow-pin: no workflow directory found', file=sys.stderr)
        return 2

    files = sorted([*WORKFLOW_DIR.glob('*.yml'), *WORKFLOW_DIR.glob('*.yaml')])
    if not files:
        print('workflow-pin: no workflow files found', file=sys.stderr)
        return 2

    checked = 0
    for path in files:
        for lineno, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            match = USES_RE.match(line)
            if not match:
                continue
            value = match.group(1)
            comment = (match.group(2) or '').strip()
            if value.startswith('./'):
                continue
            checked += 1
            pin = PIN_RE.match(value)
            if not pin:
                failures.append(f'{path}:{lineno}: external action is not pinned to a 40-char SHA: {value}')
                continue
            if not VERSION_RE.search(comment):
                failures.append(f'{path}:{lineno}: pinned action is missing a version comment: {value}')

    if failures:
        print('workflow-pin: FAIL', file=sys.stderr)
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    print(f'workflow-pin: PASS ({checked} external action uses checked)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
