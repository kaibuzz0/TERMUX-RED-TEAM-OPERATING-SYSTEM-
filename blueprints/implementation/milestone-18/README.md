# Milestone 18 — Physical Android/Termux Validation

Milestone 18 cannot be completed by the Windows PC Hermes agent. It requires an agent or operator with access to the actual Android device running Termux.

## Required starting point

```bash
git clone https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-
cd TERMUX-RED-TEAM-OPERATING-SYSTEM-
git checkout 7da6b02
python -m pytest -q   # baseline: 529 passed, 8 skipped
```

## Run the device test plan

1. Fill in `DEVICE_BASELINE.md` with actual device values.
2. Run each section of the Milestone 18 directive and record results.
3. Add defects to `TERMUX_DEFECT_LEDGER.md` with evidence.
4. Apply fixes only to concrete device failures.
5. Add regression tests in `tests/termux/` where appropriate.
6. Do not commit simulated results.
7. Push only after review.

## Deliverable

A completed `MILESTONE18_REPORT.md` with physical evidence and a clean or accepted-defect ledger.
