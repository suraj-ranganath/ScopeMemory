"""Person B: UI state model — SessionGoal -> RecipeHits -> PredictedScopes -> AccessRequests -> UI State."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dolt_store import (
    connect,
    get_session,
    list_context_graph,
    list_credential_leases,
    list_department_traces,
)

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    path = FIXTURES / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(name)
    return json.loads(path.read_text())


def _recipe_details(recipe_id: str) -> tuple[list[str], list[str], str]:
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("SELECT title FROM workflow_recipes WHERE recipe_id = %s", (recipe_id,))
        row = cur.fetchone()
        title = row["title"] if row else recipe_id
        cur.execute("SELECT tool_id FROM recipe_tools WHERE recipe_id = %s", (recipe_id,))
        tools = [x["tool_id"] for x in cur.fetchall()]
        cur.execute("SELECT scope FROM recipe_scopes WHERE recipe_id = %s", (recipe_id,))
        scopes = [x["scope"] for x in cur.fetchall()]
    conn.close()
    return tools, scopes, title


def build_ui_state(session_id: str, use_fixtures: bool = False) -> dict[str, Any]:
    if use_fixtures:
        hit = load_fixture("recipe_hits")
        return {
            "session": load_fixture("session"),
            "recipe_hits": [hit],
            "predicted_tools": hit.get("predicted_tools", []),
            "predicted_scopes": hit.get("predicted_scopes", []),
            "access_requests": [load_fixture("access_request")],
            "mode": "fixture",
        }

    session = get_session(session_id)
    if not session:
        raise ValueError(f"unknown session: {session_id}")

    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM workflow_recipes WHERE goal_class = %s AND team_id = %s AND status = 'accepted'",
            (session["goal_class"], session["team_id"]),
        )
        recipes = cur.fetchall()
        cur.execute("SELECT * FROM access_requests WHERE session_id = %s", (session_id,))
        requests = cur.fetchall()
        cur.execute(
            "SELECT * FROM policy_decisions WHERE session_id = %s ORDER BY created_at",
            (session_id,),
        )
        decisions = cur.fetchall()
        cur.execute(
            """
            SELECT *
            FROM session_events
            WHERE session_id = %s
            ORDER BY COALESCE(event_order, 0), created_at, event_id
            """,
            (session_id,),
        )
        events = cur.fetchall()
        cur.execute("SELECT * FROM recipe_proposals WHERE evidence_session_id = %s", (session_id,))
        proposals = cur.fetchall()
        cur.execute("SELECT * FROM grants WHERE session_id = %s", (session_id,))
        grants = cur.fetchall()
        cur.execute("SELECT * FROM recipe_index_meta")
        index_meta = cur.fetchall()
    conn.close()

    predicted_tools: list[str] = []
    predicted_scopes: list[str] = []
    recipe_hits: list[dict[str, Any]] = []
    for r in recipes:
        tools, scopes, title = _recipe_details(r["recipe_id"])
        predicted_tools.extend(tools)
        predicted_scopes.extend(scopes)
        recipe_hits.append({"recipe_id": r["recipe_id"], "score": 0.89, "title": title})

    normalized_requests = [_normalize_request(row) for row in requests]
    normalized_events = [
        {**e, "payload": json.loads(e["event_json"]) if isinstance(e.get("event_json"), str) else e.get("event_json")}
        for e in events
    ]
    decisions = [
        {
            **d,
            "proof": json.loads(d["proof_json"]) if isinstance(d.get("proof_json"), str) else d.get("proof_json"),
        }
        for d in decisions
    ]
    credential_leases = [_normalize_bool_fields(row) for row in list_credential_leases(session_id)]
    context_graph = list_context_graph(session_id)
    department_traces = list_department_traces()

    return {
        "session": session,
        "recipe_hits": recipe_hits,
        "predicted_tools": list(dict.fromkeys(predicted_tools)),
        "predicted_scopes": list(dict.fromkeys(predicted_scopes)),
        "access_requests": normalized_requests,
        "anticipated_requests": [
            req for req in normalized_requests
            if req.get("request_origin") == "preflight_prediction" or req.get("created_before_tool_call")
        ],
        "grants": grants,
        "credential_leases": credential_leases,
        "policy_decisions": decisions,
        "timeline": normalized_events,
        "trace_events": [_trace_event(event) for event in normalized_events],
        "context_graph": context_graph,
        "department_traces": department_traces,
        "agent_run": _agent_run(session, normalized_events, normalized_requests, decisions, credential_leases),
        "recipe_proposals": [
            {**p, "proposal": json.loads(p["proposal_json"])} for p in proposals
        ],
        "index_status": {"indexed_recipes": len(index_meta), "recipes": index_meta},
        "ui_status": session.get("status", "preflighted"),
        "mode": "live",
    }


def _normalize_request(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    source = out.get("source_trace_ids_json")
    if isinstance(source, str) and source:
        try:
            out["source_trace_ids"] = json.loads(source)
        except json.JSONDecodeError:
            out["source_trace_ids"] = []
    else:
        out["source_trace_ids"] = []
    out["created_before_tool_call"] = bool(out.get("created_before_tool_call"))
    return out


def _normalize_bool_fields(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if "secret_exposed_to_agent" in out:
        out["secret_exposed_to_agent"] = bool(out["secret_exposed_to_agent"])
    return out


def _trace_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = str(event.get("event_type") or "")
    lane = "Audit"
    if event_type.startswith(("preflight", "recipe", "scope", "historical")):
        lane = "Context"
    elif event_type.startswith(("access_request", "grant")):
        lane = "Approval"
    elif event_type.startswith(("authorization", "policy", "denial")):
        lane = "Policy"
    elif event_type.startswith(("credential", "hook")):
        lane = "Credential"
    elif event_type.startswith(("tool_call", "downstream", "output")):
        lane = "Execution"
    elif event_type.startswith(("workflow", "recipe_proposal")):
        lane = "Learning"
    return {
        "lane": lane,
        "event_type": event_type,
        "created_at": event.get("created_at"),
        "payload": event.get("payload") or {},
        "event_hash": event.get("event_hash"),
        "prev_event_hash": event.get("prev_event_hash"),
    }


def _agent_run(
    session: dict[str, Any],
    events: list[dict[str, Any]],
    requests: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    credential_leases: list[dict[str, Any]],
) -> dict[str, Any]:
    pending = [req for req in requests if req.get("status") == "pending"]
    approved = [req for req in requests if req.get("status") == "approved"]
    event_types = [str(event.get("event_type") or "") for event in events]
    status = session.get("status", "delegated")
    if pending:
        status = "waiting_for_async_approval"
    elif any(decision.get("decision") == "ALLOW" for decision in decisions) and approved:
        status = "resumed_after_approval"
    if credential_leases:
        status = "credential_bound_execution"
    if any(event == "downstream_call_executed" for event in event_types):
        status = "executed"
    return {
        "status": status,
        "current_step": event_types[-1] if event_types else "session_seeded",
        "pending_approvals": len(pending),
        "approved_requests": len(approved),
        "policy_decisions": len(decisions),
        "credential_leases": len(credential_leases),
        "last_event_hash": events[-1].get("event_hash") if events else "",
    }
