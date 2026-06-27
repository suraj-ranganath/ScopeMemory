# RFC-08: Agentic Identity Integration

## Status

**Implemented:** session delegation, identity proof, ReBAC tuples, **delegation JWT (P1)**, **IAM HTTP adapter (P2)**.

## Principle

> Agentic-IAM knows **who** the agent is. ScopeMemory decides **what** it may do — via ReBAC, not broad RBAC.

## Priority 1 — Delegation JWT

- Issued on `POST /iam/sessions` and `POST /iam/delegation-token`
- Required on `POST /auth/preflight` and `POST /auth/authorize` (configurable)
- Passed as `Authorization: Bearer` or JSON field `delegation_token`
- Verified against Dolt session + delegation record

## Priority 2 — IAM HTTP adapter

| `AGENTIC_IAM_MODE` | Source |
|--------------------|--------|
| `mock` | Dolt `agents` table |
| `http` | `GET {AGENTIC_IAM_URL}/agents/{id}` |

Built-in **`/mock-iam`** routes simulate external Agentic-IAM for local/docker demos.

## API summary

| Endpoint | Purpose |
|----------|---------|
| `GET /iam/agents/{id}` | Registry via adapter |
| `POST /iam/sessions` | Delegate + JWT |
| `POST /iam/delegation-token` | Mint JWT for existing session |
| `GET /iam/sessions/{id}/identity-proof` | ReBAC identity chain |
| `GET /mock-iam/agents/{id}` | Mock external IAM API |

## Acceptance

```bash
cd platform
docker compose --profile gateway-docker up -d --build
python3 run_agentic_identity_demo.py
python3 run_demo.py
python3 run_person_b_demo.py all
```

## Next (Priority 3+)

- MCP JSON-RPC gateway with JWT on `tools/call`
- RS256/JWKS from production Agentic-IAM
- Human approver OIDC
