"""JSON-RPC 2.0 helpers for MCP over HTTP."""

from __future__ import annotations

from typing import Any

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "scopememory-gateway"
SERVER_VERSION = "0.1.0"

JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603
MCP_AUTH_REQUIRED = -32001
MCP_POLICY_DENIED = -32002


def jsonrpc_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def jsonrpc_error(req_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def tool_result_text(payload: Any, *, is_error: bool = False) -> dict[str, Any]:
    import json

    text = json.dumps(payload, indent=2, default=str)
    return {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }
