# RFC-06: Full MVP Build Plan (Phase 2)

## Status

Deferred until RFC-07 2-hour demo is complete and validated.

**Build RFC-07 first:** [RFC-07: 2-Hour Agentic Identity Demo](RFC-07-2-hour-agentic-identity-demo.md)

## Phase 2 Goal

Extend the RFC-07 SQLite ReBAC demo into the full ScopeMemory control plane:

- Dolt canonical state
- Memgraph derived-graph recipe retrieval
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
| WP-02 | Memgraph recipe retrieval (derived graph) | WP-01 |
| WP-03 | CozoDB policy (RFC-02) | WP-01 |
| WP-04 | 1Password broker (RFC-04) | WP-03 |
| WP-05 | MCP gateway (RFC-03) | WP-03, WP-04 |
| WP-06 | Web UI | WP-05 |
| WP-07 | Learning worker | WP-01, WP-02 |
| WP-08 | Hook adapter | WP-05 |

## Two-Person Implementation Split

### Shared First Step

Before coding much, define the shared JSON contracts and seed demo story. These contracts are the boundary that lets the UI run against fixtures while the gateway and policy path are still under construction:

- `Session`
- `ToolIntent`
- `PolicyDecision`
- `AccessRequest`
- `Grant`
- `CredentialLease`
- `RecipeHit`
- `AuditEvent`

The shared seed story is the Sales Renewal Prep flow from the demo story above: Alice starts the Acme renewal goal, Linear issue creation is auto-approved, Slack customer-channel history escalates to Bob, Bob approves a short Slack read grant, the gateway executes through opaque credential leases where needed, and the prompt-injection Slack result attempts an external Slack post that must be denied.

### Person A: Runtime Enforcement

Person A owns the security-critical execution path:

- MCP gateway: `auth.preflight_goal`, `tools/list`, `tools/call`.
- CozoDB policy engine and typed fact compiler.
- Decision states: `ALLOW`, `AUTO_APPROVE`, `ESCALATE`, `DENY`, `REPAIR`.
- 1Password credential broker and opaque leases.
- Pre-tool-use hook adapter.
- Mock execution wrappers for Linear and Slack calls.
- Proof trace generation.

Core contract:

```text
ToolIntent -> PolicyDecision -> optional CredentialLease -> ExecutionResult -> AuditEvent
```

Person A is the owner for WP-03, WP-04, WP-05, WP-08, and the runtime/proof portions of WP-00.

### Person B: Memory, Demo, And Product Surface

Person B owns the governed memory loop, the visible demo, and all remaining MVP surface area not owned by Person A:

- Dolt schema and seed data.
- Workflow Authorization Recipe model.
- Memgraph recipe indexing and retrieval (derived graph queries, not a separate vector store).
- Mocked Slack data and prompt-injection scenario fixtures.
- Web UI: live session, access requests, proof tree, timeline, recipe review, credential lease inspector, and index refresh status.
- Learning worker that proposes recipe diffs.
- Demo script and fixtures.
- UI state model for `SessionGoal -> RecipeHits -> PredictedScopes -> AccessRequests -> UI State`.
- Fixture catalog for access requests, grants, leases, policy decisions, proof traces, audit events, accepted recipes, proposed recipe diffs, and denial paths.
- End-to-end demo harness that can swap fixture responses for the real gateway as Person A lands runtime pieces.
- Documentation for running the scripted happy path, approval path, denial path, and recipe-learning path.

Core contract:

```text
SessionGoal -> RecipeHits -> PredictedScopes -> AccessRequests -> UI State
```

Person B is the owner for WP-01, WP-02, WP-06, WP-07, the demo/fixture portions of WP-00, and integration/demo polish that is not security-critical runtime enforcement.

### Integration Boundary

- The JSON contracts are versioned fixtures first and API types second.
- Person B can build the UI and demo flow against static fixtures immediately after the contracts land.
- Person A can replace fixture-backed decisions with real gateway, CozoDB, and broker outputs behind the same contracts.
- Every integration handoff should preserve the proof/audit shape, even when a downstream call is still mocked.
- Person A is final owner for "can this agent do this call?"
- Person B is final owner for "why does the system think this access is normal, and how do humans see and review it?"

## Suggested Build Order

1. Together: define shared JSON contracts and lock the seed demo story.
2. Person A: promote RFC-07 ReBAC logic into the gateway fact compiler, CozoDB policy, gateway skeleton, proof trace shape, and 1Password lease shape.
3. Person B: migrate the RFC-07 SQLite subset into Dolt seed data, recipe model, mocked Slack prompt-injection data, and fixture-backed UI.
4. Integrate: `auth.preflight_goal` to recipe hits, predicted scopes, access requests, and visible UI state.
5. Integrate: approved request to grant, optional credential lease, mock Slack/Linear tool execution, and audit event.
6. Person B: wire Memgraph recipe retrieval (Session→Recipe traversals + goal scoring).
7. Polish: denial path, proof tree, Dolt recipe diff, learning proposal, hooks, and scripted demo fixtures.

## Full MVP Acceptance

- All RFC-07 demo scenes still pass through the gateway
- At least one credential lease without agent secret exposure
- Memgraph recipe retrieval tied to Dolt sync commit
- Recipe proposal branch and diff visible in UI
- Prompt-injection deny path for external Slack post

## Implementation Guardrails

Unchanged from original plan — see RFC-04, RFC-02, decisions D-SCM-001 through D-SCM-008.
