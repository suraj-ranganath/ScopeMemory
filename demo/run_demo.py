#!/usr/bin/env python3
"""ScopeMemory 2-hour Agentic Identity demo — run all scenes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rebac import DB_PATH, authorize, init_db, preflight, seed_demo


def _print(title: str, payload: dict) -> None:
    print(f"\n{'=' * 60}")
    print(title)
    print("=" * 60)
    print(json.dumps(payload, indent=2))


def cmd_init() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    init_db()
    seed_demo()
    print(f"Initialized {DB_PATH}")


def cmd_preflight() -> None:
    result = preflight("sess_demo_001")
    _print("SCENE 2 — Preflight (Agentic Identity + memory match)", result)


def cmd_authorize(tool: str, resource: str) -> None:
    d = authorize("sess_demo_001", tool, resource)
    _print(f"Authorize {tool} @ {resource}", {
        "decision": d.decision,
        "reason": d.reason,
        "context_path": d.context_path,
        "rebac_tuples": d.rebac_tuples,
        "facts": d.facts,
    })
    if d.decision == "DENY" and "all" not in sys.argv:
        sys.exit(1)


def cmd_all() -> None:
    cmd_init()

    print("\n>>> SCENE 1 — Agent registered in Agentic-IAM (mirrored in agents table)")
    print("    agent_renewal_01 | identity_ref: agentic-iam://uuid-renewal-bot | trust: 0.92")
    print("    Alice delegates RenewalBot for sess_demo_001")

    cmd_preflight()

    print("\n>>> SCENE 3 — ALLOW (ReBAC path justifies access)")
    d_allow = authorize("sess_demo_001", "linear.create_issue", "linear_team:SALES")
    _print("SCENE 3 — ALLOW", {
        "decision": d_allow.decision,
        "reason": d_allow.reason,
        "context_path": d_allow.context_path,
        "rebac_tuples": d_allow.rebac_tuples,
    })
    assert d_allow.decision == "ALLOW", f"expected ALLOW, got {d_allow.decision}"

    print("\n>>> SCENE 4 — DENY (RBAC role would over-permit; ReBAC does not)")
    d_deny = authorize("sess_demo_001", "slack.post_message", "slack_channel:external-partners")
    _print("SCENE 4 — DENY", {
        "decision": d_deny.decision,
        "reason": d_deny.reason,
        "context_path": d_deny.context_path,
        "rebac_tuples": d_deny.rebac_tuples,
    })
    assert d_deny.decision == "DENY", f"expected DENY, got {d_deny.decision}"

    print("\n>>> SCENE 5 — ESCALATE (predicted but needs human)")
    d_esc = authorize("sess_demo_001", "slack.search_messages", "slack_channel:sales-acme")
    _print("SCENE 5 — ESCALATE_HUMAN", {
        "decision": d_esc.decision,
        "reason": d_esc.reason,
        "context_path": d_esc.context_path,
    })
    assert d_esc.decision == "ESCALATE_HUMAN", f"expected ESCALATE_HUMAN, got {d_esc.decision}"

    print("\n" + "=" * 60)
    print("DEMO PASSED — Agentic Identity + ReBAC context path")
    print("=" * 60)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python run_demo.py [init|preflight|authorize|all]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        cmd_init()
    elif cmd == "preflight":
        cmd_preflight()
    elif cmd == "authorize":
        if len(sys.argv) < 4:
            print("Usage: python run_demo.py authorize <tool_id> <resource_id>")
            sys.exit(1)
        cmd_authorize(sys.argv[2], sys.argv[3])
    elif cmd == "all":
        cmd_all()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
