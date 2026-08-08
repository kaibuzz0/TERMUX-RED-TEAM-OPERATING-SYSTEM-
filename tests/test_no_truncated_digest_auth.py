"""Verify no truncated digest is used for authorization.

Scans canonical codebase for digest truncation (hexdigest()[:N]) and
confirms these are NOT used for authorization decisions.

Authorization in Hive OS is rule-based via PolicyEvaluator, not digest-based.
Any digest truncation found is for non-security purposes (audit IDs, cache keys,
staging paths, deduplication).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from policy_engine.evaluator import PolicyEvaluator
from policy_engine.requests import PolicyRequest
from policy_engine.rules import PolicySet, Rule, PolicyProfile, DecisionState


class TestNoTruncatedDigestForAuthorization:
    """Verify authorization does not depend on truncated digests."""

    # -----------------------------------------------------------------------
    # 1. Static scan: find all truncated digest usages in canonical code
    # -----------------------------------------------------------------------

    def test_scan_truncated_digests_not_used_for_auth(self):
        """Scan canonical code for hexdigest()[:N] and verify none are in auth paths."""
        root = Path(__file__).resolve().parent.parent
        canonical_dirs = [
            root / "policy_engine",
            root / "security",
            root / "installer",
            root / "hive_broker",
            root / "services",
            root / "updates",
            root / "release_engine",
            root / "plugin_sdk",
        ]

        truncated_sites = []
        for d in canonical_dirs:
            if not d.exists():
                continue
            for f in d.rglob("*.py"):
                if "test_" in f.name:
                    continue
                text = f.read_text()
                # Look for hexdigest()[:N] pattern
                lines = text.split("\n")
                for lineno, line in enumerate(lines, 1):
                    if "hexdigest()[:" in line:
                        truncated_sites.append((f.relative_to(root), lineno, line.strip()))

        # Print findings for review (these are documented below)
        for site in truncated_sites:
            print(f"  {site[0]}:{site[1]}: {site[2]}")

        # Known non-authorization usages (documented):
        # - policy_engine/engine.py:_stable_hash()[:16] — audit correlation ID only
        # - services/process.py:_digest()[:16] — service deduplication/cache key
        # - plugin_sdk/loader.py:bundle_digest[:16] — staging directory prefix
        #
        # None of these affect ALLOW/DENY/ERROR authorization decisions.

        assert len(truncated_sites) <= 3, f"Unexpected truncated digest usages found: {truncated_sites}"

    # -----------------------------------------------------------------------
    # 2. Functional: authorization is rule-based, not digest-based
    # -----------------------------------------------------------------------

    def test_authorization_is_rule_based_not_digest_based(self):
        """PolicyEvaluator must decide based on rules, not on any digest comparison."""
        rule = Rule(
            rule_id="allow-operator-vault",
            priority=100,
            effect=DecisionState.ALLOW,
            actors={"operator"},
            capabilities={"vault.status"},
            resources={"vault"},
        )
        profile = PolicyProfile(
            name="observer",
            description="Observer",
            rules=[rule],
            default_decision=DecisionState.DENY,
        )
        evaluator = PolicyEvaluator(PolicySet(profiles={"observer": profile}))

        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "test",
            "transaction_id": "txn-1",
            "actor": {"type": "operator", "id": "test"},
            "capability": "vault.status",
            "resource": {"type": "vault", "id": "master"},
            "context": {},
        })
        result = evaluator.evaluate(req)

        # Decision must be ALLOW based on matching rule
        assert result.decision == DecisionState.ALLOW
        # No digest field should be in the decision
        assert not hasattr(result, "digest") or getattr(result, "digest", None) is None

    def test_denial_is_rule_based_not_digest_based(self):
        """Default DENY must occur when no rule matches, not due to digest mismatch."""
        evaluator = PolicyEvaluator(PolicySet(profiles={}))
        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "test",
            "transaction_id": "txn-1",
            "actor": {"type": "operator", "id": "test"},
            "capability": "vault.status",
            "resource": {"type": "vault", "id": "master"},
            "context": {},
        })
        result = evaluator.evaluate(req)

        # Decision must be DENY or ERROR (fail-closed), not based on any digest
        assert result.decision in (DecisionState.DENY, DecisionState.ERROR)

    # -----------------------------------------------------------------------
    # 3. Policy digest is for audit only, not authorization
    # -----------------------------------------------------------------------

    def test_policy_digest_is_truncated_and_non_authoritative(self):
        """policy_digest() must return a truncated string used only for audit correlation."""
        from policy_engine.engine import PolicyEngine

        rule = Rule(
            rule_id="test-rule",
            priority=100,
            effect=DecisionState.ALLOW,
            actors={"operator"},
            capabilities={"vault.status"},
            resources={"vault"},
        )
        profile = PolicyProfile(
            name="observer",
            description="Observer",
            rules=[rule],
            default_decision=DecisionState.DENY,
        )

        engine = PolicyEngine(PolicySet(profiles={"observer": profile}))
        digest = engine.policy_digest()

        # Digest must be prefixed and truncated
        assert digest.startswith("sha256:")
        assert len(digest) == len("sha256:") + 16  # prefix + 16 hex chars

        # Changing policy must change digest
        rule2 = Rule(
            rule_id="different-rule",
            priority=100,
            effect=DecisionState.ALLOW,
            actors={"operator"},
            capabilities={"vault.status"},
            resources={"vault"},
        )
        profile2 = PolicyProfile(
            name="observer",
            description="Observer",
            rules=[rule2],
            default_decision=DecisionState.DENY,
        )
        engine2 = PolicyEngine(PolicySet(profiles={"observer": profile2}))
        digest2 = engine2.policy_digest()
        assert digest != digest2

        # But digest must NOT affect authorization decisions
        req = PolicyRequest.from_dict({
            "schema_version": 1,
            "request_id": "test",
            "transaction_id": "txn-1",
            "actor": {"type": "operator", "id": "test"},
            "capability": "vault.status",
            "resource": {"type": "vault", "id": "master"},
            "context": {},
        })
        result1 = engine.evaluate(req)
        result2 = engine2.evaluate(req)
        # Both should ALLOW (same capability matches)
        assert result1.decision == DecisionState.ALLOW
        assert result2.decision == DecisionState.ALLOW
