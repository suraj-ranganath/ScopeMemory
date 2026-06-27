# ScopeMemory Engineering Plan

**Status:** plan ready for implementation authorization.
**Scope:** planning only. No implementation has started.
**Tracked by:** Beads issue `ScopeMemory-9sk`.
**Primary source:** `INITIAL_ROUGH_PLAN.md`.
**Judge status:** local judges approve; cross-check `consistent`; adversary `sound`. Owner gates were resolved on 2026-06-27.

ScopeMemory is a memory-informed authorization layer for MCP agents. An agent starts with a signed goal, not broad credentials. ScopeMemory predicts the tools, scopes, resources, credentials, and approval path normally needed for that kind of work; grants short-lived access only when policy allows it; escalates uncertainty; executes downstream calls through a gateway; and records every decision with a proof tied to versioned authorization memory.

The project is not a tribal-knowledge RAG app. It is an authorization control plane with memory as evidence.

## Read Order

1. [RFC-00: Product And Architecture](plan/RFC-00-product-architecture.md)
2. [RFC-01: Domain Model And Data](plan/RFC-01-domain-model-data.md)
3. [RFC-02: Authorization Policy And Proofs](plan/RFC-02-authorization-policy-proofs.md)
4. [RFC-03: MCP Gateway Runtime](plan/RFC-03-mcp-gateway-runtime.md)
5. [RFC-04: Zero-Knowledge Credential Broker And Hooks](plan/RFC-04-zero-knowledge-credential-broker-hooks.md)
6. [RFC-05: Learning, Indexing, And Audit](plan/RFC-05-learning-indexing-audit.md)
7. [RFC-06: Demo And Build Plan](plan/RFC-06-demo-build-plan.md)
8. [Ground Truth Ledger](ground-truth-ledger.md)
9. [Open Questions](open-questions.md)
10. [Decisions](decisions.md)

## Package Contents

- `research/` records source-grounded findings, external facts, credential-injection analysis, threat model, and scope reduction.
- `plan/` is the canonical engineering plan split by system boundary.
- `judges/` records adversarial review of the research and plan.
- `ground-truth-ledger.md` separates verified facts, proposed changes, new artifacts, and unverified claims.
- `decisions.md` records stable planning decisions.

## Approval Posture

This package converges on a crisp MVP:

- One MCP gateway.
- Two downstream integrations for the demo: Linear and Slack.
- Dolt as source of truth.
- Qdrant as derived retrieval index.
- A deterministic policy engine with proof traces.
- LLM judges only as non-authoritative fact emitters.
- A credential broker that integrates password managers such as 1Password without exposing decrypted credentials to the agent, the model transcript, Dolt, Qdrant, or audit logs.

Resolved owner decisions: v1 zero knowledge means zero secret exposure to agents and ScopeMemory persistence; MVP credentials use real 1Password; Slack is mocked; policy uses CozoDB; local SR-style planning is sufficient.
