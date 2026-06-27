# Harsh Judge

Fresh evaluation. Reduce, reuse, crisp up the models to a clear buildable line, not speculative.

## Verdict

`approve`

## Score

Total: 56/60

- Completeness: 9/10
- Logical consistency: 10/10
- Source grounding: 8/10
- Interface/model correctness: 9/10
- Implementability: 10/10
- Simplicity/reuse: 10/10

## Cross-Check Verdict

`consistent`

## Adversary Verdict

`sound`

## What Can Be Cut

### Cut Multi-Provider Secrets In MVP

Keep the provider interface. Implement real 1Password first. Do not build Vault, AWS, GCP, macOS Keychain, and SPIFFE in v1.

### Cut Formal Proof Engine In MVP

Keep proof traces. Do not build a full proof generator before the gateway, policy, and audit loop exist.

### Cut Slack Interactive Approval In MVP

Use web approval. Slack approval messages are product polish, not core proof.

### Cut Real Stdio MCP Credential Launch Unless Needed For Demo

Document it and design it. Implement only if the demo requires a stdio downstream server.

### Cut Raw Session Learning

Do not index raw event logs. Do not let one successful session auto-create runtime policy.

## What Must Stay

### Credential Broker Must Stay

The user explicitly requested password-manager credentials through pre-tool-use hooks and zero knowledge. This cannot be a future add-on because it changes the data model, policy facts, audit shape, and gateway execution path.

### Hook Adapter Must Stay As Design

Even if not fully implemented first, the plan must specify hook behavior to avoid the wrong design: putting decrypted secrets in `updatedInput`.

### Prompt Injection Attack Path Must Stay

It proves why authorization cannot trust tool output.

### Dolt Diff Must Stay

It proves governed authorization memory, not just retrieval.

### Credential Non-Exposure Audit Must Stay

It proves the credential story is not merely "trust us."

## Minimal Buildable Line

One recipe, one team, two tools, one credential broker, one denial:

```text
Sales renewal prep
  -> predict Linear + Slack
  -> auto-approve Linear
  -> human-approve Slack read
  -> broker leases credentials without agent exposure
  -> execute
  -> deny external Slack post
  -> propose recipe update
  -> show Dolt diff and Memgraph recipe-index refresh
```

## Reuse Decisions

- MCP schemas are already the right boundary.
- 1Password references are already the right abstraction for secrets.
- Dolt is already the right review surface for policy memory.
- Memgraph/Dolt-derived graph retrieval is the current MVP retrieval cache.
- PreToolUse hooks are already the right client-side interception point where available.

## Over-Broad Areas To Watch

### "Zero Knowledge"

Do not overclaim. Use "zero secret exposure to agents and persistent ScopeMemory state" until the system has hardware-backed or cryptographic proof.

### "Datalog"

Do not let engine choice block the demo. Datalog-shaped facts and deterministic proof traces are enough for v1.

### "MCP Gateway"

Do not implement every connector. Implement the meta-gateway and two representative tool wrappers.

### "Learning"

Do not build autonomous policy evolution. Build proposed recipes and human merge.

## Approval Conditions

Approve the plan if the owner agrees with:

1. the precise zero-secret-exposure claim.
2. the one-recipe, two-tool MVP.
3. real 1Password for credential provider.
4. mocked Slack for the safe attack path.
5. CozoDB for policy.
6. no implementation until a follow-up build authorization.

## Final Harsh Call

The plan is still ambitious, but it is now centered on one buildable loop. The credential broker is the right hard thing to keep because it materially changes the thesis: ScopeMemory is not only deciding scopes; it is preventing agents from ever learning credentials while still letting authorized work happen.
