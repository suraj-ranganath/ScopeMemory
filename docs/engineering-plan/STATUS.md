# ScopeMemory Plan Status

## Current Phase

**Platform demo + Agentic Identity (RFC-08) + MCP gateway (RFC-03).**

Runnable stacks:

- `demo/` — SQLite RFC-07 (2-hour story)
- `platform/` — Dolt + Memgraph + Gateway + MCP JSON-RPC + Person B UI

## Verification

```bash
cd demo && python3 run_demo.py all
cd platform && python3 run_agentic_identity_demo.py
cd platform && python3 run_person_b_demo.py all
cd platform && python3 run_mcp_demo.py
```

## Route

`DEMO_FIRST` → `PLATFORM` → `AGENTIC_IDENTITY` → full RFC-06 Phase 2 (MCP, broker, production hardening)

## What Changed

| Before | After |
|--------|-------|
| Seeded delegation only | `POST /iam/sessions` creates delegation |
| Partial identity in preflight | Full `rebac_tuples` + identity proof endpoint |
| Trust score gate at IAM only | Trust score in policy facts |
| Qdrant (planned) | Memgraph derived graph for recipes + ReBAC |

## Next Step

1. Run `python3 platform/run_mcp_demo.py`
2. Credential broker + 1Password (RFC-04)
3. Production hardening (approver auth, CI, RS256/JWKS)
