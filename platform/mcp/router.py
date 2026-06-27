"""FastAPI router for MCP JSON-RPC over HTTP."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from mcp.protocol import JSONRPC_PARSE_ERROR, jsonrpc_error
from mcp.server import McpServer, parse_jsonrpc_body

router = APIRouter(tags=["mcp"])
_server = McpServer()


@router.post("/mcp")
async def mcp_jsonrpc(
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    raw = await request.body()
    try:
        body = parse_jsonrpc_body(raw)
    except ValueError as e:
        return JSONResponse(jsonrpc_error(None, JSONRPC_PARSE_ERROR, str(e)))

    if isinstance(body, list):
        responses = [_server.handle(item, authorization) for item in body]
        return JSONResponse(responses)

    return JSONResponse(_server.handle(body, authorization))


@router.get("/mcp/health")
def mcp_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "transport": "http+jsonrpc",
        "methods": ["initialize", "tools/list", "tools/call"],
        "jwt_required_on": ["tools/call"],
    }
