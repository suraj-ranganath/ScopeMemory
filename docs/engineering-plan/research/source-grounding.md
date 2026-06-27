# Source Grounding

## EXISTS

- `README.md:1-3` records the name and tagline:
  - `ScopeMemory`
  - `ScopeMemory: Memory-Informed Authorization for MCP Agents`
- `INITIAL_ROUGH_PLAN.md:1-7` states the core framing: memory-informed authorization, not RAG over tribal knowledge.
- `INITIAL_ROUGH_PLAN.md:14-30` lists the intended system pieces:
  - Dolt canonical truth and audit.
  - Qdrant retrieval.
  - Datalog decisions.
  - MCP gateway.
  - LLM judges.
  - Web demo UI.
- `INITIAL_ROUGH_PLAN.md:57-108` introduces the Workflow Authorization Recipe as the learned access pattern.
- `INITIAL_ROUGH_PLAN.md:116-118` states three load-bearing boundaries:
  - Qdrant is not source of truth.
  - LLM judge is not authority.
  - Raw Slack/Linear tokens are not given to agents.
- `INITIAL_ROUGH_PLAN.md:277-380` defines preflight authorization plus inline enforcement.
- `INITIAL_ROUGH_PLAN.md:388-410` defines five decisions: `ALLOW`, `AUTO_APPROVE_EPHEMERAL_GRANT`, `ESCALATE_HUMAN`, `DENY`, `REPAIR`.
- `INITIAL_ROUGH_PLAN.md:436-572` defines the Datalog-shaped policy model and LLM/vector/Datalog/Dolt/gateway responsibility split.
- `INITIAL_ROUGH_PLAN.md:579-726` sketches the Dolt schema.
- `INITIAL_ROUGH_PLAN.md:763-916` sketches Qdrant indexing, refresh, stale deletion, and embedding migration.
- `INITIAL_ROUGH_PLAN.md:916-989` defines access request behavior and auto-approval/human-approval conditions.
- `INITIAL_ROUGH_PLAN.md:993-1029` says the agent should not receive raw OAuth tokens.
- `INITIAL_ROUGH_PLAN.md:1114-1166` defines the gateway as a meta-MCP server with proxied tools.
- `INITIAL_ROUGH_PLAN.md:1166-1284` defines the demo happy path, attack path, and learning path.
- `INITIAL_ROUGH_PLAN.md:1286-1352` sketches a monorepo-ish build stack.
- `INITIAL_ROUGH_PLAN.md:1364-1478` defines five MVP implementation slices.
- `INITIAL_ROUGH_PLAN.md:1798-1833` defines the prompt-injection defense.

## GAP

- No credential provider tables exist in the rough schema.
- No credential lease concept exists in the rough schema.
- No hook semantics exist in the rough runtime.
- No zero-secret-exposure invariants exist in the rough audit model.
- The rough build stack is useful but under-specified for secure credential flow.

## PROPOSAL

Treat the rough plan as a strong product thesis and reorganize it:

- RFC-00 owns product architecture.
- RFC-01 owns domain model and data.
- RFC-02 owns policy and proofs.
- RFC-03 owns MCP runtime.
- RFC-04 owns credential broker, 1Password, hooks, and zero-secret-exposure invariants.
- RFC-05 owns learning, indexing, and audit.
- RFC-06 owns MVP sequencing.
