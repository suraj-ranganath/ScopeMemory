"""Shared preflight/authorize logic for REST and MCP gateways."""

from __future__ import annotations

from typing import Any

from agentic_iam import verify_agent_active
from cozo_policy import decide
from dolt_store import (
    append_session_event,
    attach_decision_to_snapshot,
    create_access_request,
    get_session,
    issue_ephemeral_grant,
    list_access_requests,
    list_active_grants,
    record_context_graph,
    save_context_snapshot,
    save_policy_decision,
    save_recipe_hits,
)
from graph_backend import authorize_context, backend_name, preflight_context, sync_graph
from policy_contracts import contract_dict


def recipe_hits_for_session(session: dict[str, Any], session_id: str) -> tuple[list[dict[str, Any]], str]:
    from graph_backend import search_recipe_hits

    hits = search_recipe_hits(
        team_id=session["team_id"],
        goal_class=session["goal_class"],
        goal_text=session["goal"],
        session_id=session_id,
    )
    return hits, backend_name()


def _commit_from_hits(recipe_hits: list[dict[str, Any]]) -> str:
    return str(recipe_hits[0].get("dolt_commit") or "demo-fixture") if recipe_hits else "demo-fixture"


def _qdrant_commit_from_hits(recipe_hits: list[dict[str, Any]]) -> str:
    return (
        str(recipe_hits[0].get("qdrant_index_commit") or recipe_hits[0].get("dolt_commit") or "demo-fixture")
        if recipe_hits
        else "demo-fixture"
    )


def _recipe_id_from_ctx(ctx: dict[str, Any]) -> str | None:
    matched = ctx.get("matched_recipe") or {}
    if matched:
        return matched.get("recipe_id") or matched.get("id")
    path = ctx.get("context_path") or []
    if len(path) > 1 and str(path[1]).startswith("recipe_"):
        return str(path[1])
    return None


def _visible_tools_for_preflight(session_id: str, predicted_tools: list[str]) -> list[str]:
    from dolt_store import connect
    from mcp.registry import AUTH_TOOL_NAMES, DOWNSTREAM_TOOL_NAMES

    visible = set(AUTH_TOOL_NAMES)
    visible.update(tool for tool in predicted_tools if tool in DOWNSTREAM_TOOL_NAMES)

    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ts.tool_id
            FROM grants g
            JOIN tool_scopes ts ON ts.scope = g.scope
            WHERE g.session_id = %s
              AND g.call_count_remaining > 0
              AND (g.expires_at IS NULL OR g.expires_at > NOW())
            """,
            (session_id,),
        )
        visible.update(row["tool_id"] for row in cur.fetchall() if row["tool_id"] in DOWNSTREAM_TOOL_NAMES)
    conn.close()
    return sorted(visible)


def run_preflight(session_id: str, agent_id: str, jwt_claims: dict[str, Any]) -> dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise ValueError("session not found in Dolt")
    agent = verify_agent_active(agent_id)
    if session["agent_id"] != agent_id:
        raise ValueError("agent does not match session")

    append_session_event(
        session_id,
        "preflight_requested",
        {
            "agent_id": agent_id,
            "delegation_jwt_verified": True,
            "user_id": jwt_claims.get("user_id"),
        },
    )
    rows, engine = sync_graph()
    ctx = preflight_context(session_id)
    recipe_hits, retrieval_engine = recipe_hits_for_session(session, session_id)
    persisted_hits = save_recipe_hits(session_id, recipe_hits)
    snapshot_payload = {
        "phase": "preflight",
        "session_id": session_id,
        "graph_context": ctx,
        "recipe_hits": recipe_hits,
        "delegation_jwt": {
            "verified": True,
            "session_id": jwt_claims.get("session_id"),
            "user_id": jwt_claims.get("user_id"),
            "legacy": jwt_claims.get("legacy", False),
        },
    }
    snapshot = save_context_snapshot(
        session_id,
        "preflight",
        snapshot_payload,
        dolt_commit_hash=_commit_from_hits(recipe_hits),
        qdrant_index_commit=_qdrant_commit_from_hits(recipe_hits),
    )
    graph_projection = record_context_graph(
        session_id,
        "preflight",
        ctx,
        recipe_hits=recipe_hits,
        snapshot_id=snapshot["snapshot_id"],
    )
    append_session_event(
        session_id,
        "preflight_completed",
        {
            "snapshot_id": snapshot["snapshot_id"],
            "recipe_hits": [h.get("recipe_id") for h in recipe_hits],
            "query_engine": engine,
            "recipe_retrieval": retrieval_engine,
        },
    )
    active_grants = list_active_grants(session_id)
    access_requests = list_access_requests(session_id)
    visible_tools = _visible_tools_for_preflight(session_id, ctx.get("predicted_tools") or [])
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
        "context_snapshot_id": snapshot["snapshot_id"],
        "fact_set_hash": snapshot["fact_set_hash"],
        "graph_projection": graph_projection,
        "visible_tools": visible_tools,
        "active_grants": active_grants,
        "access_requests": access_requests,
        "pending_access_requests": [
            req for req in access_requests if req.get("status") == "pending"
        ],
        "recipe_hits": recipe_hits,
        "reified_recipe_hits": persisted_hits,
        "recipe_retrieval": retrieval_engine,
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
    recipe_hits, retrieval_engine = recipe_hits_for_session(session, session_id)
    save_recipe_hits(session_id, recipe_hits)
    sync_graph()
    ctx = authorize_context(session_id, tool_id, resource_id)
    if "error" in ctx:
        raise ValueError(ctx["error"])
    snapshot_payload = {
        "phase": "authorize",
        "session_id": session_id,
        "tool_id": tool_id,
        "resource_id": resource_id,
        "graph_context": ctx,
        "recipe_hits": recipe_hits,
    }
    snapshot = save_context_snapshot(
        session_id,
        "authorize",
        snapshot_payload,
        dolt_commit_hash=_commit_from_hits(recipe_hits),
        qdrant_index_commit=_qdrant_commit_from_hits(recipe_hits),
    )
    facts = dict(ctx.get("facts") or {})
    facts.update({
        "context_snapshot_present": True,
        "context_snapshot_id": snapshot["snapshot_id"],
        "dolt_commit": snapshot["dolt_commit_hash"],
        "qdrant_index_commit": snapshot["qdrant_index_commit"],
    })
    ctx = {
        **ctx,
        "facts": facts,
        "context_snapshot_id": snapshot["snapshot_id"],
        "dolt_commit": snapshot["dolt_commit_hash"],
        "qdrant_index_commit": snapshot["qdrant_index_commit"],
    }
    graph_projection = record_context_graph(
        session_id,
        "authorize",
        ctx,
        recipe_hits=recipe_hits,
        snapshot_id=snapshot["snapshot_id"],
    )

    policy_decision = decide(ctx)
    proof = {
        **contract_dict(policy_decision.proof),
        "context_path": ctx["context_path"],
        "context_snapshot_id": snapshot["snapshot_id"],
        "fact_set_hash": snapshot["fact_set_hash"],
        "rebac_tuples": ctx["rebac_tuples"],
        "memgraph_facts": ctx["facts"],
        "cozo_facts": policy_decision.proof.facts,
        "graph_projection": graph_projection,
        "recipe_retrieval": retrieval_engine,
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
        context_snapshot_id=snapshot["snapshot_id"],
        dolt_commit_hash=snapshot["dolt_commit_hash"],
        qdrant_hits=recipe_hits,
        credential_lease_id=(
            policy_decision.credential_lease.lease_id
            if policy_decision.credential_lease
            else None
        ),
    )
    attach_decision_to_snapshot(snapshot["snapshot_id"], decision_id)
    append_session_event(
        session_id,
        "policy_decision_recorded",
        {
            "decision_id": decision_id,
            "decision": policy_decision.decision.value,
            "tool_id": tool_id,
            "resource_id": resource_id,
            "snapshot_id": snapshot["snapshot_id"],
            "proof_hash": policy_decision.proof.proof_hash,
        },
    )

    grant = None
    access_request = None
    if policy_decision.decision.value == "AUTO_APPROVE_EPHEMERAL_GRANT":
        grant = issue_ephemeral_grant(
            session_id,
            policy_decision.required_scope or facts.get("scope", ""),
            resource_id,
            issuer="policy:auto_approve",
            proof_id=policy_decision.proof.proof_hash,
        )
        try:
            sync_graph()
        except Exception:
            pass
    elif policy_decision.decision.value == "ESCALATE_HUMAN":
        access_request = create_access_request(
            session_id=session_id,
            user_id=str(facts.get("user_id") or session["user_id"]),
            agent_id=str(facts.get("agent_id") or agent_id),
            requested_scope=policy_decision.required_scope or str(facts.get("scope") or ""),
            requested_resource=resource_id,
            requested_tool_id=tool_id,
            reason=policy_decision.reason,
            recipe_id=_recipe_id_from_ctx(ctx),
            proof_id=policy_decision.proof.proof_hash,
        )

    return {
        "decision_id": decision_id,
        "decision": policy_decision.decision.value,
        "reason": policy_decision.reason,
        "proof": proof,
        "audit_store": "dolt",
        "context_snapshot_id": snapshot["snapshot_id"],
        "fact_set_hash": snapshot["fact_set_hash"],
        "graph_projection": graph_projection,
        "recipe_retrieval": retrieval_engine,
        "grant": grant,
        "access_request": access_request,
    }


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
