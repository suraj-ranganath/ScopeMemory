"""MCP tool/call handlers — JWT-gated authorization + mock downstream execution."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from agentic_identity.auth import resolve_delegation_token
from dolt_store import append_session_event, consume_grant, list_access_requests, list_grants
from gateway_service import (
    list_policy_decisions,
    run_authorize,
    run_preflight,
)
from mcp.protocol import MCP_AUTH_REQUIRED, MCP_POLICY_DENIED, tool_result_text
from mcp.registry import DOWNSTREAM_TOOL_NAMES
from mcp.safe_views import explain_denial, redact_decision_rows
from mcp.visibility import visible_tools_from_context
from person_b.slack_fixtures import search_slack
from runtime_execution import (
    RuntimeExecutionError,
    execute_downstream_tool,
    tool_intent_for,
    validate_tool_arguments,
)


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
    return visible_tools_from_context(
        ctx,
        list_access_requests(session_id),
        list_grants(session_id, active_only=True),
    )


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
        decision_id = args.get("decision_id")
        if decision_id:
            decisions = [d for d in decisions if d.get("decision_id") == decision_id]
        return tool_result_text({"session_id": session_id, "decisions": redact_decision_rows(decisions)})

    if name == "auth.request_scope":
        tool_id = args.get("tool_id")
        if tool_id not in DOWNSTREAM_TOOL_NAMES:
            raise McpHandlerError(MCP_POLICY_DENIED, "known downstream tool_id required")
        resource_id = _resource_for_tool(tool_id, args)
        auth = run_authorize(session_id, agent_id, tool_id, resource_id, claims)
        return tool_result_text(
            {
                "session_id": session_id,
                "tool_id": tool_id,
                "resource_id": resource_id,
                "decision": auth["decision"],
                "decision_id": auth["decision_id"],
                "check_id": auth["check_id"],
                "check_state": auth["check_state"],
                "reason": args.get("reason") or auth["reason"],
                "access_request": auth.get("access_request"),
                "grant": auth.get("grant"),
                "proof_id": auth["proof_id"],
            },
            is_error=auth["decision"] in {"DENY", "REPAIR"},
        )

    if name == "auth.explain_denial":
        decisions = redact_decision_rows(list_policy_decisions(session_id))
        return tool_result_text(explain_denial(decisions, args.get("decision_id")))

    if name == "auth.submit_workflow_feedback":
        event = append_session_event(
            session_id,
            "workflow_feedback_submitted",
            {
                "agent_id": agent_id,
                "feedback": args.get("feedback", ""),
                "scenario": args.get("scenario", ""),
            },
        )
        return tool_result_text(
            {
                "session_id": session_id,
                "event_id": event["event_id"],
                "event_hash": event["event_hash"],
                "recorded": True,
            }
        )

    if name not in DOWNSTREAM_TOOL_NAMES:
        raise McpHandlerError(MCP_POLICY_DENIED, f"unknown tool: {name}")

    repair = validate_tool_arguments(name, args)
    if repair:
        append_session_event(
            session_id,
            "tool_call_repair_returned",
            {
                "tool_id": name,
                "missing_arguments": repair["missing_arguments"],
                "safe_guidance": repair["safe_guidance"],
            },
        )
        return tool_result_text(
            {
                **repair,
                "tool_id": name,
                "session_id": session_id,
                "check_state": "repairable",
            },
            is_error=True,
        )

    resource_id = _resource_for_tool(name, args)
    append_session_event(
        session_id,
        "tool_call_requested",
        {
            "tool_id": name,
            "resource_id": resource_id,
            "tool_intent": tool_intent_for(name, args, resource_id),
        },
    )
    auth = run_authorize(session_id, agent_id, name, resource_id, claims)
    decision = auth["decision"]

    if decision in {"ALLOW", "AUTO_APPROVE_EPHEMERAL_GRANT"}:
        try:
            execution = execute_downstream_tool(
                tool_id=name,
                args=args,
                resource_id=resource_id,
                authorization=auth,
                audit_writer=append_session_event,
                grant_consumer=consume_grant,
                slack_searcher=search_slack,
            )
        except RuntimeExecutionError as e:
            raise McpHandlerError(MCP_POLICY_DENIED, str(e)) from e
        return tool_result_text(
            {
                "decision": decision,
                "decision_id": auth["decision_id"],
                "check_id": auth["check_id"],
                "check_state": auth["check_state"],
                "proof_id": auth["proof_id"],
                "grant": auth.get("grant"),
                "tool_intent": tool_intent_for(name, args, resource_id),
                "execution": execution,
                "proof_summary": {
                    "context_path": auth["proof"]["context_path"],
                    "rules": auth["proof"]["rules"],
                },
            },
        )

    append_session_event(
        session_id,
        "denial_returned",
        {
            "tool_id": name,
            "resource_id": resource_id,
            "decision": decision,
            "decision_id": auth["decision_id"],
            "proof_id": auth["proof_id"],
        },
    )
    return tool_result_text(
        {
            "error": "scope_required" if decision == "ESCALATE_HUMAN" else "policy_denied",
            "decision": decision,
            "reason": auth["reason"],
            "decision_id": auth["decision_id"],
            "check_id": auth["check_id"],
            "check_state": auth["check_state"],
            "proof_id": auth["proof_id"],
            "access_request": auth.get("access_request"),
            "tool_intent": tool_intent_for(name, args, resource_id),
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
