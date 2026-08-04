# Update Test Matrix

| Scenario | Environment | Expected result |
|----------|-------------|-----------------|
| Normal signed update | Physical Android | Stages, verifies, applies, health check passes |
| Update with local changes | Physical Android | Preserves uncommitted user files or aborts cleanly |
| Failed update | Physical Android | Health check fails, automatic rollback |
| Forced update with bad signature | CI | Rejects update, leaves current runtime intact |
| Offline bundle update | Physical Android | Verifies bundle digest, applies, rolls back if health fails |
