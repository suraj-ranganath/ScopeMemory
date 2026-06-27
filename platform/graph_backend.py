"""Graph backend selector — Memgraph primary, in-memory fallback."""

from __future__ import annotations

import os
from typing import Any

USE_FALLBACK = os.getenv("GRAPH_FALLBACK", "auto")  # auto | memgraph | inmemory

_backend: str | None = None


def _probe_memgraph() -> bool:
    try:
        from neo4j import GraphDatabase
        from config import MEMGRAPH_PASSWORD, MEMGRAPH_URI, MEMGRAPH_USER
        auth = (MEMGRAPH_USER, MEMGRAPH_PASSWORD) if MEMGRAPH_USER else None
        driver = GraphDatabase.driver(MEMGRAPH_URI, auth=auth)
        with driver.session() as s:
            s.run("RETURN 1")
        driver.close()
        return True
    except Exception:
        return False


def backend_name() -> str:
    global _backend
    if _backend:
        return _backend
    if USE_FALLBACK == "inmemory":
        _backend = "inmemory"
    elif USE_FALLBACK == "memgraph":
        _backend = "memgraph"
    else:
        _backend = "memgraph" if _probe_memgraph() else "inmemory"
    return _backend


def sync_graph() -> tuple[int, str]:
    name = backend_name()
    if name == "memgraph":
        from memgraph_sync import sync_to_memgraph
        return sync_to_memgraph(), name
    from graph_fallback import get_inmemory
    return get_inmemory().reload(), name


def preflight_context(session_id: str) -> dict[str, Any]:
    if backend_name() == "memgraph":
        from memgraph_queries import preflight_context as mg
        return mg(session_id)
    from graph_fallback import get_inmemory
    return get_inmemory().preflight(session_id)


def authorize_context(session_id: str, tool_id: str, resource_id: str) -> dict[str, Any]:
    if backend_name() == "memgraph":
        from memgraph_queries import authorize_context as mg
        return mg(session_id, tool_id, resource_id)
    from graph_fallback import get_inmemory
    return get_inmemory().authorize(session_id, tool_id, resource_id)


def search_recipe_hits(
    team_id: str,
    goal_class: str,
    goal_text: str,
    session_id: str | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if backend_name() == "memgraph":
        from memgraph_queries import search_recipe_hits as mg_search, session_recipe_hits
        if session_id:
            hits = session_recipe_hits(session_id)
            if hits:
                return hits
        return mg_search(team_id, goal_class, goal_text, limit)
    from graph_fallback import get_inmemory
    return get_inmemory().search_recipes(team_id, goal_class, goal_text, limit)
