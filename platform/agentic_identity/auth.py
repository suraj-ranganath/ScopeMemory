"""Delegation JWT verification for /auth/* endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import Header, HTTPException

from agentic_identity.delegation_jwt import (
    DelegationTokenError,
    claims_match_session,
    verify_delegation_token,
)
from config import DELEGATION_JWT_REQUIRED
from dolt_store import get_delegation, get_session


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def resolve_delegation_token(
    session_id: str,
    agent_id: str,
    delegation_token: str | None,
    authorization: str | None,
) -> dict[str, Any]:
    token = delegation_token or extract_bearer_token(authorization)
    if not token:
        if DELEGATION_JWT_REQUIRED:
            raise HTTPException(
                401,
                detail="delegation JWT required (Authorization: Bearer or delegation_token)",
            )
        return _legacy_delegation_check(session_id, agent_id)

    try:
        claims = verify_delegation_token(token)
        claims_match_session(claims, session_id, agent_id)
    except DelegationTokenError as e:
        raise HTTPException(401, detail={"error": e.code, "message": str(e)}) from e

    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "session not found in Dolt")
    if session["user_id"] != claims["user_id"] or session["team_id"] != claims["team_id"]:
        raise HTTPException(401, detail="token claims do not match session record")

    delegation = get_delegation(session_id)
    if not delegation:
        raise HTTPException(403, detail="no delegation record for session")

    return claims


def _legacy_delegation_check(session_id: str, agent_id: str) -> dict[str, Any]:
    """Fallback when DELEGATION_JWT_REQUIRED=false (local dev only)."""
    session = get_session(session_id)
    if not session or session["agent_id"] != agent_id:
        raise HTTPException(400, "agent does not match session")
    delegation = get_delegation(session_id)
    if not delegation:
        raise HTTPException(403, detail="no delegation for session")
    return {
        "session_id": session_id,
        "user_id": session["user_id"],
        "agent_id": agent_id,
        "team_id": session["team_id"],
        "legacy": True,
    }
