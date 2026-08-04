# Canonical Launcher Interpreter Resolution

**Milestone 3 — Interpreter Resolution Gate**

## Target file

```text
Hive Ops Final/bin/hive
```

## Static evidence

| Attribute | Value |
|-----------|-------|
| First line | `#!/usr/bin/env python3` |
| Shebang interpreter | `python3` |
| File size | 16,023 bytes |
| Line endings | CRLF (Windows checkout) |
| Encoding | UTF-8 |
| Python compile check | **SUCCESS** |
| Bash `-n` check | Not available on Windows host |

## Syntax family markers

| Marker | Present |
|--------|---------|
| `#!/usr/bin/env python3` | Yes |
| `import ` | Yes |
| `def ` | Yes |
| `class ` | Yes |
| `[[` / `]]` | No |
| `${...}` | No |
| `#!/bin/bash` | No |
| `#!/bin/sh` | No |
| `source ` | No |
| `declare ` | No |

## Classification

**PYTHON**

The file is a Python 3 script with a valid Python shebang. It imports standard library modules (`os`, `sys`, `subprocess`, `json`, `argparse`, `pathlib`) and defines Python functions/classes.

## Execution contract

On Termux, the canonical launcher should be invoked as:

```text
python3 "Hive Ops Final/bin/hive" [ARGS...]
```

or, if executable permissions and shebang handling are confirmed:

```text
"./Hive Ops Final/bin/hive" [ARGS...]
```

The repository-level compatibility launcher (`bin/hive`) uses the active Python interpreter (`sys.executable`) to invoke the canonical launcher. This is correct for a Python target and avoids depending on executable bits or shebang resolution on Windows.

## Windows qualification

File mode `0666` on the Windows checkout is not evidence of the interpreter. The interpreter was determined from shebang and successful Python compilation, not from file permissions.

## Risk: shebang line endings

The file uses CRLF line endings due to the Windows checkout. On Termux, the shebang line may fail if the kernel sees `#!/usr/bin/env python3`. This is a known checkout/line-ending risk, not an interpreter-classification issue. Future milestones should address `.gitattributes` or checkout normalization.

## Conclusion

Milestone 2's use of `sys.executable` to invoke `Hive Ops Final/bin/hive` is architecturally correct because the target is a Python script. No launcher interpreter correction is required. However, Milestone 3 introduces explicit interpreter detection and metadata so that future launcher type changes are caught by tests.
