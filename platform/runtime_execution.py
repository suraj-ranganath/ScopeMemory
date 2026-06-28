"""Policy-bound downstream execution for local hackathon demo apps."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.safe_views import redact_text
from policy_contracts import ToolIntent, contract_dict

EXECUTABLE_DECISIONS = {"ALLOW", "AUTO_APPROVE_EPHEMERAL_GRANT"}
EXECUTABLE_CHECK_STATES = {"approved", "auto_approved"}
SECRET_KEY_MARKERS = (
    "authorization",
    "bearer",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)

AuditWriter = Callable[[str, str, dict[str, Any]], dict[str, Any]]
GrantConsumer = Callable[[str, str, str], dict[str, Any]]
SlackSearcher = Callable[[str], dict[str, Any]]


class RuntimeExecutionError(Exception):
    """Raised when code tries to execute without an executable policy result."""


def validate_tool_arguments(tool_id: str, args: dict[str, Any]) -> dict[str, Any] | None:
    if tool_id == "slack.search_messages" and (args.get("channel") or args.get("resource_id")):
        return None
    required = {
        "linear.create_issue": ("resource_id", "title"),
        "linear.search_issues": ("resource_id", "query"),
        "linear.add_comment": ("resource_id", "issue_id", "body"),
        "slack.search_messages": ("channel",),
        "slack.post_message": ("resource_id", "text"),
    }
    missing = [name for name in required.get(tool_id, ()) if not args.get(name)]
    if not missing:
        return None
    return {
        "decision": "REPAIR",
        "error": "repair_required",
        "repairable": True,
        "safe_guidance": f"Provide required argument(s): {', '.join(missing)}",
        "missing_arguments": missing,
    }


def tool_intent_for(tool_id: str, args: dict[str, Any], resource_id: str) -> dict[str, Any]:
    intent = ToolIntent(
        session_id=str(args.get("session_id", "")),
        tool_id=tool_id,
        resource_id=resource_id,
        requested_scope=str(args.get("requested_scope", "")),
        access_kind=_access_kind(tool_id),
        idempotency_key=str(args.get("idempotency_key", "")),
    )
    return contract_dict(intent)


def execute_downstream_tool(
    *,
    tool_id: str,
    args: dict[str, Any],
    resource_id: str,
    authorization: dict[str, Any],
    audit_writer: AuditWriter | None = None,
    grant_consumer: GrantConsumer | None = None,
    slack_searcher: SlackSearcher | None = None,
) -> dict[str, Any]:
    _assert_executable(authorization)
    audit_events = []
    session_id = str(args.get("session_id") or authorization.get("proof", {}).get("session_id") or "")
    proof_id = str(authorization.get("proof_id") or "")

    if grant_consumer and authorization.get("grant", {}).get("grant_id"):
        consumed = grant_consumer(str(authorization["grant"]["grant_id"]), session_id, proof_id)
        if consumed.get("event_type") == "grant_consume_failed":
            raise RuntimeExecutionError(str(consumed.get("reason") or "grant could not be consumed"))
        audit_events.append(consumed)

    payload = _execute(tool_id, args, resource_id, authorization, slack_searcher)
    redacted_payload, redacted_fields = redact_payload(payload)
    if redacted_payload.get("untrusted_instructions_redacted"):
        redacted_fields.append("prompt_injection")

    if audit_writer and session_id:
        audit_events.append(audit_writer(session_id, "downstream_call_executed", {
            "tool_id": tool_id,
            "resource_id": resource_id,
            "decision_id": authorization.get("decision_id", ""),
            "check_id": authorization.get("check_id", ""),
            "proof_id": proof_id,
            "status": redacted_payload.get("status", "ok"),
            "mode": redacted_payload.get("mode", "mock"),
        }))
        if redacted_fields:
            audit_events.append(audit_writer(session_id, "output_redacted", {
                "tool_id": tool_id,
                "resource_id": resource_id,
                "redacted_fields": redacted_fields,
                "proof_id": proof_id,
            }))

    return {
        **redacted_payload,
        "redacted_fields": redacted_fields,
        "audit_events": [_safe_audit_summary(event) for event in audit_events if event],
    }


def redact_payload(value: Any, path: str = "") -> tuple[Any, list[str]]:
    redacted_fields: list[str] = []
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, nested in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            lower_key = str(key).lower()
            if any(marker in lower_key for marker in SECRET_KEY_MARKERS):
                out[str(key)] = "[redacted]"
                redacted_fields.append(child_path)
                continue
            out[str(key)], nested_fields = redact_payload(nested, child_path)
            redacted_fields.extend(nested_fields)
        return out, redacted_fields
    if isinstance(value, list):
        out_list = []
        for idx, item in enumerate(value):
            redacted, nested_fields = redact_payload(item, f"{path}[{idx}]")
            out_list.append(redacted)
            redacted_fields.extend(nested_fields)
        return out_list, redacted_fields
    if isinstance(value, str):
        redacted = redact_text(value)
        if redacted != value:
            redacted_fields.append(path or "value")
        return redacted, redacted_fields
    return value, redacted_fields


def _assert_executable(authorization: dict[str, Any]) -> None:
    decision = authorization.get("decision")
    check_state = authorization.get("check_state")
    if decision not in EXECUTABLE_DECISIONS or check_state not in EXECUTABLE_CHECK_STATES:
        raise RuntimeExecutionError("downstream execution requires an approved authorization check")


def _execute(
    tool_id: str,
    args: dict[str, Any],
    resource_id: str,
    authorization: dict[str, Any],
    slack_searcher: SlackSearcher | None,
) -> dict[str, Any]:
    session_id = str(args.get("session_id") or authorization.get("proof", {}).get("session_id") or "")
    agent_id = str(args.get("agent_id") or authorization.get("proof", {}).get("agent_id") or "")
    decision_id = str(authorization.get("decision_id") or "")
    lease_id = _lease_id(authorization)

    if tool_id == "linear.create_issue":
        from demo_apps import create_linear_issue
        return create_linear_issue(
            session_id=session_id,
            agent_id=agent_id,
            team_id=resource_id,
            title=str(args.get("title", "")),
            description=str(args.get("description", "")),
            policy_decision_id=decision_id,
            credential_lease_id=lease_id,
        )
    if tool_id == "linear.search_issues":
        from demo_apps import search_linear_issues
        query = str(args.get("query", ""))
        return search_linear_issues(team_id=resource_id, query=query)
    if tool_id == "linear.add_comment":
        from demo_apps import add_linear_comment
        return add_linear_comment(
            session_id=session_id,
            agent_id=agent_id,
            issue_id=str(args.get("issue_id", "")),
            body=str(args.get("body", "")),
            policy_decision_id=decision_id,
        )
    if tool_id == "slack.search_messages":
        if slack_searcher:
            payload = slack_searcher(resource_id)
            return {
                "channel": resource_id,
                "messages": payload.get("messages", []),
                "prompt_injection_detected": bool(payload.get("prompt_injection")),
                "untrusted_context_present": bool(payload.get("prompt_injection")),
                "untrusted_instructions_redacted": bool(payload.get("prompt_injection")),
                "status": "searched",
                "mode": "fixture",
            }
        from demo_apps import search_slack_messages
        payload = search_slack_messages(channel_id=resource_id)
        return {
            **payload,
            "untrusted_instructions_redacted": bool(payload.get("untrusted_context_present")),
        }
    if tool_id == "slack.post_message":
        from demo_apps import post_slack_message
        return post_slack_message(
            session_id=session_id,
            channel_id=resource_id,
            user_id=agent_id or "agent_renewal_01",
            user_name="RenewalBot",
            text=str(args.get("text", "")),
            policy_decision_id=decision_id,
        )
    raise RuntimeExecutionError(f"no executor for {tool_id}")


def _access_kind(tool_id: str) -> str:
    if tool_id in {"slack.search_messages", "linear.search_issues"}:
        return "read"
    return "write"


def _safe_audit_summary(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": event.get("event_id", ""),
        "event_type": event.get("event_type", ""),
        "event_hash": event.get("event_hash", ""),
    }


def _lease_id(authorization: dict[str, Any]) -> str:
    credential_lease = authorization.get("credential_lease")
    if not isinstance(credential_lease, dict):
        return ""
    lease = credential_lease.get("lease")
    if isinstance(lease, dict):
        return str(lease.get("lease_id") or "")
    return ""
