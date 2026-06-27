"""MCP tool/call handlers — JWT-gated authorization + mock downstream execution."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException

from agentic_identity.auth import resolve_delegation_token
from gateway_service import list_policy_decisions, run_authorize, run_preflight
from mcp.protocol import MCP_AUTH_REQUIRED, MCP_POLICY_DENIED, tool_result_text
from mcp.registry import AUTH_TOOL_NAMES, DOWNSTREAM_TOOL_NAMES
from person_b.slack_fixtures import search_slack


class McpHandlerError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def _require_session_args(arguments: dict[str, Any]) -> tuple[str, str]:
    session_id = arguments.get("session_id")
    agent_id = arguments.get("agent_id")
    if not session_id or not agent_id:
        raise McpHandlerError(
            MCP_POLICY_DENIED,
            "session_id and agent_id required in tool arguments",
        )
    return session_id, agent_id


def _resolve_jwt(session_id: str, agent_id: str, authorization: str | None) -> dict[str, Any]:
    try:
        return resolve_delegation_token(session_id, agent_id, None, authorization)
    except HTTPException as e:
        detail = e.detail
        if e.status_code == 401:
            raise McpHandlerError(MCP_AUTH_REQUIRED, "delegation JWT required", detail) from e
        if e.status_code == 403:
            raise McpHandlerError(MCP_POLICY_DENIED, "delegation forbidden", detail) from e
        if e.status_code == 404:
            raise McpHandlerError(404, "session not found", detail) from e
        raise McpHandlerError(MCP_POLICY_DENIED, str(detail), detail) from e


def visible_tools_for_session(session_id: str, agent_id: str, authorization: str | None) -> list[str]:
    """Return tool names visible to this delegated session."""
    _resolve_jwt(session_id, agent_id, authorization)
    from graph_backend import preflight_context

    ctx = preflight_context(session_id)
    predicted = set(ctx.get("predicted_tools") or [])
    visible = set(AUTH_TOOL_NAMES)
    for tool in predicted:
        if tool in DOWNSTREAM_TOOL_NAMES:
            visible.add(tool)
    visible.add("slack.post_message")
    return sorted(visible)


def handle_tool_call(
    name: str,
    arguments: dict[str, Any] | None,
    authorization: str | None,
) -> dict[str, Any]:
    args = arguments or {}
    session_id, agent_id = _require_session_args(args)
    claims = _resolve_jwt(session_id, agent_id, authorization)

    if name == "auth.preflight_goal":
        return tool_result_text(run_preflight(session_id, agent_id, claims))

    if name == "auth.show_decision_proof":
        decisions = list_policy_decisions(session_id)
        return tool_result_text({"session_id": session_id, "decisions": decisions})

    if name not in DOWNSTREAM_TOOL_NAMES:
        raise McpHandlerError(MCP_POLICY_DENIED, f"unknown tool: {name}")

    resource_id = _resource_for_tool(name, args)
    auth = run_authorize(session_id, agent_id, name, resource_id, claims)
    decision = auth["decision"]

    if decision == "ALLOW":
        execution = _mock_execute(name, args, resource_id)
        return tool_result_text(
            {
                "decision": decision,
                "decision_id": auth["decision_id"],
                "execution": execution,
                "proof_summary": {
                    "context_path": auth["proof"]["context_path"],
                    "rules": auth["proof"]["rules"],
                },
            },
        )

    return tool_result_text(
        {
            "error": "scope_required" if decision == "ESCALATE_HUMAN" else "policy_denied",
            "decision": decision,
            "reason": auth["reason"],
            "decision_id": auth["decision_id"],
            "proof_summary": {
                "context_path": auth["proof"]["context_path"],
                "rules": auth["proof"]["rules"],
            },
        },
        is_error=True,
    )


def _resource_for_tool(tool_id: str, args: dict[str, Any]) -> str:
    if tool_id == "slack.search_messages":
        channel = args.get("channel") or args.get("resource_id")
        if not channel:
            raise McpHandlerError(MCP_POLICY_DENIED, "channel required for slack.search_messages")
        return channel
    resource_id = args.get("resource_id")
    if not resource_id:
        raise McpHandlerError(MCP_POLICY_DENIED, "resource_id required")
    return resource_id


def _mock_execute(tool_id: str, args: dict[str, Any], resource_id: str) -> dict[str, Any]:
    if tool_id == "linear.create_issue":
        return {
            "issue_id": f"LIN-{uuid.uuid4().hex[:8]}",
            "team": resource_id,
            "title": args.get("title", ""),
            "status": "created",
            "mode": "mock",
        }
    if tool_id == "slack.search_messages":
        payload = search_slack(resource_id)
        return {
            "channel": resource_id,
            "messages": payload.get("messages", []),
            "prompt_injection_detected": bool(payload.get("prompt_injection")),
            "mode": "fixture",
        }
    if tool_id == "slack.post_message":
        return {
            "channel": resource_id,
            "text": args.get("text", ""),
            "status": "posted",
            "mode": "mock",
        }
    raise McpHandlerError(MCP_POLICY_DENIED, f"no executor for {tool_id}")
