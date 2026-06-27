"""Agentic-IAM identity plane — registry, session delegation, identity proofs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agentic_identity.iam_client import assert_agent_eligible, resolve_agent_from_iam
from config import AGENTIC_IAM_MODE
from dolt_store import get_agent, get_session

router = APIRouter(prefix="/iam", tags=["agentic-iam"])

# Priority 2: built-in HTTP-shaped mock registry (use AGENTIC_IAM_URL=http://gateway:8080/mock-iam)
mock_router = APIRouter(prefix="/mock-iam", tags=["mock-agentic-iam"])


class CreateSessionRequest(BaseModel):
    user_id: str
    agent_id: str
    team_id: str
    goal: str
    goal_class: str
    session_id: str | None = None


class MintTokenRequest(BaseModel):
    session_id: str


def _agent_response(agent: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent_id": agent["agent_id"],
        "identity_ref": agent["identity_ref"],
        "display_name": agent["display_name"],
        "trust_score": agent["trust_score"],
        "status": agent["status"],
        "source": agent.get("source", f"agentic-iam-{AGENTIC_IAM_MODE}"),
    }


@router.get("/agents/{agent_id}")
def get_agent_identity(agent_id: str) -> dict[str, Any]:
    """Agent registry lookup via configured IAM adapter (mock or HTTP)."""
    try:
        agent = resolve_agent_from_iam(agent_id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except RuntimeError as e:
        raise HTTPException(502, str(e)) from e
    return _agent_response(agent)


@mock_router.get("/agents/{agent_id}")
def mock_iam_get_agent(agent_id: str) -> dict[str, Any]:
    """Simulates external Agentic-IAM HTTP API (reads Dolt mirror)."""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(404, detail="agent not found")
    return _agent_response({**agent, "source": "mock-iam-http"})


@mock_router.get("/health")
def mock_iam_health() -> dict[str, str]:
    return {"status": "ok", "service": "mock-agentic-iam"}


@router.post("/sessions")
def create_session(body: CreateSessionRequest) -> dict[str, Any]:
    """Agentic Identity: human delegates agent → returns signed delegation JWT."""
    from agentic_identity.service import create_delegated_session
    from graph_backend import sync_graph

    try:
        result = create_delegated_session(
            user_id=body.user_id,
            agent_id=body.agent_id,
            team_id=body.team_id,
            goal=body.goal,
            goal_class=body.goal_class,
            session_id=body.session_id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e

    rows, engine = sync_graph()
    return {
        **result,
        "graph_synced_rows": rows,
        "graph_engine": engine,
        "iam_mode": AGENTIC_IAM_MODE,
    }


@router.post("/delegation-token")
def mint_delegation_token(body: MintTokenRequest) -> dict[str, Any]:
    """Issue a delegation JWT for an existing session (e.g. after reseed)."""
    from agentic_identity.service import mint_delegation_token_for_session

    try:
        return mint_delegation_token_for_session(body.session_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e


@router.get("/sessions/{session_id}/identity-proof")
def session_identity_proof(session_id: str) -> dict[str, Any]:
    """ReBAC identity chain: user → delegates → agent → identity_ref → session."""
    from agentic_identity.service import build_identity_proof

    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "session not found")
    try:
        return build_identity_proof(session)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except PermissionError as e:
        raise HTTPException(403, str(e)) from e


def verify_agent_active(agent_id: str) -> dict[str, Any]:
    try:
        agent = resolve_agent_from_iam(agent_id)
        assert_agent_eligible(agent)
        return agent
    except LookupError as e:
        raise HTTPException(403, detail="agent not found in Agentic-IAM") from e
    except PermissionError as e:
        raise HTTPException(403, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(502, detail=str(e)) from e
