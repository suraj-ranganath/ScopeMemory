# MCP Gateway (RFC-03 Priority 3)

ScopeMemory exposes a **meta-MCP server** at `POST /mcp` (JSON-RPC 2.0 over HTTP).

## Methods

| Method | JWT required | Purpose |
|--------|--------------|---------|
| `initialize` | No | MCP handshake |
| `tools/list` | Optional | Catalog; session-filtered when `_meta.session_id` + Bearer JWT |
| `tools/call` | **Yes** | Preflight, authorize, mock downstream execution |

## Auth tools

- `auth.preflight_goal` — recipe hits + ReBAC context (wraps `/auth/preflight`)
- `auth.show_decision_proof` — audit trail from Dolt

## Downstream tools (policy-gated)

- `linear.create_issue`
- `slack.search_messages`
- `slack.post_message`

Every `tools/call` requires:

```http
Authorization: Bearer <delegation_jwt>
```

Arguments must include `session_id` and `agent_id` matching the JWT.

## Example

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8080/iam/delegation-token \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"sess_demo_001"}' | jq -r .delegation_token)

curl -s -X POST http://127.0.0.1:8080/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0","id":1,"method":"tools/call",
    "params":{
      "name":"linear.create_issue",
      "arguments":{
        "session_id":"sess_demo_001",
        "agent_id":"agent_renewal_01",
        "resource_id":"linear_team:SALES",
        "title":"Acme renewal"
      }
    }
  }'
```

## Demo

```bash
python3 run_mcp_demo.py
```

## Next

- Streamable HTTP / SSE transport
- Real downstream MCP proxy (not mock)
- Credential broker injection on ALLOW
