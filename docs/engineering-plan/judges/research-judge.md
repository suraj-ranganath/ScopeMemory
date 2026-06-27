# Research Judge

Fresh evaluation. Judge only the research package and cited sources.

## Verdict

`approve`

## Score

Total: 54/60

- Completeness: 9/10
- Logical consistency: 9/10
- Source grounding: 8/10
- Interface/model correctness: 9/10
- Implementability: 9/10
- Simplicity/reuse: 10/10

## Cross-Check Verdict

`consistent`

## Adversary Verdict

`sound`

## Summary

The research package correctly identifies the project as memory-informed authorization rather than generic retrieval. It grounds the major design pieces in the rough plan: Dolt as canonical state, Qdrant as derived retrieval, deterministic policy, MCP gateway enforcement, LLM judges as non-authoritative fact emitters, and prompt-injection defense.

The research also makes the necessary credential correction: "gateway-held token vault" is too imprecise for the user's zero-knowledge requirement. The proposed broker, secret reference, credential binding, and lease model is the right way to integrate 1Password and pre-tool-use hooks without creating an accidental secret-exfiltration path.

## Must-Fix Findings

None blocking for planning approval.

## Should-Fix Findings

### R-001 - External Source Citations Are URL-Level, Not Line-Level

Problem: External standards are cited by URL, while local rough-plan claims are cited by file and line. This is acceptable for a planning package but weaker than the pqprime ideal.

Evidence: `research/external-standards.md` cites MCP, Claude hooks, and 1Password by URL.

Consequence if ignored: an implementer may need to re-open those docs before coding against exact request/response shapes.

Required fix before implementation: each implementation Bead that uses MCP, hooks, or 1Password should pin the exact docs and examples it relies on.

### R-002 - 1Password Provider Setup Must Be Verified Before Build

Problem: The owner selected real 1Password for the MVP. The research confirms 1Password supports secret references and developer flows, but it does not verify Suraj's local vault names, service account state, biometric unlock behavior, or CLI auth state.

Evidence: `ground-truth-ledger.md` marks current 1Password account/vault structure as unverified.

Consequence if ignored: the first live demo may block on local 1Password setup rather than product logic.

Required fix before implementation: create a setup Bead to verify `op --version`, auth status, a demo vault/item, and the desired injection mode.

### R-003 - Hook Semantics Are Host-Specific

Problem: The research uses Claude Code `PreToolUse` as the concrete hook example, while ScopeMemory should support multiple hosts.

Evidence: `RFC-04` correctly treats hooks as adapters, but implementation should avoid baking a Claude-only contract into core policy.

Consequence if ignored: the hook implementation could become the product instead of an adapter.

Required fix before implementation: define a host-neutral `ToolIntent` and `HookDecision` JSON schema.

## Source-Grounded Findings

### Confirmed

- Rough plan's main primitive is Workflow Authorization Recipe.
- Rough plan already splits memory, policy, gateway, LLM, and UI responsibilities.
- Rough plan already says raw tokens should not be given to agents.
- Rough plan already contains prompt-injection handling.
- New credential broker model is a coherent extension, not a sidecar.

### Missing But Acceptable For Plan

- Exact 1Password CLI command shapes for the final implementation.
- Exact MCP SDK selection.
- Exact policy-engine library choice.
- Exact Slack workspace or mock dataset.

## Simplicity And Reuse Review

The research avoids inventing a secret store. It reuses password-manager references and makes ScopeMemory responsible for authorization, not secret custody. It also avoids making hooks the trusted root. That is the strongest simplification in the package.

## Approval Conditions

Resolved by owner on 2026-06-27:

1. Zero-secret-exposure definition approved.
2. Real 1Password selected for MVP.
3. Local SR-style planning accepted without live pooled arbiter pass.

## Residual Risk

The plan is source-grounded enough for implementation planning. It is not yet a coding spec for exact CLI invocation, OAuth app setup, or MCP SDK types.
