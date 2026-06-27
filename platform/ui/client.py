"""HTTP client for ScopeMemory gateway (REST + MCP JSON-RPC)."""

from __future__ import annotations

import json
from typing import Any

import requests


class GatewayClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8080", timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get(self, path: str, token: str | None = None) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = requests.get(self._url(path), headers=headers, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def post(
        self,
        path: str,
        body: dict | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = requests.post(
            self._url(path),
            json=body or {},
            headers=headers,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    # --- health & admin ---

    def health(self) -> dict[str, Any]:
        return self.get("/health")

    def reseed(self) -> dict[str, Any]:
        return self.post("/admin/reseed")

    # --- agentic identity ---

    def get_agent(self, agent_id: str) -> dict[str, Any]:
        return self.get(f"/iam/agents/{agent_id}")

    def create_session(
        self,
        user_id: str,
        agent_id: str,
        team_id: str,
        goal: str,
        goal_class: str,
    ) -> dict[str, Any]:
        return self.post(
            "/iam/sessions",
            {
                "user_id": user_id,
                "agent_id": agent_id,
                "team_id": team_id,
                "goal": goal,
                "goal_class": goal_class,
            },
        )

    def mint_token(self, session_id: str) -> str:
        out = self.post("/iam/delegation-token", {"session_id": session_id})
        return out["delegation_token"]

    def identity_proof(self, session_id: str) -> dict[str, Any]:
        return self.get(f"/iam/sessions/{session_id}/identity-proof")

    # --- auth ---

    def preflight(self, session_id: str, agent_id: str, token: str) -> dict[str, Any]:
        return self.post(
            "/auth/preflight",
            {"session_id": session_id, "agent_id": agent_id},
            token=token,
        )

    def authorize(
        self,
        session_id: str,
        agent_id: str,
        tool_id: str,
        resource_id: str,
        token: str,
    ) -> dict[str, Any]:
        return self.post(
            "/auth/authorize",
            {
                "session_id": session_id,
                "agent_id": agent_id,
                "tool_id": tool_id,
                "resource_id": resource_id,
            },
            token=token,
        )

    def proof_trail(self, session_id: str) -> dict[str, Any]:
        return self.get(f"/auth/proof/{session_id}")

    # --- person b demo ---

    def ui_state(self, session_id: str) -> dict[str, Any]:
        return self.get(f"/demo/ui-state/{session_id}")

    def approve_request(self, request_id: str, approver_id: str = "user_bob") -> dict[str, Any]:
        return self.post(
            f"/demo/access-requests/{request_id}/approve",
            {"approver_id": approver_id},
        )

    def slack_search(self, channel: str) -> dict[str, Any]:
        return self.get(f"/demo/slack/search?channel={channel}")

    def index_recipes(self) -> dict[str, Any]:
        return self.post("/index/recipes")

    def propose_recipe(self, session_id: str) -> dict[str, Any]:
        return self.post(f"/demo/recipes/propose?session_id={session_id}")

    # --- mcp ---

    def mcp(
        self,
        method: str,
        params: dict | None = None,
        token: str | None = None,
        req_id: int = 1,
    ) -> dict[str, Any]:
        body = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            body["params"] = params
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = requests.post(
            self._url("/mcp"),
            json=body,
            headers=headers,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    @staticmethod
    def format_error(exc: Exception) -> str:
        if isinstance(exc, requests.HTTPError) and exc.response is not None:
            try:
                detail = exc.response.json()
                return json.dumps(detail, indent=2)
            except Exception:
                return exc.response.text or str(exc)
        return str(exc)
