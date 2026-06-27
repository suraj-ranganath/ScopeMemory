# ScopeMemory Decisions

<!-- Prefix: SCM - new decisions: D-SCM-NNN. Allocation rule: next ID = max existing + 1. -->

### D-SCM-001 - 2026-06-27 - Frame ScopeMemory As Authorization Memory
**Decision:** ScopeMemory is an authorization memory layer for MCP agents, not a generic organizational-memory retrieval product. The central primitive is the Workflow Authorization Recipe: a governed record of the tools, scopes, resources, credential bindings, approval modes, and evidence normally needed for a class of agent work.
**Reason:** The rough plan's strongest claim is that an agent should not begin with broad credentials. It should predict narrow task-specific access, preflight missing scopes, auto-approve safe predictable grants, escalate uncertainty, enforce every call, and audit with proof.
**Affected:** RFC-00, RFC-01, RFC-02, RFC-05.
**Status:** active

### D-SCM-002 - 2026-06-27 - Dolt Is Canonical, Qdrant Is Derived
**Decision:** Dolt owns canonical authorization state: recipes, policies, tool mappings, grants, approvals, credential reference metadata, and audit event hashes. Qdrant is a derived retrieval index over accepted recipes and non-secret recipe chunks.
**Reason:** Authorization state needs branch, diff, review, merge, and historical audit semantics. Vector retrieval needs fast semantic recall with payload filters, but it must not become the source of truth.
**Affected:** RFC-01, RFC-05.
**Status:** active

### D-SCM-003 - 2026-06-27 - LLMs Emit Candidate Facts, Not Decisions
**Decision:** LLM judges may classify goals, summarize evidence, propose recipes, and emit typed candidate facts with confidence. They do not approve access and they do not override policy. Deterministic policy decides `ALLOW`, `AUTO_APPROVE_EPHEMERAL_GRANT`, `ESCALATE_HUMAN`, `DENY`, or `REPAIR`.
**Reason:** This is the core security story. Memory and LLMs help discover likely access; policy remains the authority.
**Affected:** RFC-02, RFC-05.
**Status:** active

### D-SCM-004 - 2026-06-27 - Credentials Are Brokered Through Opaque Leases
**Decision:** Password-manager credentials, including 1Password secrets, are never materialized into agent-visible tool input, model context, Dolt rows, Qdrant payloads, UI, or audit logs. ScopeMemory stores secret references and credential metadata; execution uses opaque short-lived credential leases resolved only inside the broker or gateway execution boundary.
**Reason:** The user explicitly requested password-manager integration through pre-tool-use hooks and zero-knowledge treatment. Injecting decrypted secrets directly through a hook would violate that requirement because hook inputs and rewritten tool inputs can become model-visible or logged.
**Affected:** RFC-01, RFC-02, RFC-03, RFC-04, RFC-05.
**Status:** active

### D-SCM-005 - 2026-06-27 - Pre-Tool-Use Hooks Are A Client-Side Enforcement Adapter
**Decision:** Pre-tool-use hooks are not the primary authorization system. They are an adapter for agent clients that can intercept tool calls before execution. The canonical enforcement point remains the ScopeMemory MCP gateway and credential broker.
**Reason:** Hooks vary by host client and cannot solve every transport. Stdio MCP servers need launch-time credential injection. HTTP/API tools can be proxied by the gateway. Shell commands can be wrapped. The plan must not depend on one client hook system for correctness.
**Affected:** RFC-03, RFC-04.
**Status:** active

### D-SCM-008 - 2026-06-27 - Authorization Memory Is A Context Graph
**Decision:** ScopeMemory models authorization memory as a Memory Data Context Graph. Dolt stores canonical graph nodes, edges, session recipe similarity reifications, and session context snapshots. Qdrant produces candidate semantic `similar_to` edges only; hits used in decisions must be reified in Dolt before policy evaluation. The gateway materializes a session context subgraph on every preflight and tool call, projects it to Datalog facts, and requires a valid `context_path` for allow/auto-approve decisions when a snapshot exists.
**Reason:** Recipes, scopes, grants, and sessions are relational. A flat recipe blob cannot explain why access was predicted or prove memory-consistency. The context graph makes traversals explicit, auditable, and renderable in the proof UI.
**Affected:** RFC-00, RFC-01, RFC-02, RFC-03, RFC-05.
**Status:** active

### D-SCM-006 - 2026-06-27 - MVP Proves The Full Loop With Narrow Surfaces
**Decision:** The first build proves one end-to-end lifecycle: preflight, access request, credential lease, gateway enforcement, audit proof, prompt-injection denial, recipe proposal, Dolt diff, and Qdrant refresh. It uses two downstream services: Linear and Slack or Slack-mock.
**Reason:** Building every integration, every secret provider, and a formal proof engine would obscure the product thesis. The MVP must show the whole control loop with a small number of surfaces.
**Affected:** RFC-06.
**Status:** superseded by D-SCM-009 for first build; reactivated for Phase 2

### D-SCM-007 - 2026-06-27 - Owner Locks MVP Planning Choices
**Decision:** The owner approved the v1 zero-knowledge definition as "zero secret exposure to agents and ScopeMemory persistence"; selected real 1Password for the MVP credential provider; selected mocked Slack for the demo attack/customer-context path; selected CozoDB as the initial policy engine; and accepted the local SR-style planning pass without a live pooled arbiter run.
**Reason:** These choices remove the remaining owner gates from the planning package and make the implementation path crisp: build the real credential-broker path, keep Slack safe and deterministic, make the policy layer concretely Datalog-like with CozoDB, and proceed without waiting on Squire pool reconciliation.
**Affected:** README, STATUS, drive, open-questions, RFC-02, RFC-04, RFC-06, judges, ground-truth-ledger.
**Status:** active — Phase 2 only; RFC-07 demo defers 1Password and CozoDB

### D-SCM-009 - 2026-06-27 - Demo First With RFC-07 Two-Hour Scope
**Decision:** The first implementation is RFC-07 only: SQLite + Python ReBAC demo proving Agentic Identity delegation, recipe memory, context_path proofs, ALLOW/DENY/ESCALATE. Full RFC-06 MVP (Dolt, Qdrant, CozoDB, 1Password, MCP gateway, UI) is Phase 2 and must not block the demo.
**Reason:** Prior plan overshot feasible demo time. RFC-07 delivers a correct, runnable Agentic Identity story in 2 hours.
**Affected:** RFC-00, RFC-01, RFC-02, RFC-06, RFC-07, STATUS, README, demo/.
**Status:** active
