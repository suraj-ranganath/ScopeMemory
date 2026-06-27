"""Person B: Memgraph recipe indexer (WP-02) — derived graph queries, not a separate vector store."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from dolt_store import connect
from graph_backend import search_recipe_hits, sync_graph


def _content_hash(recipe: dict[str, Any], tools: list[str], scopes: list[str]) -> str:
    blob = json.dumps({"recipe": recipe, "tools": tools, "scopes": scopes}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def index_accepted_recipes(dolt_commit: str = "main") -> dict[str, Any]:
    """Sync Dolt → Memgraph, then record index metadata in Dolt."""
    rows, engine = sync_graph()
    conn = connect()
    indexed = []
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM workflow_recipes WHERE status = 'accepted'")
        recipes = cur.fetchall()
        for recipe in recipes:
            cur.execute("SELECT tool_id FROM recipe_tools WHERE recipe_id = %s", (recipe["recipe_id"],))
            tools = [r["tool_id"] for r in cur.fetchall()]
            cur.execute("SELECT scope FROM recipe_scopes WHERE recipe_id = %s", (recipe["recipe_id"],))
            scopes = [r["scope"] for r in cur.fetchall()]
            ch = _content_hash(recipe, tools, scopes)
            graph_node_id = f"Recipe:{recipe['recipe_id']}"
            cur.execute(
                """
                INSERT INTO recipe_index_meta (recipe_id, graph_node_id, dolt_commit_hash, content_hash)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE graph_node_id=%s, dolt_commit_hash=%s, content_hash=%s, indexed_at=NOW()
                """,
                (
                    recipe["recipe_id"], graph_node_id, dolt_commit, ch,
                    graph_node_id, dolt_commit, ch,
                ),
            )
            indexed.append(recipe["recipe_id"])
    conn.close()
    return {
        "indexed": indexed,
        "graph_engine": engine,
        "synced_rows": rows,
        "dolt_commit": dolt_commit,
    }


def search_recipes(
    goal_text: str,
    team_id: str,
    goal_class: str | None = None,
    session_id: str | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    return search_recipe_hits(
        team_id=team_id,
        goal_class=goal_class or "",
        goal_text=goal_text,
        session_id=session_id,
        limit=limit,
    )
