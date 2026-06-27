"""Async authorization check contract and in-memory lifecycle service."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from cozo_policy import decide
from policy_contracts import (
    AuthorizationCheck,
    AuthorizationCheckState,
    Decision,
    PolicyDecision,
)


TERMINAL_STATES = {
    AuthorizationCheckState.APPROVED,
    AuthorizationCheckState.AUTO_APPROVED,
    AuthorizationCheckState.DENIED,
    AuthorizationCheckState.REPAIRABLE,
    AuthorizationCheckState.EXPIRED,
    AuthorizationCheckState.CANCELLED,
}

EXECUTABLE_STATES = {
    AuthorizationCheckState.APPROVED,
    AuthorizationCheckState.AUTO_APPROVED,
}


class AuthorizationCheckService:
    def __init__(self, now: Callable[[], datetime] | None = None):
        self._now = now or (lambda: datetime.now(UTC))
        self._checks: dict[str, AuthorizationCheck] = {}
        self._idempotency_index: dict[tuple[str, str], str] = {}
        self._decisions: dict[str, PolicyDecision] = {}

    def create(
        self,
        *,
        session_id: str,
        tool_id: str,
        resource_id: str,
        idempotency_key: str,
        ttl_seconds: int = 900,
    ) -> AuthorizationCheck:
        index_key = (session_id, idempotency_key)
        existing_id = self._idempotency_index.get(index_key)
        if existing_id:
            return self.get(existing_id)

        now = self._now()
        check = AuthorizationCheck(
            check_id=f"check_{uuid.uuid4().hex}",
            idempotency_key=idempotency_key,
            session_id=session_id,
            tool_id=tool_id,
            resource_id=resource_id,
            state=AuthorizationCheckState.CREATED,
            created_at=_timestamp(now),
            updated_at=_timestamp(now),
            expires_at=_timestamp(now + timedelta(seconds=ttl_seconds)),
        )
        self._checks[check.check_id] = check
        self._idempotency_index[index_key] = check.check_id
        return check

    def evaluate(
        self,
        *,
        context: dict[str, object],
        idempotency_key: str,
        ttl_seconds: int = 900,
    ) -> AuthorizationCheck:
        session_id = str(context.get("session_id") or (context.get("facts") or {}).get("session_id") or "")
        tool_id = str(context.get("tool_id") or (context.get("facts") or {}).get("tool_id") or "")
        resource_id = str(context.get("resource_id") or (context.get("facts") or {}).get("resource_id") or "")
        check = self.create(
            session_id=session_id,
            tool_id=tool_id,
            resource_id=resource_id,
            idempotency_key=idempotency_key,
            ttl_seconds=ttl_seconds,
        )
        if check.state in TERMINAL_STATES or check.state == AuthorizationCheckState.WAITING_FOR_HUMAN:
            return self._expire_if_needed(check)

        check = self._transition(check, AuthorizationCheckState.FACTS_COMPILED, "compiled normalized policy facts")
        check = self._transition(check, AuthorizationCheckState.POLICY_EVALUATING, "policy engine evaluating")
        decision = decide(context)
        self._decisions[check.check_id] = decision
        state = state_for_decision(decision.decision)
        return self._transition(
            check,
            state,
            decision.reason,
            decision=decision.decision,
            proof_id=decision.proof.proof_hash,
        )

    def get(self, check_id: str) -> AuthorizationCheck:
        check = self._checks[check_id]
        return self._expire_if_needed(check)

    def cancel(self, check_id: str, reason: str = "authorization check cancelled") -> AuthorizationCheck:
        check = self.get(check_id)
        if check.state in TERMINAL_STATES:
            return check
        return self._transition(check, AuthorizationCheckState.CANCELLED, reason)

    def decision_for(self, check_id: str) -> PolicyDecision | None:
        return self._decisions.get(check_id)

    def can_execute(self, check_id: str) -> bool:
        return self.get(check_id).state in EXECUTABLE_STATES

    def _expire_if_needed(self, check: AuthorizationCheck) -> AuthorizationCheck:
        if check.state in TERMINAL_STATES:
            return check
        if self._now() >= _parse_timestamp(check.expires_at):
            return self._transition(check, AuthorizationCheckState.EXPIRED, "authorization check expired")
        return check

    def _transition(
        self,
        check: AuthorizationCheck,
        state: AuthorizationCheckState,
        safe_reason: str,
        decision: Decision | None = None,
        proof_id: str = "",
    ) -> AuthorizationCheck:
        updated = replace(
            check,
            state=state,
            updated_at=_timestamp(self._now()),
            decision=decision if decision is not None else check.decision,
            proof_id=proof_id or check.proof_id,
            safe_reason=safe_reason,
        )
        self._checks[updated.check_id] = updated
        return updated


def state_for_decision(decision: Decision) -> AuthorizationCheckState:
    if decision == Decision.ALLOW:
        return AuthorizationCheckState.APPROVED
    if decision == Decision.AUTO_APPROVE_EPHEMERAL_GRANT:
        return AuthorizationCheckState.AUTO_APPROVED
    if decision == Decision.ESCALATE_HUMAN:
        return AuthorizationCheckState.WAITING_FOR_HUMAN
    if decision == Decision.REPAIR:
        return AuthorizationCheckState.REPAIRABLE
    return AuthorizationCheckState.DENIED


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
