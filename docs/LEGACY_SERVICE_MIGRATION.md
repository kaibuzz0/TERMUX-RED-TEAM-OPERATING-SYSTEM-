# Legacy Service Migration

The legacy `.svc` loader (`hive_services.sh`) is preserved as a known-working Android/Termux baseline.

The native adapter parses `.svc` files textually without sourcing or executing them. Each field is classified as `SAFE_TO_TRANSLATE`, `REQUIRES_REVIEW`, `UNSUPPORTED_SHELL`, or `DANGEROUS`.

Migration is plan-only in Milestone 11. Use `hive service migrate-legacy` to inspect proposals.
