"""In-process graph fallback when Memgraph is unavailable (e.g. Docker Desktop Mac)."""

from __future__ import annotations

from typing import Any

from dolt_store import fetch_all_for_sync
from grant_lifecycle import grant_row_is_active


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
        recipes_by_id = {r["recipe_id"]: r for r in self.data.get("workflow_recipes", [])}
        similarity_rows = sorted(
            [
                r for r in self.data.get("session_recipe_similarity", [])
                if r["session_id"] == session_id and bool(r.get("reified", True))
            ],
            key=lambda r: (int(r.get("rank_order", 99)), -float(r.get("score", 0))),
        )
        recipe = None
        if similarity_rows:
            recipe = recipes_by_id.get(similarity_rows[0]["recipe_id"])
        if not recipe:
            recipes = [
                r for r in self.data.get("workflow_recipes", [])
                if r["goal_class"] == s["goal_class"] and r["team_id"] == s["team_id"]
            ]
            recipe = recipes[0] if recipes else None
        tools, scopes = [], []
        if recipe:
            tools = [r["tool_id"] for r in self.data.get("recipe_tools", []) if r["recipe_id"] == recipe["recipe_id"]]
            scopes = [r["scope"] for r in self.data.get("recipe_scopes", []) if r["recipe_id"] == recipe["recipe_id"]]
        agent = agents.get(s["agent_id"])
        delegation = delegations.get(session_id)
        from agentic_identity.tuples import preflight_tuples
        rebac_tuples = preflight_tuples(s, agent, delegation, recipe)
        return {
            "session_id": session_id,
            "agent": agent,
            "user_id": s["user_id"],
            "goal_class": s["goal_class"],
            "matched_recipe": recipe,
            "predicted_tools": tools,
            "predicted_scopes": scopes,
            "delegation_present": delegation is not None,
            "delegation": delegation,
            "identity_ref": agent.get("identity_ref") if agent else None,
            "agent_trust_score": agent.get("trust_score") if agent else None,
            "rebac_tuples": rebac_tuples,
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
            if (
                g["session_id"] == session_id
                and g["scope"] == ts["scope"]
                and g["resource_id"] == resource_id
                and grant_row_is_active(g)
            )
        )
        agents = {r["agent_id"]: r for r in self.data.get("agents", [])}
        agent = agents.get(s["agent_id"])
        similarity = next(
            (
                r for r in self.data.get("session_recipe_similarity", [])
                if recipe and r["session_id"] == session_id and r["recipe_id"] == recipe["recipe_id"]
            ),
            None,
        )
        facts = {
            "session_id": session_id,
            "tool_id": tool_id,
            "resource_id": resource_id,
            "scope": ts["scope"],
            "user_id": s["user_id"],
            "agent_id": s["agent_id"],
            "session_team": s["team_id"],
            "resource_team": res["team_id"],
            "goal_class": s["goal_class"],
            "delegation_present": pf.get("delegation_present", False),
            "recipe_predicts_tool": predicts,
            "same_team": res["team_id"] == s["team_id"],
            "grant_present": grant_present,
            "resource_external": bool(res["external_flag"]),
            "resource_sensitivity": res["sensitivity"],
            "access_kind": ts["access_kind"],
            "scope_approval_mode": scope_mode,
            "agent_trust_score": agent.get("trust_score") if agent else None,
            "similarity_score": float(similarity["score"]) if similarity else (1.0 if recipe else 0.0),
            "similarity_reified": bool(similarity.get("reified", True)) if similarity else True,
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
            "rebac_tuples": [
                t for t in [
                    f"session:{session_id}#matches@recipe:{recipe['recipe_id']}" if recipe else "",
                    f"recipe:{recipe['recipe_id']}#predicts_tool@{tool_id}" if predicts and recipe else "",
                    f"tool:{tool_id}#requires_scope@{ts['scope']}",
                    f"scope:{ts['scope']}#applies_to@{resource_id}",
                    f"resource:{resource_id}#owned_by@team:{res['team_id']}",
                    f"user:{s['user_id']}#delegates@agent:{s['agent_id']}@session:{session_id}" if pf.get("delegation_present", False) else "",
                ]
                if t
            ],
            "facts": facts,
        }

    def search_recipes(
        self, team_id: str, goal_class: str, goal_text: str, limit: int = 3,
    ) -> list[dict[str, Any]]:
        hits = []
        for recipe in self.data.get("workflow_recipes", []):
            if recipe["team_id"] != team_id or recipe["status"] != "accepted":
                continue
            score = 0.0
            if recipe["goal_class"] == goal_class:
                score += 0.6
            gt = goal_text.lower()
            if recipe["goal_class"].lower() in gt:
                score += 0.2
            if recipe["title"].lower() in gt:
                score += 0.2
            if score <= 0:
                continue
            tools = [
                r["tool_id"] for r in self.data.get("recipe_tools", [])
                if r["recipe_id"] == recipe["recipe_id"]
            ]
            scopes = [
                r["scope"] for r in self.data.get("recipe_scopes", [])
                if r["recipe_id"] == recipe["recipe_id"]
            ]
            hits.append({
                "recipe_id": recipe["recipe_id"],
                "title": recipe["title"],
                "goal_class": recipe["goal_class"],
                "score": round(score, 3),
                "dolt_commit": "main",
                "predicted_tools": tools,
                "predicted_scopes": scopes,
            })
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits[:limit]


_graph: InMemoryGraph | None = None


def get_inmemory() -> InMemoryGraph:
    global _graph
    if _graph is None:
        _graph = InMemoryGraph()
    return _graph
