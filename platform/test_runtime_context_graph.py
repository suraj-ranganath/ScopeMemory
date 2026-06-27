from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "pymysql" not in sys.modules:
    pymysql = types.ModuleType("pymysql")
    cursors = types.ModuleType("pymysql.cursors")

    class DictCursor:
        pass

    cursors.DictCursor = DictCursor
    pymysql.cursors = cursors
    sys.modules["pymysql"] = pymysql
    sys.modules["pymysql.cursors"] = cursors

from graph_fallback import InMemoryGraph  # noqa: E402


class RuntimeContextGraphTests(unittest.TestCase):
    def test_schema_declares_durable_context_graph_runtime_tables(self) -> None:
        schema = (ROOT / "dolt" / "schema.sql").read_text()

        for table in (
            "graph_nodes",
            "graph_edges",
            "session_recipe_similarity",
            "session_context_snapshots",
        ):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", schema)

        for column in (
            "prev_event_hash",
            "event_hash",
            "context_snapshot_id",
            "dolt_commit_hash",
            "recipe_hits_json",
            "recipe_index_commit",
            "call_count_remaining",
        ):
            self.assertIn(column, schema)

    def test_in_memory_graph_prefers_reified_similarity_rows(self) -> None:
        graph = InMemoryGraph()
        graph.data = {
            "sessions": [
                {
                    "session_id": "sess_1",
                    "user_id": "user_1",
                    "team_id": "team_sales",
                    "agent_id": "agent_1",
                    "goal_class": "sales_renewal_prep",
                }
            ],
            "agents": [
                {
                    "agent_id": "agent_1",
                    "display_name": "RenewalBot",
                    "identity_ref": "agentic-iam://agent-1",
                    "trust_score": 0.92,
                }
            ],
            "delegations": [
                {"session_id": "sess_1", "user_id": "user_1", "agent_id": "agent_1"}
            ],
            "workflow_recipes": [
                {
                    "recipe_id": "recipe_default",
                    "title": "Default",
                    "team_id": "team_sales",
                    "goal_class": "sales_renewal_prep",
                    "status": "accepted",
                },
                {
                    "recipe_id": "recipe_reified",
                    "title": "Reified",
                    "team_id": "team_sales",
                    "goal_class": "sales_renewal_prep",
                    "status": "accepted",
                },
            ],
            "session_recipe_similarity": [
                {
                    "session_id": "sess_1",
                    "recipe_id": "recipe_reified",
                    "score": 0.94,
                    "rank_order": 1,
                    "reified": 1,
                }
            ],
            "recipe_tools": [
                {"recipe_id": "recipe_reified", "tool_id": "linear.create_issue", "required": 1}
            ],
            "recipe_scopes": [
                {
                    "recipe_id": "recipe_reified",
                    "scope": "linear:issues:create",
                    "approval_mode": "auto_approve",
                }
            ],
            "tool_scopes": [
                {
                    "tool_id": "linear.create_issue",
                    "scope": "linear:issues:create",
                    "access_kind": "write",
                }
            ],
            "resources": [
                {
                    "resource_id": "linear_team:SALES",
                    "team_id": "team_sales",
                    "sensitivity": "normal",
                    "external_flag": 0,
                }
            ],
            "grants": [],
        }

        preflight = graph.preflight("sess_1")
        self.assertEqual(preflight["matched_recipe"]["recipe_id"], "recipe_reified")

        auth = graph.authorize("sess_1", "linear.create_issue", "linear_team:SALES")
        self.assertEqual(auth["facts"]["similarity_score"], 0.94)
        self.assertTrue(auth["facts"]["similarity_reified"])
        self.assertEqual(auth["context_path"][1], "recipe_reified")


if __name__ == "__main__":
    unittest.main()
