#!/usr/bin/env python3
"""Stdio MCP bridge for Codex -> ScopeMemory Gateway.

Codex launches this as a local MCP server. The bridge mints a session-scoped
delegation token and proxies MCP JSON-RPC messages to the HTTP gateway.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


GATEWAY_URL = os.getenv("SCOPEMEMORY_GATEWAY_URL", "http://127.0.0.1:8080").rstrip("/")
SESSION_ID = os.getenv("SCOPEMEMORY_SESSION_ID", "sess_demo_001")
AGENT_ID = os.getenv("SCOPEMEMORY_AGENT_ID", "agent_renewal_01")


def main() -> None:
    while True:
        message = _read_message()
        if message is None:
            return
        try:
            response = _handle(message)
        except Exception as exc:
            response = _jsonrpc_error(message.get("id") if isinstance(message, dict) else None, -32603, str(exc))
        if response is not None:
            _write_message(response)


def _handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _proxy_mcp(_with_session_meta(message), token=_delegation_token())
    if method == "tools/call":
        return _proxy_mcp(_with_default_arguments(message), token=_delegation_token())
    return _proxy_mcp(message)


def _with_session_meta(message: dict[str, Any]) -> dict[str, Any]:
    out = dict(message)
    params = dict(out.get("params") or {})
    meta = dict(params.get("_meta") or {})
    meta.setdefault("session_id", SESSION_ID)
    meta.setdefault("agent_id", AGENT_ID)
    params["_meta"] = meta
    out["params"] = params
    return out


def _with_default_arguments(message: dict[str, Any]) -> dict[str, Any]:
    out = dict(message)
    params = dict(out.get("params") or {})
    args = dict(params.get("arguments") or {})
    args.setdefault("session_id", SESSION_ID)
    args.setdefault("agent_id", AGENT_ID)
    params["arguments"] = args
    out["params"] = params
    return out


def _delegation_token() -> str:
    payload = _http_json("/iam/delegation-token", {"session_id": SESSION_ID})
    return str(payload["delegation_token"])


def _proxy_mcp(message: dict[str, Any], token: str = "") -> dict[str, Any]:
    return _http_json("/mcp", message, token=token)


def _http_json(path: str, body: dict[str, Any], token: str = "") -> dict[str, Any]:
    data = json.dumps(body).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{GATEWAY_URL}{path}", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"ScopeMemory HTTP {exc.code}: {detail}") from exc


def _read_message() -> dict[str, Any] | None:
    stream = sys.stdin.buffer
    while True:
        first = stream.readline()
        if first == b"":
            return None
        if first.strip():
            break
    if first.lstrip().startswith(b"{"):
        return json.loads(first.decode())

    headers: dict[str, str] = {}
    line = first
    while line.strip():
        key, _, value = line.decode(errors="replace").partition(":")
        headers[key.strip().lower()] = value.strip()
        line = stream.readline()
        if line == b"":
            return None
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        raise ValueError("missing Content-Length")
    return json.loads(stream.read(length).decode())


def _write_message(message: dict[str, Any]) -> None:
    payload = json.dumps(message, separators=(",", ":")).encode()
    sys.stdout.buffer.write(f"Content-Length: {len(payload)}\r\n\r\n".encode())
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def _jsonrpc_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


if __name__ == "__main__":
    main()
