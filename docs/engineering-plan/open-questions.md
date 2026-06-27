# ScopeMemory Open Questions

## OQ-001 - Exact Definition Of Zero Knowledge

Status: resolved by owner on 2026-06-27.

Decision: define the v1 claim as **zero secret exposure to the agent and ScopeMemory persistence**, not mathematical zero-knowledge against the execution boundary.

Reason: a gateway that calls Slack, Linear, GitHub, or a shell command must eventually present a bearer token, API key, OAuth token, or signed proof to the downstream system. Unless the downstream API supports hardware-backed signing or token exchange, some trusted execution component sees the credential in memory. The binding promise should be precise:

- The agent never sees decrypted credentials.
- The model transcript never contains decrypted credentials.
- Dolt, Qdrant, audit logs, and UI never store decrypted credentials.
- Hooks never rewrite model-visible tool input with decrypted credentials.
- The password manager or credential broker resolves a secret only inside the execution boundary and only for a short-lived authorized call.

## OQ-002 - Initial Policy Engine

Status: resolved by owner on 2026-06-27.

Decision: use CozoDB for the initial policy engine.

Reason: the project benefits from making the Datalog-like policy layer real from the first implementation pass. CozoDB remains subordinate to ScopeMemory's typed fact compiler and proof/audit contract; LLMs and retrieval still emit inputs, not decisions.

## OQ-003 - Real Versus Mock Downstream Integrations

Status: resolved by owner on 2026-06-27.

Decision: use mocked Slack for the MVP prompt-injection and customer-context demo. Linear can still be real if credentials are available.

Reason: the demo needs a safe attack path. A mock Slack source makes exfiltration denial reliable without requiring risky workspace data.

## OQ-004 - Where To Run Credential Injection For Stdio MCP Servers

Recommended default: launch stdio MCP servers through the ScopeMemory broker at session start. Do not rely on a pre-tool-use hook to patch credentials into an already-running stdio server.

Reason: environment variables for stdio MCP servers are fixed when the process starts. Pre-tool-use hooks can block, rewrite, or route a tool call, but they cannot safely mutate the environment of an already-running server process.

## OQ-005 - Human Approval UX

Recommended default: build a web approval page first. Add Slack approval messages only after the core proof and gateway loop works.

Reason: Slack interactive approvals add app-install and token complexity that distracts from the authorization-memory story.

## OQ-006 - Recipe Confidence Thresholds

Recommended default for demo:

- Retrieval candidate threshold: `0.70`.
- Auto-approval threshold: `0.82`.
- Human escalation threshold: anything below `0.82`, any high-risk scope, any restricted resource, or any external destination.

Reason: the rough plan uses `0.80` and `0.82`; this keeps retrieval broad while keeping auto-approval conservative.

## OQ-007 - External Secrets Manager Support Beyond 1Password

Status: resolved by owner on 2026-06-27.

Decision: use real 1Password for the MVP credential provider. Keep the provider interface, but do not substitute a demo provider for the core credential story.

Reason: the zero-knowledge architecture should not bake in 1Password, but the first build should exercise the real password-manager path. Supporting multiple real providers before the demo would dilute the core authorization loop.

## OQ-008 - SR Code Arbiter Mode

Status: resolved by owner on 2026-06-27.

Decision: the local SR-style planning pass is sufficient. Do not run a live pooled SR Code arbiter pass before implementation unless a later review uncovers a new risk.
