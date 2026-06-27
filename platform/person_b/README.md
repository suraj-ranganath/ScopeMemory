# Person B — Memory, Demo, Product Surface (RFC-06)

Person B owns WP-01 (seed), WP-02 (Memgraph recipe retrieval), WP-06 (Web UI), WP-07 (learning worker), and demo fixtures.

## Layout

```
person_b/
  contracts/     # Shared JSON contract examples
  fixtures/      # Static fixtures for UI + harness
  memgraph_recipe_index.py
  learning_worker.py
  ui_state.py
  slack_fixtures.py
web/             # Demo UI (served at /)
```

## Core flow

```text
SessionGoal → RecipeHits (Memgraph) → PredictedScopes → AccessRequests → UI State
```

Recipe retrieval uses the **same derived graph** as ReBAC policy — Dolt syncs to Memgraph, then Cypher traversals rank recipes:

- `Session-[:MATCHES]->Recipe` for session-bound hits
- `Team-[:OWNS]->Recipe` + goal_class / goal-text scoring for search

## Run

```bash
cd platform
docker compose --profile gateway-docker up -d --build
python3 run_person_b_demo.py all
```

Open the UI at http://127.0.0.1:8080/

## Demo paths

| Path | What it shows |
|------|----------------|
| `happy` | Preflight recipe hits (Memgraph) + Linear ALLOW |
| `approval` | Slack ESCALATE → Bob approves grant |
| `denial` | Prompt-injection fixture + external Slack DENY |
| `learning` | Graph sync index + recipe v4 proposal |

## API (Person B)

| Endpoint | Purpose |
|----------|---------|
| `GET /demo/ui-state/{session_id}` | Full UI state |
| `POST /demo/access-requests/{id}/approve` | Bob approval |
| `GET /demo/slack/search?channel=...` | Mock Slack + injection |
| `POST /index/recipes` | Dolt → Memgraph sync + index metadata |
| `POST /demo/recipes/propose` | Learning worker |

Preflight includes `recipe_hits` from Memgraph (or in-memory graph fallback when Memgraph is unavailable).
