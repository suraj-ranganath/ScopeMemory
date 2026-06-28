from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from mcp.registry import AUTH_TOOL_NAMES, DOWNSTREAM_TOOL_NAMES  # noqa: E402
from mcp.safe_views import explain_denial, redact_text  # noqa: E402
from mcp.visibility import visible_tools_from_context  # noqa: E402


class McpGatewaySurfaceTests(unittest.TestCase):
    def test_auth_catalog_includes_scope_denial_and_feedback_tools(self) -> None:
        self.assertIn("auth.request_scope", AUTH_TOOL_NAMES)
        self.assertIn("auth.explain_denial", AUTH_TOOL_NAMES)
        self.assertIn("auth.submit_workflow_feedback", AUTH_TOOL_NAMES)

    def test_downstream_catalog_includes_demo_linear_wrapper_surface(self) -> None:
        self.assertIn("linear.create_issue", DOWNSTREAM_TOOL_NAMES)
        self.assertIn("linear.search_issues", DOWNSTREAM_TOOL_NAMES)
        self.assertIn("linear.add_comment", DOWNSTREAM_TOOL_NAMES)

    def test_visible_tools_are_predicted_or_auth_tools_only(self) -> None:
        visible = visible_tools_from_context({"predicted_tools": ["linear.create_issue"]})

        self.assertIn("auth.preflight_goal", visible)
        self.assertIn("linear.create_issue", visible)
        self.assertNotIn("slack.post_message", visible)

    def test_denial_explanation_uses_redacted_proof_summary(self) -> None:
        explanation = explain_denial([
            {
                "decision_id": "dec_1",
                "tool_id": "slack.post_message",
                "resource_id": "slack_channel:external-partners",
                "decision": "DENY",
                "proof_json": {
                    "reason": "external write not predicted as safe",
                    "rules": ["deny_external_write"],
                    "required_scope": "slack:chat:write",
                    "context_path": ["sess_demo_001", "recipe_sales_renewal_v3"],
                },
            }
        ])

        self.assertTrue(explanation["found"])
        self.assertEqual(explanation["primary_rule"], "deny_external_write")
        self.assertEqual(explanation["required_scope"], "slack:chat:write")

    def test_redacts_obvious_secret_references_from_demo_output(self) -> None:
        self.assertEqual(redact_text("Authorization: Bearer abc"), "[redacted]")
        self.assertEqual(redact_text("op://Vault/Item/token"), "[redacted]")


if __name__ == "__main__":
    unittest.main()
