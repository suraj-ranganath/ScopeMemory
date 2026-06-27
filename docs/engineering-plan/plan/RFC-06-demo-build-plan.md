# RFC-06: Full MVP Build Plan (Phase 2)

## Status

Deferred until RFC-07 2-hour demo is complete and validated.

**Build RFC-07 first:** [RFC-07: 2-Hour Agentic Identity Demo](RFC-07-2-hour-agentic-identity-demo.md)

## Phase 2 Goal

Extend the RFC-07 SQLite ReBAC demo into the full ScopeMemory control plane:

- Dolt canonical state
- Qdrant semantic recipe retrieval
- CozoDB policy engine
- MCP gateway
- 1Password credential broker
- Web approval UI
- Recipe learning worker

## Demo Story (full MVP)

Same narrative as RFC-07, plus credential leases, MCP tool proxy, and recipe proposal on a Dolt branch.

## Work Packages (Phase 2 only)

| WP | Deliverable | Depends on |
|----|-------------|------------|
| WP-01 | Dolt schema (RFC-01 full) + seed | RFC-07 validated |
| WP-02 | Qdrant indexer | WP-01 |
| WP-03 | CozoDB policy (RFC-02) | WP-01 |
| WP-04 | 1Password broker (RFC-04) | WP-03 |
| WP-05 | MCP gateway (RFC-03) | WP-03, WP-04 |
| WP-06 | Web UI | WP-05 |
| WP-07 | Learning worker | WP-01, WP-02 |
| WP-08 | Hook adapter | WP-05 |

## Suggested Build Order

1. Promote RFC-07 ReBAC logic into gateway fact compiler
2. WP-01 Dolt schema (migrate from SQLite subset)
3. WP-03 policy engine
4. WP-05 gateway with mocked Slack/Linear
5. WP-06 minimal web UI
6. WP-02 Qdrant (replace goal_class exact match)
7. WP-04 credential broker
8. WP-07 learning worker
9. WP-08 hooks

## Full MVP Acceptance

- All RFC-07 demo scenes still pass through the gateway
- At least one credential lease without agent secret exposure
- Qdrant retrieval tied to Dolt commit
- Recipe proposal branch and diff visible in UI
- Prompt-injection deny path for external Slack post

## Implementation Guardrails

Unchanged from original plan — see RFC-04, RFC-02, decisions D-SCM-001 through D-SCM-008.
