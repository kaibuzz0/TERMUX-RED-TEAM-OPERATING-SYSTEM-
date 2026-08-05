"""Hive OS verified update and recovery package."""

from __future__ import annotations

from updates.errors import (
    AntiRollbackError,
    BundleError,
    CompatibilityError,
    RollbackError,
    TrustError,
    UpdateError,
)
from updates.trust import TrustLevel, TrustStore
from updates.metadata import build_metadata, parse_metadata
from updates.signing import generate_keypair, sign_metadata, verify_metadata
from updates.verifier import BundleVerifier
from updates.updater import Updater
from updates.recovery import diagnose, RecoveryLevel

__all__ = [
    "AntiRollbackError",
    "BundleError",
    "CompatibilityError",
    "RollbackError",
    "TrustError",
    "UpdateError",
    "TrustLevel",
    "TrustStore",
    "build_metadata",
    "parse_metadata",
    "generate_keypair",
    "sign_metadata",
    "verify_metadata",
    "BundleVerifier",
    "Updater",
    "diagnose",
    "RecoveryLevel",
]
