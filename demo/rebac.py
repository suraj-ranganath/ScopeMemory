"""ReBAC context-path authorization for the 2-hour Agentic Identity demo."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "scopememory.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

TOOL_SCOPES = {
    "linear.create_issue": ("linear:issues:create", "write"),
    "slack.search_messages": ("slack:channels:history", "read"),
    "slack.post_message": ("slack:chat:write", "write"),
}


@dataclass
class Decision:
    decision: str
    session_id: str
    tool_id: str
    resource_id: str
    context_path: list[str] = field(default_factory=list)
    rebac_tuples: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)
    reason: str = ""


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    conn = connect(db_path)
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
    conn.close()


def seed_demo(db_path: Path = DB_PATH) -> None:
    conn = connect(db_path)
    cur = conn.cursor()

    tables = [
        "grants", "recipe_scopes", "recipe_tools", "workflow_recipes",
        "delegations", "sessions", "resources", "tool_scopes",
        "agents", "user_teams", "teams", "users",
    ]
    for t in tables:
        cur.execute(f"DELETE FROM {t}")

    cur.executemany(
        "INSERT INTO users VALUES (?, ?)",
        [("user_alice", "Alice"), ("user_bob", "Bob")],
    )
    cur.executemany(
        "INSERT INTO teams VALUES (?, ?)",
        [("team_sales", "Sales"), ("team_security", "Security")],
    )
    cur.executemany(
        "INSERT INTO user_teams VALUES (?, ?, ?)",
        [("user_alice", "team_sales", "member"), ("user_bob", "team_security", "admin")],
    )
    cur.execute(
        "INSERT INTO agents VALUES (?, ?, ?, ?, ?)",
        ("agent_renewal_01", "RenewalBot", "agentic-iam://uuid-renewal-bot", 0.92, "active"),
    )
    cur.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "sess_demo_001",
            "user_alice",
            "team_sales",
            "agent_renewal_01",
            "Prepare renewal follow-up for Acme. Create a Linear issue for next steps.",
            "sales_renewal_prep",
            "preflighted",
        ),
    )
    cur.execute(
        "INSERT INTO delegations VALUES (?, ?, ?, datetime('now'))",
        ("sess_demo_001", "user_alice", "agent_renewal_01"),
    )
    cur.execute(
        "INSERT INTO workflow_recipes VALUES (?, ?, ?, ?, ?)",
        (
            "recipe_sales_renewal_v3",
            "Sales Renewal Prep v3",
            "team_sales",
            "sales_renewal_prep",
            "accepted",
        ),
    )
    for tool in ("linear.create_issue", "slack.search_messages"):
        cur.execute(
            "INSERT INTO recipe_tools VALUES (?, ?, ?)",
            ("recipe_sales_renewal_v3", tool, 1),
        )
    cur.executemany(
        "INSERT INTO recipe_scopes VALUES (?, ?, ?)",
        [
            ("recipe_sales_renewal_v3", "linear:issues:create", "auto_approve"),
            ("recipe_sales_renewal_v3", "slack:channels:history", "human_required"),
        ],
    )
    cur.executemany(
        "INSERT INTO resources VALUES (?, ?, ?, ?)",
        [
            ("linear_team:SALES", "team_sales", "normal", 0),
            ("slack_channel:sales-acme", "team_sales", "restricted", 0),
            ("slack_channel:external-partners", "team_sales", "high", 1),
        ],
    )
    cur.executemany(
        "INSERT INTO tool_scopes VALUES (?, ?, ?)",
        [
            ("linear.create_issue", "linear:issues:create", "write"),
            ("slack.search_messages", "slack:channels:history", "read"),
            ("slack.post_message", "slack:chat:write", "write"),
        ],
    )
    cur.execute(
        "INSERT INTO grants VALUES (?, ?, ?, ?, ?)",
        ("grant_linear_001", "sess_demo_001", "linear:issues:create", "linear_team:SALES", None),
    )

    conn.commit()
    conn.close()


def preflight(session_id: str, db_path: Path = DB_PATH) -> dict[str, Any]:
    conn = connect(db_path)
    cur = conn.cursor()

    session = cur.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
    if not session:
        conn.close()
        raise ValueError(f"unknown session: {session_id}")

    agent = cur.execute("SELECT * FROM agents WHERE agent_id = ?", (session["agent_id"],)).fetchone()
    delegation = cur.execute(
        "SELECT * FROM delegations WHERE session_id = ?", (session_id,)
    ).fetchone()
    recipe = cur.execute(
        """
        SELECT * FROM workflow_recipes
        WHERE goal_class = ? AND team_id = ? AND status = 'accepted'
        LIMIT 1
        """,
        (session["goal_class"], session["team_id"]),
    ).fetchone()

    tools = []
    scopes = []
    if recipe:
        tools = [
            r["tool_id"]
            for r in cur.execute(
                "SELECT tool_id FROM recipe_tools WHERE recipe_id = ?", (recipe["recipe_id"],)
            ).fetchall()
        ]
        scopes = [
            r["scope"]
            for r in cur.execute(
                "SELECT scope FROM recipe_scopes WHERE recipe_id = ?", (recipe["recipe_id"],)
            ).fetchall()
        ]

    conn.close()

    return {
        "session_id": session_id,
        "agent": dict(agent) if agent else None,
        "delegation": dict(delegation) if delegation else None,
        "goal_class": session["goal_class"],
        "matched_recipe": dict(recipe) if recipe else None,
        "predicted_tools": tools,
        "predicted_scopes": scopes,
        "rebac_tuples": _preflight_tuples(session, agent, delegation, recipe),
    }


def _preflight_tuples(session, agent, delegation, recipe) -> list[str]:
    tuples = [
        f"user:{session['user_id']}#member@team:{session['team_id']}",
        f"agent:{session['agent_id']}#executes@session:{session['session_id']}",
    ]
    if agent:
        tuples.append(f"agent:{agent['agent_id']}#identity@{agent['identity_ref']}")
    if delegation:
        tuples.append(
            f"user:{delegation['user_id']}#delegates@agent:{delegation['agent_id']}@session:{session['session_id']}"
        )
    if recipe:
        tuples.append(f"session:{session['session_id']}#matches@recipe:{recipe['recipe_id']}")
    return tuples


def authorize(
    session_id: str,
    tool_id: str,
    resource_id: str,
    db_path: Path = DB_PATH,
) -> Decision:
    conn = connect(db_path)
    cur = conn.cursor()

    session = cur.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
    if not session:
        conn.close()
        return Decision("DENY", session_id, tool_id, resource_id, reason="unknown session")

    delegation = cur.execute(
        "SELECT 1 FROM delegations WHERE session_id = ? AND user_id = ? AND agent_id = ?",
        (session_id, session["user_id"], session["agent_id"]),
    ).fetchone()
    if not delegation:
        conn.close()
        return Decision(
            "DENY", session_id, tool_id, resource_id,
            reason="no delegation: agent not authorized to act for user on this session",
            facts=["missing_delegation"],
        )

    recipe = cur.execute(
        """
        SELECT * FROM workflow_recipes
        WHERE goal_class = ? AND team_id = ? AND status = 'accepted'
        LIMIT 1
        """,
        (session["goal_class"], session["team_id"]),
    ).fetchone()

    resource = cur.execute(
        "SELECT * FROM resources WHERE resource_id = ?", (resource_id,)
    ).fetchone()
    if not resource:
        conn.close()
        return Decision("DENY", session_id, tool_id, resource_id, reason="unknown resource")

    tool_row = cur.execute(
        "SELECT * FROM tool_scopes WHERE tool_id = ?", (tool_id,)
    ).fetchone()
    if not tool_row:
        conn.close()
        return Decision("DENY", session_id, tool_id, resource_id, reason="unknown tool")

    scope = tool_row["scope"]
    access_kind = tool_row["access_kind"]

    predicts_tool = cur.execute(
        "SELECT 1 FROM recipe_tools WHERE recipe_id = ? AND tool_id = ?",
        (recipe["recipe_id"], tool_id),
    ).fetchone() if recipe else None

    scope_mode = cur.execute(
        "SELECT approval_mode FROM recipe_scopes WHERE recipe_id = ? AND scope = ?",
        (recipe["recipe_id"], scope),
    ).fetchone() if recipe else None

    grant = cur.execute(
        """
        SELECT 1 FROM grants
        WHERE session_id = ? AND scope = ? AND resource_id = ?
        """,
        (session_id, scope, resource_id),
    ).fetchone()

    path = [
        session_id,
        recipe["recipe_id"] if recipe else "none",
        tool_id,
        scope,
        resource_id,
        resource["team_id"],
        session["user_id"],
        session["agent_id"],
    ]

    tuples = [
        f"session:{session_id}#matches@recipe:{recipe['recipe_id']}" if recipe else "",
        f"recipe:{recipe['recipe_id']}#predicts_tool@{tool_id}" if predicts_tool else "",
        f"tool:{tool_id}#needs@{scope}",
        f"scope:{scope}#applies_to@{resource_id}",
        f"resource:{resource_id}#owned_by@team:{resource['team_id']}",
        f"user:{session['user_id']}#delegates@agent:{session['agent_id']}@session:{session_id}",
    ]
    tuples = [t for t in tuples if t]

    facts = [
        f"session_team({session_id}, {session['team_id']})",
        f"recipe_predicts_tool({predicts_tool is not None})",
        f"resource_external({bool(resource['external'])})",
        f"grant_present({grant is not None})",
    ]

    conn.close()

    if resource["team_id"] != session["team_id"]:
        return Decision(
            "DENY", session_id, tool_id, resource_id,
            context_path=path, rebac_tuples=tuples, facts=facts,
            reason="resource not owned by session team",
        )

    if not predicts_tool:
        return Decision(
            "DENY", session_id, tool_id, resource_id,
            context_path=path, rebac_tuples=tuples, facts=facts,
            reason="recipe did not predict this tool",
        )

    if resource["external"] and access_kind == "write":
        return Decision(
            "DENY", session_id, tool_id, resource_id,
            context_path=path, rebac_tuples=tuples, facts=facts,
            reason="external write not predicted by recipe and not granted",
        )

    if grant:
        return Decision(
            "ALLOW", session_id, tool_id, resource_id,
            context_path=path, rebac_tuples=tuples, facts=facts,
            reason="grant exists for scope@resource",
        )

    if scope_mode and scope_mode["approval_mode"] == "human_required":
        return Decision(
            "ESCALATE_HUMAN", session_id, tool_id, resource_id,
            context_path=path, rebac_tuples=tuples, facts=facts,
            reason="scope requires human approval",
        )

    if scope_mode and scope_mode["approval_mode"] == "auto_approve":
        return Decision(
            "ALLOW", session_id, tool_id, resource_id,
            context_path=path, rebac_tuples=tuples, facts=facts,
            reason="recipe auto-approves scope for team resource",
        )

    return Decision(
        "DENY", session_id, tool_id, resource_id,
        context_path=path, rebac_tuples=tuples, facts=facts,
        reason="no grant and scope not auto-approved",
    )
