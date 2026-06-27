from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from authorization_checks import AuthorizationCheckService  # noqa: E402
from policy_contracts import AuthorizationCheckState  # noqa: E402


class AuthorizationCheckServiceTests(unittest.TestCase):
    def test_allow_check_is_idempotent_and_executable(self) -> None:
        service = AuthorizationCheckService()

        first = service.evaluate(context=_ctx("linear.create_issue", "linear_team:SALES", {
            "scope": "linear:issues:create",
            "access_kind": "write",
            "delegation_present": True,
            "recipe_predicts_tool": True,
            "same_team": True,
            "grant_present": True,
            "scope_approval_mode": "auto_approve",
        }), idempotency_key="idem-allow")
        second = service.evaluate(context=_ctx("linear.create_issue", "linear_team:SALES", {
            "scope": "linear:issues:create",
            "access_kind": "write",
            "delegation_present": True,
            "recipe_predicts_tool": True,
            "same_team": True,
            "grant_present": True,
        }), idempotency_key="idem-allow")

        self.assertEqual(first.check_id, second.check_id)
        self.assertEqual(first.state, AuthorizationCheckState.APPROVED)
        self.assertTrue(service.can_execute(first.check_id))
        self.assertTrue(first.proof_id.startswith("sha256:"))

    def test_human_escalation_is_pending_and_not_executable(self) -> None:
        service = AuthorizationCheckService()

        check = service.evaluate(context=_ctx("slack.search_messages", "slack_channel:sales-acme", {
            "scope": "slack:channels:history",
            "access_kind": "read",
            "delegation_present": True,
            "recipe_predicts_tool": True,
            "same_team": True,
            "grant_present": False,
            "scope_approval_mode": "human_required",
        }), idempotency_key="idem-human")

        self.assertEqual(check.state, AuthorizationCheckState.WAITING_FOR_HUMAN)
        self.assertFalse(service.can_execute(check.check_id))

    def test_denied_and_repairable_checks_are_terminal_non_executable(self) -> None:
        service = AuthorizationCheckService()

        denied = service.evaluate(context=_ctx("linear.create_issue", "linear_team:SALES", {
            "scope": "linear:issues:create",
            "delegation_present": False,
            "recipe_predicts_tool": True,
            "same_team": True,
            "grant_present": True,
        }), idempotency_key="idem-deny")
        repair = service.evaluate(context=_ctx("linear.create_issue", "linear_team:SALES", {
            "scope": "linear:issues:create",
            "schema_valid": False,
            "schema_repairable": True,
            "delegation_present": True,
            "recipe_predicts_tool": True,
            "same_team": True,
        }), idempotency_key="idem-repair")

        self.assertEqual(denied.state, AuthorizationCheckState.DENIED)
        self.assertEqual(repair.state, AuthorizationCheckState.REPAIRABLE)
        self.assertFalse(service.can_execute(denied.check_id))
        self.assertFalse(service.can_execute(repair.check_id))

    def test_created_check_expires(self) -> None:
        current = datetime(2026, 6, 27, 22, 15, tzinfo=UTC)

        def now() -> datetime:
            return current

        service = AuthorizationCheckService(now=now)
        check = service.create(
            session_id="sess_test",
            tool_id="linear.create_issue",
            resource_id="linear_team:SALES",
            idempotency_key="idem-expire",
            ttl_seconds=1,
        )
        current = current + timedelta(seconds=2)

        self.assertEqual(service.get(check.check_id).state, AuthorizationCheckState.EXPIRED)
        self.assertFalse(service.can_execute(check.check_id))


def _ctx(tool_id: str, resource_id: str, facts: dict[str, object]) -> dict[str, object]:
    scope = str(facts.get("scope") or "scope:test")
    return {
        "session_id": "sess_test",
        "tool_id": tool_id,
        "resource_id": resource_id,
        "context_path": [
            "sess_test",
            "recipe_sales_renewal_v3",
            tool_id,
            scope,
            resource_id,
            "team_sales",
            "user_alice",
            "agent_renewal_01",
        ],
        "facts": {
            "session_id": "sess_test",
            "tool_id": tool_id,
            "resource_id": resource_id,
            "user_id": "user_alice",
            "agent_id": "agent_renewal_01",
            "session_team": "team_sales",
            "resource_team": "team_sales",
            "goal_class": "sales_renewal_prep",
            "resource_sensitivity": "normal",
            "similarity_score": 1.0,
            "similarity_reified": True,
            **facts,
        },
    }


if __name__ == "__main__":
    unittest.main()
