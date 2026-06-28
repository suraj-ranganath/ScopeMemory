"""1Password provider adapter for broker-owned credential verification.

The provider proves that a lease-bound op:// reference is usable without
returning secret bytes to the ScopeMemory process.
"""

from __future__ import annotations

import shutil
import subprocess
import os
import sys
import uuid
from dataclasses import dataclass
from enum import Enum

from credential_broker import LeaseUseResult, LeaseUseState


class ProviderResolveState(str, Enum):
    RESOLVED = "resolved"
    DENIED = "denied"
    ESCALATE_HUMAN = "escalate_human"


@dataclass(frozen=True)
class ProviderResolveResult:
    state: ProviderResolveState
    safe_reason: str
    provider_operation_id: str
    credential_ref_hash: str = ""
    secret_exposed_to_agent: bool = False

    def safe_metadata(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "safe_reason": self.safe_reason,
            "provider_operation_id": self.provider_operation_id,
            "credential_ref_hash": self.credential_ref_hash,
            "secret_exposed_to_agent": self.secret_exposed_to_agent,
            "secret_known_to_gateway": False,
        }


class OnePasswordProvider:
    def __init__(self, op_path: str | None = None, timeout_seconds: int = 30, auto_signin: bool = True):
        self.op_path = op_path or shutil.which("op")
        self.timeout_seconds = timeout_seconds
        self.auto_signin = auto_signin

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

        completed = self._try_verify_secret_reference(secret_ref, operation_id, lease_use)
        if isinstance(completed, ProviderResolveResult):
            return completed

        if completed.returncode != 0 and self.auto_signin and _error_state(completed.stderr or "") == ProviderResolveState.ESCALATE_HUMAN:
            if self._attempt_desktop_signin():
                completed = self._try_verify_secret_reference(secret_ref, operation_id, lease_use)
                if isinstance(completed, ProviderResolveResult):
                    return completed

        if completed.returncode != 0:
            return ProviderResolveResult(
                state=_error_state(completed.stderr or ""),
                safe_reason=_safe_error_reason(completed.stderr or ""),
                provider_operation_id=operation_id,
                credential_ref_hash=lease_use.lease.credential_ref_hash,
            )

        return ProviderResolveResult(
            state=ProviderResolveState.RESOLVED,
            safe_reason="1Password reference injected into subprocess without exposing secret material",
            provider_operation_id=operation_id,
            credential_ref_hash=lease_use.lease.credential_ref_hash,
            secret_exposed_to_agent=False,
        )

    def _try_verify_secret_reference(
        self,
        secret_ref: str,
        operation_id: str,
        lease_use: LeaseUseResult,
    ) -> subprocess.CompletedProcess[str] | ProviderResolveResult:
        try:
            return self._verify_secret_reference(secret_ref)
        except subprocess.TimeoutExpired:
            return ProviderResolveResult(
                state=ProviderResolveState.ESCALATE_HUMAN,
                safe_reason="1Password CLI timed out",
                provider_operation_id=operation_id,
                credential_ref_hash=lease_use.lease.credential_ref_hash if lease_use.lease else "",
            )
        except OSError:
            return ProviderResolveResult(
                state=ProviderResolveState.ESCALATE_HUMAN,
                safe_reason="1Password CLI could not be executed",
                provider_operation_id=operation_id,
                credential_ref_hash=lease_use.lease.credential_ref_hash if lease_use.lease else "",
            )

    def _verify_secret_reference(self, secret_ref: str) -> subprocess.CompletedProcess[str]:
        assert self.op_path is not None
        env = os.environ.copy()
        env["SCOPEMEMORY_1P_SECRET"] = secret_ref
        return subprocess.run(
            [
                self.op_path,
                "run",
                "--",
                sys.executable,
                "-c",
                (
                    "import os, sys; "
                    "value = os.environ.get('SCOPEMEMORY_1P_SECRET', ''); "
                    "sys.exit(0 if value and not value.startswith('op://') else 3)"
                ),
            ],
            check=False,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=self.timeout_seconds,
        )

    def _attempt_desktop_signin(self) -> bool:
        if not self.op_path:
            return False
        try:
            completed = subprocess.run(
                [self.op_path, "signin", "--force"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=max(self.timeout_seconds, 60),
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return completed.returncode == 0


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
