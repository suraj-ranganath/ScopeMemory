"""MCP JSON-RPC server — initialize, tools/list, tools/call."""

from __future__ import annotations

from typing import Any

from agentic_identity.auth import extract_bearer_token
from agentic_identity.delegation_jwt import DelegationTokenError, verify_delegation_token
from mcp.handlers import McpHandlerError, handle_tool_call, visible_tools_for_session
from mcp.protocol import (
    JSONRPC_INVALID_PARAMS,
    JSONRPC_INVALID_REQUEST,
    JSONRPC_METHOD_NOT_FOUND,
    JSONRPC_PARSE_ERROR,
    MCP_AUTH_REQUIRED,
    MCP_PROTOCOL_VERSION,
    SERVER_NAME,
    SERVER_VERSION,
    jsonrpc_error,
    jsonrpc_result,
)
from mcp.registry import ALL_TOOLS, AUTH_TOOLS, DOWNSTREAM_TOOLS


class McpServer:
    def handle(self, body: Any, authorization: str | None = None) -> dict[str, Any]:
        if not isinstance(body, dict):
            return jsonrpc_error(None, JSONRPC_INVALID_REQUEST, "request must be a JSON object")

        req_id = body.get("id")
        method = body.get("method")
        params = body.get("params") or {}

        if body.get("jsonrpc") != "2.0":
            return jsonrpc_error(req_id, JSONRPC_INVALID_REQUEST, "jsonrpc must be '2.0'")
        if not method:
            return jsonrpc_error(req_id, JSONRPC_INVALID_REQUEST, "method required")

        try:
            if method == "initialize":
                return self._initialize(req_id, params)
            if method == "notifications/initialized":
                return jsonrpc_result(req_id, {})
            if method == "tools/list":
                return self._tools_list(req_id, params, authorization)
            if method == "tools/call":
                return self._tools_call(req_id, params, authorization)
            return jsonrpc_error(req_id, JSONRPC_METHOD_NOT_FOUND, f"method not found: {method}")
        except McpHandlerError as e:
            return jsonrpc_error(req_id, e.code, e.message, e.data)
        except Exception as e:
            return jsonrpc_error(req_id, -32603, str(e))

    def _initialize(self, req_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        return jsonrpc_result(
            req_id,
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": True}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            },
        )

    def _tools_list(
        self,
        req_id: Any,
        params: dict[str, Any],
        authorization: str | None,
    ) -> dict[str, Any]:
        meta = params.get("_meta") or {}
        session_id = meta.get("session_id") or params.get("session_id")
        agent_id = meta.get("agent_id") or params.get("agent_id")

        if session_id and agent_id:
            names = visible_tools_for_session(session_id, agent_id, authorization)
            tools = [ALL_TOOLS[n] for n in names if n in ALL_TOOLS]
        else:
            tools = AUTH_TOOLS + DOWNSTREAM_TOOLS

        return jsonrpc_result(req_id, {"tools": tools})

    def _tools_call(
        self,
        req_id: Any,
        params: dict[str, Any],
        authorization: str | None,
    ) -> dict[str, Any]:
        if not extract_bearer_token(authorization):
            raise McpHandlerError(
                MCP_AUTH_REQUIRED,
                "delegation JWT required on tools/call (Authorization: Bearer)",
            )

        name = params.get("name")
        arguments = params.get("arguments")
        if not name:
            raise McpHandlerError(JSONRPC_INVALID_PARAMS, "params.name required")
        if arguments is not None and not isinstance(arguments, dict):
            raise McpHandlerError(JSONRPC_INVALID_PARAMS, "params.arguments must be an object")

        result = handle_tool_call(name, arguments, authorization)
        return jsonrpc_result(req_id, result)


def decode_session_from_jwt(authorization: str | None) -> tuple[str, str] | None:
    token = extract_bearer_token(authorization)
    if not token:
        return None
    try:
        claims = verify_delegation_token(token)
        return claims["session_id"], claims["agent_id"]
    except DelegationTokenError:
        return None


def parse_jsonrpc_body(raw: bytes) -> Any:
    import json

    try:
        return json.loads(raw.decode())
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(str(e)) from e
