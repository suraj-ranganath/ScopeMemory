from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from credential_broker import (  # noqa: E402
    CredentialBinding,
    CredentialBroker,
    LeaseMintRequest,
    LeaseMintState,
)
from hook_adapter import (  # noqa: E402
    SecretAccessPattern,
    codex_pre_tool_use_output,
    evaluate_hook_intent,
    normalize_pre_tool_use,
)
from onepassword_readiness import (  # noqa: E402
    OnePasswordProviderStatus,
    OnePasswordReadiness,
    detect_onepassword_readiness,
)


class OnePasswordReadinessTests(unittest.TestCase):
    def test_missing_provider_tools_fail_closed_without_secret_resolution(self) -> None:
        readiness = detect_onepassword_readiness(
            env={},
            op_path=None,
            app_path=Path("/definitely/missing/1Password.app"),
            mcp_path=Path("/definitely/missing/onepassword-mcp"),
        )

        self.assertEqual(readiness.status, OnePasswordProviderStatus.UNAVAILABLE)
        self.assertFalse(readiness.can_resolve_live_secrets)
        self.assertEqual(readiness.provider_modes, [])


class HookAdapterTests(unittest.TestCase):
    def test_direct_op_read_is_denied_for_codex(self) -> None:
        intent = normalize_pre_tool_use("codex", {
            "tool_name": "Bash",
            "tool_input": {"command": "op read op://ScopeMemory Demo/Linear API Token/token"},
        })

        self.assertEqual(intent.secret_access_pattern, SecretAccessPattern.DIRECT_SECRET_READ)
        decision = evaluate_hook_intent(intent)
        output = codex_pre_tool_use_output(decision)

        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn("op://", output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_mcp_tool_input_with_token_is_denied(self) -> None:
        intent = normalize_pre_tool_use("claude_code", {
            "tool_name": "mcp__linear__create_issue",
            "tool_input": {"title": "Follow up", "token": "fixture-token-value"},
        })

        self.assertEqual(intent.secret_access_pattern, SecretAccessPattern.SECRET_IN_INPUT)
        self.assertEqual(evaluate_hook_intent(intent).decision.value, "DENY")


class CredentialBrokerTests(unittest.TestCase):
    def test_broker_does_not_mint_when_provider_unavailable(self) -> None:
        readiness = OnePasswordReadiness(
            platform_name="Darwin",
            desktop_app_present=False,
            op_cli_path=None,
            op_cli_version=None,
            onepassword_mcp_path=None,
            service_account_token_present=False,
            status=OnePasswordProviderStatus.UNAVAILABLE,
        )
        result = CredentialBroker(readiness).mint_lease(_request("gateway_header"))

        self.assertEqual(result.state, LeaseMintState.DENIED)
        self.assertIsNone(result.lease)

    def test_broker_mints_opaque_gateway_lease_with_ready_service_account_mode(self) -> None:
        readiness = OnePasswordReadiness(
            platform_name="Darwin",
            desktop_app_present=True,
            op_cli_path=None,
            op_cli_version=None,
            onepassword_mcp_path=None,
            service_account_token_present=True,
            status=OnePasswordProviderStatus.READY,
            provider_modes=["onepassword_sdk_service_account"],
        )
        result = CredentialBroker(readiness).mint_lease(_request("gateway_header"))

        self.assertEqual(result.state, LeaseMintState.MINTED)
        assert result.lease is not None
        self.assertTrue(result.lease.lease_id.startswith("lease_"))
        self.assertEqual(result.lease.credential_ref, "credref_linear_sales")
        self.assertTrue(result.lease.credential_ref_hash.startswith("sha256:"))
        self.assertFalse(result.lease.secret_exposed_to_agent)


def _request(injection_mode: str) -> LeaseMintRequest:
    return LeaseMintRequest(
        session_id="sess_test",
        tool_id="linear.create_issue",
        scope="linear:issues:create",
        resource_id="linear_team:SALES",
        binding=CredentialBinding(
            credential_ref_id="credref_linear_sales",
            provider="onepassword",
            credential_class="linear.oauth_token",
            owner_team="sales-ops",
            injection_mode=injection_mode,
        ),
    )


if __name__ == "__main__":
    unittest.main()
