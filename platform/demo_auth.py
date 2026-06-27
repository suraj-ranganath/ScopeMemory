"""Shared helpers for demo scripts — delegation JWT on /auth/* calls."""

from __future__ import annotations

import json
import urllib.request


def api_post(base: str, path: str, body: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}", data=data, method="POST", headers=headers,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def mint_token(base: str, session_id: str) -> str:
    out = api_post(base, "/iam/delegation-token", {"session_id": session_id})
    return out["delegation_token"]
