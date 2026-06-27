"""MCP tool catalog — RFC-03 meta-server tools + demo downstream tools."""

from __future__ import annotations

from typing import Any

SESSION_ARGS = {
    "session_id": {"type": "string", "description": "Active delegation session"},
    "agent_id": {"type": "string", "description": "Agent identity from Agentic-IAM"},
}

RESOURCE_ARG = {
    "resource_id": {
        "type": "string",
        "description": "Target resource (e.g. linear_team:SALES, slack_channel:sales-acme)",
    },
}


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


AUTH_TOOLS: list[dict[str, Any]] = [
    _tool(
        "auth.preflight_goal",
        "Preflight session goal — recipe hits, predicted tools/scopes, ReBAC context.",
        {
            **SESSION_ARGS,
        },
        ["session_id", "agent_id"],
    ),
    _tool(
        "auth.show_decision_proof",
        "Return policy decision audit trail for a session.",
        {
            **SESSION_ARGS,
            "decision_id": {"type": "string", "description": "Optional policy decision id"},
        },
        ["session_id", "agent_id"],
    ),
    _tool(
        "auth.request_scope",
        "Create or refresh a human approval request for a policy-gated scope.",
        {
            **SESSION_ARGS,
            **RESOURCE_ARG,
            "tool_id": {"type": "string", "description": "Requested downstream MCP tool"},
            "reason": {"type": "string", "description": "Safe user-facing reason for the request"},
        },
        ["session_id", "agent_id", "tool_id", "resource_id"],
    ),
    _tool(
        "auth.explain_denial",
        "Explain a denied policy decision without exposing secrets.",
        {
            **SESSION_ARGS,
            "decision_id": {"type": "string", "description": "Optional policy decision id"},
        },
        ["session_id", "agent_id"],
    ),
    _tool(
        "auth.submit_workflow_feedback",
        "Record safe workflow feedback for later recipe review.",
        {
            **SESSION_ARGS,
            "feedback": {"type": "string", "description": "Safe feedback text"},
            "scenario": {"type": "string", "description": "Optional demo scenario or recipe id"},
        },
        ["session_id", "agent_id", "feedback"],
    ),
]

DOWNSTREAM_TOOLS: list[dict[str, Any]] = [
    _tool(
        "linear.create_issue",
        "Create a Linear issue (policy-gated; mock execution in demo).",
        {
            **SESSION_ARGS,
            **RESOURCE_ARG,
            "title": {"type": "string", "description": "Issue title"},
            "description": {"type": "string", "description": "Issue body"},
        },
        ["session_id", "agent_id", "resource_id", "title"],
    ),
    _tool(
        "slack.search_messages",
        "Search Slack channel history (policy-gated; fixture data in demo).",
        {
            **SESSION_ARGS,
            "channel": {
                "type": "string",
                "description": "Channel resource id (e.g. slack_channel:sales-acme)",
            },
        },
        ["session_id", "agent_id", "channel"],
    ),
    _tool(
        "slack.post_message",
        "Post a Slack message (policy-gated; mock execution in demo).",
        {
            **SESSION_ARGS,
            **RESOURCE_ARG,
            "text": {"type": "string", "description": "Message text"},
        },
        ["session_id", "agent_id", "resource_id", "text"],
    ),
]

ALL_TOOLS: dict[str, dict[str, Any]] = {
    t["name"]: t for t in AUTH_TOOLS + DOWNSTREAM_TOOLS
}

AUTH_TOOL_NAMES = {t["name"] for t in AUTH_TOOLS}
DOWNSTREAM_TOOL_NAMES = {t["name"] for t in DOWNSTREAM_TOOLS}
