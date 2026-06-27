"""Signed delegation JWT — Priority 1: prove delegation on every /auth/* call."""

from __future__ import annotations

import time
from typing import Any

import jwt

from config import (
    DELEGATION_JWT_AUDIENCE,
    DELEGATION_JWT_ISSUER,
    DELEGATION_JWT_SECRET,
    DELEGATION_JWT_TTL_SECONDS,
)


class DelegationTokenError(Exception):
    def __init__(self, message: str, code: str = "invalid_token") -> None:
        super().__init__(message)
        self.code = code


def issue_delegation_token(
    session: dict[str, Any],
    agent: dict[str, Any],
    *,
    ttl_seconds: int | None = None,
) -> str:
    now = int(time.time())
    ttl = ttl_seconds if ttl_seconds is not None else DELEGATION_JWT_TTL_SECONDS
    payload = {
        "iss": DELEGATION_JWT_ISSUER,
        "aud": DELEGATION_JWT_AUDIENCE,
        "sub": agent["agent_id"],
        "session_id": session["session_id"],
        "user_id": session["user_id"],
        "agent_id": session["agent_id"],
        "team_id": session["team_id"],
        "identity_ref": agent["identity_ref"],
        "trust_score": agent["trust_score"],
        "iat": now,
        "exp": now + ttl,
        "token_type": "delegation",
    }
    return jwt.encode(payload, DELEGATION_JWT_SECRET, algorithm="HS256")


def verify_delegation_token(token: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            DELEGATION_JWT_SECRET,
            algorithms=["HS256"],
            audience=DELEGATION_JWT_AUDIENCE,
            issuer=DELEGATION_JWT_ISSUER,
        )
    except jwt.ExpiredSignatureError as e:
        raise DelegationTokenError("delegation token expired", "expired") from e
    except jwt.InvalidTokenError as e:
        raise DelegationTokenError("delegation token invalid", "invalid") from e

    if claims.get("token_type") != "delegation":
        raise DelegationTokenError("wrong token type", "wrong_type")
    required = ("session_id", "user_id", "agent_id", "team_id", "identity_ref")
    for key in required:
        if not claims.get(key):
            raise DelegationTokenError(f"missing claim: {key}", "missing_claim")
    return claims


def claims_match_session(claims: dict[str, Any], session_id: str, agent_id: str) -> None:
    if claims["session_id"] != session_id:
        raise DelegationTokenError("token session_id mismatch", "session_mismatch")
    if claims["agent_id"] != agent_id:
        raise DelegationTokenError("token agent_id mismatch", "agent_mismatch")
