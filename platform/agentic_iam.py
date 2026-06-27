"""Agentic-IAM identity plane (mock for demo — swap for real Agentic-IAM API)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from dolt_store import get_agent

router = APIRouter(prefix="/iam", tags=["agentic-iam"])


@router.get("/agents/{agent_id}")
def get_agent_identity(agent_id: str) -> dict[str, Any]:
    """Mirror of Agentic-IAM agent registry lookup."""
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="agent not found")
    return {
        "agent_id": agent["agent_id"],
        "identity_ref": agent["identity_ref"],
        "display_name": agent["display_name"],
        "trust_score": agent["trust_score"],
        "status": agent["status"],
        "source": "agentic-iam-mock",
    }


def verify_agent_active(agent_id: str) -> dict[str, Any]:
    agent = get_agent(agent_id)
    if not agent or agent["status"] != "active":
        raise HTTPException(status_code=403, detail="agent not active in Agentic-IAM")
    if agent["trust_score"] < 0.5:
        raise HTTPException(status_code=403, detail="agent trust score too low")
    return agent
