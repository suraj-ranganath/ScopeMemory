# RFC-04: Zero-Knowledge Credential Broker And Hooks

## Status

Plan ready for implementation authorization.

## Goal

Integrate credentials from password managers such as 1Password into ScopeMemory without exposing decrypted credentials to the agent, model transcript, project files, Dolt, Qdrant, audit logs, or UI.

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

- `1password`: resolves `op://...` references through 1Password CLI/service-account/environment flows.

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

## PreToolUse Hook Adapter

Hooks are an adapter for clients that can intercept tool calls before execution.

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

Execution:

1. Policy grants a credential lease.
2. Broker verifies session, tool, scope, resource, TTL, and caller.
3. Broker resolves the secret reference through 1Password.
4. Broker injects into gateway request or child process.
5. Broker records provider operation ID and lease use, not secret value.

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
- Broker cannot guarantee non-exposure: `DENY`.
