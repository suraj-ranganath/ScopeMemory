#!/usr/bin/env python3
"""MCP JSON-RPC demo — Priority 3 (RFC-03): JWT on tools/call."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from demo_auth import mint_token

BASE = "http://127.0.0.1:8080"
MCP = f"{BASE}/mcp"
SESSION = "sess_demo_001"
AGENT = "agent_renewal_01"
REQ_ID = 1


def mcp_call(
    method: str,
    params: dict | None = None,
    *,
    token: str | None = None,
    req_id: int | None = None,
) -> dict:
    body = {"jsonrpc": "2.0", "id": req_id if req_id is not None else REQ_ID, "method": method}
    if params is not None:
        body["params"] = params
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(MCP, data=data, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()}") from e


def assert_ok(label: str, cond: bool, detail: str = "") -> None:
    if not cond:
        raise AssertionError(f"{label}{': ' + detail if detail else ''}")
    print(f"  OK {label}")


def main() -> None:
    try:
        health = urllib.request.urlopen(f"{BASE}/health", timeout=10)
        health_data = json.loads(health.read().decode())
    except Exception as e:
        print(f"Gateway not reachable: {e}")
        sys.exit(1)

    print(f"mcp_endpoint={health_data.get('mcp_endpoint')} jwt_required={health_data.get('delegation_jwt_required')}")

    reseed = urllib.request.Request(
        f"{BASE}/admin/reseed", data=b"{}", method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(reseed, timeout=30):
        pass
    token = mint_token(BASE, SESSION)
    print("Delegation JWT minted")

    print("\n=== initialize ===")
    init = mcp_call("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "mcp-demo", "version": "0.1.0"},
    }, req_id=1)
    assert_ok("initialize", "result" in init and init["result"]["serverInfo"]["name"] == "scopememory-gateway")

    print("\n=== tools/list (session-scoped via JWT) ===")
    listed = mcp_call(
        "tools/list",
        {"_meta": {"session_id": SESSION, "agent_id": AGENT}},
        token=token,
        req_id=2,
    )
    names = [t["name"] for t in listed["result"]["tools"]]
    print(f"  tools: {names}")
    assert_ok("auth.preflight_goal in catalog", "auth.preflight_goal" in names)
    assert_ok("linear.create_issue in catalog", "linear.create_issue" in names)

    print("\n=== tools/call without JWT is rejected ===")
    denied = mcp_call(
        "tools/call",
        {
            "name": "auth.preflight_goal",
            "arguments": {"session_id": SESSION, "agent_id": AGENT},
        },
        req_id=3,
    )
    assert_ok("401 without JWT", denied.get("error", {}).get("code") == -32001)

    print("\n=== auth.preflight_goal (JWT) ===")
    pre = mcp_call(
        "tools/call",
        {
            "name": "auth.preflight_goal",
            "arguments": {"session_id": SESSION, "agent_id": AGENT},
        },
        token=token,
        req_id=4,
    )
    pre_text = pre["result"]["content"][0]["text"]
    pre_data = json.loads(pre_text)
    assert_ok("preflight recipe hits", len(pre_data.get("recipe_hits", [])) >= 1)

    print("\n=== linear.create_issue ALLOW (JWT) ===")
    allow = mcp_call(
        "tools/call",
        {
            "name": "linear.create_issue",
            "arguments": {
                "session_id": SESSION,
                "agent_id": AGENT,
                "resource_id": "linear_team:SALES",
                "title": "Acme renewal follow-up",
            },
        },
        token=token,
        req_id=5,
    )
    allow_payload = json.loads(allow["result"]["content"][0]["text"])
    assert_ok("linear ALLOW", allow_payload.get("decision") == "ALLOW")
    assert_ok("mock issue created", "issue_id" in allow_payload.get("execution", {}))

    print("\n=== slack.post_message DENY (JWT) ===")
    deny = mcp_call(
        "tools/call",
        {
            "name": "slack.post_message",
            "arguments": {
                "session_id": SESSION,
                "agent_id": AGENT,
                "resource_id": "slack_channel:external-partners",
                "text": "leaked notes",
            },
        },
        token=token,
        req_id=6,
    )
    assert_ok("slack DENY isError", deny["result"]["isError"] is True)
    deny_payload = json.loads(deny["result"]["content"][0]["text"])
    assert_ok("policy_denied", deny_payload.get("decision") == "DENY")

    print("\n=== slack.search_messages ESCALATE (JWT) ===")
    esc = mcp_call(
        "tools/call",
        {
            "name": "slack.search_messages",
            "arguments": {
                "session_id": SESSION,
                "agent_id": AGENT,
                "channel": "slack_channel:sales-acme",
            },
        },
        token=token,
        req_id=7,
    )
    esc_payload = json.loads(esc["result"]["content"][0]["text"])
    assert_ok("slack ESCALATE", esc_payload.get("decision") == "ESCALATE_HUMAN")

    print("\n" + "=" * 60)
    print("MCP DEMO PASSED")
    print("  JSON-RPC tools/call with delegation JWT + policy gate")
    print("=" * 60)


if __name__ == "__main__":
    main()
