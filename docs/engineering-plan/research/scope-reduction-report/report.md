# Scope Reduction Report

## Directive

Reduce, reuse, crisp up the models to a clear buildable line, not speculative.

## Cuts

- Cut multi-provider password-manager implementation from the MVP. Keep the provider interface and implement real 1Password first.
- Cut full formal proof generation. Keep a deterministic proof trace listing facts, rules, decision, commit hashes, and event hash chain.
- Cut real Slack interactive approvals from the first demo. Use a web approval page first.
- Cut enterprise IdP sync, SPIFFE/SPIRE, real token exchange, and workload identity from the MVP. Model them as production extensions.
- Cut broad connector support. Use Linear and Slack or Slack-mock only.
- Cut indexing raw session events. Only accepted recipes are indexed for normal retrieval.
- Cut autonomous recipe acceptance. LLMs propose recipes; humans merge Dolt changes.

## Reuse Decisions

- Reuse MCP tool schemas as the runtime authorization boundary.
- Reuse Dolt for branch/diff/review semantics.
- Reuse Qdrant only for retrieval, not authorization truth.
- Reuse password-manager secret references instead of inventing secret storage.
- Reuse pre-tool-use hooks as an adapter, not a new core policy engine.

## Minimal Buildable Line

The MVP is one closed loop:

1. Seed Dolt with users, teams, tools, scopes, credential refs, and one accepted recipe.
2. Index accepted recipe chunks in Qdrant.
3. Start a session with a signed goal.
4. Preflight predicts tools, scopes, resources, and credential binding.
5. Auto-approve Linear issue creation; create human request for Slack customer-channel read.
6. Issue a credential lease after policy and approval.
7. Execute Slack search and Linear issue creation through the gateway.
8. Deny an external Slack post triggered by prompt injection.
9. Audit every decision with proof.
10. Propose a recipe update on a Dolt branch and show the diff.

## Required Decision Entries

- D-SCM-001 through D-SCM-007 in `decisions.md`.

## Remaining Blockers

- Owner approved the MVP line.
- Owner accepted local SR-style planning without live SR Code pool arbiters.
- Owner selected real 1Password for the first demo credential path.
