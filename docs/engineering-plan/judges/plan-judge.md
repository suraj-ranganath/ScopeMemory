# Plan Judge

Fresh evaluation. Judge only the canonical ScopeMemory plan package and cited sources.

## Verdict

`approve`

## Score

Total: 55/60

- Completeness: 9/10
- Logical consistency: 9/10
- Source grounding: 8/10
- Interface/model correctness: 9/10
- Implementability: 10/10
- Simplicity/reuse: 10/10

## Cross-Check Verdict

`consistent`

## Adversary Verdict

`sound`

## Summary

The plan package is buildable and split along real boundaries: product architecture, data model, policy/proof engine, MCP runtime, credential broker/hooks, learning/indexing/audit, and MVP sequencing. The credential broker is integrated throughout the model rather than bolted on at the end.

The most important design choice is precise: ScopeMemory does not claim mathematical zero-knowledge for bearer-token APIs. It claims zero secret exposure to agents and persistent ScopeMemory state. That is honest and implementable.

## Must-Fix Findings

None blocking for implementation planning.

## Should-Fix Findings

### P-001 - Policy Engine Choice Resolved To CozoDB

Problem: Resolved. The owner selected CozoDB as the initial policy engine.

Evidence: `open-questions.md` OQ-002 and `RFC-02` engine notes.

Consequence if ignored: implementation could stall debating engine choice.

Required fix before coding WP-03: define the CozoDB schema/query boundary and keep ScopeMemory's typed fact compiler/proof API outside CozoDB.

### P-002 - Credential Broker Trust Boundary Needs Implementation Hardening

Problem: `RFC-04` states the broker is trusted, but implementation must specify process isolation, log scrubbing, child process environment handling, and failure behavior.

Evidence: `RFC-04` defines modes but does not define OS-specific hardening.

Consequence if ignored: secrets could leak through env dumps, process output, crash logs, shell history, or command-line args.

Required fix before coding WP-04: create a broker hardening checklist for macOS/local demo and production.

### P-003 - Stdio MCP Server Mode Is Correct But Easy To Miss

Problem: The plan correctly says stdio server credentials must be injected at process launch, not at individual tool-call time.

Evidence: `open-questions.md` OQ-004 and `RFC-04` stdio example.

Consequence if ignored: implementers may build only a PreToolUse hook and discover too late that stdio server env cannot be patched after launch.

Required fix before coding WP-05: make stdio launch mode an explicit integration test or demo non-goal.

### P-004 - Qdrant Payload Redaction Needs Tests

Problem: The plan says Qdrant payloads must not include secret refs or raw session/customer data, but does not define tests.

Evidence: `RFC-01` Qdrant payload rules and `RFC-05` indexing rules.

Consequence if ignored: retrieval index could become a data leak.

Required fix before coding WP-02: add snapshot tests over payload shape.

### P-005 - Human Approval Semantics Need Exact UI State

Problem: The plan describes access requests but not exact transitions for pending, approved, denied, expired, revoked, and superseded.

Evidence: `RFC-01` table and `RFC-06` UI work package.

Consequence if ignored: approval UI and policy engine may disagree.

Required fix before coding WP-06: define an access request state machine.

## Interface And Model Correctness

Strong:

- Recipes include credential classes, not just scopes.
- Credential leases are bound to session, grant, credential ref, binding, injection mode, TTL, and no-agent-exposure.
- Policy proof includes credential facts.
- Gateway remains canonical runtime boundary.
- Hooks are adapters.
- Learning does not auto-merge into policy.

Needs precision later:

- ID generation strategy.
- exact schema JSON validation library.
- exact Slack/Linear resource normalization.
- exact redaction policy.
- exact provider adapter protocol.

## Implementability Review

The work package order is sensible. The plan starts with Dolt schema and policy, then credential broker, then gateway, UI, retrieval, learning, and hook adapter. This avoids building UI over an ungrounded policy model.

## Simplicity And Reuse Review

The plan cuts:

- full formal proof engine.
- real Slack interactive approvals.
- multi-provider secret manager implementation.
- raw-session indexing.
- direct hook-as-security-root model.

These cuts preserve the project thesis while making the first build realistic.

## Approval Conditions

Owner decisions resolved on 2026-06-27:

1. zero-secret-exposure claim approved.
2. CozoDB selected as first policy engine.
3. real 1Password selected for MVP credentials.
4. mocked Slack selected for MVP.
5. local SR-style planning accepted without live pooled arbiter pass.

## Residual Risk

The package is ready for planning approval, not implementation autopilot. Each WP should become Beads issues with acceptance criteria and tests.
