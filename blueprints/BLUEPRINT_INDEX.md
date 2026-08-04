# HIVE OS Blueprint Index

**Repository:** `https://github.com/kaibuzz0/TERMUX-RED-TEAM-OPERATING-SYSTEM-`
**Local clone:** `E:/Hermes-USB-Portable-main/TERMUX-RED-TEAM-OPERATING-SYSTEM-`
**Phase:** 2 — Target Architecture and Blueprint Freeze Preparation

## Sections

### 00-baseline
- `REPOSITORY_BASELINE.md`
- `ENVIRONMENT_BASELINE.md` — includes Windows-vs-Termux qualification labels
- `EVIDENCE_INDEX.md`
- `raw_inventory.json`
- `head_inspection_dump.md`

### 01-repository-forensics
- `COMPLETE_FILE_INVENTORY.md`
- `DIRECTORY_PURPOSE_MAP.md`
- `ENTRYPOINT_MAP.md`
- `COMMAND_MAP.md`
- `INSTALLATION_FLOW.md`
- `UPDATE_FLOW.md`
- `REPAIR_FLOW.md`
- `HERMES_INTEGRATION_MAP.md`
- `DUPLICATION_MATRIX.md`
- `UNKNOWN_COMPONENTS.md`
- `SKILL_MODIFICATION_DISCLOSURE.md`

### 02-current-system-model
- `CURRENT_ARCHITECTURE.md`
- `CURRENT_COMPONENT_CATALOG.md`
- `CURRENT_DATA_FLOWS.md`
- `CURRENT_PROCESS_MODEL.md`
- `CURRENT_TRUST_BOUNDARIES.md`
- `CURRENT_NETWORK_MODEL.md`
- `CURRENT_PERMISSION_MODEL.md`
- `CURRENT_FAILURE_MODES.md`

### 03-security
- `THREAT_MODEL.md`
- `SECURITY_INVARIANTS.md` — 12 invariants
- `ATTACK_SURFACE.md`
- `SECRET_HANDLING_AUDIT.md`
- `SHELL_SAFETY_AUDIT.md`
- `SUPPLY_CHAIN_AUDIT.md`
- `NETWORK_EXPOSURE_AUDIT.md`
- `AGENT_THREAT_MODEL.md`
- `ROOT_VS_NONROOT_SECURITY.md`
- `SECURITY_RISK_REGISTER.md`

### 04-target-architecture
- `HIVE_OS_VISION.md`
- `TARGET_ARCHITECTURE.md`
- `COMPONENT_SPECIFICATIONS.md`
- `CONTROL_PLANE_SPEC.md`
- `WORKSPACE_SPEC.md`
- `AGENT_CONTROL_SPEC.md`
- `HERMES_PLUGIN_SPEC.md`
- `POLICY_ENGINE_SPEC.md`
- `VAULT_SPEC.md`
- `SERVICE_SUPERVISOR_SPEC.md`
- `UPDATE_SYSTEM_SPEC.md`
- `RECOVERY_SYSTEM_SPEC.md`
- `BACKUP_SYSTEM_SPEC.md`
- `TUI_SPEC.md`
- `COMMAND_API_SPEC.md`
- `CONFIGURATION_SCHEMA_SPEC.md`
- `LOGGING_AND_AUDIT_SPEC.md`
- `RESOURCE_MANAGEMENT_SPEC.md`
- `ROLLBACK_SAFETY_GUIDE.md`

### 05-platform-design
- `STANDARD_TERMUX_PROFILE.md`
- `TERMUX_API_PROFILE.md`
- `ROOT_ENHANCED_PROFILE.md`
- `PROOT_COMPATIBILITY_PROFILE.md`
- `DESKTOP_LINUX_PROFILE.md`
- `CUSTOM_ROM_RESEARCH_PROFILE.md`
- `ANDROID_LIFECYCLE_MODEL.md`
- `STORAGE_MODEL.md`
- `BATTERY_AND_THERMAL_MODEL.md`
- `PLATFORM_CONTROL_MATRIX.md`
- `DEVICE_SUPPORT_MATRIX.md`

### 06-migration
- `CANONICAL_SOURCE_DECISION.md`
- `FILE_CLASSIFICATION_LEDGER.md`
- `TARGET_REPOSITORY_TREE.md`
- `MOVE_PLAN.md`
- `ARCHIVE_PLAN.md`
- `COMPATIBILITY_PLAN.md`
- `CONFIG_MIGRATION_PLAN.md`
- `DATA_MIGRATION_PLAN.md`
- `ROLLBACK_PLAN.md`
- `PHASED_IMPLEMENTATION_PLAN.md`

### 07-verification
- `ACCEPTANCE_CRITERIA.md`
- `TEST_ARCHITECTURE.md`
- `SECURITY_TEST_PLAN.md`
- `INSTALL_TEST_MATRIX.md`
- `UPDATE_TEST_MATRIX.md`
- `RECOVERY_TEST_MATRIX.md`
- `HERMES_INTEGRATION_TEST_PLAN.md`
- `PHYSICAL_TERMUX_VALIDATION_PLAN.md`
- `PERFORMANCE_BUDGETS.md`
- `RELEASE_GATES.md`

### 08-decisions
- `ADR-TEMPLATE.md`
- `ADR-0001-canonical-source.md`
- `ADR-0002-hermes-integration-boundary.md`
- `ADR-0003-termux-security-boundary.md`
- `ADR-0004-control-plane.md`
- `ADR-0005-storage-layout.md`
- `ADR-0006-agent-permissions.md`
- `ADR-0007-dependency-authority.md`
- `ADR-0008-session-gate-terminology.md`
- `ADR-0009-policy-enforcement-boundary.md`
- `ADR-0010-update-trust-model.md`
- `ADR-0011-recovery-model.md`

### 09-diagrams
- `current-system.mmd`
- `boot-flow.mmd`
- `command-flow.mmd`
- `trust-boundaries.mmd`
- `data-flow.mmd`
- `current-network-model.mmd`
- `target-system.mmd`
- `target-control-plane.mmd`
- `target-hermes-integration.mmd`
- `target-agent-permission-flow.mmd`
- `target-update-flow.mmd`
- `target-recovery-flow.mmd`
- `target-storage-flow.mmd`
- `platform-boundaries.mmd`
- `migration-sequence.mmd`

### 10-reviews
- `ARCHITECT_REVIEW.md`
- `SECURITY_REVIEW.md`
- `TERMUX_REVIEW.md`
- `TESTABILITY_REVIEW.md`
- `RECOVERY_REVIEW.md`
- `BLUEPRINT_GAP_REPORT.md`
- `BLUEPRINT_FREEZE_REPORT.md`

### Phase reports
- `PHASE0_COMPLETION_REPORT.md`
- `PHASE1_COMPLETION_REPORT.md`
- `PHASE2_COMPLETION_REPORT.md`

## Blueprint freeze classification

**CONDITIONALLY READY**

Phase 0, 1, and 2 deliverables are complete. The blueprint is ready for human review and, after acceptance, for Milestone 1 implementation.

## Important caveat

All runtime claims remain **UNVERIFIED ON TERMUX**. Physical Android validation is required before release.
