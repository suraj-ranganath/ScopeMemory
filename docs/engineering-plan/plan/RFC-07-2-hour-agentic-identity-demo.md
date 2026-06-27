# RFC-07: 2-Hour Agentic Identity Demo (Binding First Build)

## Status

**This RFC is the binding scope for the first implementation.** Build this before RFC-06 full MVP.

## Goal

Prove the Agentic Identity story in one terminal demo:

> **Agentic-IAM knows who the agent is. ScopeMemory decides what the agent may do — via a ReBAC context path, not a broad role.**

## Non-Goals For This Build

Do not build in the 2-hour window:

- Docker, Dolt, Qdrant, CozoDB
- 1Password / credential broker
- MCP gateway / JSON-RPC server
- Web UI (terminal JSON output is enough)
- LLM judges, recipe learning, Dolt diff
- Full RFC-01 schema (24 tables)

Those remain in RFC-00 through RFC-06 as **Phase 2**.

## Demo Story (2 minutes to present)

**Actors**

- Alice (`user_alice`) — sales human
- RenewalBot (`agent_renewal_01`) — registered agent (Agentic-IAM identity)
- ScopeMemory demo — ReBAC checker over SQLite

**Goal**

```text
Prepare renewal follow-up for Acme. Create a Linear issue for next steps.
```

**Scene 1 — Identity + delegation**

```text
Agent RenewalBot is registered (agent_id, trust_score).
Alice delegates RenewalBot for session sess_demo_001.
```

**Scene 2 — Preflight (memory predicts access)**

```text
Goal class: sales_renewal_prep
Matched recipe: recipe_sales_renewal_v3
Predicted tools: linear.create_issue, slack.search_messages
Context path printed as ReBAC tuple chain
```

**Scene 3 — ALLOW**

```text
Tool: linear.create_issue on resource linear_team:SALES
Decision: ALLOW
Proof: session → recipe → tool → scope → resource → team ← user ← delegates ← agent
```

**Scene 4 — DENY (Agentic Identity value vs RBAC)**

```text
Tool: slack.post_message on resource slack_channel:external-partners
Decision: DENY
Reason: recipe did not predict tool; external resource; no grant
RBAC would have allowed "sales_agent" to post — ReBAC did not
```

## Time Budget (120 minutes)

| Minutes | Task | Deliverable |
|---------|------|-------------|
| 0–15 | Clone, `pip install`, init DB | `demo/scopememory.db` |
| 15–35 | Schema + seed | `demo/schema.sql`, seed runs |
| 35–70 | ReBAC path builder + policy | `demo/rebac.py` |
| 70–95 | CLI demo script | `demo/run_demo.py` |
| 95–110 | Dry-run + fix | All 4 scenes pass |
| 110–120 | README polish | One-command demo |

## Stack

```text
Python 3.12
SQLite (stdlib sqlite3)
No external services
Optional: FastAPI only if time remains (CLI is sufficient)
```

## Data Model (8 tables)

Binding subset of RFC-01. Implemented in `demo/schema.sql`.

| Table | Purpose |
|-------|---------|
| `users` | Human identities |
| `teams` | Org boundary |
| `user_teams` | `member_of` |
| `agents` | Agentic-IAM agent registry mirror |
| `delegations` | `user#delegates@agent@session` |
| `sessions` | Bounded agent run + goal |
| `workflow_recipes` | Learned access pattern |
| `recipe_tools` | `recipe#predicts_tool@tool` |
| `recipe_scopes` | `recipe#predicts_scope@scope` |
| `resources` | `resource#owned_by@team` |
| `grants` | Ephemeral `session#grant@scope@resource` |

Recipe matching in v0: **exact `goal_class` string match** (no Qdrant).

## ReBAC Edges (demo subset)

| Edge | Storage |
|------|---------|
| `member_of` | `user_teams` |
| `delegates` | `delegations` |
| `executes` | `sessions.agent_id` |
| `has_goal` | `sessions.goal_class` |
| `matches` | `sessions.goal_class = recipes.goal_class` |
| `predicts_tool` | `recipe_tools` |
| `predicts_scope` | `recipe_scopes` + tool→scope map in code |
| `owned_by` | `resources.team_id` |
| `granted` | `grants` |

## Policy (3 rules only)

```text
1. DENY if no delegation for (user, agent, session)
2. DENY if recipe does not predict tool OR resource not owned by session team
3. DENY if external resource and tool is write/post
4. ALLOW if grant exists OR (recipe predicts tool + scope + low-risk write)
5. ESCALATE if recipe predicts but no grant and scope approval_mode = human_required
```

Decision states for demo: `ALLOW`, `DENY`, `ESCALATE_HUMAN`.

## API Surface (CLI commands)

```bash
python demo/run_demo.py init          # schema + seed
python demo/run_demo.py preflight     # scene 2
python demo/run_demo.py authorize ... # scenes 3–4
python demo/run_demo.py all           # full demo script
```

## Acceptance Checklist

All must pass in under 2 hours of implementation time:

- [ ] `python demo/run_demo.py all` exits 0
- [ ] Agent record exists with `identity_ref` (Agentic-IAM link field)
- [ ] Delegation tuple shown in preflight output
- [ ] ALLOW for `linear.create_issue` includes `context_path` array (≥5 hops)
- [ ] DENY for external Slack post includes reason + failed edge
- [ ] No Docker, no secrets, no network required
- [ ] README documents Phase 2 deferrals explicitly

## Phase 2 Promotion Path

When extending beyond 2 hours, promote in this order:

1. Replace SQLite recipe match → Qdrant semantic match (RFC-05)
2. Replace inline policy → CozoDB (RFC-02)
3. Add MCP gateway wrapper (RFC-03)
4. Swap SQLite → Dolt (RFC-01 full schema)
5. Add credential broker (RFC-04)
6. Add web UI (RFC-06 screens)

## Integration With Agentic-IAM

For the demo, `agents.identity_ref` is an opaque string pointing at Agentic-IAM's agent UUID. No live API call required — document the field as the integration seam.

```json
{
  "agent_id": "agent_renewal_01",
  "identity_ref": "agentic-iam://uuid-renewal-bot",
  "trust_score": 0.92,
  "status": "active"
}
```

Live Agentic-IAM integration is Phase 2: call `POST /api/v1/authz/authorize` only after ScopeMemory ReBAC path succeeds.
