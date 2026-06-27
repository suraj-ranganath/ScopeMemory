"""1Password provider adapter for broker-owned credential resolution."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from dataclasses import dataclass
from enum import Enum

from credential_broker import LeaseUseResult, LeaseUseState


class ProviderResolveState(str, Enum):
    RESOLVED = "resolved"
    DENIED = "denied"
    ESCALATE_HUMAN = "escalate_human"


@dataclass(frozen=True)
class SecretValue:
    _value: str

    def reveal_to_broker(self) -> str:
        return self._value

    def __bool__(self) -> bool:
        return bool(self._value)

    def __repr__(self) -> str:
        return "SecretValue(<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"


@dataclass(frozen=True)
class ProviderResolveResult:
    state: ProviderResolveState
    safe_reason: str
    provider_operation_id: str
    credential_ref_hash: str = ""
    secret: SecretValue | None = None
    secret_exposed_to_agent: bool = False

    def safe_metadata(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "safe_reason": self.safe_reason,
            "provider_operation_id": self.provider_operation_id,
            "credential_ref_hash": self.credential_ref_hash,
            "secret_exposed_to_agent": self.secret_exposed_to_agent,
        }


class OnePasswordProvider:
    def __init__(self, op_path: str | None = None, timeout_seconds: int = 10):
        self.op_path = op_path or shutil.which("op")
        self.timeout_seconds = timeout_seconds

    def resolve_for_lease(self, lease_use: LeaseUseResult, secret_ref: str) -> ProviderResolveResult:
        operation_id = f"opcli_{uuid.uuid4().hex}"
        if lease_use.state != LeaseUseState.APPROVED or lease_use.lease is None:
            return ProviderResolveResult(
                state=ProviderResolveState.DENIED,
                safe_reason="credential lease use was not approved",
                provider_operation_id=operation_id,
            )
        if lease_use.lease.secret_exposed_to_agent:
            return ProviderResolveResult(
                state=ProviderResolveState.DENIED,
                safe_reason="credential lease is marked agent-exposing",
                provider_operation_id=operation_id,
                credential_ref_hash=lease_use.lease.credential_ref_hash,
            )
        if not secret_ref.startswith("op://"):
            return ProviderResolveResult(
                state=ProviderResolveState.DENIED,
                safe_reason="1Password secret reference must use op:// syntax",
                provider_operation_id=operation_id,
                credential_ref_hash=lease_use.lease.credential_ref_hash,
            )
        if not self.op_path:
            return ProviderResolveResult(
                state=ProviderResolveState.ESCALATE_HUMAN,
                safe_reason="1Password CLI is unavailable",
                provider_operation_id=operation_id,
                credential_ref_hash=lease_use.lease.credential_ref_hash,
            )

        try:
            completed = subprocess.run(
                [self.op_path, "read", "--no-newline", secret_ref],
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return ProviderResolveResult(
                state=ProviderResolveState.ESCALATE_HUMAN,
                safe_reason="1Password CLI timed out",
                provider_operation_id=operation_id,
                credential_ref_hash=lease_use.lease.credential_ref_hash,
            )
        except OSError:
            return ProviderResolveResult(
                state=ProviderResolveState.ESCALATE_HUMAN,
                safe_reason="1Password CLI could not be executed",
                provider_operation_id=operation_id,
                credential_ref_hash=lease_use.lease.credential_ref_hash,
            )

        if completed.returncode != 0:
            return ProviderResolveResult(
                state=_error_state(completed.stderr),
                safe_reason=_safe_error_reason(completed.stderr),
                provider_operation_id=operation_id,
                credential_ref_hash=lease_use.lease.credential_ref_hash,
            )

        return ProviderResolveResult(
            state=ProviderResolveState.RESOLVED,
            safe_reason="1Password reference resolved inside broker boundary",
            provider_operation_id=operation_id,
            credential_ref_hash=lease_use.lease.credential_ref_hash,
            secret=SecretValue(completed.stdout),
            secret_exposed_to_agent=False,
        )


def _error_state(stderr: str) -> ProviderResolveState:
    lowered = stderr.lower()
    if any(marker in lowered for marker in (
        "sign in",
        "signin",
        "signed in",
        "no account found",
        "unlock",
        "locked",
        "approval",
        "cancel",
    )):
        return ProviderResolveState.ESCALATE_HUMAN
    return ProviderResolveState.DENIED


def _safe_error_reason(stderr: str) -> str:
    state = _error_state(stderr)
    if state == ProviderResolveState.ESCALATE_HUMAN:
        return "1Password requires human authorization"
    return "1Password secret reference could not be resolved"
