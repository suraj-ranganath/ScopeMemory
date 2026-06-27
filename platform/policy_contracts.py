"""Shared ScopeMemory runtime contracts.

These dataclasses are the typed contract artifacts for the hackathon runtime.
They intentionally contain metadata, proof references, and opaque credential
handles, but never raw credential values.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


CONTRACT_VERSION = "scopememory.policy.v0"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    AUTO_APPROVE_EPHEMERAL_GRANT = "AUTO_APPROVE_EPHEMERAL_GRANT"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"
    DENY = "DENY"
    REPAIR = "REPAIR"


class AuthorizationCheckState(str, Enum):
    CREATED = "created"
    FACTS_COMPILED = "facts_compiled"
    POLICY_EVALUATING = "policy_evaluating"
    WAITING_FOR_HUMAN = "waiting_for_human"
    APPROVED = "approved"
    AUTO_APPROVED = "auto_approved"
    DENIED = "denied"
    REPAIRABLE = "repairable"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Session:
    session_id: str
    user_id: str
    team_id: str
    agent_id: str
    goal_class: str
    goal_hash: str = ""
    agent_host: str = "scopememory-demo"


@dataclass(frozen=True)
class ToolIntent:
    session_id: str
    tool_id: str
    resource_id: str
    schema_valid: bool = True
    schema_repairable: bool = False
    requested_scope: str = ""
    access_kind: str = ""
    idempotency_key: str = ""
    signed_goal_hash: str = ""


@dataclass(frozen=True)
class RecipeHit:
    session_id: str
    recipe_id: str
    score: float
    dolt_commit: str
    qdrant_index_commit: str
    similarity_reified: bool = True
    status: str = "accepted"


@dataclass(frozen=True)
class Grant:
    grant_id: str
    session_id: str
    scope: str
    resource_id: str
    issuer: str = "policy"
    proof_id: str = ""
    ttl_seconds: int = 900
    call_count_remaining: int = 1


@dataclass(frozen=True)
class CredentialLease:
    lease_id: str
    session_id: str
    tool_id: str
    scope: str
    resource_id: str
    credential_ref: str
    credential_ref_hash: str
    provider: str
    injection_mode: str
    expires_at: str
    provider_mode: str = ""
    provider_operation_id: str = ""
    max_uses: int = 1
    secret_exposed_to_agent: bool = False


@dataclass(frozen=True)
class AccessRequest:
    request_id: str
    session_id: str
    tool_id: str
    scope: str
    resource_id: str
    decision: Decision
    proof_id: str
    safe_summary: str
    state: AuthorizationCheckState = AuthorizationCheckState.WAITING_FOR_HUMAN


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    session_id: str
    event_type: str
    body: dict[str, Any]
    previous_hash: str = ""
    event_hash: str = ""


@dataclass(frozen=True)
class PolicyProofTrace:
    decision: Decision
    session_id: str
    tool: str
    required_scope: str
    resource: str
    reason: str
    rules: list[str]
    facts: list[str]
    context_path: list[str] = field(default_factory=list)
    context_snapshot_id: str = ""
    dolt_commit: str = "demo-fixture"
    qdrant_index_commit: str = "demo-fixture"
    proof_hash: str = ""
    candidate_decisions: list[dict[str, Any]] = field(default_factory=list)
    policy_engine: str = "cozo-datalog"


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str
    session_id: str
    tool_id: str
    resource_id: str
    required_scope: str
    proof: PolicyProofTrace
    check_state: AuthorizationCheckState
    credential_lease: CredentialLease | None = None


def contract_dict(value: Any) -> dict[str, Any]:
    data = plain_data(value)
    data["contract_version"] = CONTRACT_VERSION
    return data


def canonical_json(value: Any) -> str:
    return json.dumps(plain_data(value), sort_keys=True, separators=(",", ":"))


def plain_data(value: Any) -> Any:
    def normalize(item: Any) -> Any:
        if isinstance(item, Enum):
            return item.value
        if hasattr(item, "__dataclass_fields__"):
            return {k: normalize(v) for k, v in asdict(item).items()}
        if isinstance(item, dict):
            return {str(k): normalize(v) for k, v in sorted(item.items())}
        if isinstance(item, list):
            return [normalize(v) for v in item]
        return item

    return normalize(value)


def stable_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
