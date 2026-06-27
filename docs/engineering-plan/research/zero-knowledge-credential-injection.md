# Zero-Knowledge Credential Injection Research

## Thesis

The project should use the phrase "zero knowledge" carefully. In v1, ScopeMemory should guarantee **zero secret exposure to agents and persistent ScopeMemory state**:

- The agent does not see decrypted credentials.
- The model transcript does not contain decrypted credentials.
- Tool input visible to the model does not contain decrypted credentials.
- Dolt, Memgraph, audit logs, and UI do not contain decrypted credentials.
- Secret values are resolved only inside a trusted execution boundary and only for an authorized call.

This is not a claim that the gateway can call a bearer-token API without any trusted component seeing a bearer token. That requires downstream token exchange, workload identity, signing protocols, or hardware isolation. The product should be precise and earn trust.

## Injection Modes

### Gateway Proxy Mode

Use for HTTP APIs such as Linear, Slack, GitHub, and future SaaS connectors.

```text
agent -> ScopeMemory MCP gateway -> downstream API
```

The agent calls a proxied MCP tool. The gateway validates schema, runs policy, resolves an opaque credential lease, attaches the downstream credential, executes, redacts, logs, and returns the result. This is the cleanest mode.

### Stdio MCP Launch Mode

Use for MCP servers that need tokens in environment variables at process start.

```text
ScopeMemory session start
  -> policy predicts allowed connector
  -> credential broker resolves lease
  -> broker launches MCP server with env injected
  -> agent talks to gateway or launched server through narrowed catalog
```

Do not rely on a pre-tool-use hook to change credentials for an already-running stdio server. That is too late.

### PreToolUse Hook Mode

Use for host clients that expose tool-call hooks.

The hook receives a proposed tool call and sends a normalized intent to ScopeMemory. ScopeMemory returns:

- allow without credential.
- block and explain.
- rewrite to a gateway call.
- rewrite a shell command to `scopememory exec --lease <opaque-lease> -- ...`.
- create access request and pause.

The hook must not return an `updatedInput` containing decrypted secrets. It may return secret references, lease IDs, or wrapper commands that resolve secrets outside model-visible text.

### Shell Command Wrapper Mode

Use for commands that need environment variables:

```text
scopememory exec --lease lease_123 --env GITHUB_TOKEN=ref:credref_abc -- gh issue list
```

The wrapper resolves the secret just before `execve`, scrubs logs, prevents echoing, and zeroizes where possible. The model sees only the wrapper and lease ID.

### 1Password Provider Mode

Use 1Password secret references and CLI/environment workflows:

```text
credential_ref = op://Engineering/Linear API Token/token
credential_class = linear.oauth_token
provider = 1password
```

ScopeMemory stores the reference and metadata, not the value. The broker is the only process allowed to call `op read`, `op run`, or provider APIs, and only after policy grants a credential lease.

## Hook Deny Rules

The hook should deny or escalate:

- Direct `op read` in an agent shell command unless wrapped by ScopeMemory.
- `op item get --fields password` or equivalent direct secret exfiltration.
- `--no-masking` or flags that disable secret redaction.
- Echoing environment variables likely to hold secrets.
- Writing decrypted secrets into files.
- Passing secrets on command lines where process listing or logs can expose them.

## Datalog Facts

Credential facts should talk about metadata, not values:

```prolog
credential_ref("credref_linear_sales", "1password", "linear.oauth_token").
credential_owner_team("credref_linear_sales", "sales-ops").
credential_allows_scope("credref_linear_sales", "linear:issues:create").
credential_injection_mode("credref_linear_sales", "gateway_header").
credential_ref_last_rotated("credref_linear_sales", "2026-06-01").
secret_value_known_to_agent("sess_123", false).
lease_requested("sess_123", "credref_linear_sales", "linear.create_issue").
provider_authz_satisfied("lease_123", "1password_touchid_or_service_account").
```

Decisions depend on these facts plus normal scope, resource, team, and recipe facts.

## Audit Facts

Audit stores:

- credential reference ID.
- provider kind.
- provider request ID or local operation ID.
- lease ID.
- lease TTL.
- scope/resource binding.
- proof hash.
- redaction policy.

Audit never stores:

- token value.
- password value.
- `.env` plaintext.
- `op://` item path if it would reveal sensitive customer names beyond the approved metadata policy.

## Recommended MVP

Implement the real 1Password provider path first. A test fixture may stub provider responses for unit tests, but the demo credential story should exercise 1Password secret references through the broker:

```text
access request approved
  -> credential lease issued
  -> broker resolves ref at execution
  -> gateway uses credential
  -> audit proves no agent exposure
```
