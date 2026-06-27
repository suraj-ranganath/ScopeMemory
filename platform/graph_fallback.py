"""In-process graph fallback when Memgraph is unavailable (e.g. Docker Desktop Mac)."""

from __future__ import annotations

from typing import Any

from dolt_store import fetch_all_for_sync


class InMemoryGraph:
    def __init__(self) -> None:
        self.data: dict[str, list[dict[str, Any]]] = {}

    def reload(self) -> int:
        self.data = fetch_all_for_sync()
        return sum(len(v) for v in self.data.values())

    def preflight(self, session_id: str) -> dict[str, Any]:
        sessions = {r["session_id"]: r for r in self.data.get("sessions", [])}
        s = sessions.get(session_id)
        if not s:
            return {"error": "session not found", "session_id": session_id}
        agents = {r["agent_id"]: r for r in self.data.get("agents", [])}
        delegations = {r["session_id"]: r for r in self.data.get("delegations", [])}
        recipes = [r for r in self.data.get("workflow_recipes", []) if r["goal_class"] == s["goal_class"] and r["team_id"] == s["team_id"]]
        recipe = recipes[0] if recipes else None
        tools, scopes = [], []
        if recipe:
            tools = [r["tool_id"] for r in self.data.get("recipe_tools", []) if r["recipe_id"] == recipe["recipe_id"]]
            scopes = [r["scope"] for r in self.data.get("recipe_scopes", []) if r["recipe_id"] == recipe["recipe_id"]]
        return {
            "session_id": session_id,
            "agent": agents.get(s["agent_id"]),
            "user_id": s["user_id"],
            "goal_class": s["goal_class"],
            "matched_recipe": recipe,
            "predicted_tools": tools,
            "predicted_scopes": scopes,
            "delegation_present": session_id in delegations,
        }

    def authorize(self, session_id: str, tool_id: str, resource_id: str) -> dict[str, Any]:
        pf = self.preflight(session_id)
        if "error" in pf:
            return pf
        sessions = {r["session_id"]: r for r in self.data.get("sessions", [])}
        s = sessions[session_id]
        resources = {r["resource_id"]: r for r in self.data.get("resources", [])}
        res = resources.get(resource_id)
        if not res:
            return {"error": "resource not found"}
        tool_scopes = {r["tool_id"]: r for r in self.data.get("tool_scopes", [])}
        ts = tool_scopes.get(tool_id)
        if not ts:
            return {"error": "tool not found"}
        recipe = pf.get("matched_recipe")
        predicts = tool_id in pf.get("predicted_tools", [])
        scope_mode = None
        if recipe:
            for rs in self.data.get("recipe_scopes", []):
                if rs["recipe_id"] == recipe["recipe_id"] and rs["scope"] == ts["scope"]:
                    scope_mode = rs["approval_mode"]
        grant_present = any(
            g for g in self.data.get("grants", [])
            if g["session_id"] == session_id and g["scope"] == ts["scope"] and g["resource_id"] == resource_id
        )
        facts = {
            "delegation_present": pf.get("delegation_present", False),
            "recipe_predicts_tool": predicts,
            "same_team": res["team_id"] == s["team_id"],
            "grant_present": grant_present,
            "resource_external": bool(res["external_flag"]),
            "access_kind": ts["access_kind"],
            "scope_approval_mode": scope_mode,
        }
        context_path = [
            session_id,
            recipe["recipe_id"] if recipe else None,
            tool_id,
            ts["scope"],
            resource_id,
            res["team_id"],
            s["user_id"],
            s["agent_id"],
        ]
        return {
            "session_id": session_id,
            "tool_id": tool_id,
            "resource_id": resource_id,
            "context_path": [x for x in context_path if x],
            "rebac_tuples": [],
            "facts": facts,
        }


_graph: InMemoryGraph | None = None


def get_inmemory() -> InMemoryGraph:
    global _graph
    if _graph is None:
        _graph = InMemoryGraph()
    return _graph
