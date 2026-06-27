"""Memgraph ReBAC traversals and recipe retrieval over the derived graph."""

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
    OPTIONAL MATCH (u:User {id: s.user_id})-[del:DELEGATES {session_id: s.id}]->(a:Agent {id: s.agent_id})
    OPTIONAL MATCH (u)-[:MEMBER_OF]->(t:Team {id: s.team_id})
    OPTIONAL MATCH (s)-[:MATCHES]->(r:Recipe)
    OPTIONAL MATCH (r)-[:PREDICTS_TOOL]->(tool:MCPTool)
    OPTIONAL MATCH (r)-[:PREDICTS_SCOPE]->(sc:Scope)
    RETURN s, a, u, t, r, del,
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
    agent_dict = dict(a) if a else None
    recipe_dict = dict(r) if r else None
    session_dict = {
        "session_id": s["id"],
        "user_id": s["user_id"],
        "team_id": s["team_id"],
        "agent_id": s["agent_id"],
        "goal_class": s["goal_class"],
    }
    delegation = None
    if u is not None and rec.get("del"):
        delegation = {
            "session_id": session_id,
            "user_id": s["user_id"],
            "agent_id": s["agent_id"],
        }

    from agentic_identity.tuples import preflight_tuples
    rebac_tuples = preflight_tuples(session_dict, agent_dict, delegation, recipe_dict)

    return {
        "session_id": session_id,
        "agent": agent_dict,
        "user_id": s["user_id"],
        "goal_class": s["goal_class"],
        "matched_recipe": recipe_dict,
        "predicted_tools": [t for t in rec["predicted_tools"] if t],
        "predicted_scopes": [sc for sc in rec["predicted_scopes"] if sc],
        "delegation_present": delegation is not None,
        "delegation": delegation,
        "agent_trust_score": agent_dict.get("trust_score") if agent_dict else None,
        "identity_ref": agent_dict.get("identity_ref") if agent_dict else None,
        "rebac_tuples": rebac_tuples,
    }


def authorize_context(session_id: str, tool_id: str, resource_id: str) -> dict[str, Any]:
    query = """
    MATCH (s:Session {id: $sid})
    MATCH (tool:MCPTool {id: $tool_id})
    MATCH (res:Resource {id: $resource_id})
    MATCH (tool)-[:REQUIRES_SCOPE]->(sc:Scope)
    OPTIONAL MATCH (u:User {id: s.user_id})-[del:DELEGATES {session_id: s.id}]->(a:Agent {id: s.agent_id})
    OPTIONAL MATCH (s)-[:MATCHES]->(r:Recipe)
    OPTIONAL MATCH (r)-[:PREDICTS_TOOL]->(pt:MCPTool {id: $tool_id})
    OPTIONAL MATCH (res)-[:OWNED_BY]->(t:Team)
    OPTIONAL MATCH (r)-[:PREDICTS_SCOPE]->(psc:Scope {id: sc.id})
    OPTIONAL MATCH (s)-[:GRANTED]->(gsc:Scope {id: sc.id})-[:APPLIES_TO]->(res)
    RETURN s, u, a, r, tool, res, t, sc,
           pt IS NOT NULL AS recipe_predicts_tool,
           psc.approval_mode AS scope_approval_mode,
           gsc IS NOT NULL AS grant_present,
           res.external AS resource_external,
           sc.access_kind AS access_kind,
           res.team_id = s.team_id AS same_team,
           a.trust_score AS agent_trust_score
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
            "agent_trust_score": rec["agent_trust_score"],
            "similarity_score": 1.0 if rec["r"] else 0.0,
            "similarity_reified": True,
        },
    }


def search_recipe_hits(
    team_id: str,
    goal_class: str,
    goal_text: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Rank accepted team recipes by goal_class match and goal-text overlap."""
    query = """
    MATCH (t:Team {id: $team_id})-[:OWNS]->(r:Recipe {status: 'accepted'})
    OPTIONAL MATCH (r)-[:PREDICTS_TOOL]->(tool:MCPTool)
    OPTIONAL MATCH (r)-[:PREDICTS_SCOPE]->(sc:Scope)
    WITH r,
         collect(DISTINCT tool.id) AS tools,
         collect(DISTINCT sc.id) AS scopes,
         $goal_class AS gc,
         toLower($goal_text) AS gt
    WITH r, tools, scopes,
         (CASE WHEN r.goal_class = gc THEN 0.6 ELSE 0.0 END +
          CASE WHEN gt CONTAINS toLower(r.goal_class) THEN 0.2 ELSE 0.0 END +
          CASE WHEN gt CONTAINS toLower(r.title) THEN 0.2 ELSE 0.0 END) AS score
    WHERE score > 0
    RETURN r.id AS recipe_id,
           r.title AS title,
           r.goal_class AS goal_class,
           score,
           tools,
           scopes
    ORDER BY score DESC
    LIMIT $limit
    """
    driver = _driver()
    with driver.session() as session:
        rows = session.run(
            query,
            team_id=team_id,
            goal_class=goal_class,
            goal_text=goal_text,
            limit=limit,
        )
        hits = [
            {
                "recipe_id": rec["recipe_id"],
                "title": rec["title"],
                "goal_class": rec["goal_class"],
                "score": round(float(rec["score"]), 3),
                "dolt_commit": "main",
                "predicted_tools": [t for t in rec["tools"] if t],
                "predicted_scopes": [s for s in rec["scopes"] if s],
            }
            for rec in rows
        ]
    driver.close()
    return hits


def session_recipe_hits(session_id: str) -> list[dict[str, Any]]:
    """Recipe hits via Session-[:MATCHES]->Recipe graph edge."""
    query = """
    MATCH (s:Session {id: $sid})-[:MATCHES]->(r:Recipe)
    OPTIONAL MATCH (r)-[:PREDICTS_TOOL]->(tool:MCPTool)
    OPTIONAL MATCH (r)-[:PREDICTS_SCOPE]->(sc:Scope)
    RETURN r.id AS recipe_id,
           r.title AS title,
           r.goal_class AS goal_class,
           collect(DISTINCT tool.id) AS tools,
           collect(DISTINCT sc.id) AS scopes
    """
    driver = _driver()
    with driver.session() as session:
        rows = list(session.run(query, sid=session_id))
    driver.close()
    return [
        {
            "recipe_id": rec["recipe_id"],
            "title": rec["title"],
            "goal_class": rec["goal_class"],
            "score": 0.89,
            "dolt_commit": "main",
            "predicted_tools": [t for t in rec["tools"] if t],
            "predicted_scopes": [s for s in rec["scopes"] if s],
        }
        for rec in rows
    ]
