from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from credential_broker import CredentialBroker, LeaseMintRequest, LeaseUseRequest  # noqa: E402
from onepassword_provider import OnePasswordProvider, ProviderResolveState  # noqa: E402
from onepassword_readiness import OnePasswordProviderStatus, OnePasswordReadiness  # noqa: E402
from test_credential_hooks import _binding  # noqa: E402


class OnePasswordProviderTests(unittest.TestCase):
    def test_resolves_with_fake_op_without_returning_secret_to_gateway(self) -> None:
        op_path = _fake_op()
        lease_use = _approved_lease_use()

        result = OnePasswordProvider(op_path=op_path).resolve_for_lease(
            lease_use,
            "op://ScopeMemory Demo/Linear API Token/token",
        )

        self.assertEqual(result.state, ProviderResolveState.RESOLVED)
        self.assertNotIn("resolved-demo-token", str(result.safe_metadata()))
        self.assertFalse(result.safe_metadata()["secret_exposed_to_agent"])
        self.assertFalse(result.safe_metadata()["secret_known_to_gateway"])

    def test_requires_approved_lease_use(self) -> None:
        minted = _broker().mint_lease(_request())
        assert minted.lease is not None
        denied_use = _broker().authorize_use(LeaseUseRequest(
            lease_id=minted.lease.lease_id,
            session_id="sess_test",
            tool_id="linear.create_issue",
            scope="linear:issues:create",
            resource_id="linear_team:SALES",
            caller="agent",
        ))

        result = OnePasswordProvider(op_path=_fake_op()).resolve_for_lease(
            denied_use,
            "op://ScopeMemory Demo/Linear API Token/token",
        )

        self.assertEqual(result.state, ProviderResolveState.DENIED)

    def test_locked_or_cancelled_cli_escalates_human(self) -> None:
        op_path = _fake_op(run_body='echo "no account found for filter" >&2; exit 1')

        result = OnePasswordProvider(op_path=op_path).resolve_for_lease(
            _approved_lease_use(),
            "op://ScopeMemory Demo/Linear API Token/token",
        )

        self.assertEqual(result.state, ProviderResolveState.ESCALATE_HUMAN)

    def test_invalid_reference_is_denied_before_cli_call(self) -> None:
        result = OnePasswordProvider(op_path=_fake_op()).resolve_for_lease(
            _approved_lease_use(),
            "not-a-secret-reference",
        )

        self.assertEqual(result.state, ProviderResolveState.DENIED)


def _approved_lease_use():
    broker = _broker()
    minted = broker.mint_lease(_request())
    assert minted.lease is not None
    return broker.authorize_use(LeaseUseRequest(
        lease_id=minted.lease.lease_id,
        session_id="sess_test",
        tool_id="linear.create_issue",
        scope="linear:issues:create",
        resource_id="linear_team:SALES",
        caller="gateway",
    ))


def _request() -> LeaseMintRequest:
    return LeaseMintRequest(
        session_id="sess_test",
        tool_id="linear.create_issue",
        scope="linear:issues:create",
        resource_id="linear_team:SALES",
        binding=_binding("gateway_header"),
    )


def _broker() -> CredentialBroker:
    readiness = OnePasswordReadiness(
        platform_name="Darwin",
        desktop_app_present=True,
        op_cli_path="/fake/op",
        op_cli_version="test",
        op_account_configured=True,
        onepassword_mcp_path=None,
        service_account_token_present=False,
        status=OnePasswordProviderStatus.READY,
        provider_modes=["op_cli_secret_reference"],
    )
    return CredentialBroker(readiness)


def _fake_op(run_body: str | None = None) -> str:
    temp_dir = tempfile.mkdtemp(prefix="scopememory-op-")
    op_path = Path(temp_dir) / "op"
    body = run_body or (
        'shift\n'
        'if [ "$1" = "--" ]; then shift; fi\n'
        'SCOPEMEMORY_1P_SECRET="resolved-demo-token" "$@"\n'
    )
    op_path.write_text(f"#!/bin/sh\nif [ \"$1\" != \"run\" ]; then exit 2; fi\n{body}\n")
    os.chmod(op_path, 0o700)
    return str(op_path)


if __name__ == "__main__":
    unittest.main()
