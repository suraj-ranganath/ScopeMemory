"""Opaque credential lease minting for ScopeMemory runtime execution.

The broker in this file does not resolve secret values. It chooses a compatible
1Password provider mode, mints an opaque lease, and fails closed when no real
provider path is ready.
"""

from __future__ import annotations

import uuid
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


@dataclass(frozen=True)
class LeaseMintResult:
    state: LeaseMintState
    safe_reason: str
    lease: CredentialLease | None = None
    setup_required: tuple[str, ...] = ()


class CredentialBroker:
    def __init__(self, readiness: OnePasswordReadiness):
        self.readiness = readiness

    def mint_lease(self, request: LeaseMintRequest) -> LeaseMintResult:
        provider_mode = choose_provider_mode(self.readiness, request.binding.injection_mode)
        if provider_mode is None:
            return LeaseMintResult(
                state=_blocked_state(self.readiness),
                safe_reason="1Password provider is not ready for this credential injection mode",
                setup_required=tuple(self.readiness.setup_required),
            )

        expires_at = datetime.now(UTC) + timedelta(seconds=request.ttl_seconds)
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
        return LeaseMintResult(
            state=LeaseMintState.MINTED,
            safe_reason="opaque credential lease minted; secret value remains broker-only",
            lease=lease,
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
            "onepassword_sdk_service_account",
            "op_cli_secret_reference",
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
