"""Demo credential lease runtime for policy-bound downstream execution."""

from __future__ import annotations

from typing import Any

from credential_broker import (
    CredentialBinding,
    CredentialBroker,
    LeaseMintRequest,
    LeaseMintState,
    LeaseUseRequest,
)
from dolt_store import (
    append_session_event,
    attach_credential_lease_to_decision,
    find_credential_binding,
    mark_credential_lease_used,
    save_credential_lease,
)
from onepassword_readiness import OnePasswordProviderStatus, OnePasswordReadiness


def mint_gateway_credential_lease(
    *,
    session_id: str,
    tool_id: str,
    scope: str,
    resource_id: str,
    decision_id: str,
    proof_id: str,
) -> dict[str, Any] | None:
    """Mint and authorize a broker-owned lease for a credential-bound tool call.

    The hackathon path records the opaque lease and gateway injection boundary
    without resolving a live 1Password secret. Live provider setup is handled
    later; this path still keeps the secret handle out of agent-visible traces.
    """

    binding_row = find_credential_binding(tool_id, scope, resource_id)
    if not binding_row:
        return None

    append_session_event(
        session_id,
        "credential_binding_selected",
        {
            "decision_id": decision_id,
            "tool_id": tool_id,
            "scope": scope,
            "resource_id": resource_id,
            "credential_ref_id": binding_row["credential_ref_id"],
            "provider": binding_row["provider"],
            "injection_mode": binding_row["injection_mode"],
            "secret_exposed_to_agent": False,
            "secret_known_to_gateway": False,
        },
    )

    broker = CredentialBroker(_demo_ready_onepassword())
    binding = CredentialBinding(
        credential_ref_id=binding_row["credential_ref_id"],
        provider=binding_row["provider"],
        credential_class=binding_row["credential_class"],
        owner_team=binding_row["owner_team"],
        injection_mode=binding_row["injection_mode"],
    )
    minted = broker.mint_lease(LeaseMintRequest(
        session_id=session_id,
        tool_id=tool_id,
        scope=scope,
        resource_id=resource_id,
        binding=binding,
        ttl_seconds=900,
        max_uses=1,
        would_expose_secret_to_agent=False,
    ))
    if minted.state != LeaseMintState.MINTED or minted.lease is None:
        append_session_event(
            session_id,
            "credential_lease_blocked",
            {
                "decision_id": decision_id,
                "tool_id": tool_id,
                "scope": scope,
                "resource_id": resource_id,
                "state": minted.state.value,
                "safe_reason": minted.safe_reason,
                "setup_required": list(minted.setup_required),
                "secret_known_to_gateway": False,
            },
        )
        return {
            "state": minted.state.value,
            "safe_reason": minted.safe_reason,
            "setup_required": list(minted.setup_required),
        }

    lease_row = save_credential_lease(minted.lease)
    attach_credential_lease_to_decision(decision_id, minted.lease.lease_id)
    append_session_event(
        session_id,
        "credential_lease_minted",
        {
            "decision_id": decision_id,
            "proof_id": proof_id,
            "lease_id": minted.lease.lease_id,
            "credential_ref_hash": minted.lease.credential_ref_hash,
            "provider": minted.lease.provider,
            "provider_mode": minted.lease.provider_mode,
            "injection_mode": minted.lease.injection_mode,
            "secret_exposed_to_agent": False,
            "secret_known_to_gateway": False,
            "max_uses": minted.lease.max_uses,
            "expires_at": minted.lease.expires_at,
        },
    )

    lease_use = broker.authorize_use(LeaseUseRequest(
        lease_id=minted.lease.lease_id,
        session_id=session_id,
        tool_id=tool_id,
        scope=scope,
        resource_id=resource_id,
        caller="gateway",
    ))
    if lease_use.state.value != "approved":
        append_session_event(
            session_id,
            "credential_lease_blocked",
            {
                "decision_id": decision_id,
                "lease_id": minted.lease.lease_id,
                "state": lease_use.state.value,
                "safe_reason": lease_use.safe_reason,
                "secret_exposed_to_agent": False,
                "secret_known_to_gateway": False,
            },
        )
        return {
            "state": lease_use.state.value,
            "safe_reason": lease_use.safe_reason,
            "lease": lease_row,
        }

    evidence = dict(lease_use.evidence or {})
    evidence["secret_known_to_gateway"] = False
    remaining = int(evidence.get("remaining_uses", 0))
    used_row = mark_credential_lease_used(minted.lease.lease_id, uses_remaining=remaining)
    append_session_event(
        session_id,
        "credential_injected_by_gateway",
        {
            "decision_id": decision_id,
            "lease_id": minted.lease.lease_id,
            "credential_ref_hash": minted.lease.credential_ref_hash,
            "provider": minted.lease.provider,
            "provider_mode": minted.lease.provider_mode,
            "provider_operation_id": minted.lease.provider_operation_id,
            "provider_resolution_state": "broker_owned_demo",
            "injection_mode": minted.lease.injection_mode,
            "remaining_uses": remaining,
            "secret_exposed_to_agent": False,
            "secret_known_to_gateway": False,
            "execution_boundary": "gateway",
        },
    )
    safe_binding = {
        key: value for key, value in binding_row.items()
        if key != "secret_ref_handle"
    }
    return {
        "state": "used",
        "binding": safe_binding,
        "lease": used_row or lease_row,
        "evidence": evidence,
    }


def _demo_ready_onepassword() -> OnePasswordReadiness:
    return OnePasswordReadiness(
        platform_name="demo",
        desktop_app_present=True,
        op_cli_path=None,
        op_cli_version=None,
        op_account_configured=False,
        onepassword_mcp_path=None,
        service_account_token_present=True,
        status=OnePasswordProviderStatus.READY,
        provider_modes=["onepassword_sdk_service_account"],
        setup_required=[],
        notes=["Demo readiness: secret resolution is broker-owned and never serialized."],
    )
