#!/usr/bin/env python3
"""End-to-end demo for Dolt → Memgraph → CozoDB gateway stack."""

from __future__ import annotations

import json
import sys
import time

import httpx

BASE = "http://127.0.0.1:8080"


def wait_health(timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE}/health", timeout=2)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit("Gateway not healthy — run ./run_stack.sh first")


def main() -> None:
    wait_health()
    client = httpx.Client(base_url=BASE, timeout=30)

    print("\n=== Agentic-IAM identity lookup ===")
    iam = client.get("/iam/agents/agent_renewal_01").json()
    print(json.dumps(iam, indent=2))

    print("\n=== Preflight (Dolt truth → Memgraph query) ===")
    pre = client.post("/auth/preflight", json={
        "session_id": "sess_demo_001",
        "agent_id": "agent_renewal_01",
    }).json()
    print(json.dumps(pre, indent=2))

    print("\n=== ALLOW: linear.create_issue ===")
    allow = client.post("/auth/authorize", json={
        "session_id": "sess_demo_001",
        "agent_id": "agent_renewal_01",
        "tool_id": "linear.create_issue",
        "resource_id": "linear_team:SALES",
    }).json()
    print(json.dumps(allow, indent=2))
    assert allow["decision"] == "ALLOW", allow

    print("\n=== DENY: external slack post ===")
    deny = client.post("/auth/authorize", json={
        "session_id": "sess_demo_001",
        "agent_id": "agent_renewal_01",
        "tool_id": "slack.post_message",
        "resource_id": "slack_channel:external-partners",
    }).json()
    print(json.dumps(deny, indent=2))
    assert deny["decision"] == "DENY", deny

    print("\n=== ESCALATE: slack search ===")
    esc = client.post("/auth/authorize", json={
        "session_id": "sess_demo_001",
        "agent_id": "agent_renewal_01",
        "tool_id": "slack.search_messages",
        "resource_id": "slack_channel:sales-acme",
    }).json()
    print(json.dumps(esc, indent=2))
    assert esc["decision"] == "ESCALATE_HUMAN", esc

    print("\n=== Audit trail in Dolt ===")
    proof = client.get("/auth/proof/sess_demo_001").json()
    print(f"policy_decisions stored: {len(proof['decisions'])}")

    print("\n" + "=" * 60)
    print("STACK DEMO PASSED")
    print("  Agentic-IAM → Gateway → Dolt + Memgraph → CozoDB")
    print("=" * 60)


if __name__ == "__main__":
    main()
