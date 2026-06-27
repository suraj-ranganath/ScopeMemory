# Scope Reduce Report

This report records the harsh-reduction pressure that changed the plan package. It intentionally uses the SR Code `*reduce*/report.md` shape.

## Directive

Reduce, reuse, crisp up the models to a clear buildable line, not speculative.

## Cuts Applied

- Multi-provider secret-manager implementation is deferred. The plan keeps the provider interface but starts with real 1Password.
- Full formal proof generation is deferred. The plan keeps deterministic proof traces tied to facts, rules, Dolt commits, recipe index commits, and event hashes.
- Slack interactive approval is deferred. The web approval page is the first human approval surface.
- SPIFFE/SPIRE, enterprise IdP sync, real workload identity, and token exchange are production extensions, not MVP requirements.
- Raw session indexing is rejected. Only accepted recipes can enter the normal recipe retrieval layer.
- Autonomous recipe acceptance is rejected. LLMs propose; humans merge.

## Reuse Decisions

- Use MCP tool schemas as the call boundary.
- Use Dolt for reviewable authorization memory.
- Use Memgraph/Dolt-derived graph retrieval only.
- Use password-manager secret references instead of storing secrets.
- Use pre-tool-use hooks as an adapter for hosts that expose them.

## Minimal Buildable Line

The canonical MVP is one closed loop:

```text
preflight goal
  -> retrieve recipe
  -> predict Linear + Slack
  -> auto-approve Linear
  -> human-approve Slack read
  -> issue credential lease
  -> execute through gateway
  -> deny external exfiltration attempt
  -> audit proof
  -> propose Dolt recipe diff
  -> re-index accepted recipe
```

## Package Changes

- Added `RFC-04` as a first-class credential broker and hooks plan.
- Added credential provider, credential ref, credential binding, and credential lease tables to `RFC-01`.
- Added credential facts and no-agent-exposure invariants to `RFC-02`.
- Added hook and injection-mode runtime behavior to `RFC-03` and `RFC-04`.
- Added credential lease audit invariants to `RFC-05`.
- Reduced the build plan in `RFC-06` to a two-tool, one-recipe demo.

## Resolved Owner Gates

- Zero-secret-exposure wording approved.
- Real 1Password chosen for MVP.
- Local SR-style planning accepted without a live pooled SR Code arbiter pass.
