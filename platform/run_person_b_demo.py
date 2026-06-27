#!/usr/bin/env python3
"""Person B demo harness — happy, approval, denial, learning paths (RFC-06)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from demo_auth import api_post, mint_token

BASE = "http://127.0.0.1:8080"
SESSION = "sess_demo_001"
AGENT = "agent_renewal_01"

_TOKEN: str | None = None


def _token() -> str:
    global _TOKEN
    if _TOKEN is None:
        _TOKEN = mint_token(BASE, SESSION)
    return _TOKEN


def req(method: str, path: str, body: dict | None = None) -> dict:
    if method == "POST" and path.startswith("/auth/"):
        assert body is not None
        return api_post(BASE, path, body, token=_token())
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(r, timeout=30) as resp:
        return json.loads(resp.read().decode())


def assert_eq(label: str, got, expected) -> None:
    if got != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {got!r}")
    print(f"  OK {label}: {got}")


def path_happy() -> None:
    print("\n=== Path 1: Happy (Linear auto-approve) ===")
    pre = req("POST", "/auth/preflight", {"session_id": SESSION, "agent_id": AGENT})
    assert_eq("recipe hits", len(pre.get("recipe_hits", [])), 1)
    auth = req("POST", "/auth/authorize", {
        "session_id": SESSION, "agent_id": AGENT,
        "tool_id": "linear.create_issue", "resource_id": "linear_team:SALES",
    })
    assert_eq("linear decision", auth["decision"], "ALLOW")


def path_approval() -> None:
    print("\n=== Path 2: Approval (Slack escalate → Bob approves) ===")
    auth = req("POST", "/auth/authorize", {
        "session_id": SESSION, "agent_id": AGENT,
        "tool_id": "slack.search_messages", "resource_id": "slack_channel:sales-acme",
    })
    assert_eq("slack decision", auth["decision"], "ESCALATE_HUMAN")
    state = req("GET", f"/demo/ui-state/{SESSION}")
    pending = [r for r in state["access_requests"] if r["status"] == "pending"]
    if pending:
        approved = req("POST", f"/demo/access-requests/{pending[0]['request_id']}/approve", {"approver_id": "user_bob"})
        assert_eq("approved", approved["status"], "approved")


def path_denial() -> None:
    print("\n=== Path 3: Denial (prompt-injection external post) ===")
    slack = req("GET", "/demo/slack/search?channel=slack_channel:sales-acme")
    assert slack.get("prompt_injection"), "expected prompt injection fixture"
    auth = req("POST", "/auth/authorize", {
        "session_id": SESSION, "agent_id": AGENT,
        "tool_id": "slack.post_message", "resource_id": "slack_channel:external-partners",
    })
    assert_eq("external post", auth["decision"], "DENY")


def path_learning() -> None:
    print("\n=== Path 4: Learning (graph index + recipe proposal v4) ===")
    idx = req("POST", "/index/recipes")
    print(f"  OK graph index ({idx.get('graph_engine')}): {idx.get('indexed')}")
    proposal = req("POST", f"/demo/recipes/propose?session_id={SESSION}")
    assert proposal.get("should_propose_recipe") is True
    print(f"  OK proposal: {proposal['proposal_id']}")


def main() -> None:
    paths = sys.argv[1:] or ["happy", "approval", "denial", "learning"]
    try:
        req("GET", "/health")
    except Exception as e:
        print(f"Gateway not reachable at {BASE}: {e}")
        sys.exit(1)

    reseed = req("POST", "/admin/reseed")
    print(f"Demo reseeded ({reseed.get('graph_engine')}, {reseed.get('synced_rows')} rows)")
    global _TOKEN
    _TOKEN = mint_token(BASE, SESSION)
    print("Delegation JWT minted")

    if "all" in paths or not paths:
        path_happy()
        path_approval()
        path_denial()
        path_learning()
    else:
        for p in paths:
            {"happy": path_happy, "approval": path_approval, "denial": path_denial, "learning": path_learning}[p]()

    print("\nPERSON B DEMO PASSED")


if __name__ == "__main__":
    main()
