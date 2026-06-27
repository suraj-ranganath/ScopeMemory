"""Person B: learning worker — recipe proposal (WP-07)."""

from __future__ import annotations

import json
from typing import Any

from dolt_store import connect


def propose_recipe_from_session(session_id: str) -> dict[str, Any]:
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM sessions WHERE session_id = %s", (session_id,))
        session = cur.fetchone()
        if not session:
            conn.close()
            raise ValueError(f"unknown session: {session_id}")

        cur.execute(
            "SELECT * FROM workflow_recipes WHERE goal_class = %s AND team_id = %s AND status = 'accepted' LIMIT 1",
            (session["goal_class"], session["team_id"]),
        )
        base = cur.fetchone()
        if not base:
            conn.close()
            return {
                "should_propose_recipe": False,
                "session_id": session_id,
                "reason": f"no accepted recipe for goal_class={session['goal_class']}",
            }

        cur.execute("SELECT tool_id FROM recipe_tools WHERE recipe_id = %s", (base["recipe_id"],))
        tools = [r["tool_id"] for r in cur.fetchall()]
        cur.execute("SELECT scope, approval_mode FROM recipe_scopes WHERE recipe_id = %s", (base["recipe_id"],))
        scopes = {r["scope"]: r["approval_mode"] for r in cur.fetchall()}
        cur.execute(
            "SELECT decision, tool_id FROM policy_decisions WHERE session_id = %s",
            (session_id,),
        )
        decisions = cur.fetchall()

    proposal_id = f"proposal/recipe-{session['goal_class']}-v4"
    proposal = {
        "should_propose_recipe": True,
        "proposal_id": proposal_id,
        "base_recipe_id": base["recipe_id"],
        "title": f"{base['title']} (learned v4)",
        "goal_class": session["goal_class"],
        "tools": tools,
        "scopes": scopes,
        "confidence": 0.84,
        "evidence_sessions": [session_id],
        "safety_notes": "External Slack posting remains denied unless explicitly predicted.",
        "decisions_observed": [{"decision": d["decision"], "tool_id": d["tool_id"]} for d in decisions],
    }

    with conn.cursor() as cur:
        cur.execute("DELETE FROM recipe_proposals WHERE proposal_id = %s", (proposal_id,))
        cur.execute(
            """
            INSERT INTO recipe_proposals
            (proposal_id, base_recipe_id, title, goal_class, proposal_json, status, evidence_session_id)
            VALUES (%s, %s, %s, %s, %s, 'proposed', %s)
            """,
            (
                proposal_id, base["recipe_id"], proposal["title"], session["goal_class"],
                json.dumps(proposal), session_id,
            ),
        )
    conn.close()
    return proposal
