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
        "Request authorization for a tool/resource pair without executing the downstream tool.",
        {
            **SESSION_ARGS,
            "tool_id": {"type": "string", "description": "Downstream tool to authorize"},
            **RESOURCE_ARG,
            "channel": {
                "type": "string",
                "description": "Slack channel resource id when requesting slack.search_messages",
            },
            "reason": {"type": "string", "description": "User-facing reason for the access request"},
        },
        ["session_id", "agent_id", "tool_id"],
    ),
    _tool(
        "auth.explain_denial",
        "Return the latest safe denial or escalation explanation for a session.",
        {
            **SESSION_ARGS,
            "decision_id": {"type": "string", "description": "Optional policy decision id"},
        },
        ["session_id", "agent_id"],
    ),
    _tool(
        "auth.submit_workflow_feedback",
        "Submit bounded workflow feedback for future recipe/policy tuning.",
        {
            **SESSION_ARGS,
            "decision_id": {"type": "string", "description": "Decision being reviewed"},
            "outcome": {"type": "string", "description": "accepted, rejected, repaired, or noisy"},
            "note": {"type": "string", "description": "Safe non-secret feedback note"},
        },
        ["session_id", "agent_id", "decision_id", "outcome"],
    ),
]

DOWNSTREAM_TOOLS: list[dict[str, Any]] = [
    _tool(
        "linear.create_issue",
        "Create a Linear issue (policy-gated; durable local demo app).",
        {
            **SESSION_ARGS,
            **RESOURCE_ARG,
            "title": {"type": "string", "description": "Issue title"},
            "description": {"type": "string", "description": "Issue body"},
        },
        ["session_id", "agent_id", "resource_id", "title"],
    ),
    _tool(
        "linear.search_issues",
        "Search Linear issues (policy-gated; durable local demo app).",
        {
            **SESSION_ARGS,
            **RESOURCE_ARG,
            "query": {"type": "string", "description": "Search query"},
        },
        ["session_id", "agent_id", "resource_id", "query"],
    ),
    _tool(
        "linear.add_comment",
        "Add a Linear issue comment (policy-gated; durable local demo app).",
        {
            **SESSION_ARGS,
            **RESOURCE_ARG,
            "issue_id": {"type": "string", "description": "Issue id"},
            "body": {"type": "string", "description": "Comment body"},
        },
        ["session_id", "agent_id", "resource_id", "issue_id", "body"],
    ),
    _tool(
        "slack.search_messages",
        "Search Slack channel history (policy-gated; durable local demo app).",
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
        "Post a Slack message (policy-gated; durable local demo app).",
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
