"""Opaque credential lease minting for ScopeMemory runtime execution.

The broker in this file does not resolve secret values. It chooses a compatible
1Password provider mode, mints an opaque lease, and fails closed when no real
provider path is ready.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum

from onepassword_readiness import OnePasswordReadiness, OnePasswordProviderStatus
from policy_contracts import CredentialLease, stable_hash


DEFAULT_LEASE_TTL_SECONDS = 900


class LeaseMintState(str, Enum):
    MINTED = "minted"
    DENIED = "denied"
    ESCALATE_HUMAN = "escalate_human"


class LeaseUseState(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    NOT_FOUND = "not_found"
    EXHAUSTED = "exhausted"


@dataclass(frozen=True)
class CredentialBinding:
    credential_ref_id: str
    provider: str
    credential_class: str
    owner_team: str
    injection_mode: str
    secret_ref_handle: str = ""


@dataclass(frozen=True)
class LeaseMintRequest:
    session_id: str
    tool_id: str
    scope: str
    resource_id: str
    binding: CredentialBinding
    ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS
    max_uses: int = 1
    would_expose_secret_to_agent: bool = False


@dataclass(frozen=True)
class LeaseMintResult:
    state: LeaseMintState
    safe_reason: str
    lease: CredentialLease | None = None
    setup_required: tuple[str, ...] = ()


@dataclass(frozen=True)
class LeaseUseRequest:
    lease_id: str
    session_id: str
    tool_id: str
    scope: str
    resource_id: str
    caller: str


@dataclass(frozen=True)
class LeaseUseResult:
    state: LeaseUseState
    safe_reason: str
    lease: CredentialLease | None = None
    evidence: dict[str, object] | None = None


@dataclass
class _LeaseRecord:
    lease: CredentialLease
    expires_at: datetime
    uses_remaining: int


class CredentialBroker:
    def __init__(
        self,
        readiness: OnePasswordReadiness,
        now: Callable[[], datetime] | None = None,
    ):
        self.readiness = readiness
        self._now = now or (lambda: datetime.now(UTC))
        self._leases: dict[str, _LeaseRecord] = {}

    def mint_lease(self, request: LeaseMintRequest) -> LeaseMintResult:
        if request.would_expose_secret_to_agent:
            return LeaseMintResult(
                state=LeaseMintState.DENIED,
                safe_reason="credential lease would expose secret material to the agent",
            )
        if request.ttl_seconds <= 0:
            return LeaseMintResult(state=LeaseMintState.DENIED, safe_reason="credential lease TTL must be positive")
        if request.max_uses <= 0:
            return LeaseMintResult(state=LeaseMintState.DENIED, safe_reason="credential lease max_uses must be positive")

        provider_mode = choose_provider_mode(self.readiness, request.binding.injection_mode)
        if provider_mode is None:
            return LeaseMintResult(
                state=_blocked_state(self.readiness),
                safe_reason="1Password provider is not ready for this credential injection mode",
                setup_required=tuple(self.readiness.setup_required),
            )

        expires_at = self._now() + timedelta(seconds=request.ttl_seconds)
        credential_ref_hash = stable_hash({
            "credential_ref_id": request.binding.credential_ref_id,
            "provider": request.binding.provider,
            "credential_class": request.binding.credential_class,
        })
        lease = CredentialLease(
            lease_id=f"lease_{uuid.uuid4().hex}",
            session_id=request.session_id,
            tool_id=request.tool_id,
            scope=request.scope,
            resource_id=request.resource_id,
            credential_ref=request.binding.credential_ref_id,
            credential_ref_hash=credential_ref_hash,
            provider=request.binding.provider,
            injection_mode=request.binding.injection_mode,
            provider_mode=provider_mode,
            provider_operation_id=f"provider_pending_{uuid.uuid4().hex}",
            expires_at=expires_at.isoformat().replace("+00:00", "Z"),
            max_uses=request.max_uses,
            secret_exposed_to_agent=False,
        )
        result = LeaseMintResult(
            state=LeaseMintState.MINTED,
            safe_reason="opaque credential lease minted; secret value remains broker-only",
            lease=lease,
        )
        self._leases[lease.lease_id] = _LeaseRecord(
            lease=lease,
            expires_at=expires_at,
            uses_remaining=request.max_uses,
        )
        return result

    def inspect_lease(self, lease_id: str) -> CredentialLease | None:
        record = self._leases.get(lease_id)
        return record.lease if record else None

    def authorize_use(self, request: LeaseUseRequest) -> LeaseUseResult:
        record = self._leases.get(request.lease_id)
        if record is None:
            return LeaseUseResult(state=LeaseUseState.NOT_FOUND, safe_reason="credential lease was not found")

        lease = record.lease
        mismatch = _lease_binding_mismatch(lease, request)
        if mismatch:
            return LeaseUseResult(state=LeaseUseState.DENIED, safe_reason=mismatch, lease=lease)
        if lease.secret_exposed_to_agent:
            return LeaseUseResult(
                state=LeaseUseState.DENIED,
                safe_reason="credential lease is marked as agent-exposing and cannot be used",
                lease=lease,
            )
        if request.caller not in {"gateway", "broker", "exec_wrapper", "mcp_launcher"}:
            return LeaseUseResult(
                state=LeaseUseState.DENIED,
                safe_reason="credential lease can only be used by an authorized execution boundary",
                lease=lease,
            )
        if self._now() >= record.expires_at:
            return LeaseUseResult(state=LeaseUseState.EXPIRED, safe_reason="credential lease is expired", lease=lease)
        if record.uses_remaining <= 0:
            return LeaseUseResult(state=LeaseUseState.EXHAUSTED, safe_reason="credential lease max_uses is exhausted", lease=lease)

        record.uses_remaining -= 1
        evidence: dict[str, object] = {
            "lease_id": lease.lease_id,
            "credential_ref_id": lease.credential_ref,
            "credential_ref_hash": lease.credential_ref_hash,
            "provider": lease.provider,
            "provider_mode": lease.provider_mode,
            "provider_operation_id": lease.provider_operation_id,
            "injection_mode": lease.injection_mode,
            "remaining_uses": record.uses_remaining,
            "secret_exposed_to_agent": False,
        }
        return LeaseUseResult(
            state=LeaseUseState.APPROVED,
            safe_reason="credential lease use approved for broker-controlled execution",
            lease=lease,
            evidence=evidence,
        )


def choose_provider_mode(readiness: OnePasswordReadiness, injection_mode: str) -> str | None:
    if readiness.status != OnePasswordProviderStatus.READY:
        return None

    available = set(readiness.provider_modes)
    if injection_mode == "onepassword_mcp_environment":
        return _first_available(available, ("onepassword_mcp_environment",))
    if injection_mode == "process_env":
        return _first_available(available, ("onepassword_mcp_environment", "op_run_process_env"))
    if injection_mode == "gateway_header":
        return _first_available(available, (
            "op_cli_secret_reference",
            "onepassword_sdk_service_account",
            "onepassword_sdk_desktop",
        ))
    if injection_mode in {"stdin_or_fd", "local_socket", "provider_native"}:
        return _first_available(available, (
            "onepassword_sdk_service_account",
            "op_cli_secret_reference",
            "op_run_process_env",
            "onepassword_mcp_environment",
        ))
    return None


def _first_available(available: set[str], preferred: tuple[str, ...]) -> str | None:
    for mode in preferred:
        if mode in available:
            return mode
    return None


def _blocked_state(readiness: OnePasswordReadiness) -> LeaseMintState:
    if readiness.status == OnePasswordProviderStatus.SETUP_REQUIRED:
        return LeaseMintState.ESCALATE_HUMAN
    return LeaseMintState.DENIED


def _lease_binding_mismatch(lease: CredentialLease, request: LeaseUseRequest) -> str:
    expected = {
        "session_id": lease.session_id,
        "tool_id": lease.tool_id,
        "scope": lease.scope,
        "resource_id": lease.resource_id,
    }
    actual = {
        "session_id": request.session_id,
        "tool_id": request.tool_id,
        "scope": request.scope,
        "resource_id": request.resource_id,
    }
    for key, expected_value in expected.items():
        if actual[key] != expected_value:
            return f"credential lease {key} binding mismatch"
    return ""
