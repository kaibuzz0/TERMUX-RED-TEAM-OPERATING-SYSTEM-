"""Policy request model and normalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from policy_engine.errors import PolicyRequestError, PolicyValidationError
from policy_engine.schema import TypedSchema, FieldSpec, check_bounded_size, validate_id


REQUEST_SCHEMA = TypedSchema(
    "policy_request",
    version=1,
    fields={
        "schema_version": FieldSpec("schema_version", int, required=True),
        "request_id": FieldSpec("request_id", str, required=True),
        "transaction_id": FieldSpec("transaction_id", str),
        "actor": FieldSpec("actor", dict, required=True),
        "capability": FieldSpec("capability", str, required=True),
        "resource": FieldSpec("resource", dict, required=True),
        "context": FieldSpec("context", dict, required=True),
    },
)

ACTOR_SCHEMA = TypedSchema(
    "actor",
    version=1,
    fields={
        "type": FieldSpec("type", str, required=True),
        "id": FieldSpec("id", str, required=True),
        "profile": FieldSpec("profile", str),
        "session_id": FieldSpec("session_id", str),
        "broker_policy_profile": FieldSpec("broker_policy_profile", str),
        "authentication_state": FieldSpec("authentication_state", str),
        "origin": FieldSpec("origin", str),
        "capability_set": FieldSpec("capability_set", list),
    },
)

RESOURCE_SCHEMA = TypedSchema(
    "resource",
    version=1,
    fields={
        "type": FieldSpec("type", str, required=True),
        "id": FieldSpec("id", str, required=True),
        "attributes": FieldSpec("attributes", dict),
    },
    allow_unknown=True,
)

CONTEXT_SCHEMA = TypedSchema(
    "context",
    version=1,
    fields={
        "configuration_profile": FieldSpec("configuration_profile", str),
        "broker_policy_profile": FieldSpec("broker_policy_profile", str),
        "runtime_platform": FieldSpec("runtime_platform", str),
        "transaction_id": FieldSpec("transaction_id", str),
        "runtime_mode": FieldSpec("runtime_mode", str),
        "maintenance_mode": FieldSpec("maintenance_mode", bool),
        "recovery_mode": FieldSpec("recovery_mode", bool),
        "vault_state": FieldSpec("vault_state", str, allowed_values={"LOCKED", "UNLOCKED", "UNKNOWN"}),
        "active_release": FieldSpec("active_release", str),
        "rollback_available": FieldSpec("rollback_available", bool),
        "service_state": FieldSpec("service_state", str),
        "update_verification_state": FieldSpec("update_verification_state", str),
        "physical_validation_status": FieldSpec("physical_validation_status", str),
        "operator_confirmation_state": FieldSpec("operator_confirmation_state", dict),
        "approval_state": FieldSpec("approval_state", dict),
        "broker_version": FieldSpec("broker_version", str),
        "policy_version": FieldSpec("policy_version", int),
        "broker_policy_profile": FieldSpec("broker_policy_profile", str),
        "current_time": FieldSpec("current_time", (int, float)),
        "manifest_digest": FieldSpec("manifest_digest", str),
        "runtime_platform": FieldSpec("runtime_platform", str),
        "transaction_id": FieldSpec("transaction_id", str),
    },
    allow_unknown=True,
)

KNOWN_SCHEMA_VERSIONS = {1}


@dataclass(frozen=True)
class PolicyRequest:
    """Normalized policy evaluation request."""

    schema_version: int
    request_id: str
    transaction_id: str
    actor: dict[str, Any]
    capability: str
    resource: dict[str, Any]
    context: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyRequest":
        """Normalize and validate a raw request."""
        check_bounded_size(data, max_size=1000, max_depth=8)
        validated = REQUEST_SCHEMA.validate(data)
        schema_version = validated["schema_version"]
        if schema_version not in KNOWN_SCHEMA_VERSIONS:
            raise PolicyRequestError(f"Unsupported policy request schema version: {schema_version}")

        actor = ACTOR_SCHEMA.validate(validated["actor"])
        resource = RESOURCE_SCHEMA.validate(validated["resource"])
        context = CONTEXT_SCHEMA.validate(validated["context"])

        validate_id(validated["request_id"], "request_id")
        if validated.get("transaction_id"):
            validate_id(validated["transaction_id"], "transaction_id")
        from policy_engine.actors import validate_actor
        from policy_engine.capabilities import validate_capability
        from policy_engine.resources import validate_resource
        validate_actor(actor["type"])
        validate_id(actor["id"], "actor.id")
        validate_resource(resource["type"])
        validate_id(resource["id"], "resource.id")
        validate_capability(validated["capability"])

        return cls(
            schema_version=schema_version,
            request_id=validated["request_id"],
            transaction_id=validated.get("transaction_id", ""),
            actor=actor,
            capability=validated["capability"],
            resource=resource,
            context=context,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "transaction_id": self.transaction_id,
            "actor": self.actor,
            "capability": self.capability,
            "resource": self.resource,
            "context": self.context,
        }
