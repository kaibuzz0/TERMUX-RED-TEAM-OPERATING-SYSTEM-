# Dashboard Reachability Analysis

**Milestone 4 — Conditional decision on `Hive Ops Final/bin/hive-dashboard`**

## Invocation sources

- `hive-dashboard` literal occurrences in canonical launcher: 1
- `dashboard` literal occurrences in canonical launcher: 8

## Direct call flow evidence

Searching canonical launcher for `dashboard` command handling:

- line 12: `hive dashboard           - Launch TUI dashboard`
- line 54: `'dashboard': self.cmd_dashboard,`
- line 264: `def cmd_dashboard(self, args):`
- line 265: `"""Launch TUI dashboard."""`
- line 266: `# Try Python dashboard first`
- line 267: `ok, out, err = self._run_python('hive-dashboard')`
- line 270: `print("Dashboard not available. Use: hive status")`

## Port and bind evidence in dashboard file

- Port-like strings found: []
- Bind address strings found: ['127.0.0.1']

## Conclusion

The canonical launcher does reference `hive-dashboard` via the `dashboard` command. The dashboard file contains `127.0.0.1` references used with `nc -z` to **probe** local SOCKS endpoints; no server constructor (`bind`, `listen`, `serve_forever`, `HTTPServer`, etc.) was found.

**Classification:** NO LISTENER EVIDENCE

**Decision:** Defer `hive-dashboard` path repair to a later milestone. It is not required for core `hive --help`, `status`, or `doctor`, and its path assumptions remain unresolved. Repair will be considered only after a separate safety review.

## Listener-related lines in dashboard file

- line 7: `import os`
- line 8: `import sys`
- line 9: `import time`
- line 10: `import json`
- line 11: `import subprocess`
- line 12: `from pathlib import Path`
- line 13: `from datetime import datetime`
- line 14: `from typing import Dict, List, Optional`
- line 37: `def _check_socks(self, port: int = 9050) -> bool:`
- line 40: `result = subprocess.run(['nc', '-z', '127.0.0.1', str(port)],`
- line 131: `port = 9052 if mode == 'local' else 9050`
- line 132: `socks_up = self._check_socks(port)`
- line 136: `print(f"║   Mode: {mode:<10} SOCKS: 127.0.0.1:{port:<5}         ║")`
- line 193: `import select`
- line 194: `import sys`

**Updated decision:** Defer `hive-dashboard` repair. It is reachable from `hive dashboard` but not required for core `hive status`, `doctor`, or `--help`. Listener presence requires a separate safety review.

## Listener construction search

Patterns checked: ['socket.bind', '.bind(', '.listen(', 'serve_forever', 'HTTPServer', 'TCPServer', 'FastAPI', 'Flask', 'uvicorn', 'http.server', 'aiohttp', 'websockets.serve']
Found: None

Result: No evidence that the dashboard itself binds or opens a listener.
