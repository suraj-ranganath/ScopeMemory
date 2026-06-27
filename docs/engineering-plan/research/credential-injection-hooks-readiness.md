# Credential Injection Hooks Readiness

## Status

Date: 2026-06-27

Bead: `ScopeMemory-09o.2.2`

Scope: local 1Password readiness, Claude Code hook behavior, Codex hook behavior, and the first broker adapter shape for MCP calls.

## Local Readiness

Checked on Suraj's Mac:

- 1Password desktop app: present at `/Applications/1Password.app`.
- 1Password CLI `op`: not found on `PATH`.
- 1Password MCP server executable: not found at `/Applications/1Password.app/Contents/MacOS/onepassword-mcp`.
- Search under `/Applications/1Password.app/Contents` did not find `op` or `onepassword-mcp`.
- No secret value was read, printed, written, or persisted during this check.

Consequence: the real 1Password provider is not locally resolvable yet. ScopeMemory should treat this as provider unavailable and fail closed by returning `DENY` or `ESCALATE_HUMAN`, depending on the policy context. It should not fall back to plaintext `.env` files or direct `op read` from an agent shell.

## Source Facts

### 1Password MCP Server For Codex

Source: `https://www.1password.dev/environments/mcp-server`

Relevant facts:

- The 1Password MCP server is a local bridge that lets MCP clients such as Codex manage 1Password Environments with authorization prompts.
- The MCP server does not read or return secrets to the AI tool. Secrets stay in 1Password and are accessed only by authorized processes.
- Runtime injection uses an in-memory FIFO local `.env` mount. 1Password injects variables into the application process; values live in memory only for the authorized process and only while needed.
- Current setup requires 1Password desktop app for Mac or Linux and a 1Password Environment.
- Codex configuration on Mac uses `/Applications/1Password.app/Contents/MacOS/onepassword-mcp`.
- The desktop app may prompt for approval when the MCP client connects or accesses an Environment.

ScopeMemory implication: for Codex developer-environment workflows, prefer the 1Password MCP server and Environment mount path when available. It is the cleanest no-agent-secret path because the AI tool can work with names and configuration while 1Password owns secret injection.

### 1Password CLI Secret References

Source: `https://www.1password.dev/cli/secret-references`

Relevant facts:

- Secret references use the shape `op://<vault-name>/<item-name>/[section-name/]<field-name>`.
- 1Password CLI can resolve references with `op read`, `op run`, or `op inject`.
- `op read` can print a secret to stdout or write it to a file. This is not safe for agent-visible execution.
- `op run` can pass secrets as environment variables to a subprocess for the duration of that process.
- `op inject` can render files with plaintext secrets. That is only safe inside a broker-owned temporary boundary with strict cleanup and redaction.
- 1Password recommends service accounts for least-privilege CLI access.

ScopeMemory implication: the agent must not call `op read` directly. The broker may use CLI resolution only after a valid credential lease, and only inside a trusted execution boundary that prevents secret values from entering model-visible output, Beads, Dolt, Qdrant, UI fixtures, or logs.

### 1Password SDKs

Source: `https://www.1password.dev/sdks`

Relevant facts:

- SDKs are available for Go, JavaScript, and Python.
- SDKs can load secrets with secret references and read environment variables from 1Password Environments.
- SDK auth modes include desktop-app authorization prompts and service account tokens.
- Service accounts are best for automated least-privilege access. Desktop auth is best for local human-in-the-loop workflows.
- SDKs are version 0; pin exact versions because minor releases may break integration code.

ScopeMemory implication: for the Python gateway/broker, the SDK path is probably better than shelling out long term, but the first adapter should keep a provider interface so the implementation can choose CLI, SDK desktop auth, SDK service-account auth, or 1Password MCP Environment injection per execution mode.

### 1Password Agent Hook

Source: `https://www.1password.dev/environments/agent-hook-validate`

Relevant facts:

- 1Password provides an agent hook that validates locally mounted `.env` files from 1Password Environments before supported agents execute shell commands.
- The hook supports Claude Code, Cursor, GitHub Copilot, and Windsurf.
- The hook communicates with agents over JSON on stdin/stdout and can observe, block, or modify behavior.
- The hook validates whether configured environment mounts exist and are FIFO named pipes.
- Its default mode can fail open if it cannot access the 1Password database.

ScopeMemory implication: the 1Password hook is useful setup validation, but it is not sufficient as ScopeMemory's enforcement root. ScopeMemory credential access must fail closed when the broker cannot prove provider readiness.

### Claude Code Hooks

Source: `https://code.claude.com/docs/en/hooks`

Relevant facts:

- `PreToolUse` runs after Claude creates tool parameters and before a tool call executes.
- Command hooks receive JSON on stdin.
- `PreToolUse` matches normal tools and MCP tools. MCP names follow `mcp__<server>__<tool>`.
- `PreToolUse` can return `hookSpecificOutput.permissionDecision` values such as `allow`, `deny`, `ask`, and `defer`.
- `updatedInput` can replace the tool input before execution.
- If multiple `PreToolUse` hooks disagree, deny has highest precedence.

ScopeMemory implication: Claude Code can host a strong adapter for direct shell and MCP tool calls. It can deny direct `op read`, deny tool inputs that contain secret material, or rewrite a command to `scopememory exec --lease <lease_id> -- ...`. The hook must never put decrypted credentials in `updatedInput`.

### Codex Hooks

Source: `https://developers.openai.com/codex/hooks`

Relevant facts:

- Codex supports hook config through `hooks.json` or inline `[hooks]` config.
- `PreToolUse` can intercept supported Bash, `apply_patch`, and MCP tool calls.
- Command hooks receive one JSON object on stdin.
- To deny a supported tool call, Codex accepts `hookSpecificOutput.permissionDecision = "deny"` with a safe reason.
- To rewrite supported tool input, Codex accepts `permissionDecision = "allow"` with `updatedInput`.
- Multiple matching command hooks for the same event are launched concurrently, so one hook cannot prevent another matching hook from starting.
- Non-managed hooks require review and trust before they run.
- Codex documents `PreToolUse` as a guardrail, not a complete enforcement boundary.

ScopeMemory implication: Codex hooks are useful adapters, especially for local shell commands and MCP calls, but the canonical enforcement point must remain the ScopeMemory gateway/broker. Managed hooks are preferable for organization-level enforcement. Project hooks are useful for the demo but should not be the only control protecting credentials.

## Provider Mode Decision

Preferred order for the MVP:

1. `onepassword_mcp_environment`: use the official 1Password MCP server and Environments for Codex-managed local application secrets when the binary and Environment are available.
2. `onepassword_sdk`: use the Python SDK inside the broker/gateway for HTTP API execution when a desktop auth flow or service account is configured.
3. `op_run_process_env`: use `op run` only when a short-lived child process needs env vars and the broker owns the child process.
4. `op_cli_secret_reference`: use direct `op read` only inside broker code, never in an agent-visible shell, and only when a downstream SDK/API requires a token value in memory.
5. `mock_provider`: tests may use deterministic non-secret placeholders, but the live demo credential story should not pretend the mock is real 1Password readiness.

Do not use:

- direct `op read` from Claude, Codex, or any model-visible shell command.
- plaintext `.env` as a fallback.
- `op inject --out-file` into the repo or any persistent path.
- hook `updatedInput` containing credential values.
- storing raw `op://` paths when they reveal sensitive names beyond approved metadata policy.

## Hook Adapter Contract

Normalize host-specific hook input into:

```json
{
  "agent_host": "claude_code|codex",
  "hook_event": "PreToolUse",
  "session_id": "host-session-id",
  "tool_name": "Bash|mcp__server__tool",
  "tool_input": {},
  "cwd": "/repo/path",
  "access_kind": "read|write|execute",
  "secret_access_pattern": "none|direct_secret_read|secret_in_input|env_print|secret_file_write",
  "resource_hints": []
}
```

Return only safe outputs:

```json
{
  "decision": "ALLOW|DENY|ESCALATE_HUMAN|REPAIR",
  "safe_reason": "string",
  "updated_input": {},
  "lease_id": "lease_opaque_optional",
  "access_request_id": "request_optional"
}
```

For Claude Code, map this back to `hookSpecificOutput.permissionDecision`. For Codex, map it to Codex's supported `PreToolUse` JSON shape. If the host cannot safely rewrite or block the call, return a safe denial and rely on the gateway-only path.

## Failure Modes

- `op` CLI missing: provider unavailable; `DENY` direct secret resolution, or `ESCALATE_HUMAN` with setup guidance.
- 1Password MCP binary missing or feature disabled: Environment injection unavailable; use gateway-only tools or escalate setup.
- 1Password desktop app locked: `ESCALATE_HUMAN`; the user must approve or unlock.
- User cancels desktop approval: `ESCALATE_HUMAN`; do not retry in a loop.
- Service account token absent: SDK service-account mode unavailable; do not ask the agent for the token.
- Service account unauthorized for the vault/Environment: `DENY` or `ESCALATE_HUMAN` depending on whether policy allows repair.
- Broker cannot prove that output is scrubbed: `DENY`.
- Hook unavailable, untrusted, or skipped: do not permit direct secret access; route through the gateway or deny.

## Chosen Non-Secret Reference Shape

For fixtures and docs, use opaque IDs by default:

```text
credential_ref_id = credref_linear_sales
provider = onepassword
credential_class = linear.oauth_token
injection_mode = gateway_header
secret_ref_handle = broker-only opaque handle
```

When a real 1Password reference must be shown in setup-only docs, use a placeholder shape:

```text
op://ScopeMemory Demo/Linear API Token/token
```

This is a shape, not a verified vault, item, or field on Suraj's machine.

## Next Build Slice

1. Add a provider readiness check that reports only paths, versions, booleans, and setup-required reasons.
2. Add broker data types for provider mode, credential ref hash, lease ID, provider operation ID, and no-agent-exposure evidence.
3. Add a hook normalizer for Claude Code and Codex `PreToolUse`.
4. Add deny tests for direct `op read`, `op inject --out-file`, env printing, and MCP tool args containing secret-like fields.
5. Add execution wrappers only after readiness reports at least one real provider path.
