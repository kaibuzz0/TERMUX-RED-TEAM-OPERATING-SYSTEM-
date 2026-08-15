"""Diagnostic finding model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from diagnostics.severity import Severity


@dataclass
class Finding:
    code: str
    severity: Severity
    component: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    remediation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity.value,
            "component": self.component,
            "message": self.message,
            "evidence": self.evidence,
            "remediation": self.remediation,
        }
