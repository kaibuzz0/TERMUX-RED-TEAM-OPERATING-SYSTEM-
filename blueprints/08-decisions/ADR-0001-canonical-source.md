# ADR-0001: Canonical Source Decision

## Status

Proposed — pending human review.

## Context

The repository contains two parallel production trees (`Hive Ops Final/` and `Hive Ops DevAI/`) plus root-level installers. The project needs one declared canonical source so that installation, update, repair, and documentation can be consistent.

## Decision

- **Canonical foundation:** `Hive Ops Final/` after limited security and consistency repair.
- **Reference only:** `Hive Ops DevAI/` — selectively merge capabilities, not keep as a second root.
- **Root scripts:** keep as top-level entry points, rewrite for transactionality and verification.

## Consequences

- Install/update/repair scripts must be updated to operate on the canonical tree only.
- DevAI features (agents, orchestrator, specialist tools) must be ported into the canonical architecture with bounded behavior.
- The embedded `original hive os complete/` legacy subtree must be archived.

## Rejected alternatives

- Making `Hive Ops DevAI/` canonical: it is not maintained by the current updater/repair scripts and is more fragmented.
- Keeping both trees: perpetuates divergence and user confusion.
- Rewriting from scratch: the directive forbids replacement/clean-room rewrite; transform the existing repo.
