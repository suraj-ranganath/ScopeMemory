# ScopeMemory Ground-Truth Ledger

## Verified Facts

- `README.md` names the project as `ScopeMemory: Memory-Informed Authorization for MCP Agents`. Source: `README.md:1-3`.
- `INITIAL_ROUGH_PLAN.md` frames the project as memory-informed authorization, not tribal-knowledge RAG. Source: `INITIAL_ROUGH_PLAN.md:1-7`.
- The rough plan proposes Dolt as canonical governed state for recipes, grants, approvals, policies, and audit events. Source: `INITIAL_ROUGH_PLAN.md:14-15`.
- The rough plan proposes Qdrant as the semantic/hybrid retrieval index over workflow authorization recipes. Source: `INITIAL_ROUGH_PLAN.md:17-18`.
- The rough plan proposes a Datalog engine as the deterministic allow/deny/auto-approve/escalate authority. Source: `INITIAL_ROUGH_PLAN.md:20-21`, `INITIAL_ROUGH_PLAN.md:566-572`.
- The rough plan proposes an MCP gateway that intercepts Linear, Slack, GitHub, and other tool calls. Source: `INITIAL_ROUGH_PLAN.md:23-24`, `INITIAL_ROUGH_PLAN.md:1114-1150`.
- The rough plan explicitly says Qdrant should not be source of truth, LLM judges should not be final authority, and raw Slack/Linear tokens should not be given to the agent. Source: `INITIAL_ROUGH_PLAN.md:116-118`.
- The rough plan's core session flow has preflight authorization followed by inline MCP enforcement. Source: `INITIAL_ROUGH_PLAN.md:277-380`.
- The rough plan's decision states are `ALLOW`, `AUTO_APPROVE_EPHEMERAL_GRANT`, `ESCALATE_HUMAN`, `DENY`, and `REPAIR`. Source: `INITIAL_ROUGH_PLAN.md:388-410`.
- The rough plan's Dolt schema includes users, teams, MCP servers/tools, tool-required scopes, recipes, recipe evidence, sessions, events, access requests, grants, and policy decisions. Source: `INITIAL_ROUGH_PLAN.md:579-726`.
- The rough plan's Qdrant strategy indexes accepted recipes for retrieval, uses payload filters, and supports embedding migration through blue-green collections. Source: `INITIAL_ROUGH_PLAN.md:763-916`.
- The rough plan states the agent should never receive raw OAuth tokens and the gateway should attach credentials only at execution time. Source: `INITIAL_ROUGH_PLAN.md:993-1029`.
- The rough plan uses three LLM judge roles: recipe proposal, access request fact emission, and audit summarization. Source: `INITIAL_ROUGH_PLAN.md:1029-1110`.
- The rough plan includes a prompt-injection defense: tool outputs are untrusted observations and cannot change the signed session goal, create grants, or change recipe match. Source: `INITIAL_ROUGH_PLAN.md:1798-1833`.
- The rough plan's MVP includes Dolt schema, Qdrant recipe retrieval, MCP-ish gateway, policy engine, access request UI, proof timeline, and recipe proposal diff. Source: `INITIAL_ROUGH_PLAN.md:1838-1876`.
- MCP tools are schema-described external actions with `tools/list`, `tools/call`, `inputSchema`, and tool-list change notifications. Source: MCP tools spec, `https://modelcontextprotocol.io/specification/2025-11-25/server/tools`.
- MCP authorization includes insufficient-scope behavior that can be represented as richer ScopeMemory access requests. Source: MCP authorization spec, `https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization`.
- Claude Code hooks include `PreToolUse`, hook input, and optional output that can block or modify tool input. Source: Anthropic Claude Code hooks docs, `https://docs.anthropic.com/en/docs/claude-code/hooks`.
- 1Password secret references use `op://vault/item/field` style references and can be resolved by CLI flows without putting raw secrets in project files. Source: 1Password CLI secret references docs, `https://www.1password.dev/cli/secret-references`.
- 1Password environments can load secrets into processes through local `.env` workflows and developer tools without storing plaintext in the repo. Source: 1Password developer docs, `https://www.1password.dev/`.

## Canonical Conflict Resolutions

- **Rough plan token vault versus zero knowledge:** The rough plan says "gateway-held token vault." The canonical plan refines this to a credential broker with opaque leases. The gateway may execute with credentials, but ScopeMemory state stores only secret references, hashes, metadata, and lease IDs. Decrypted secrets are never stored in Dolt, Qdrant, logs, UI, or agent-visible inputs.
- **Datalog engine choice:** The rough plan names CozoDB or Crepe. Owner selected CozoDB for the initial policy engine on 2026-06-27.
- **Hooks as injection mechanism:** The user requested pre-tool-use hooks for password manager credentials. The canonical plan uses hooks to enforce, block, rewrite, or route calls, not to paste decrypted secrets into tool arguments.
- **Hackathon schedule versus engineering spec:** The rough plan includes a 40-hour build schedule. The canonical plan preserves it as an MVP sequence but separates architecture, data model, runtime, credential broker, learning, and demo plan.

## EXISTS / CHANGE / NEW Ledger

### EXISTS

- Existing rough plan with the project thesis, architecture, data schema, gateway, policy, UI, audit, and demo concept.
- Existing Git repo with README and Beads initialized.
- SR Code planning workflow and package checker.

### CHANGE

- Refine "token handling" into a zero-secret-exposure credential broker.
- Move 1Password/password-manager integration from an add-on to a core part of the gateway, policy, audit, and data model.
- Separate authorization memory from credential material.
- Turn one rough implementation schedule into canonical subsystem RFCs and an explicit MVP line.

### NEW

- Credential provider registry.
- Secret reference metadata table.
- Credential binding table.
- Credential lease table.
- Credential broker service.
- Hook adapter for `PreToolUse`-style clients.
- Launch-time injection mode for stdio MCP servers.
- Shell command wrapper mode for CLI tools.
- Opaque grant/lease model that connects policy decisions to password-manager retrieval.

## Unverified Claims

- The exact 1Password vault/item structure for the live MVP credential demo.
- The exact mocked Slack data set and malicious prompt-injection fixture.
- Whether the final product will support true cryptographic zero-knowledge proofs beyond zero secret exposure to agents and persistence.
