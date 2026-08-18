# Investigation Items

## INV-001: Investigate whether hivedev tooling ever generated or distributed a real signing key

- **Linked audit finding:** HRA-001
- **Owner:** security
- **Deliverable:** Signed memo or incident report; key rotation plan if needed
- **Due before:** Before REM-002 merges

## INV-002: Determine if command-site-snapshot workflow should exist on bootstrap branch

- **Linked audit finding:** HRA-016
- **Owner:** release
- **Deliverable:** Decision: keep on master only vs. restore on bootstrap; branch strategy doc
- **Due before:** Before REM-007

## INV-003: Evaluate pywin32 vs. ctypes for Windows ACL snapshot in REM-003

- **Linked audit finding:** HRA-003
- **Owner:** platform
- **Deliverable:** Spike PR with benchmark and dependency analysis
- **Due before:** Before REM-003 implementation

## INV-004: Survey Termux community for install/update pain points not covered by tests

- **Linked audit finding:** HRA-004
- **Owner:** termux-portability
- **Deliverable:** Issue list and prioritized backlog
- **Due before:** Before REM-008

