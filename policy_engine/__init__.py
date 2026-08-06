"""Hive OS Policy & Permission Engine.

The Policy Engine is the single authorization authority for the platform.
It evaluates requests and returns structured decisions.
It never executes actions.
"""

from __future__ import annotations

from policy_engine.engine import PolicyEngine
from policy_engine.decisions import Decision, DecisionState
from policy_engine.errors import PolicyError
from policy_engine.requests import PolicyRequest

__all__ = ["PolicyEngine", "Decision", "DecisionState", "PolicyError", "PolicyRequest"]

__version__ = "1.0.0"
