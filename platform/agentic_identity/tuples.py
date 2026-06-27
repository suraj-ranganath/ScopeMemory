"""ReBAC tuple builders for Agentic Identity proofs (RFC-07 parity)."""

from __future__ import annotations

from typing import Any


def preflight_tuples(
    session: dict[str, Any],
    agent: dict[str, Any] | None,
    delegation: dict[str, Any] | None,
    recipe: dict[str, Any] | None,
) -> list[str]:
    sid = session["session_id"]
    tuples = [
        f"user:{session['user_id']}#member@team:{session['team_id']}",
        f"agent:{session['agent_id']}#executes@session:{sid}",
    ]
    if agent:
        aid = agent.get("agent_id") or agent.get("id")
        tuples.append(f"agent:{aid}#identity@{agent['identity_ref']}")
    if delegation:
        tuples.append(
            f"user:{delegation['user_id']}#delegates@agent:{delegation['agent_id']}@session:{sid}"
        )
    if recipe:
        rid = recipe.get("recipe_id") or recipe.get("id")
        if rid:
            tuples.append(f"session:{sid}#matches@recipe:{rid}")
    return tuples


def identity_proof(
    session: dict[str, Any],
    agent: dict[str, Any],
    delegation: dict[str, Any] | None,
    rebac_tuples: list[str],
) -> dict[str, Any]:
    return {
        "session_id": session["session_id"],
        "user_id": session["user_id"],
        "team_id": session["team_id"],
        "agent_id": session["agent_id"],
        "identity_ref": agent["identity_ref"],
        "trust_score": agent["trust_score"],
        "agent_status": agent["status"],
        "delegation_present": delegation is not None,
        "delegation": delegation,
        "rebac_tuples": rebac_tuples,
        "story": "Agentic-IAM knows who the agent is; ScopeMemory decides what it may do via ReBAC.",
    }
