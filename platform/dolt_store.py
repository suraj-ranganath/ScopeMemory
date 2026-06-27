"""Dolt (MySQL wire) canonical store."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from config import DOLT_DATABASE, DOLT_HOST, DOLT_PASSWORD, DOLT_PORT, DOLT_USER

SCHEMA_PATH = Path(__file__).parent / "dolt" / "schema.sql"


def connect(database: str | None = None):
    db = database if database is not None else DOLT_DATABASE
    conn = pymysql.connect(
        host=DOLT_HOST,
        port=DOLT_PORT,
        user=DOLT_USER,
        password=DOLT_PASSWORD,
        database=db,
        cursorclass=DictCursor,
        autocommit=True,
    )
    if db:
        with conn.cursor() as cur:
            cur.execute(f"USE `{db}`")
    return conn


def ensure_database() -> None:
    conn = connect(database=None)
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DOLT_DATABASE}`")
    conn.close()


def init_schema() -> None:
    ensure_database()
    conn = connect(database=None)
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DOLT_DATABASE}`")
        cur.execute(f"USE `{DOLT_DATABASE}`")
    conn.close()
    conn = connect()
    sql = SCHEMA_PATH.read_text()
    with conn.cursor() as cur:
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)
    conn.close()


def seed_demo() -> None:
    conn = connect()
    cur = conn.cursor()
    tables = [
        "policy_decisions", "grants", "recipe_scopes", "recipe_tools",
        "workflow_recipes", "delegations", "sessions", "resources",
        "tool_scopes", "agents", "user_teams", "teams", "users",
    ]
    for t in tables:
        cur.execute(f"DELETE FROM {t}")

    cur.executemany("INSERT INTO users VALUES (%s, %s)", [("user_alice", "Alice")])
    cur.executemany("INSERT INTO teams VALUES (%s, %s)", [("team_sales", "Sales")])
    cur.execute(
        "INSERT INTO user_teams VALUES (%s, %s, %s)",
        ("user_alice", "team_sales", "member"),
    )
    cur.execute(
        "INSERT INTO agents VALUES (%s, %s, %s, %s, %s)",
        ("agent_renewal_01", "RenewalBot", "agentic-iam://uuid-renewal-bot", 0.92, "active"),
    )
    cur.execute(
        """
        INSERT INTO sessions
        (session_id, user_id, team_id, agent_id, goal, goal_class, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            "sess_demo_001", "user_alice", "team_sales", "agent_renewal_01",
            "Prepare renewal follow-up for Acme. Create a Linear issue.",
            "sales_renewal_prep", "preflighted",
        ),
    )
    cur.execute(
        "INSERT INTO delegations VALUES (%s, %s, %s, NOW())",
        ("sess_demo_001", "user_alice", "agent_renewal_01"),
    )
    cur.execute(
        "INSERT INTO workflow_recipes VALUES (%s, %s, %s, %s, %s)",
        ("recipe_sales_renewal_v3", "Sales Renewal Prep v3", "team_sales", "sales_renewal_prep", "accepted"),
    )
    for tool in ("linear.create_issue", "slack.search_messages"):
        cur.execute("INSERT INTO recipe_tools VALUES (%s, %s, %s)", ("recipe_sales_renewal_v3", tool, 1))
    cur.executemany(
        "INSERT INTO recipe_scopes VALUES (%s, %s, %s)",
        [
            ("recipe_sales_renewal_v3", "linear:issues:create", "auto_approve"),
            ("recipe_sales_renewal_v3", "slack:channels:history", "human_required"),
        ],
    )
    cur.executemany(
        "INSERT INTO resources VALUES (%s, %s, %s, %s)",
        [
            ("linear_team:SALES", "team_sales", "normal", 0),
            ("slack_channel:sales-acme", "team_sales", "restricted", 0),
            ("slack_channel:external-partners", "team_sales", "high", 1),
        ],
    )
    cur.executemany(
        "INSERT INTO tool_scopes VALUES (%s, %s, %s)",
        [
            ("linear.create_issue", "linear:issues:create", "write"),
            ("slack.search_messages", "slack:channels:history", "read"),
            ("slack.post_message", "slack:chat:write", "write"),
        ],
    )
    cur.execute(
        "INSERT INTO grants VALUES (%s, %s, %s, %s)",
        ("grant_linear_001", "sess_demo_001", "linear:issues:create", "linear_team:SALES"),
    )
    conn.close()


def get_session(session_id: str) -> dict[str, Any] | None:
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM sessions WHERE session_id = %s", (session_id,))
        row = cur.fetchone()
    conn.close()
    return row


def get_agent(agent_id: str) -> dict[str, Any] | None:
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM agents WHERE agent_id = %s", (agent_id,))
        row = cur.fetchone()
    conn.close()
    return row


def save_policy_decision(
    session_id: str,
    tool_id: str,
    resource_id: str,
    decision: str,
    proof: dict[str, Any],
) -> str:
    decision_id = f"dec_{uuid.uuid4().hex[:12]}"
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO policy_decisions
            (decision_id, session_id, tool_id, resource_id, decision, proof_json)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (decision_id, session_id, tool_id, resource_id, decision, json.dumps(proof)),
        )
    conn.close()
    return decision_id


def fetch_all_for_sync() -> dict[str, list[dict[str, Any]]]:
    conn = connect()
    data: dict[str, list] = {}
    tables = [
        "users", "teams", "user_teams", "agents", "sessions", "delegations",
        "workflow_recipes", "recipe_tools", "recipe_scopes", "resources",
        "tool_scopes", "grants",
    ]
    with conn.cursor() as cur:
        for t in tables:
            cur.execute(f"SELECT * FROM {t}")
            data[t] = list(cur.fetchall())
        cur.execute(
            """
            INSERT INTO sync_metadata (sync_key, last_sync_at, row_count)
            VALUES ('memgraph', NOW(), %s)
            ON DUPLICATE KEY UPDATE last_sync_at = NOW(), row_count = %s
            """,
            (sum(len(v) for v in data.values()), sum(len(v) for v in data.values())),
        )
    conn.close()
    return data
