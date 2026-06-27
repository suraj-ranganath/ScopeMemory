# ScopeMemory Engineering Plan

**Status:** RFC-07 2-hour demo ready to build. Phase 2 RFCs deferred.
**Tracked by:** Beads issue `ScopeMemory-9sk`.
**First command:** `cd demo && python run_demo.py all`

ScopeMemory is a memory-informed authorization layer for MCP agents. For the Agentic Identity demo, it shows **ReBAC context-path authorization** — agents earn task-scoped access via relationship traversal, not broad roles.

## Build Order

### Now (2 hours)

1. **[RFC-07: 2-Hour Agentic Identity Demo](plan/RFC-07-2-hour-agentic-identity-demo.md)** — binding
2. Run `demo/run_demo.py all`

### Later (Phase 2)

3. [RFC-00: Product And Architecture](plan/RFC-00-product-architecture.md)
4. [RFC-01: Domain Model And Data](plan/RFC-01-domain-model-data.md) — full 24-table Dolt schema
5. [RFC-02: Authorization Policy And Proofs](plan/RFC-02-authorization-policy-proofs.md) — CozoDB
6. [RFC-03: MCP Gateway Runtime](plan/RFC-03-mcp-gateway-runtime.md)
7. [RFC-04: Zero-Knowledge Credential Broker](plan/RFC-04-zero-knowledge-credential-broker-hooks.md)
8. [RFC-05: Learning, Indexing, And Audit](plan/RFC-05-learning-indexing-audit.md)
9. [RFC-06: Full MVP Build Plan](plan/RFC-06-demo-build-plan.md)

## Reference

- [Decisions](decisions.md)
- [Open Questions](open-questions.md)
- [Ground Truth Ledger](ground-truth-ledger.md)
- [STATUS](STATUS.md)

## Demo Acceptance

```bash
cd demo && python run_demo.py all
# Must print: DEMO PASSED — Agentic Identity + ReBAC context path
```
