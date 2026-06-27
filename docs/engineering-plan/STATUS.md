# ScopeMemory Plan Status

## Current Phase

**RFC-07 — 2-hour Agentic Identity demo.** Runnable scaffold in `demo/`.

## Route

`DEMO_FIRST` — simplified from `HIGH_END` planning phase.

Reason: full RFC-00 through RFC-06 cannot be built correctly in 2 hours. RFC-07 defines a binding subset with working code.

## Verification

Completed:

- Full engineering plan package (RFC-00 through RFC-06)
- RFC-07 2-hour demo spec
- Runnable demo: `demo/schema.sql`, `demo/rebac.py`, `demo/run_demo.py`

Pending:

- Run `python demo/run_demo.py all` on target machine
- Phase 2 implementation authorization

## What Changed

| Before | After |
|--------|-------|
| 40-hour MVP as first build | 2-hour SQLite ReBAC demo first |
| 24 Dolt tables required day 1 | 11 SQLite tables in `demo/` |
| CozoDB + 1Password + Qdrant + MCP | Deferred to RFC-06 Phase 2 |
| 7 UI screens | Terminal JSON proof output |

## Next Step

```bash
cd demo && python run_demo.py all
```

Then extend per RFC-06 Phase 2 work packages.
