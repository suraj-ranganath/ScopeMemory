# RFC-00: Product And Architecture

## Status

**First build:** RFC-07 (2-hour Agentic Identity demo).  
**This document:** target architecture for Phase 2 full MVP.

## Demo Scope (RFC-07 — build this first)

For the 2-hour Agentic Identity demo, implement only:

```text
Agentic-IAM identity mirror (agents.identity_ref)
  → user delegates agent for session
  → recipe matches goal_class
  → ReBAC context_path check
  → ALLOW | DENY | ESCALATE_HUMAN + proof JSON
```

Implementation: `demo/` directory, SQLite, Python CLI. No MCP gateway, no Dolt, no Memgraph.

See [RFC-07](RFC-07-2-hour-agentic-identity-demo.md).

## Product Claim

ScopeMemory gives MCP agents just-in-time, task-scoped authorization based on governed memory of successful workflows. It answers this question:

```text
Given this user, team, goal, available MCP tools, historical recipes, and current grants,
what tools, scopes, resources, credentials, and approvals should this agent be allowed to use?
```

The agent does not inherit all of a human's access. It starts with a signed goal and a narrow tool catalog. ScopeMemory expands access only when policy, memory, credential availability, and human approval allow it.

## Architecture

```text
Agent host
  - Claude Code, Codex, custom agent, or MCP-compatible runtime
  - optional PreToolUse-style hook adapter
  |
  v
ScopeMemory MCP Gateway
  - auth.preflight_goal
  - proxied Slack/Linear/GitHub tools
  - auth.request_scope
  - auth.show_decision_proof
  - auth.submit_workflow_feedback
  |
  +--> Context Graph Compiler
  |      - session context subgraph materialization
  |      - graph traversal over Dolt-derived Memgraph nodes/edges
  |      - recipe hit reification
  |      - snapshot persistence
  |
  +--> Policy Engine
  |      - typed facts from graph snapshots
  |      - deterministic decisions
  |      - proof trace with context_path
  |
  +--> Dolt
  |      - canonical recipes
  |      - tool/scope maps
  |      - graph_nodes, graph_edges, session_context_snapshots
  |      - credential refs and bindings
  |      - grants and access requests
  |      - policy decisions and audit hashes
  |
  +--> Memgraph
  |      - derived graph and recipe retrieval view
  |      - session-to-recipe matches and ReBAC traversals
  |      - accepted recipes only for normal authorization recall
  |
  +--> Credential Broker
  |      - 1Password/provider adapters
  |      - opaque credential leases
  |      - process/header/env injection only inside execution boundary
  |
  +--> LLM Judges
         - goal classification
         - access request fact emission
         - recipe proposals
         - audit summaries
         - never final authority
```

## Runtime Loop

### Preflight

1. User or agent host calls `auth.preflight_goal`.
2. Gateway creates a session with immutable goal text, user, team, agent, and available tool context.
3. Gateway retrieves accepted recipe candidates from the Dolt/Memgraph-derived graph.
4. Gateway reifies recipe hits into session recipe metadata and builds the session context subgraph.
5. Gateway filters candidates by team, status, valid time window, available tools, and resource visibility.
6. Gateway expands subgraph traversals: recipe → tools → scopes → resources → credential bindings.
7. Gateway persists `session_context_snapshots` for the preflight phase.
8. Gateway projects subgraph to typed policy facts.
9. Policy decides which missing grants can be auto-approved, escalated, denied, or repaired.
10. Gateway returns a narrowed tool catalog and access request state.

### Inline Enforcement

1. Agent calls a tool.
2. Gateway validates the tool input schema.
3. Gateway normalizes the intent: tool, resource, write/read kind, destination, data sensitivity, and credential class.
4. Gateway updates the session context subgraph for the tool call phase.
5. Gateway compiles typed facts including graph edges and context paths.
6. Policy returns a decision and proof trace.
7. If execution needs a secret, the credential broker issues or uses an opaque lease.
8. Gateway executes the downstream call or blocks.
9. Gateway appends hash-chained audit events, new graph edges, and returns redacted output.

## Decision States

- `ALLOW`: the tool call is valid and already authorized.
- `AUTO_APPROVE_EPHEMERAL_GRANT`: a short-lived grant can be issued because recipe, team policy, resource, risk, and credential binding are safe.
- `ESCALATE_HUMAN`: the request may be legitimate but needs human review.
- `DENY`: hard policy rejects the request.
- `REPAIR`: the call is structurally invalid and should be corrected by the agent.

## Control Plane Responsibilities

### Dolt

Dolt is canonical. It stores governed state, the Memory Data Context Graph node/edge layer, session context snapshots, and the audit trail. Any change that affects future authorization must be reviewable as a data diff.

### Memgraph

Memgraph is a derived graph/retrieval layer only. It materializes non-secret recipe, session, tool, scope, resource, and grant relationships from Dolt so the gateway can retrieve accepted recipes and traverse context paths. Every recipe hit used in authorization must be tied back to Dolt state and a recipe index/sync commit.

### Policy Engine

Policy decides. It consumes facts from session context subgraphs, graph traversals, schemas, tool mappings, recipe retrieval, grants, resource metadata, human approvals, and credential broker state. It emits a decision plus a traceable proof including `context_path`.

### Credential Broker

The broker resolves secret references into execution-time credentials without exposing decrypted values to the agent or ScopeMemory persistence.

### LLM Judges

LLMs perceive, classify, summarize, and propose. They can emit facts such as `goal_consistent=true` or `recipe_candidate=...`. They do not approve access.

## Product Surfaces

### Agent Tools

- `auth.preflight_goal`
- `auth.request_scope`
- `auth.explain_denial`
- `auth.show_decision_proof`
- Proxied downstream tools such as `linear.create_issue` and `slack.search_messages`

### Human UI

- Live session view.
- Memory context graph panel with highlighted authorization paths.
- Predicted tools and scopes.
- Access request queue.
- Approval form with proof, context path, and redacted arguments.
- Tool-call timeline.
- Recipe review with Dolt diff.
- Graph/index status and recipe hit provenance.

### Security UI

- Policy rule catalog.
- High-risk denials.
- Credential lease history without secrets.
- Recipe proposal review.
- Stale or deprecated recipe index status.

## Non-Goals

- Do not build a generic RAG assistant.
- Do not let the retrieval layer authorize.
- Do not let LLM judges authorize.
- Do not store decrypted credentials.
- Do not use hooks as the only enforcement point.
- Do not index raw session events for normal authorization recall.
