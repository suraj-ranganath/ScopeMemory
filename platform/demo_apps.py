"""Local demo app adapters rendered by the hackathon web UI.

These adapters intentionally behave like real downstream apps from the
ScopeMemory gateway's point of view: tool calls mutate/read durable Dolt rows,
and the React `/linear` and `/slack` pages render those rows.
"""

from __future__ import annotations

import uuid
from typing import Any

from dolt_store import connect


def create_linear_issue(
    *,
    session_id: str,
    agent_id: str,
    team_id: str,
    title: str,
    description: str,
    policy_decision_id: str,
    credential_lease_id: str = "",
) -> dict[str, Any]:
    issue_id = f"LIN-{uuid.uuid4().hex[:8]}"
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO demo_linear_issues
            (issue_id, team_id, title, description, state, priority, source_session_id,
             created_by_agent_id, policy_decision_id, credential_lease_id)
            VALUES (%s, %s, %s, %s, 'open', 'medium', %s, %s, %s, %s)
            """,
            (
                issue_id,
                team_id,
                title,
                description,
                session_id,
                agent_id,
                policy_decision_id,
                credential_lease_id or None,
            ),
        )
        cur.execute("SELECT * FROM demo_linear_issues WHERE issue_id = %s", (issue_id,))
        row = cur.fetchone()
    conn.close()
    return {
        **row,
        "status": "created",
        "mode": "demo_mcp",
        "app_path": f"/linear/issues/{issue_id}",
    }


def search_linear_issues(*, team_id: str, query: str) -> dict[str, Any]:
    needle = f"%{query.lower()}%"
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM demo_linear_issues
            WHERE team_id = %s
              AND (LOWER(title) LIKE %s OR LOWER(description) LIKE %s)
            ORDER BY created_at DESC, issue_id DESC
            """,
            (team_id, needle, needle),
        )
        issues = list(cur.fetchall())
    conn.close()
    return {"team": team_id, "query": query, "issues": issues, "status": "searched", "mode": "demo_mcp"}


def add_linear_comment(
    *,
    session_id: str,
    agent_id: str,
    issue_id: str,
    body: str,
    policy_decision_id: str,
) -> dict[str, Any]:
    comment_id = f"comment_{uuid.uuid4().hex[:10]}"
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO demo_linear_comments
            (comment_id, issue_id, body, source_session_id, created_by_agent_id, policy_decision_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (comment_id, issue_id, body, session_id, agent_id, policy_decision_id),
        )
        cur.execute("SELECT * FROM demo_linear_comments WHERE comment_id = %s", (comment_id,))
        row = cur.fetchone()
    conn.close()
    return {**row, "status": "commented", "mode": "demo_mcp", "app_path": f"/linear/issues/{issue_id}"}


def search_slack_messages(*, channel_id: str) -> dict[str, Any]:
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT *
            FROM demo_slack_messages
            WHERE channel_id = %s
            ORDER BY created_at ASC, message_id ASC
            """,
            (channel_id,),
        )
        messages = list(cur.fetchall())
    conn.close()
    return {
        "channel": channel_id,
        "messages": messages,
        "untrusted_context_present": any(bool(message.get("is_untrusted")) for message in messages),
        "status": "searched",
        "mode": "demo_mcp",
        "app_path": f"/slack/channels/{channel_id}",
    }


def post_slack_message(
    *,
    session_id: str,
    channel_id: str,
    user_id: str,
    user_name: str,
    text: str,
    policy_decision_id: str,
) -> dict[str, Any]:
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO demo_slack_messages
            (message_id, channel_id, user_id, user_name, text, source_session_id,
             policy_decision_id, message_kind, is_untrusted)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'message', 0)
            """,
            (message_id, channel_id, user_id, user_name, text, session_id, policy_decision_id),
        )
        cur.execute("SELECT * FROM demo_slack_messages WHERE message_id = %s", (message_id,))
        row = cur.fetchone()
    conn.close()
    return {**row, "status": "posted", "mode": "demo_mcp", "app_path": f"/slack/channels/{channel_id}"}
