# ScopeMemory Plan Status

## Current Phase

**Platform demo + Agentic Identity integration (RFC-08).**

Runnable stacks:

- `demo/` — SQLite RFC-07 (2-hour story)
- `platform/` — Dolt + Memgraph + Gateway + Person B UI + Agentic Identity APIs

## Verification

```bash
cd demo && python3 run_demo.py all
cd platform && python3 run_agentic_identity_demo.py
cd platform && python3 run_person_b_demo.py all
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

1. Run `python3 platform/run_agentic_identity_demo.py`
2. Signed delegation tokens + live Agentic-IAM HTTP adapter
3. MCP JSON-RPC gateway (RFC-03)
