"""Shared preflight/authorize logic for REST and MCP gateways."""

from __future__ import annotations

from typing import Any

from agentic_iam import verify_agent_active
from authorization_checks import AuthorizationCheckService
from dolt_store import (
    append_session_event,
    create_ephemeral_grant,
    create_or_update_access_request,
    find_active_grant,
    get_session,
    list_access_requests,
    list_grants,
    save_policy_decision,
)
from graph_backend import authorize_context, backend_name, preflight_context, sync_graph
from mcp.visibility import visible_tools_from_context
from policy_contracts import Decision, contract_dict, stable_hash


AUTHZ_CHECKS = AuthorizationCheckService()


def recipe_hits_for_session(session: dict[str, Any], session_id: str) -> tuple[list[dict[str, Any]], str]:
    from graph_backend import search_recipe_hits

    hits = search_recipe_hits(
        team_id=session["team_id"],
        goal_class=session["goal_class"],
        goal_text=session["goal"],
        session_id=session_id,
    )
    return hits, backend_name()


def run_preflight(session_id: str, agent_id: str, jwt_claims: dict[str, Any]) -> dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise ValueError("session not found in Dolt")
    agent = verify_agent_active(agent_id)
    if session["agent_id"] != agent_id:
        raise ValueError("agent does not match session")

    rows, engine = sync_graph()
    ctx = preflight_context(session_id)
    recipe_hits, retrieval_engine = recipe_hits_for_session(session, session_id)
    access_requests = list_access_requests(session_id)
    grants = list_grants(session_id, active_only=True)
    preflight_event = append_session_event(
        session_id,
        "preflight_requested",
        {
            "agent_id": agent_id,
            "predicted_tools": ctx.get("predicted_tools", []),
            "predicted_scopes": ctx.get("predicted_scopes", []),
            "recipe_retrieval": retrieval_engine,
        },
    )
    identity = {
        "identity_ref": agent["identity_ref"],
        "trust_score": agent["trust_score"],
        "delegation_required": True,
        "delegation_verified": True,
        "iam_source": agent.get("source"),
    }
    return {
        "session_id": session_id,
        "agentic_iam": {
            "agent_id": agent["agent_id"],
            "identity_ref": agent["identity_ref"],
            "trust_score": agent["trust_score"],
            "source": agent.get("source"),
        },
        "delegation_jwt": {
            "verified": True,
            "session_id": jwt_claims.get("session_id"),
            "user_id": jwt_claims.get("user_id"),
            "legacy": jwt_claims.get("legacy", False),
        },
        "agentic_identity": identity,
        "source_of_truth": "dolt",
        "query_engine": engine,
        "synced_rows": rows,
        "recipe_hits": recipe_hits,
        "recipe_retrieval": retrieval_engine,
        "visible_tools": visible_tools_from_context(ctx, access_requests, grants),
        "human_required_requests": [
            req for req in access_requests if req.get("status") == "pending"
        ],
        "approved_grants": grants,
        "audit_event": {
            "event_id": preflight_event["event_id"],
            "event_hash": preflight_event["event_hash"],
            "prev_event_hash": preflight_event["prev_event_hash"],
        },
        **ctx,
    }


def run_authorize(
    session_id: str,
    agent_id: str,
    tool_id: str,
    resource_id: str,
    jwt_claims: dict[str, Any],
) -> dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise ValueError("session not found in Dolt")
    verify_agent_active(agent_id)
    if session["agent_id"] != agent_id:
        raise ValueError("agent does not match session")

    sync_graph()
    ctx = authorize_context(session_id, tool_id, resource_id)
    if "error" in ctx:
        raise ValueError(ctx["error"])

    idempotency_key = _idempotency_key(ctx)
    append_session_event(
        session_id,
        "authorization_check_requested",
        {
            "tool_id": tool_id,
            "resource_id": resource_id,
            "idempotency_key": idempotency_key,
        },
    )
    check = AUTHZ_CHECKS.evaluate(context=ctx, idempotency_key=idempotency_key)
    policy_decision = AUTHZ_CHECKS.decision_for(check.check_id)
    if policy_decision is None:
        raise ValueError("authorization check did not produce a policy decision")

    proof = {
        **contract_dict(policy_decision.proof),
        "context_path": ctx["context_path"],
        "rebac_tuples": ctx["rebac_tuples"],
        "memgraph_facts": ctx["facts"],
        "cozo_facts": policy_decision.proof.facts,
        "delegation_jwt": {
            "verified": True,
            "user_id": jwt_claims.get("user_id"),
            "identity_ref": jwt_claims.get("identity_ref"),
            "legacy": jwt_claims.get("legacy", False),
        },
    }

    decision_id = save_policy_decision(
        session_id,
        tool_id,
        resource_id,
        policy_decision.decision.value,
        proof,
    )
    access_request = None
    grant = None
    if policy_decision.decision == Decision.ESCALATE_HUMAN:
        access_request = create_or_update_access_request(
            session_id=session_id,
            user_id=session["user_id"],
            tool_id=tool_id,
            scope=policy_decision.required_scope,
            resource_id=resource_id,
            reason=policy_decision.reason,
            recipe_id=_recipe_id_from_context(ctx),
            proof_id=policy_decision.proof.proof_hash,
        )
    elif policy_decision.decision == Decision.AUTO_APPROVE_EPHEMERAL_GRANT:
        grant = create_ephemeral_grant(
            session_id=session_id,
            scope=policy_decision.required_scope,
            resource_id=resource_id,
            issuer="policy",
            proof_id=policy_decision.proof.proof_hash,
            reason=policy_decision.reason,
            ttl_seconds=900,
            call_count_remaining=1,
        )
    elif policy_decision.decision == Decision.ALLOW:
        grant = find_active_grant(session_id, policy_decision.required_scope, resource_id)

    event = append_session_event(
        session_id,
        "policy_decision",
        {
            "decision_id": decision_id,
            "check_id": check.check_id,
            "tool_id": tool_id,
            "resource_id": resource_id,
            "decision": policy_decision.decision.value,
            "proof_id": policy_decision.proof.proof_hash,
            "access_request_id": access_request.get("request_id") if access_request else "",
            "grant_id": grant.get("grant_id") if grant else "",
        },
    )

    result = {
        "decision_id": decision_id,
        "check_id": check.check_id,
        "check_state": check.state.value,
        "proof_id": policy_decision.proof.proof_hash,
        "decision": policy_decision.decision.value,
        "reason": policy_decision.reason,
        "proof": proof,
        "audit_store": "dolt",
        "audit_event": {
            "event_id": event["event_id"],
            "event_hash": event["event_hash"],
            "prev_event_hash": event["prev_event_hash"],
        },
    }
    if access_request:
        result["access_request"] = access_request
    if grant:
        result["grant"] = grant
    return result


def list_policy_decisions(session_id: str) -> list[dict[str, Any]]:
    import pymysql
    from config import DOLT_DATABASE, DOLT_HOST, DOLT_PASSWORD, DOLT_PORT, DOLT_USER
    from pymysql.cursors import DictCursor

    conn = pymysql.connect(
        host=DOLT_HOST,
        port=DOLT_PORT,
        user=DOLT_USER,
        password=DOLT_PASSWORD,
        database=DOLT_DATABASE,
        cursorclass=DictCursor,
    )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM policy_decisions WHERE session_id = %s ORDER BY created_at DESC",
            (session_id,),
        )
        rows = cur.fetchall()
    conn.close()
    return rows


def _idempotency_key(ctx: dict[str, Any]) -> str:
    facts = ctx.get("facts") or {}
    return stable_hash({
        "session_id": ctx.get("session_id"),
        "tool_id": ctx.get("tool_id"),
        "resource_id": ctx.get("resource_id"),
        "grant_present": facts.get("grant_present"),
        "scope": facts.get("scope"),
        "scope_approval_mode": facts.get("scope_approval_mode"),
    })


def _recipe_id_from_context(ctx: dict[str, Any]) -> str:
    path = ctx.get("context_path") or []
    return str(path[1]) if len(path) > 1 else ""
