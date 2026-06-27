"""Agentic-IAM adapter — Priority 2: mock (Dolt mirror) vs live HTTP registry."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Protocol

from config import AGENTIC_IAM_API_KEY, AGENTIC_IAM_MODE, AGENTIC_IAM_URL, TRUST_SCORE_MIN
from dolt_store import get_agent


class IamAdapter(Protocol):
    def fetch_agent(self, agent_id: str) -> dict[str, Any]: ...


class MockIamAdapter:
    """Reads agent registry mirror from Dolt (demo / offline)."""

    def fetch_agent(self, agent_id: str) -> dict[str, Any]:
        agent = get_agent(agent_id)
        if not agent:
            raise LookupError(f"agent not registered: {agent_id}")
        return _normalize_agent(agent, source="mock-dolt")


class HttpIamAdapter:
    """Live Agentic-IAM HTTP registry (GET {AGENTIC_IAM_URL}/agents/{agent_id})."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def fetch_agent(self, agent_id: str) -> dict[str, Any]:
        url = f"{self.base_url}/agents/{agent_id}"
        headers = {"Accept": "application/json"}
        if AGENTIC_IAM_API_KEY:
            headers["Authorization"] = f"Bearer {AGENTIC_IAM_API_KEY}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise LookupError(f"agent not found in Agentic-IAM: {agent_id}") from e
            raise RuntimeError(f"Agentic-IAM HTTP {e.code}: {e.read().decode()}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Agentic-IAM unreachable at {url}: {e.reason}") from e
        return _normalize_agent(data, source="http")


def _normalize_agent(raw: dict[str, Any], source: str) -> dict[str, Any]:
    agent_id = raw.get("agent_id") or raw.get("id")
    if not agent_id:
        raise ValueError("IAM response missing agent_id")
    return {
        "agent_id": agent_id,
        "identity_ref": raw["identity_ref"],
        "display_name": raw.get("display_name", agent_id),
        "trust_score": float(raw.get("trust_score", 0)),
        "status": raw.get("status", "unknown"),
        "source": source,
    }


def get_iam_adapter() -> IamAdapter:
    if AGENTIC_IAM_MODE == "http":
        if not AGENTIC_IAM_URL:
            raise RuntimeError("AGENTIC_IAM_MODE=http requires AGENTIC_IAM_URL")
        return HttpIamAdapter(AGENTIC_IAM_URL)
    return MockIamAdapter()


def resolve_agent_from_iam(agent_id: str) -> dict[str, Any]:
    adapter = get_iam_adapter()
    return adapter.fetch_agent(agent_id)


def assert_agent_eligible(agent: dict[str, Any]) -> None:
    if agent["status"] != "active":
        raise PermissionError(f"agent not active: {agent['agent_id']}")
    if agent["trust_score"] < TRUST_SCORE_MIN:
        raise PermissionError(f"agent trust score too low: {agent['trust_score']}")
