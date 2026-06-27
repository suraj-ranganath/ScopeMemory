# ScopeMemory Platform Stack

Architecture (built and runnable):

```text
                    ┌─────────────────────┐
                    │   Agentic-IAM       │
                    │   (identity plane)  │
                    └──────────┬──────────┘
                               │ agent_id, trust_score
                               v
┌──────────────────────────────────────────────────────────────┐
│                  ScopeMemory MCP Gateway                      │
│  preflight → authorize → proof                               │
└───────┬──────────────────────┬───────────────────────────────┘
        │                      │
        v                      v
┌───────────────┐      ┌───────────────────┐
│ Dolt          │      │ Memgraph          │
│ SOURCE OF     │ sync │ DERIVED QUERY     │
│ TRUTH         │─────►│ ENGINE            │
└───────────────┘      └─────────┬─────────┘
                                 │ typed facts
                                 v
                        ┌───────────────────┐
                        │ Policy Engine     │
                        │ ALLOW/DENY/ESCALATE│
                        └───────────────────┘
```

## Quick start

```bash
cd platform

# One-time: allow gateway to connect to Dolt
python3 init_dolt_user.py

# Start stack + run demo
chmod +x run_stack.sh
./run_stack.sh
```

Or manually:

```bash
docker compose --profile gateway-docker up -d --build
python3 run_demo.py
```

Expected output: `STACK DEMO PASSED`

## Components

| Layer | Implementation | Port |
|-------|----------------|------|
| Agentic-IAM | `/iam/agents/{id}` mock | 8080 |
| Gateway | FastAPI `app.py` | 8080 |
| Dolt | `dolthub/dolt-sql-server` | 3306 |
| Memgraph | optional `--profile memgraph` | 7687 |
| Graph fallback | in-process when Memgraph down | — |
| Policy | deterministic rules (`cozo_policy.py`) | in-process |
| Audit | `policy_decisions` in Dolt | 3306 |

## API

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/iam/agents/agent_renewal_01
curl -X POST http://127.0.0.1:8080/auth/preflight \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"sess_demo_001","agent_id":"agent_renewal_01"}'
curl -X POST http://127.0.0.1:8080/auth/authorize \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"sess_demo_001","agent_id":"agent_renewal_01","tool_id":"linear.create_issue","resource_id":"linear_team:SALES"}'
curl http://127.0.0.1:8080/auth/proof/sess_demo_001
```

## Memgraph (optional)

On Docker Desktop Mac, Memgraph may need `vm.max_map_count` in Docker settings.
If Memgraph is unavailable, the gateway uses an **in-memory graph fallback** synced from Dolt (same ReBAC logic).

```bash
docker compose --profile memgraph up -d memgraph
# health should show "graph_backend":"memgraph"
```

## Data flow

1. **Writes** → Dolt only (sessions, recipes, grants, policy_decisions)
2. **Sync** → Dolt rows → Memgraph nodes/edges (or in-memory graph)
3. **Reads** → Memgraph Cypher traversals for context_path
4. **Policy** → facts from graph → ALLOW/DENY/ESCALATE
5. **Audit** → proof JSON stored back in Dolt

## Files

| File | Role |
|------|------|
| `dolt/schema.sql` | Canonical schema |
| `dolt_store.py` | Dolt read/write |
| `memgraph_sync.py` | Dolt → Memgraph sync |
| `memgraph_queries.py` | Cypher ReBAC queries |
| `graph_fallback.py` | In-memory graph when Memgraph down |
| `cozo_policy.py` | Policy decisions |
| `agentic_iam.py` | Identity plane mock |
| `app.py` | Gateway |
| `run_demo.py` | End-to-end acceptance test |

## Phase 2

- Swap policy evaluator to embedded CozoDB Datalog
- Connect live Agentic-IAM API instead of mock
- Enable Memgraph Lab UI for graph visualization
- Add MCP JSON-RPC wrapper around gateway endpoints
