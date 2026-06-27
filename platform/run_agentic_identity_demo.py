#!/usr/bin/env python3
"""Agentic Identity demo — JWT delegation + IAM adapter (Priorities 1 & 2)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from demo_auth import api_post, mint_token

BASE = "http://127.0.0.1:8080"
SESSION = "sess_demo_001"
AGENT = "agent_renewal_01"


def req(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{BASE}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        raise RuntimeError(f"HTTP {e.code} {path}: {detail}") from e


def main() -> None:
    try:
        health = req("GET", "/health")
    except Exception as e:
        print(f"Gateway not reachable: {e}")
        sys.exit(1)

    print(f"iam_mode={health.get('iam_mode')} jwt_required={health.get('delegation_jwt_required')}")
    req("POST", "/admin/reseed")

    print("\n=== P2: IAM registry (adapter) ===")
    agent = req("GET", f"/iam/agents/{AGENT}")
    print(json.dumps(agent, indent=2))
    assert agent["identity_ref"].startswith("agentic-iam://")
    print(f"  OK source={agent.get('source')}")

    if health.get("iam_mode") == "http":
        mock = req("GET", f"/mock-iam/agents/{AGENT}")
        assert mock["agent_id"] == AGENT
        print("  OK live HTTP adapter → /mock-iam/agents")

    print("\n=== P1: Auth without JWT is rejected ===")
    try:
        req("POST", "/auth/preflight", {"session_id": SESSION, "agent_id": AGENT})
        raise SystemExit("expected 401 without delegation JWT")
    except RuntimeError as e:
        assert "401" in str(e), e
        print("  OK 401 without token")

    print("\n=== Scene: Alice delegates RenewalBot (new session + JWT) ===")
    created = req("POST", "/iam/sessions", {
        "user_id": "user_alice",
        "agent_id": AGENT,
        "team_id": "team_sales",
        "goal": "Prepare renewal follow-up for Acme. Create a Linear issue.",
        "goal_class": "sales_renewal_prep",
    })
    sid = created["session"]["session_id"]
    token = created["delegation_token"]
    print(f"  session_id={sid} jwt_len={len(token)}")

    print("\n=== Identity proof ===")
    proof = req("GET", f"/iam/sessions/{sid}/identity-proof")
    assert proof["delegation_present"]
    assert any("delegates" in t for t in proof["rebac_tuples"])

    print("\n=== Preflight with Bearer JWT ===")
    pre = api_post(BASE, "/auth/preflight", {"session_id": sid, "agent_id": AGENT}, token=token)
    assert pre["delegation_jwt"]["verified"]
    print(f"  OK verified user={pre['delegation_jwt']['user_id']}")

    print("\n=== ALLOW linear.create_issue (JWT) ===")
    allow = api_post(BASE, "/auth/authorize", {
        "session_id": sid, "agent_id": AGENT,
        "tool_id": "linear.create_issue", "resource_id": "linear_team:SALES",
    }, token=token)
    assert allow["decision"] == "ALLOW"
    assert allow["proof"]["delegation_jwt"]["verified"]
    print(f"  OK {allow['decision']}")

    print("\n=== DENY external Slack ===")
    deny = api_post(BASE, "/auth/authorize", {
        "session_id": sid, "agent_id": AGENT,
        "tool_id": "slack.post_message", "resource_id": "slack_channel:external-partners",
    }, token=token)
    assert deny["decision"] == "DENY"
    print(f"  OK {deny['decision']}")

    print("\n=== ESCALATE Slack read ===")
    esc = api_post(BASE, "/auth/authorize", {
        "session_id": sid, "agent_id": AGENT,
        "tool_id": "slack.search_messages", "resource_id": "slack_channel:sales-acme",
    }, token=token)
    assert esc["decision"] == "ESCALATE_HUMAN"
    print(f"  OK {esc['decision']}")

    print("\n=== Mint JWT for seeded session ===")
    seed_token = mint_token(BASE, SESSION)
    pre2 = api_post(BASE, "/auth/preflight", {"session_id": SESSION, "agent_id": AGENT}, token=seed_token)
    assert pre2["delegation_jwt"]["verified"]
    print("  OK reseed session accepts minted JWT")

    print("\n" + "=" * 60)
    print("AGENTIC IDENTITY DEMO PASSED")
    print("  P1 JWT delegation + P2 IAM adapter on /auth/*")
    print("=" * 60)


if __name__ == "__main__":
    main()
