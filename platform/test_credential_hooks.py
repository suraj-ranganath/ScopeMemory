from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from credential_broker import (  # noqa: E402
    CredentialBinding,
    CredentialBroker,
    LeaseMintRequest,
    LeaseMintState,
    LeaseUseRequest,
    LeaseUseState,
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
            search_path=False,
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

    def test_safe_shell_call_can_be_routed_through_exec_wrapper(self) -> None:
        intent = normalize_pre_tool_use("codex", {
            "tool_name": "Bash",
            "tool_input": {"command": "curl https://api.linear.app/graphql"},
        })

        decision = evaluate_hook_intent(intent, lease_id="lease_safe_123")
        output = codex_pre_tool_use_output(decision)

        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "allow")
        self.assertEqual(decision.route, "scopememory_exec")
        rewritten = output["hookSpecificOutput"]["updatedInput"]["command"]
        self.assertTrue(rewritten.startswith("scopememory exec --lease lease_safe_123 -- "))
        self.assertNotIn("op://", rewritten)


class CredentialBrokerTests(unittest.TestCase):
    def test_broker_does_not_mint_when_provider_unavailable(self) -> None:
        readiness = OnePasswordReadiness(
            platform_name="Darwin",
            desktop_app_present=False,
            op_cli_path=None,
            op_cli_version=None,
            op_account_configured=False,
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
            op_account_configured=False,
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

    def test_broker_refuses_agent_exposing_lease(self) -> None:
        broker = CredentialBroker(_ready_service_account())
        result = broker.mint_lease(LeaseMintRequest(
            session_id="sess_test",
            tool_id="linear.create_issue",
            scope="linear:issues:create",
            resource_id="linear_team:SALES",
            binding=_binding("gateway_header"),
            would_expose_secret_to_agent=True,
        ))

        self.assertEqual(result.state, LeaseMintState.DENIED)
        self.assertIsNone(result.lease)

    def test_lease_use_is_bound_and_max_use_enforced(self) -> None:
        broker = CredentialBroker(_ready_service_account())
        minted = broker.mint_lease(_request("gateway_header"))
        assert minted.lease is not None

        approved = broker.authorize_use(_use_request(minted.lease.lease_id, caller="gateway"))
        exhausted = broker.authorize_use(_use_request(minted.lease.lease_id, caller="gateway"))

        self.assertEqual(approved.state, LeaseUseState.APPROVED)
        assert approved.evidence is not None
        self.assertEqual(approved.evidence["remaining_uses"], 0)
        self.assertFalse(approved.evidence["secret_exposed_to_agent"])
        self.assertEqual(exhausted.state, LeaseUseState.EXHAUSTED)

    def test_lease_use_rejects_binding_mismatch_and_agent_caller(self) -> None:
        broker = CredentialBroker(_ready_service_account())
        minted = broker.mint_lease(_request("gateway_header"))
        assert minted.lease is not None

        mismatch = broker.authorize_use(LeaseUseRequest(
            lease_id=minted.lease.lease_id,
            session_id="sess_test",
            tool_id="slack.post_message",
            scope="linear:issues:create",
            resource_id="linear_team:SALES",
            caller="gateway",
        ))
        agent = broker.authorize_use(_use_request(minted.lease.lease_id, caller="agent"))

        self.assertEqual(mismatch.state, LeaseUseState.DENIED)
        self.assertEqual(agent.state, LeaseUseState.DENIED)

    def test_lease_use_expires(self) -> None:
        current = datetime(2026, 6, 27, 22, 0, tzinfo=UTC)

        def now() -> datetime:
            return current

        broker = CredentialBroker(_ready_service_account(), now=now)
        minted = broker.mint_lease(LeaseMintRequest(
            session_id="sess_test",
            tool_id="linear.create_issue",
            scope="linear:issues:create",
            resource_id="linear_team:SALES",
            binding=_binding("gateway_header"),
            ttl_seconds=1,
        ))
        assert minted.lease is not None
        current = current + timedelta(seconds=2)

        result = broker.authorize_use(_use_request(minted.lease.lease_id, caller="gateway"))

        self.assertEqual(result.state, LeaseUseState.EXPIRED)


def _request(injection_mode: str) -> LeaseMintRequest:
    return LeaseMintRequest(
        session_id="sess_test",
        tool_id="linear.create_issue",
        scope="linear:issues:create",
        resource_id="linear_team:SALES",
        binding=_binding(injection_mode),
    )


def _binding(injection_mode: str) -> CredentialBinding:
    return CredentialBinding(
        credential_ref_id="credref_linear_sales",
        provider="onepassword",
        credential_class="linear.oauth_token",
        owner_team="sales-ops",
        injection_mode=injection_mode,
    )


def _ready_service_account() -> OnePasswordReadiness:
    return OnePasswordReadiness(
        platform_name="Darwin",
        desktop_app_present=True,
        op_cli_path=None,
        op_cli_version=None,
        op_account_configured=False,
        onepassword_mcp_path=None,
        service_account_token_present=True,
        status=OnePasswordProviderStatus.READY,
        provider_modes=["onepassword_sdk_service_account"],
    )


def _use_request(lease_id: str, caller: str) -> LeaseUseRequest:
    return LeaseUseRequest(
        lease_id=lease_id,
        session_id="sess_test",
        tool_id="linear.create_issue",
        scope="linear:issues:create",
        resource_id="linear_team:SALES",
        caller=caller,
    )


if __name__ == "__main__":
    unittest.main()
