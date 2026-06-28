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
    update_credential_lease_provider_operation,
)
from onepassword_provider import OnePasswordProvider, ProviderResolveState
from onepassword_readiness import detect_onepassword_readiness


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

    The provider uses 1Password `op run` after policy approval, so the secret is
    injected into a child execution boundary and never returned to ScopeMemory.
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

    readiness = detect_onepassword_readiness()
    broker = CredentialBroker(readiness)
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

    provider = OnePasswordProvider(op_path=readiness.op_cli_path)
    provider_result = provider.resolve_for_lease(lease_use, str(binding_row.get("secret_ref_handle") or ""))
    if provider_result.state != ProviderResolveState.RESOLVED:
        provider_metadata = provider_result.safe_metadata()
        append_session_event(
            session_id,
            "credential_provider_resolution_failed",
            {
                "decision_id": decision_id,
                "lease_id": minted.lease.lease_id,
                "provider": minted.lease.provider,
                "provider_mode": minted.lease.provider_mode,
                "provider_operation_id": provider_result.provider_operation_id,
                "provider_resolution_state": provider_result.state.value,
                "safe_reason": provider_result.safe_reason,
                "secret_exposed_to_agent": False,
                "secret_known_to_gateway": False,
            },
        )
        return {
            "state": provider_result.state.value,
            "safe_reason": provider_result.safe_reason,
            "lease": lease_row,
            "provider_resolution": provider_metadata,
        }

    update_credential_lease_provider_operation(minted.lease.lease_id, provider_result.provider_operation_id)
    evidence = dict(lease_use.evidence or {})
    evidence.update({
        "provider_operation_id": provider_result.provider_operation_id,
        "provider_resolution_state": provider_result.state.value,
        "secret_known_to_gateway": False,
    })
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
            "provider_operation_id": provider_result.provider_operation_id,
            "provider_resolution_state": provider_result.state.value,
            "injection_mode": minted.lease.injection_mode,
            "remaining_uses": remaining,
            "secret_exposed_to_agent": False,
            "secret_known_to_gateway": False,
            "execution_boundary": "op_run_subprocess",
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
        "provider_resolution": provider_result.safe_metadata(),
    }
