# RFC-04: Zero-Knowledge Credential Broker And Hooks

## Status

Plan ready for implementation authorization.

## Goal

Integrate credentials from password managers such as 1Password into ScopeMemory without exposing decrypted credentials to the agent, model transcript, project files, Dolt, Memgraph, audit logs, or UI.

## Precise Claim

ScopeMemory v1 provides **zero secret exposure to agents and persistent ScopeMemory state**.

It does not claim that no trusted execution component ever sees a bearer credential. A gateway, broker, or downstream SDK must present a credential unless the downstream system supports token exchange, signatures, or hardware-backed proof. The v1 guarantee is that secret material is kept out of the agent and out of durable ScopeMemory memory.

## Components

### Credential Broker

Local or server-side service that owns provider adapters and execution-time secret resolution.

Responsibilities:

- Resolve secret references only after policy issues a lease.
- Keep decrypted values in memory only as long as needed.
- Inject into downstream execution by header, process env, stdin, file descriptor, local socket, or SDK callback.
- Scrub logs and child process output.
- Return non-secret evidence to the gateway.

### Provider Adapter

Provider-specific resolver. V1 provider:

- `1password`: resolves broker-only references through 1Password CLI, SDK, service-account, desktop-auth, or Environment flows.

The adapter must expose capabilities separately because each mode fits a different execution boundary:

- `onepassword_mcp_environment`: official 1Password MCP server and Environments. Prefer for Codex-managed local application secrets when the local MCP binary and Environment are configured.
- `onepassword_sdk_desktop`: Python SDK desktop-app auth. Prefer for local gateway/broker execution with human approval.
- `onepassword_sdk_service_account`: Python SDK service-account auth. Prefer for automated broker execution with least-privilege vault or Environment access.
- `op_run_process_env`: CLI `op run` around a short-lived broker-owned child process.
- `op_cli_secret_reference`: direct secret-reference resolution inside broker code only; never agent-visible.

Future providers:

- macOS Keychain.
- AWS Secrets Manager.
- GCP Secret Manager.
- Vault.
- SPIFFE/SPIRE or workload-identity token exchange.

### Credential Lease

Opaque runtime object:

```json
{
  "lease_id": "lease_123",
  "session_id": "sess_123",
  "grant_id": "grant_123",
  "credential_ref_id": "credref_linear_sales",
  "tool_id": "linear.create_issue",
  "scope": "linear:issues:create",
  "resource": "linear_team:SALES",
  "injection_mode": "gateway_header",
  "expires_at": "2026-06-27T20:30:00Z",
  "max_uses": 1
}
```

The lease is safe to show to the agent only as an opaque handle. It is not a capability unless presented to the broker by the authorized execution path.

## Injection Modes

### `gateway_header`

Gateway resolves the lease and attaches an API credential to a downstream HTTP request. Use for Linear, Slack, GitHub, and other proxied API tools.

### `process_env`

Broker launches a child process with environment variables set. Use for CLIs and stdio servers only when unavoidable.

Rules:

- Use short-lived subprocesses.
- Prefer secret references or file descriptors over command-line arguments.
- Block commands that echo env vars or write secrets to disk.
- Never show the resolved env in model-visible hook output.

### `stdin_or_fd`

Broker passes secret material through stdin, a named pipe, or file descriptor. Prefer this when the downstream process supports it.

### `local_socket`

Broker exposes a local socket that serves tokens to an approved child process or gateway plugin. Use for long-lived local tools that cannot receive env per call.

### `provider_native`

Use a provider-native runtime such as `op run` or a 1Password environment. The broker still owns the invocation and proof.

### `onepassword_mcp_environment`

Use the official 1Password MCP server to manage a 1Password Environment and mount runtime variables for an authorized application process. This mode is preferred for Codex local development workflows because the MCP server does not return secret values to the AI tool.

Rules:

- Treat the 1Password MCP server as a provider adapter, not as the ScopeMemory policy engine.
- Store only Environment IDs, variable names, provider operation IDs, and lease metadata.
- Require the local MCP server binary and desktop-app approval path to be available before claiming this mode.
- Deny or escalate if the MCP server is missing, disabled, untrusted, or the user cancels the approval prompt.

## PreToolUse Hook Adapter

Hooks are an adapter for clients that can intercept tool calls before execution.

Claude Code and Codex both support `PreToolUse`, but their behavior is not identical. ScopeMemory must normalize host-specific hook JSON into `ToolIntent` and keep the canonical authorization result in the gateway/broker.

### Host Constraints

- Claude Code can match MCP tools with names like `mcp__server__tool`; `PreToolUse` command hooks receive JSON on stdin and can deny, ask, defer, allow, or rewrite tool input.
- Codex can intercept supported Bash, `apply_patch`, and MCP tool calls; command hooks receive JSON on stdin and can deny or rewrite supported inputs.
- Codex matching command hooks for the same event can launch concurrently, so a project hook must not be the only credential protection layer.
- Both hosts can run hooks with high local privileges. Hook scripts must validate and sanitize all tool input.
- Neither host hook may place decrypted credentials into `updatedInput`, additional context, stdout, stderr, transcript-visible text, or project files.

### Hook Input

The hook normalizes:

- tool name.
- tool input.
- shell command if tool is Bash.
- session ID.
- working directory.
- target resource hints.
- whether the call would read or write.
- whether the call appears to access secrets.

### Hook Output

Allowed outputs:

- allow unchanged.
- block with safe reason.
- rewrite to a ScopeMemory gateway tool.
- rewrite shell command to `scopememory exec --lease <lease_id> -- <command>`.
- create access request and block until approved.

Disallowed outputs:

- decrypted credential in `updatedInput`.
- plaintext `.env`.
- direct `Authorization: Bearer ...` header.
- `op read` output.
- full `op://` path if policy marks it sensitive.

## Hook Enforcement Examples

### Direct 1Password Read

Input:

```text
op read op://Engineering/Linear/token
```

Decision:

```text
DENY
```

Reason: direct secret read bypasses credential broker and would expose secret material to shell output or transcript.

### Linear CLI With Lease

Input:

```text
linear issue create --team SALES --title "Follow up with Acme"
```

Hook rewrite:

```text
scopememory exec --lease lease_linear_123 -- linear issue create --team SALES --title "Follow up with Acme"
```

The wrapper resolves the token inside the child process environment and suppresses secret output.

### Stdio MCP Server

Wrong:

```text
PreToolUse tries to add SLACK_BOT_TOKEN to an already-running server.
```

Right:

```text
scopememory mcp-launch slack --session sess_123 --credential-binding binding_slack_sales
```

The server starts under the broker with correct environment and catalog constraints.

## 1Password Integration

Store:

```text
provider_id = onepassword_local
credential_ref_id = credref_linear_sales
secret_ref = encrypted_or_broker-only handle to op://Engineering/Linear/token
credential_class = linear.oauth_token
owner_team = sales-ops
```

For setup docs, a placeholder secret reference may use this shape:

```text
op://ScopeMemory Demo/Linear API Token/token
```

This is not a verified vault/item/field. Runtime policy should prefer opaque `credential_ref_id` values and store raw provider paths only when the metadata policy allows them.

Execution:

1. Policy grants a credential lease.
2. Broker verifies session, tool, scope, resource, TTL, and caller.
3. Broker resolves the secret reference through 1Password.
4. Broker injects into gateway request or child process.
5. Broker records provider operation ID and lease use, not secret value.

### Lease Use Enforcement

The lease is not a bearer token for the agent. It can only be consumed by an approved execution boundary:

- `gateway`
- `broker`
- `exec_wrapper`
- `mcp_launcher`

Each use must match the lease's session, tool, scope, and resource. Expired leases, exhausted `max_uses`, mismatched bindings, direct agent callers, and any lease marked `secret_exposed_to_agent=true` are denied. Successful use returns only non-secret evidence: `lease_id`, `credential_ref_id`, `credential_ref_hash`, provider metadata, injection mode, remaining uses, and `secret_exposed_to_agent=false`.

## Audit Contract

For every credential use, store:

- `lease_id`
- `credential_ref_id`
- `credential_ref_hash`
- `provider_id`
- `injection_mode`
- `session_id`
- `tool_id`
- `scope`
- `resource`
- `expires_at`
- `used_at`
- `secret_exposed_to_agent=false`

Do not store:

- secret value.
- raw token.
- password.
- private key.
- full `.env`.
- command output containing a secret.

## Failure Behavior

- Provider unavailable: `ESCALATE_HUMAN` or `DENY`, depending on policy.
- User cancels 1Password prompt: `ESCALATE_HUMAN` with safe reason.
- Credential lease expired: `REPAIR` if refresh is safe, else `ESCALATE_HUMAN`.
- Hook unavailable: fall back to gateway-only tools; do not allow direct secret access.
- 1Password MCP server missing or disabled: do not claim Environment injection; escalate setup or deny.
- `op` CLI missing: do not use CLI provider mode; escalate setup or deny.
- Service account token absent: do not ask the agent for the token; mark service-account mode unavailable.
- Broker cannot guarantee non-exposure: `DENY`.
