"""Sync Dolt canonical rows → Memgraph derived graph."""

from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from config import MEMGRAPH_PASSWORD, MEMGRAPH_URI, MEMGRAPH_USER
from dolt_store import fetch_all_for_sync


def _driver():
    auth = (MEMGRAPH_USER, MEMGRAPH_PASSWORD) if MEMGRAPH_USER else None
    return GraphDatabase.driver(MEMGRAPH_URI, auth=auth)


def clear_graph(session) -> None:
    session.run("MATCH (n) DETACH DELETE n")


def sync_to_memgraph() -> int:
    data = fetch_all_for_sync()
    driver = _driver()
    with driver.session() as session:
        clear_graph(session)
        for row in data["users"]:
            session.run("MERGE (u:User {id: $id}) SET u.display_name = $name", id=row["user_id"], name=row["display_name"])
        for row in data["teams"]:
            session.run("MERGE (t:Team {id: $id}) SET t.name = $name", id=row["team_id"], name=row["name"])
        for row in data["user_teams"]:
            session.run(
                """
                MATCH (u:User {id: $uid}), (t:Team {id: $tid})
                MERGE (u)-[r:MEMBER_OF]->(t) SET r.role = $role
                """,
                uid=row["user_id"], tid=row["team_id"], role=row["role"],
            )
        for row in data["agents"]:
            session.run(
                """
                MERGE (a:Agent {id: $id})
                SET a.display_name = $name, a.identity_ref = $ref,
                    a.trust_score = $trust, a.status = $status
                """,
                id=row["agent_id"], name=row["display_name"], ref=row["identity_ref"],
                trust=row["trust_score"], status=row["status"],
            )
        for row in data["sessions"]:
            session.run(
                """
                MERGE (s:Session {id: $id})
                SET s.user_id = $uid, s.team_id = $tid, s.agent_id = $aid,
                    s.goal = $goal, s.goal_class = $gc, s.status = $status
                """,
                id=row["session_id"], uid=row["user_id"], tid=row["team_id"],
                aid=row["agent_id"], goal=row["goal"], gc=row["goal_class"], status=row["status"],
            )
            session.run(
                """
                MATCH (u:User {id: $uid}), (a:Agent {id: $aid}), (s:Session {id: $sid})
                MERGE (u)-[:RUNS]->(s)
                MERGE (a)-[:EXECUTES]->(s)
                """,
                uid=row["user_id"], aid=row["agent_id"], sid=row["session_id"],
            )
        for row in data["delegations"]:
            session.run(
                """
                MATCH (u:User {id: $uid}), (a:Agent {id: $aid}), (s:Session {id: $sid})
                MERGE (u)-[d:DELEGATES {session_id: $sid}]->(a)
                SET d.delegated_at = timestamp()
                MERGE (u)-[:DELEGATED_FOR {session_id: $sid}]->(s)
                MERGE (a)-[:ACTS_FOR {session_id: $sid}]->(s)
                """,
                uid=row["user_id"], aid=row["agent_id"], sid=row["session_id"],
            )
        for row in data["workflow_recipes"]:
            session.run(
                """
                MERGE (r:Recipe {id: $id})
                SET r.title = $title, r.team_id = $tid, r.goal_class = $gc, r.status = $status
                """,
                id=row["recipe_id"], title=row["title"], tid=row["team_id"],
                gc=row["goal_class"], status=row["status"],
            )
            session.run(
                "MATCH (t:Team {id: $tid}), (r:Recipe {id: $rid}) MERGE (t)-[:OWNS]->(r)",
                tid=row["team_id"], rid=row["recipe_id"],
            )
        for row in data["sessions"]:
            session.run(
                """
                MATCH (s:Session {id: $sid}), (r:Recipe {goal_class: $gc, team_id: $tid, status: 'accepted'})
                MERGE (s)-[m:MATCHES {source: 'dolt_goal_match'}]->(r)
                SET m.score = 0.89, m.reified = true
                """,
                sid=row["session_id"], gc=row["goal_class"], tid=row["team_id"],
            )
        for row in data.get("session_recipe_similarity", []):
            session.run(
                """
                MATCH (s:Session {id: $sid}), (r:Recipe {id: $rid})
                MERGE (s)-[m:MATCHES {source: 'session_recipe_similarity'}]->(r)
                SET m.score = $score,
                    m.rank_order = $rank_order,
                    m.reified = $reified,
                    m.dolt_commit_hash = $dolt_commit_hash,
                    m.qdrant_index_commit = $qdrant_index_commit
                """,
                sid=row["session_id"],
                rid=row["recipe_id"],
                score=float(row["score"]),
                rank_order=int(row["rank_order"]),
                reified=bool(row["reified"]),
                dolt_commit_hash=row["dolt_commit_hash"],
                qdrant_index_commit=row["qdrant_index_commit"],
            )
        for row in data["recipe_tools"]:
            session.run(
                """
                MERGE (tool:MCPTool {id: $tid})
                WITH tool
                MATCH (r:Recipe {id: $rid})
                MERGE (r)-[:PREDICTS_TOOL {required: $req}]->(tool)
                """,
                tid=row["tool_id"], rid=row["recipe_id"], req=bool(row["required"]),
            )
        for row in data["recipe_scopes"]:
            session.run(
                """
                MERGE (sc:Scope {id: $scope})
                SET sc.approval_mode = $mode
                WITH sc
                MATCH (r:Recipe {id: $rid})
                MERGE (r)-[:PREDICTS_SCOPE {approval_mode: $mode}]->(sc)
                """,
                scope=row["scope"], mode=row["approval_mode"], rid=row["recipe_id"],
            )
        for row in data["tool_scopes"]:
            session.run(
                """
                MERGE (tool:MCPTool {id: $tid})
                MERGE (sc:Scope {id: $scope})
                SET sc.access_kind = $kind
                MERGE (tool)-[:REQUIRES_SCOPE]->(sc)
                """,
                tid=row["tool_id"], scope=row["scope"], kind=row["access_kind"],
            )
        for row in data["resources"]:
            session.run(
                """
                MERGE (res:Resource {id: $id})
                SET res.team_id = $tid, res.sensitivity = $sens, res.external = $ext
                WITH res
                MATCH (t:Team {id: $tid})
                MERGE (res)-[:OWNED_BY]->(t)
                """,
                id=row["resource_id"], tid=row["team_id"],
                sens=row["sensitivity"], ext=bool(row["external_flag"]),
            )
        for row in data["grants"]:
            session.run(
                """
                MATCH (s:Session {id: $sid})
                MERGE (sc:Scope {id: $scope})
                MERGE (res:Resource {id: $rid})
                MERGE (s)-[:GRANTED {grant_id: $gid}]->(sc)
                MERGE (sc)-[:APPLIES_TO]->(res)
                """,
                sid=row["session_id"], scope=row["scope"], rid=row["resource_id"], gid=row["grant_id"],
            )
    driver.close()
    return sum(len(v) for v in data.values())
