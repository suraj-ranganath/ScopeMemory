# External Standards And Product Facts

## EXISTS

- MCP tools are exposed through `tools/list` and invoked through `tools/call`; each tool has a name, description, and input schema. This supports treating tool invocation as the exact authorization boundary.
  - Source: MCP tools spec, `https://modelcontextprotocol.io/specification/2025-11-25/server/tools`.
- MCP servers can signal tool-list changes. This supports narrowing and expanding an agent's visible tool catalog as grants change.
  - Source: MCP tools spec, `https://modelcontextprotocol.io/specification/2025-11-25/server/tools`.
- MCP authorization includes insufficient-scope behavior. ScopeMemory can enrich this with recipe-backed access requests and proof traces.
  - Source: MCP authorization spec, `https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization`.
- Claude Code supports hooks including `PreToolUse`. Hook output can block or steer calls before the tool executes, and MCP tool names can be matched as `mcp__<server>__<tool>`.
  - Source: Claude Code hooks docs, `https://code.claude.com/docs/en/hooks`.
- Codex supports hooks configured through `hooks.json` or inline config. `PreToolUse` can deny or rewrite supported Bash, file-edit, and MCP tool calls, but Codex describes hooks as guardrails rather than a complete enforcement boundary.
  - Source: OpenAI Codex hooks docs, `https://developers.openai.com/codex/hooks`.
- 1Password supports secret references and developer workflows intended to avoid hardcoding plaintext secrets into files.
  - Source: 1Password CLI secret references docs, `https://www.1password.dev/cli/secret-references`.
- 1Password MCP Server for Codex can manage 1Password Environments without returning secrets to the AI tool; runtime values are injected into an authorized application process.
  - Source: 1Password MCP Server docs, `https://www.1password.dev/environments/mcp-server`.
- 1Password SDKs support Go, JavaScript, and Python integrations with desktop-app auth or service-account auth.
  - Source: 1Password SDK docs, `https://www.1password.dev/sdks`.
- 1Password's local `.env` validation hook can validate mounted Environment files before supported agents run shell commands, but its default mode may fail open when it cannot access the 1Password database.
  - Source: 1Password agent hook docs, `https://www.1password.dev/environments/agent-hook-validate`.

## GAP

- There is no single portable "pre-tool-use hook" standard across every MCP client. The product must model hooks as adapters, not as the security root.
- 1Password MCP/Environment injection is the best fit for Codex local app runtime secrets, but it does not replace ScopeMemory policy decisions for downstream Slack/Linear tool authorization.
- 1Password's validation hook is setup assurance, not a credential broker. ScopeMemory must fail closed when provider readiness is unknown.
- Password-manager injection differs by tool transport:
  - HTTP APIs can be proxied by a gateway.
  - Stdio MCP servers need launch-time environment injection.
  - Shell commands need process-wrapper injection.
  - Long-lived local tools may need a sidecar or local socket.

## PROPOSAL

ScopeMemory should standardize around its own credential lease protocol. Client hooks, MCP gateway calls, CLI wrappers, and stdio server launchers all become adapters into that same protocol.

```text
Tool call intent
  -> normalize
  -> policy facts
  -> decision
  -> optional credential lease
  -> execution adapter
  -> audit proof
```

This keeps MCP, Claude hooks, 1Password, and future clients cohesive without making any one of them the whole system.
