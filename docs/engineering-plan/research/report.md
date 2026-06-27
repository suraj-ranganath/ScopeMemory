# ScopeMemory Research Report

## TL;DR

ScopeMemory should be designed as an authorization control plane that learns from successful agent workflows. The system predicts the narrow access an agent will likely need, creates or requests short-lived grants, enforces every actual MCP tool call, and records a proof-backed audit trail. The rough plan is directionally strong: Dolt is canonical state, retrieval is derived and non-authoritative, deterministic policy makes decisions, and the MCP gateway is the runtime boundary. The current MVP uses Memgraph-derived graph/recipe retrieval rather than a separate vector store.

The main addition is credential handling. Password manager integration must not be a side path. It must be part of the authorization model:

- A recipe predicts tools, scopes, resources, approval mode, and credential binding.
- Policy decides whether a credential lease can be issued.
- The credential broker resolves 1Password or other provider references only inside the execution boundary.
- Pre-tool-use hooks enforce or route calls before execution, but they never paste decrypted secrets into model-visible tool input.
- Audit stores references, hashes, lease IDs, and provider metadata, not secret values.

## Method

Research was read-only. Sources checked:

- Local repo README and rough plan.
- SR Code planning pipeline, routing, orchestration, judge, synthesis, and quality-bar instructions.
- pqprime exemplar package shape.
- Current public docs for MCP tools and authorization, Claude Code hooks, and 1Password developer/CLI secret reference behavior.

## EXISTS

- The repo exists and names the project ScopeMemory. `README.md:1-3`.
- The rough plan states the core thesis: memory-informed authorization for agents, with preflight scope prediction and Datalog-audited tool calls. `INITIAL_ROUGH_PLAN.md:1-7`.
- The rough plan already separates canonical state, retrieval, deterministic policy, runtime gateway, LLM judges, and UI. `INITIAL_ROUGH_PLAN.md:14-30`.
- The rough plan already says raw Slack/Linear tokens should not be given to the agent. `INITIAL_ROUGH_PLAN.md:116-118`, `INITIAL_ROUGH_PLAN.md:993-1029`.
- The rough plan already includes prompt-injection handling by treating tool outputs as untrusted observations. `INITIAL_ROUGH_PLAN.md:1798-1833`.
- MCP tools expose structured tool metadata and calls; the gateway can sit exactly at that boundary.
- Claude Code's `PreToolUse` hook family can inspect and control tool calls before execution, making it a viable client-side adapter.
- 1Password supports secret references and developer flows that keep secret values out of repo files.

## GAP

- The rough plan says "gateway-held token vault" but does not specify a zero-secret-exposure model.
- The rough plan does not model credential references, credential bindings, credential leases, or hook-mediated execution.
- The rough plan does not distinguish HTTP proxy credentials, stdio MCP launch-time credentials, and shell command credentials.
- The rough plan's Datalog examples do not yet include credential-provider facts or password-manager authorization facts.
- The rough plan has a build schedule but not a split engineering spec that an implementation team can follow.

## PROPOSAL

Build ScopeMemory around six subsystems:

1. Product and architecture: gateway, policy, memory, credential broker, UI.
2. Domain model and data: Dolt canonical tables and Memgraph-derived graph/retrieval indexes.
3. Authorization policy and proofs: deterministic decisions over typed facts.
4. MCP gateway runtime: tools/list, tools/call, preflight, dynamic catalog, downstream execution.
5. Zero-knowledge credential broker and hooks: 1Password/password-manager integration through opaque leases.
6. Learning, indexing, and audit: recipe proposal, review, indexing, tamper-evident events.

## Open Questions

See `open-questions.md`.

## Recommended Next Phase

Owner review. If approved, implementation should begin with RFC-06's MVP sequence and create Beads issues for each build slice.
