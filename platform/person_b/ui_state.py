"""Person B: UI state model — SessionGoal -> RecipeHits -> PredictedScopes -> AccessRequests -> UI State."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dolt_store import connect, get_session

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
        cur.execute("SELECT * FROM session_events WHERE session_id = %s ORDER BY created_at", (session_id,))
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

    return {
        "session": session,
        "recipe_hits": recipe_hits,
        "predicted_tools": list(dict.fromkeys(predicted_tools)),
        "predicted_scopes": list(dict.fromkeys(predicted_scopes)),
        "access_requests": requests,
        "grants": grants,
        "policy_decisions": [
            {
                **d,
                "proof": json.loads(d["proof_json"]) if isinstance(d.get("proof_json"), str) else d.get("proof_json"),
            }
            for d in decisions
        ],
        "timeline": [
            {**e, "payload": json.loads(e["event_json"]) if isinstance(e.get("event_json"), str) else e.get("event_json")}
            for e in events
        ],
        "recipe_proposals": [
            {**p, "proposal": json.loads(p["proposal_json"])} for p in proposals
        ],
        "index_status": {"indexed_recipes": len(index_meta), "recipes": index_meta},
        "ui_status": session.get("status", "preflighted"),
        "mode": "live",
    }
