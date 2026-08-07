# Release Installation

Offline-first installation flow:

1. Acquire release bundle
2. Verify signature and trust
3. Check manifest and digests
4. Check anti-rollback sequence
5. Stage to staging root
6. Transaction journal
7. Activate atomically
8. Preserve rollback point

Failed install or activation preserves the active release.
