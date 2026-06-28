from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cozo_policy import compile_policy_facts, decide, _evaluate_with_cozo, _evaluate_with_python


def demo_ctx(
    tool: str = "linear.create_issue",
    resource: str = "linear_team:SALES",
    scope: str = "linear:issues:create",
    *,
    recipe_predicts_tool: bool = True,
    grant_present: bool = True,
    resource_external: bool = False,
    resource_sensitivity: str = "normal",
    access_kind: str = "write",
    approval_mode: str | None = "auto_approve",
    context_path: list[str] | None = None,
    **extra_facts,
):
    path = context_path
    if path is None:
        path = [
            "sess_demo_001",
            "recipe_sales_renewal_v3",
            tool,
            scope,
            resource,
            "team_sales",
            "user_alice",
            "agent_renewal_01",
        ]
    facts = {
        "session_id": "sess_demo_001",
        "tool_id": tool,
        "resource_id": resource,
        "scope": scope,
        "user_id": "user_alice",
        "agent_id": "agent_renewal_01",
        "session_team": "team_sales",
        "resource_team": "team_sales",
        "goal_class": "sales_renewal_prep",
        "delegation_present": True,
        "recipe_predicts_tool": recipe_predicts_tool,
        "same_team": True,
        "grant_present": grant_present,
        "resource_external": resource_external,
        "resource_sensitivity": resource_sensitivity,
        "access_kind": access_kind,
        "scope_approval_mode": approval_mode,
        **extra_facts,
    }
    return {
        "session_id": "sess_demo_001",
        "tool_id": tool,
        "resource_id": resource,
        "context_path": path,
        "facts": facts,
    }


class PolicyAgentTests(unittest.TestCase):
    def test_current_grant_allows_with_stable_proof_hash(self):
        first = decide(demo_ctx())
        second = decide(demo_ctx())

        self.assertEqual(first.decision.value, "ALLOW")
        self.assertEqual(first.reason, "grant exists for scope@resource")
        self.assertEqual(first.proof.policy_engine, "cozo-datalog")
        self.assertIn("allow_current_grant", first.proof.rules)
        self.assertEqual(first.proof.proof_hash, second.proof.proof_hash)

    def test_auto_approve_ephemeral_grant_requires_safe_context(self):
        result = decide(demo_ctx(grant_present=False))

        self.assertEqual(result.decision.value, "AUTO_APPROVE_EPHEMERAL_GRANT")
        self.assertIn("auto_approve_recipe_scope", result.proof.rules)

    def test_human_required_scope_escalates(self):
        result = decide(demo_ctx(
            tool="slack.search_messages",
            resource="slack_channel:sales-acme",
            scope="slack:channels:history",
            grant_present=False,
            resource_sensitivity="restricted",
            access_kind="read",
            approval_mode="human_required",
        ))

        self.assertEqual(result.decision.value, "ESCALATE_HUMAN")
        self.assertEqual(result.check_state.value, "waiting_for_human")

    def test_external_post_is_hard_denied_over_default_deny(self):
        result = decide(demo_ctx(
            tool="slack.post_message",
            resource="slack_channel:external-partners",
            scope="slack:chat:write",
            recipe_predicts_tool=False,
            grant_present=False,
            resource_external=True,
            resource_sensitivity="high",
            access_kind="write",
            approval_mode=None,
        ))

        self.assertEqual(result.decision.value, "DENY")
        self.assertEqual(result.reason, "external write not predicted as safe")
        self.assertIn("deny_external_write", result.proof.rules)

    def test_agent_trust_below_minimum_is_denied(self):
        result = decide(demo_ctx(agent_trust_score=0.4))

        self.assertEqual(result.decision.value, "DENY")
        self.assertEqual(result.reason, "agent trust score below minimum")
        self.assertIn("deny_low_trust", result.proof.rules)

    def test_external_write_low_sensitive_trust_escalates_over_grant(self):
        result = decide(demo_ctx(
            tool="slack.post_message",
            resource="slack_channel:external-partners",
            scope="slack:chat:write",
            grant_present=True,
            resource_external=True,
            resource_sensitivity="high",
            access_kind="write",
            agent_trust_score=0.7,
        ))

        self.assertEqual(result.decision.value, "ESCALATE_HUMAN")
        self.assertEqual(result.reason, "external write requires higher agent trust")
        self.assertIn("escalate_low_trust_external", result.proof.rules)

    def test_repairable_schema_error_returns_repair(self):
        result = decide(demo_ctx(
            grant_present=False,
            schema_valid=False,
            schema_repairable=True,
        ))

        self.assertEqual(result.decision.value, "REPAIR")
        self.assertEqual(result.check_state.value, "repairable")

    def test_direct_secret_read_overrides_grant(self):
        result = decide(demo_ctx(attempted_direct_secret_read=True))

        self.assertEqual(result.decision.value, "DENY")
        self.assertEqual(result.reason, "direct password-manager secret read bypasses broker")
        self.assertIn("deny_direct_secret_read", result.proof.rules)

    def test_unreified_recipe_hit_is_denied(self):
        result = decide(demo_ctx(similarity_reified=False))

        self.assertEqual(result.decision.value, "DENY")
        self.assertIn("deny_unreified_recipe_hit", result.proof.rules)

    def test_missing_context_path_blocks_graph_backed_decision(self):
        result = decide(demo_ctx(context_path=[], context_snapshot_present=True))

        self.assertEqual(result.decision.value, "DENY")
        self.assertIn("deny_missing_context_path", result.proof.rules)

    def test_secret_values_are_not_projected_into_facts(self):
        result = decide(demo_ctx(api_token="super-secret-token-value"))

        self.assertEqual(result.decision.value, "DENY")
        rendered_facts = "\n".join(result.proof.facts)
        self.assertNotIn("super-secret-token-value", rendered_facts)
        self.assertIn("violation(sess_demo_001, linear.create_issue, linear_team:SALES, secret_exposure)", rendered_facts)

    def test_cozo_and_python_fallback_agree_when_cozo_available(self):
        try:
            import pycozo  # noqa: F401
        except Exception:
            self.skipTest("pycozo/cozo-embedded not installed in this Python environment")

        compiled = compile_policy_facts(demo_ctx(
            tool="slack.post_message",
            resource="slack_channel:external-partners",
            scope="slack:chat:write",
            recipe_predicts_tool=False,
            grant_present=False,
            resource_external=True,
            resource_sensitivity="high",
            access_kind="write",
            approval_mode=None,
        ))
        cozo_result = _evaluate_with_cozo(compiled)
        python_result = _evaluate_with_python(compiled)

        self.assertEqual(cozo_result.decision, python_result.decision)
        self.assertEqual(cozo_result.reason, python_result.reason)
        self.assertEqual(cozo_result.rule, python_result.rule)


if __name__ == "__main__":
    unittest.main()
