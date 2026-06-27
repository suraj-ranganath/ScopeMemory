"""Memgraph ReBAC traversals for context subgraph and proof paths."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from config import MEMGRAPH_PASSWORD, MEMGRAPH_URI, MEMGRAPH_USER


def _driver():
    auth = (MEMGRAPH_USER, MEMGRAPH_PASSWORD) if MEMGRAPH_USER else None
    return GraphDatabase.driver(MEMGRAPH_URI, auth=auth)


def preflight_context(session_id: str) -> dict[str, Any]:
    query = """
    MATCH (s:Session {id: $sid})
    OPTIONAL MATCH (a:Agent {id: s.agent_id})
    OPTIONAL MATCH (u:User {id: s.user_id})-[:DELEGATES]->(a)
    OPTIONAL MATCH (s)-[:MATCHES]->(r:Recipe)
    OPTIONAL MATCH (r)-[:PREDICTS_TOOL]->(tool:MCPTool)
    OPTIONAL MATCH (r)-[:PREDICTS_SCOPE]->(sc:Scope)
    RETURN s, a, u, r,
           collect(DISTINCT tool.id) AS predicted_tools,
           collect(DISTINCT sc.id) AS predicted_scopes
    """
    driver = _driver()
    with driver.session() as neo:
        rec = neo.run(query, sid=session_id).single()
    driver.close()
    if not rec or not rec["s"]:
        return {"error": "session not found", "session_id": session_id}
    s, a, u, r = rec["s"], rec["a"], rec["u"], rec["r"]
    return {
        "session_id": session_id,
        "agent": dict(a) if a else None,
        "user_id": s["user_id"],
        "goal_class": s["goal_class"],
        "matched_recipe": dict(r) if r else None,
        "predicted_tools": [t for t in rec["predicted_tools"] if t],
        "predicted_scopes": [sc for sc in rec["predicted_scopes"] if sc],
        "delegation_present": u is not None,
    }


def authorize_context(session_id: str, tool_id: str, resource_id: str) -> dict[str, Any]:
    query = """
    MATCH (s:Session {id: $sid})
    MATCH (tool:MCPTool {id: $tool_id})
    MATCH (res:Resource {id: $resource_id})
    MATCH (tool)-[:REQUIRES_SCOPE]->(sc:Scope)
    OPTIONAL MATCH (u:User {id: s.user_id})-[:DELEGATES]->(a:Agent {id: s.agent_id})
    OPTIONAL MATCH (s)-[:MATCHES]->(r:Recipe)
    OPTIONAL MATCH (r)-[:PREDICTS_TOOL]->(tool)
    OPTIONAL MATCH (res)-[:OWNED_BY]->(t:Team)
    OPTIONAL MATCH (r)-[:PREDICTS_SCOPE]->(psc:Scope {id: sc.id})
    OPTIONAL MATCH (s)-[:GRANTED]->(gsc:Scope {id: sc.id})-[:APPLIES_TO]->(res)
    RETURN s, u, a, r, tool, res, t, sc,
           r IS NOT NULL AND EXISTS { (r)-[:PREDICTS_TOOL]->(tool) } AS recipe_predicts_tool,
           psc.approval_mode AS scope_approval_mode,
           gsc IS NOT NULL AS grant_present,
           res.external AS resource_external,
           sc.access_kind AS access_kind,
           res.team_id = s.team_id AS same_team
    """
    driver = _driver()
    with driver.session() as neo:
        rec = neo.run(query, sid=session_id, tool_id=tool_id, resource_id=resource_id).single()
    driver.close()

    if not rec or not rec["s"]:
        return {"error": "session not found"}

    context_path = [
        session_id,
        rec["r"]["id"] if rec["r"] else None,
        tool_id,
        rec["sc"]["id"] if rec["sc"] else None,
        resource_id,
        rec["t"]["id"] if rec["t"] else rec["res"]["team_id"],
        rec["s"]["user_id"],
        rec["s"]["agent_id"],
    ]

    rebac_tuples = []
    if rec["u"] and rec["a"]:
        rebac_tuples.append(
            f"user:{rec['s']['user_id']}#delegates@agent:{rec['s']['agent_id']}"
        )
    if rec["r"]:
        rebac_tuples.append(f"session:{session_id}#matches@recipe:{rec['r']['id']}")
        if rec["recipe_predicts_tool"]:
            rebac_tuples.append(f"recipe:{rec['r']['id']}#predicts_tool@{tool_id}")
    if rec["sc"]:
        rebac_tuples.append(f"tool:{tool_id}#requires_scope@{rec['sc']['id']}")
        rebac_tuples.append(f"scope:{rec['sc']['id']}#applies_to@{resource_id}")

    return {
        "session_id": session_id,
        "tool_id": tool_id,
        "resource_id": resource_id,
        "context_path": [x for x in context_path if x],
        "rebac_tuples": rebac_tuples,
        "facts": {
            "session_id": session_id,
            "tool_id": tool_id,
            "resource_id": resource_id,
            "scope": rec["sc"]["id"] if rec["sc"] else "",
            "user_id": rec["s"]["user_id"],
            "agent_id": rec["s"]["agent_id"],
            "session_team": rec["s"]["team_id"],
            "resource_team": rec["res"]["team_id"],
            "goal_class": rec["s"]["goal_class"],
            "delegation_present": rec["u"] is not None,
            "recipe_predicts_tool": bool(rec["recipe_predicts_tool"]),
            "same_team": bool(rec["same_team"]),
            "grant_present": bool(rec["grant_present"]),
            "resource_external": bool(rec["resource_external"]),
            "resource_sensitivity": rec["res"]["sensitivity"],
            "access_kind": rec["access_kind"],
            "scope_approval_mode": rec["scope_approval_mode"],
            "similarity_score": 1.0 if rec["r"] else 0.0,
            "similarity_reified": True,
        },
    }
