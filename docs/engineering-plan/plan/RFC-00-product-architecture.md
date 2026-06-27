# RFC-00: Product And Architecture

## Status

Plan ready for implementation authorization.

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
  |      - graph traversal over Dolt nodes/edges
  |      - Qdrant similar_to reification
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
  +--> Qdrant
  |      - derived recipe retrieval index
  |      - semantic similar_to candidate edges
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
3. Gateway retrieves accepted recipe candidates from Qdrant.
4. Gateway reifies semantic hits into `session_recipe_similarity` and builds the session context subgraph.
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

### Qdrant

Qdrant is retrieval only. It stores non-secret recipe chunks with metadata payloads and produces candidate `similar_to` edges. Every Qdrant hit used in authorization must be reified in Dolt via `session_recipe_similarity` and tied back to a Dolt commit hash.

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
- Index status and Qdrant hit provenance.

### Security UI

- Policy rule catalog.
- High-risk denials.
- Credential lease history without secrets.
- Recipe proposal review.
- Stale or deprecated recipe index status.

## Non-Goals

- Do not build a generic RAG assistant.
- Do not let Qdrant authorize.
- Do not let LLM judges authorize.
- Do not store decrypted credentials.
- Do not use hooks as the only enforcement point.
- Do not index raw session events for normal authorization recall.
