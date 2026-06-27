# Threat Model

## Assets

- Downstream credentials: OAuth tokens, API keys, service account secrets, 1Password references.
- Authorization memory: recipes, policies, team mappings, tool-scope mappings.
- Audit log integrity.
- User and team resource boundaries.
- Agent session goals and approvals.
- Customer and internal data returned by tools.

## Trust Boundaries

- Agent/model boundary: untrusted for authorization.
- Tool output boundary: untrusted observations.
- MCP gateway boundary: trusted enforcement point.
- Credential broker boundary: trusted execution boundary for secret resolution.
- Password manager boundary: source of credential truth.
- Dolt main branch: canonical governed state.
- Qdrant index: derived, non-authoritative cache.
- Human approver boundary: authority for high-risk and uncertain grants.

## Attacker Goals

- Make the agent call a tool outside the signed goal.
- Exfiltrate customer data to an external Slack channel or arbitrary URL.
- Trick the agent into requesting broad scopes.
- Get raw credentials into model context, shell output, logs, Dolt, Qdrant, or UI.
- Poison recipes through successful-looking but unsafe sessions.
- Exploit a stale Qdrant index to retrieve deprecated recipes.
- Replay or extend an ephemeral grant after TTL.
- Bypass policy by directly invoking `op read`, `gh auth token`, or similar secret commands.

## Required Controls

- Signed or immutable session goal.
- Preflight narrows visible tool catalog.
- Inline enforcement for every actual tool call.
- Datalog-shaped deterministic policy as final authority.
- Human escalation for high-risk, external, cross-team, admin, private customer, bulk export, and low-confidence requests.
- Credential leases bound to session, tool, scope, resource, TTL, and caller.
- Hook rules that block direct secret retrieval and command-line leaks.
- Hash-chained session events.
- Policy decisions tied to Dolt commit and Qdrant index build commit.
- Accepted recipes only in normal retrieval.
- Proposed recipes isolated from auto-approval until reviewed.

## Prompt Injection Scenario

1. User asks for sales renewal prep.
2. Slack search returns a malicious message instructing the agent to post customer notes externally.
3. Agent attempts `slack.post_message` to an external channel.
4. ScopeMemory denies because:
   - tool output cannot expand the session goal.
   - external destination is high risk.
   - recipe did not predict external posting.
   - no approved grant exists.
   - policy requires human approval or denies entirely.

## Credential Exposure Scenario

1. Agent proposes `op read op://Engineering/Linear/token`.
2. PreToolUse hook intercepts Bash.
3. Hook normalizes the command as direct secret exfiltration.
4. Policy returns `DENY` or `ESCALATE_HUMAN`.
5. Hook blocks execution and returns a safe explanation.
6. Audit records intent hash and decision, not the secret reference value if policy marks it sensitive.

## Poisoned Learning Scenario

1. An unsafe session succeeds because a human approved a one-off exception.
2. Recipe proposal judge proposes auto-approving the same scope in the future.
3. Dolt proposal branch is created, but the recipe is not indexed for normal retrieval.
4. Human/security review sees that the evidence included a one-off exception.
5. Recipe is rejected or marked human-required.

## Residual Risks

- A trusted gateway or broker compromise can expose credentials in memory.
- Environment-variable injection is less safe than downstream token exchange or signing protocols.
- Human approvers can approve unsafe access.
- Retrieval confidence can be misleading without evaluation data.
- Hooks are client-specific and cannot replace gateway enforcement.
