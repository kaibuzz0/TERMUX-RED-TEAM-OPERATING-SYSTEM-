# Move Plan

## Philosophy

No big-bang rewrite. Moves happen after compatibility layers and tests are in place.

## Milestone sequencing

1. **M1: Canonical-source declaration** — add metadata and tests; no runtime moves.
2. **M2: Compatibility launcher** — establish canonical dispatcher; old commands route through it.
3. **M3-M10:** incremental component migration (paths, auth, installer, updater, state, supervisor, workspaces, agent broker, Hermes plugin, TUI).
4. **M12:** legacy archive migration — move `Hive Ops DevAI/` and `Hive Ops Final/original hive os complete/` to `archive/` only after references are resolved.

## Move rules

- Every move is preceded by a compatibility layer or alias.
- Tests must pass before and after the move.
- Old paths remain functional during deprecation period.
- User data is never moved.
- No moves are performed in Phase 2.
