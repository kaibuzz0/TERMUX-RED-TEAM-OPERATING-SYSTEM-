"""Plugin audit trail records.

No secrets, no full environment, no raw uncontrolled stdout.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class PluginAuditRecord:
    plugin_id: str
    plugin_version: str
    manifest_digest: str
    installation_id: str
    transaction_id: str | None = None
    actor: str | None = None
    requested_capability: str | None = None
    granted_capability: str | None = None
    policy_decision: str | None = None
    execution_result: str | None = None
    lifecycle_transition: str | None = None
    signature_trust: str | None = None
    config_digest: str | None = None
    timeout: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version,
            "manifest_digest": self.manifest_digest,
            "installation_id": self.installation_id,
            "transaction_id": self.transaction_id,
            "actor": self.actor,
            "requested_capability": self.requested_capability,
            "granted_capability": self.granted_capability,
            "policy_decision": self.policy_decision,
            "execution_result": self.execution_result,
            "lifecycle_transition": self.lifecycle_transition,
            "signature_trust": self.signature_trust,
            "config_digest": self.config_digest,
            "timeout": self.timeout,
            "timestamp": self.timestamp,
        }


def redact_secrets(value: Any) -> Any:
    """Recursively redact dict/list values that look like secrets."""
    if isinstance(value, dict):
        return {k: "[redacted]" if _looks_like_secret_key(k) else redact_secrets(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_secrets(v) for v in value]
    if isinstance(value, str) and _looks_like_secret(value):
        return "[redacted]"
    return value


def _looks_like_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(term in lowered for term in ("secret", "password", "token", "key", "credential"))


def _looks_like_secret(value: str) -> bool:
    # Simple heuristic: long high-entropy strings.
    if len(value) < 16:
        return False
    digits = sum(c.isdigit() for c in value)
    upper = sum(c.isupper() for c in value)
    lower = sum(c.islower() for c in value)
    return digits >= 4 and upper >= 4 and lower >= 4
