"""MCP tool/call handlers with policy-bound downstream execution."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from agentic_identity.auth import resolve_delegation_token
from credential_runtime import mint_gateway_credential_lease
from dolt_store import append_session_event, connect, consume_grant_for_tool, mark_access_request_tool_call_seen
from gateway_service import list_policy_decisions, run_authorize, run_preflight
from mcp.protocol import MCP_AUTH_REQUIRED, MCP_POLICY_DENIED, tool_result_text
from mcp.registry import AUTH_TOOL_NAMES, DOWNSTREAM_TOOL_NAMES
from mcp.safe_views import explain_denial, redact_decision_rows
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
    predicted = set(ctx.get("predicted_tools") or [])
    visible = set(AUTH_TOOL_NAMES)
    for tool in predicted:
        if tool in DOWNSTREAM_TOOL_NAMES:
            visible.add(tool)
    for tool in _granted_tools_for_session(session_id):
        if tool in DOWNSTREAM_TOOL_NAMES:
            visible.add(tool)
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
        decisions = redact_decision_rows(list_policy_decisions(session_id))
        decision_id = args.get("decision_id")
        if decision_id:
            decisions = [row for row in decisions if row.get("decision_id") == decision_id]
        return tool_result_text({"session_id": session_id, "decisions": decisions})

    if name == "auth.request_scope":
        requested_tool = args.get("tool_id")
        if not requested_tool:
            raise McpHandlerError(MCP_POLICY_DENIED, "tool_id required")
        if requested_tool not in DOWNSTREAM_TOOL_NAMES:
            raise McpHandlerError(MCP_POLICY_DENIED, f"unknown downstream tool: {requested_tool}")
        resource_id = _resource_for_tool(requested_tool, args)
        auth = run_authorize(session_id, agent_id, requested_tool, resource_id, claims)
        return tool_result_text(
            {
                "decision": auth["decision"],
                "decision_id": auth["decision_id"],
                "check_id": auth.get("check_id"),
                "check_state": auth.get("check_state"),
                "proof_id": auth.get("proof_id"),
                "reason": auth["reason"],
                "access_request": auth.get("access_request"),
                "grant": auth.get("grant"),
                "proof_summary": _proof_summary(auth),
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
                "decision_id": args.get("decision_id", ""),
                "outcome": args.get("outcome", ""),
                "note": args.get("note", ""),
                "agent_id": agent_id,
            },
        )
        return tool_result_text(
            {
                "accepted": True,
                "event_id": event["event_id"],
                "event_hash": event["event_hash"],
            }
        )

    if name not in DOWNSTREAM_TOOL_NAMES:
        raise McpHandlerError(MCP_POLICY_DENIED, f"unknown tool: {name}")

    repair = validate_tool_arguments(name, args)
    if repair:
        append_session_event(
            session_id,
            "tool_call_repair_requested",
            {"tool_id": name, "missing_arguments": repair.get("missing_arguments", [])},
        )
        return tool_result_text(repair, is_error=True)

    resource_id = _resource_for_tool(name, args)
    tool_intent = tool_intent_for(name, args, resource_id)
    append_session_event(
        session_id,
        "hook_pre_tool_use_checked",
        {
            "agent_host": "codex",
            "tool_id": name,
            "resource_id": resource_id,
            "route": "scope_memory_gateway",
            "secret_access_pattern": "none",
            "permission_decision": "allow",
            "secret_exposed_to_agent": False,
        },
    )
    append_session_event(
        session_id,
        "tool_call_requested",
        {"tool_id": name, "resource_id": resource_id, "tool_intent": tool_intent},
    )
    mark_access_request_tool_call_seen(session_id, name, resource_id)
    auth = run_authorize(session_id, agent_id, name, resource_id, claims)
    decision = auth["decision"]

    if decision in {"ALLOW", "AUTO_APPROVE_EPHEMERAL_GRANT"}:
        consumed_grant = consume_grant_for_tool(
            session_id,
            name,
            resource_id,
            decision_id=auth["decision_id"],
        )
        if not consumed_grant:
            raise McpHandlerError(
                MCP_POLICY_DENIED,
                "policy allowed execution but no live grant was available",
                {
                    "decision_id": auth["decision_id"],
                    "check_id": auth.get("check_id"),
                    "tool_id": name,
                    "resource_id": resource_id,
                },
            )
        credential_lease = mint_gateway_credential_lease(
            session_id=session_id,
            tool_id=name,
            scope=str(consumed_grant.get("scope") or ""),
            resource_id=resource_id,
            decision_id=auth["decision_id"],
            proof_id=auth.get("proof_id", ""),
        )
        if credential_lease and credential_lease.get("state") != "used":
            raise McpHandlerError(
                MCP_POLICY_DENIED,
                "credential lease could not be minted for approved execution",
                credential_lease,
            )
        execution_auth = {
            **auth,
            "grant": auth.get("grant") or consumed_grant,
            "credential_lease": credential_lease,
        }
        try:
            execution = execute_downstream_tool(
                tool_id=name,
                args=args,
                resource_id=resource_id,
                authorization=execution_auth,
                audit_writer=append_session_event,
                slack_searcher=search_slack,
            )
        except RuntimeExecutionError as e:
            raise McpHandlerError(MCP_POLICY_DENIED, str(e), {"decision_id": auth["decision_id"]}) from e
        return tool_result_text(
            {
                "decision": decision,
                "decision_id": auth["decision_id"],
                "check_id": auth.get("check_id"),
                "check_state": auth.get("check_state"),
                "proof_id": auth.get("proof_id"),
                "grant": auth.get("grant") or consumed_grant,
                "consumed_grant": consumed_grant,
                "credential_lease": credential_lease,
                "tool_intent": tool_intent,
                "execution": execution,
                "proof_summary": _proof_summary(auth),
            },
        )

    append_session_event(
        session_id,
        "denial_returned",
        {
            "tool_id": name,
            "resource_id": resource_id,
            "decision_id": auth["decision_id"],
            "check_id": auth.get("check_id"),
            "decision": decision,
            "error": _error_for_decision(decision),
        },
    )
    return tool_result_text(
        {
            "error": _error_for_decision(decision),
            "decision": decision,
            "reason": auth["reason"],
            "decision_id": auth["decision_id"],
            "check_id": auth.get("check_id"),
            "check_state": auth.get("check_state"),
            "proof_id": auth.get("proof_id"),
            "access_request": auth.get("access_request"),
            "proof_summary": _proof_summary(auth),
        },
        is_error=True,
    )


def _granted_tools_for_session(session_id: str) -> set[str]:
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ts.tool_id
            FROM grants g
            JOIN tool_scopes ts ON ts.scope = g.scope
            WHERE g.session_id = %s
              AND g.call_count_remaining > 0
              AND (g.expires_at IS NULL OR g.expires_at > NOW())
            """,
            (session_id,),
        )
        rows = cur.fetchall()
    conn.close()
    return {row["tool_id"] for row in rows}


def _proof_summary(auth: dict[str, Any]) -> dict[str, Any]:
    proof = auth.get("proof") or {}
    return {
        "check_id": auth.get("check_id") or proof.get("check_id", ""),
        "check_state": auth.get("check_state") or proof.get("check_state", ""),
        "proof_id": auth.get("proof_id", ""),
        "context_path": proof.get("context_path", []),
        "context_snapshot_id": proof.get("context_snapshot_id") or auth.get("context_snapshot_id"),
        "fact_set_hash": proof.get("fact_set_hash") or auth.get("fact_set_hash"),
        "rules": proof.get("rules", []),
    }


def _error_for_decision(decision: str) -> str:
    if decision == "ESCALATE_HUMAN":
        return "scope_required"
    if decision == "REPAIR":
        return "repair_required"
    return "policy_denied"


def _resource_for_tool(tool_id: str, args: dict[str, Any]) -> str:
    if tool_id == "slack.search_messages":
        channel = args.get("channel") or args.get("resource_id")
        if not channel:
            raise McpHandlerError(MCP_POLICY_DENIED, "channel required for slack.search_messages")
        return str(channel)
    resource_id = args.get("resource_id")
    if not resource_id:
        raise McpHandlerError(MCP_POLICY_DENIED, "resource_id required")
    return str(resource_id)
