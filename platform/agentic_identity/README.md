# Agentic Identity (RFC-08)

ScopeMemory implements **authorization memory**; Agentic-IAM owns **agent identity**.

## Priorities implemented

### Priority 1 — Signed delegation JWT

Every `/auth/preflight` and `/auth/authorize` call requires a valid delegation token unless `DELEGATION_JWT_REQUIRED=false`.

**Obtain token:**

```bash
# New session (returns delegation_token)
curl -X POST http://127.0.0.1:8080/iam/sessions -H 'Content-Type: application/json' -d '{
  "user_id":"user_alice","agent_id":"agent_renewal_01","team_id":"team_sales",
  "goal":"Acme renewal","goal_class":"sales_renewal_prep"
}'

# Existing session (after reseed)
curl -X POST http://127.0.0.1:8080/iam/delegation-token -H 'Content-Type: application/json' \
  -d '{"session_id":"sess_demo_001"}'
```

**Use token:**

```bash
curl -X POST http://127.0.0.1:8080/auth/preflight \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"sess_demo_001","agent_id":"agent_renewal_01"}'
```

JWT claims: `session_id`, `user_id`, `agent_id`, `team_id`, `identity_ref`, `trust_score`, `exp`.

Env: `DELEGATION_JWT_SECRET`, `DELEGATION_JWT_TTL_SECONDS`, `DELEGATION_JWT_ISSUER`, `DELEGATION_JWT_AUDIENCE`.

### Priority 2 — Live IAM HTTP adapter

| Mode | Env | Behavior |
|------|-----|----------|
| `mock` | `AGENTIC_IAM_MODE=mock` | Read agents from Dolt mirror (default) |
| `http` | `AGENTIC_IAM_MODE=http` + `AGENTIC_IAM_URL` | `GET {URL}/agents/{id}` |

Docker stack uses **http** mode pointing at built-in **`/mock-iam`** (simulates external Agentic-IAM).

```bash
curl http://127.0.0.1:8080/mock-iam/agents/agent_renewal_01
curl http://127.0.0.1:8080/iam/agents/agent_renewal_01   # via adapter
```

For production, set `AGENTIC_IAM_URL=https://your-agentic-iam.example/api/v1`.

Optional: `AGENTIC_IAM_API_KEY` sent as `Authorization: Bearer`.

## Module layout

```
agentic_identity/
  delegation_jwt.py   # issue + verify JWT
  iam_client.py       # mock vs HTTP adapter
  auth.py             # gateway delegation verification
  service.py          # sessions + proofs
  tuples.py           # ReBAC tuple builders
```

## Demo

```bash
python3 run_agentic_identity_demo.py
```

## Next

- Streamable HTTP / SSE MCP transport
- Real downstream MCP proxy (RFC-04 credential broker)
- RS256 / JWKS from real Agentic-IAM
