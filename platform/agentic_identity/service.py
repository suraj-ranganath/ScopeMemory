"""Agentic Identity service — session delegation, identity proof, IAM adapter."""

from __future__ import annotations

import uuid
from typing import Any

from agentic_identity.delegation_jwt import issue_delegation_token
from agentic_identity.iam_client import assert_agent_eligible, resolve_agent_from_iam
from agentic_identity.tuples import identity_proof, preflight_tuples
from dolt_store import connect, get_delegation, get_session


def resolve_agent(agent_id: str) -> dict[str, Any]:
    """Resolve agent via IAM adapter (mock Dolt mirror or live HTTP)."""
    agent = resolve_agent_from_iam(agent_id)
    assert_agent_eligible(agent)
    return agent


def create_delegated_session(
    user_id: str,
    agent_id: str,
    team_id: str,
    goal: str,
    goal_class: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    agent = resolve_agent(agent_id)

    sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
        if not cur.fetchone():
            conn.close()
            raise ValueError(f"unknown user: {user_id}")
        cur.execute("SELECT 1 FROM teams WHERE team_id = %s", (team_id,))
        if not cur.fetchone():
            conn.close()
            raise ValueError(f"unknown team: {team_id}")
        cur.execute(
            """
            INSERT INTO sessions
            (session_id, user_id, team_id, agent_id, goal, goal_class, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'preflighted')
            """,
            (sid, user_id, team_id, agent_id, goal, goal_class),
        )
        cur.execute(
            "INSERT INTO delegations (session_id, user_id, agent_id, delegated_at) VALUES (%s, %s, %s, NOW())",
            (sid, user_id, agent_id),
        )
    conn.close()

    session = get_session(sid)
    delegation = get_delegation(sid)
    proof = build_identity_proof(session)
    token = issue_delegation_token(session, agent)
    return {
        "session": session,
        "delegation": delegation,
        "identity_proof": proof,
        "delegation_token": token,
    }


def mint_delegation_token_for_session(session_id: str) -> dict[str, Any]:
    session = get_session(session_id)
    if not session:
        raise ValueError(f"unknown session: {session_id}")
    delegation = get_delegation(session_id)
    if not delegation:
        raise ValueError(f"no delegation for session: {session_id}")
    agent = resolve_agent(session["agent_id"])
    token = issue_delegation_token(session, agent)
    return {
        "session_id": session_id,
        "delegation_token": token,
        "expires_in_seconds": None,
    }


def build_identity_proof(session: dict[str, Any] | None) -> dict[str, Any]:
    if not session:
        raise ValueError("session required")
    agent = resolve_agent(session["agent_id"])
    delegation = get_delegation(session["session_id"])

    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT * FROM workflow_recipes
            WHERE goal_class = %s AND team_id = %s AND status = 'accepted' LIMIT 1
            """,
            (session["goal_class"], session["team_id"]),
        )
        recipe = cur.fetchone()
    conn.close()

    tuples = preflight_tuples(session, agent, delegation, recipe)
    return identity_proof(session, agent, delegation, tuples)
