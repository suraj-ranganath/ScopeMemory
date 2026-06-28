#!/usr/bin/env python3
"""Codex PreToolUse hook adapter for ScopeMemory."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

from hook_adapter import codex_pre_tool_use_output, evaluate_hook_intent, normalize_pre_tool_use


GATEWAY_URL = os.getenv("SCOPEMEMORY_GATEWAY_URL", "http://127.0.0.1:8080").rstrip("/")
SESSION_ID = os.getenv("SCOPEMEMORY_SESSION_ID", "sess_demo_001")


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    payload.setdefault("session_id", SESSION_ID)

    local_intent = normalize_pre_tool_use("codex", payload)
    local_decision = evaluate_hook_intent(local_intent)
    local_output = codex_pre_tool_use_output(local_decision)

    try:
        output = _post_hook(payload)
    except Exception:
        output = local_output

    print(json.dumps(output, separators=(",", ":")))


def _post_hook(payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{GATEWAY_URL}/codex/hooks/pre-tool-use",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"ScopeMemory hook HTTP {exc.code}: {detail}") from exc


if __name__ == "__main__":
    main()
