# External Standards And Product Facts

## EXISTS

- MCP tools are exposed through `tools/list` and invoked through `tools/call`; each tool has a name, description, and input schema. This supports treating tool invocation as the exact authorization boundary.
  - Source: MCP tools spec, `https://modelcontextprotocol.io/specification/2025-11-25/server/tools`.
- MCP servers can signal tool-list changes. This supports narrowing and expanding an agent's visible tool catalog as grants change.
  - Source: MCP tools spec, `https://modelcontextprotocol.io/specification/2025-11-25/server/tools`.
- MCP authorization includes insufficient-scope behavior. ScopeMemory can enrich this with recipe-backed access requests and proof traces.
  - Source: MCP authorization spec, `https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization`.
- Claude Code supports hooks including `PreToolUse`. Hook output can block or steer calls before the tool executes.
  - Source: Anthropic Claude Code hooks docs, `https://docs.anthropic.com/en/docs/claude-code/hooks`.
- 1Password supports secret references and developer workflows intended to avoid hardcoding plaintext secrets into files.
  - Source: 1Password CLI secret references docs, `https://www.1password.dev/cli/secret-references`.
- 1Password developer tooling includes environments and secret-management flows for local development.
  - Source: 1Password developer docs, `https://www.1password.dev/`.

## GAP

- There is no single portable "pre-tool-use hook" standard across every MCP client. The product must model hooks as adapters, not as the security root.
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
