#!/usr/bin/env python3
"""End-to-end demo for Dolt → Memgraph → Gateway stack (stdlib only — no pip deps on host)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8080"


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {e.code} {path}: {detail}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"Cannot reach gateway at {BASE}: {e.reason}") from e


def wait_health(timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            _request("GET", "/health")
            return
        except SystemExit:
            pass
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit("Gateway not healthy — run: docker compose --profile gateway-docker up -d")


def main() -> None:
    wait_health()
    reseed = _request("POST", "/admin/reseed")
    print(f"Demo reseeded ({reseed.get('graph_engine')}, {reseed.get('synced_rows')} rows)")

    print("\n=== Agentic-IAM identity lookup ===")
    iam = _request("GET", "/iam/agents/agent_renewal_01")
    print(json.dumps(iam, indent=2))

    print("\n=== Preflight (Dolt truth → graph query) ===")
    pre = _request("POST", "/auth/preflight", {
        "session_id": "sess_demo_001",
        "agent_id": "agent_renewal_01",
    })
    print(json.dumps(pre, indent=2))

    print("\n=== ALLOW: linear.create_issue ===")
    allow = _request("POST", "/auth/authorize", {
        "session_id": "sess_demo_001",
        "agent_id": "agent_renewal_01",
        "tool_id": "linear.create_issue",
        "resource_id": "linear_team:SALES",
    })
    print(json.dumps(allow, indent=2))
    assert allow["decision"] == "ALLOW", allow

    print("\n=== DENY: external slack post ===")
    deny = _request("POST", "/auth/authorize", {
        "session_id": "sess_demo_001",
        "agent_id": "agent_renewal_01",
        "tool_id": "slack.post_message",
        "resource_id": "slack_channel:external-partners",
    })
    print(json.dumps(deny, indent=2))
    assert deny["decision"] == "DENY", deny

    print("\n=== ESCALATE: slack search ===")
    esc = _request("POST", "/auth/authorize", {
        "session_id": "sess_demo_001",
        "agent_id": "agent_renewal_01",
        "tool_id": "slack.search_messages",
        "resource_id": "slack_channel:sales-acme",
    })
    print(json.dumps(esc, indent=2))
    assert esc["decision"] == "ESCALATE_HUMAN", esc

    print("\n=== Audit trail in Dolt ===")
    proof = _request("GET", "/auth/proof/sess_demo_001")
    print(f"policy_decisions stored: {len(proof['decisions'])}")

    print("\n" + "=" * 60)
    print("STACK DEMO PASSED")
    print("  Agentic-IAM → Gateway → Dolt + Graph → Policy")
    print("=" * 60)


if __name__ == "__main__":
    main()
