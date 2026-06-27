"""Shared preflight/authorize logic for REST and MCP gateways."""

from __future__ import annotations

from typing import Any

from agentic_iam import verify_agent_active
from cozo_policy import evaluate, export_facts
from dolt_store import get_session, save_policy_decision
from graph_backend import authorize_context, backend_name, preflight_context, sync_graph


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

    decision, reason, rules = evaluate(ctx["facts"])
    cozo_facts = export_facts(ctx["facts"])

    proof = {
        "decision": decision,
        "reason": reason,
        "context_path": ctx["context_path"],
        "rebac_tuples": ctx["rebac_tuples"],
        "memgraph_facts": ctx["facts"],
        "cozo_facts": cozo_facts,
        "rules": rules,
        "policy_engine": "deterministic-rules",
        "delegation_jwt": {
            "verified": True,
            "user_id": jwt_claims.get("user_id"),
            "identity_ref": jwt_claims.get("identity_ref"),
            "legacy": jwt_claims.get("legacy", False),
        },
    }

    decision_id = save_policy_decision(session_id, tool_id, resource_id, decision, proof)

    return {
        "decision_id": decision_id,
        "decision": decision,
        "reason": reason,
        "proof": proof,
        "audit_store": "dolt",
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
