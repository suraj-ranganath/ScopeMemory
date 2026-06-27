# ScopeMemory 2-Hour Agentic Identity Demo

Binding implementation for [RFC-07](../docs/engineering-plan/plan/RFC-07-2-hour-agentic-identity-demo.md).

## Run (one command)

```bash
cd demo
python run_demo.py all
```

Requires Python 3.12+ and no pip dependencies.

## What it proves

1. **Agentic Identity** — agent has `identity_ref` pointing at Agentic-IAM registry
2. **Delegation** — user delegates agent for a bounded session
3. **ReBAC** — access decided by relationship path, not a broad role
4. **Memory** — recipe predicts tools/scopes for the goal class
5. **Proof** — every decision prints `context_path` and ReBAC tuples

## Scenes

| Scene | Result |
|-------|--------|
| Preflight | Matches `recipe_sales_renewal_v3` |
| `linear.create_issue` @ `linear_team:SALES` | **ALLOW** |
| `slack.post_message` @ external channel | **DENY** |
| `slack.search_messages` @ customer channel | **ESCALATE_HUMAN** |

## Phase 2

See RFC-06 for full MVP (Dolt, Memgraph, MCP gateway, 1Password, UI).
