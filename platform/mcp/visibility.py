"""Pure MCP catalog visibility helpers."""

from __future__ import annotations

from typing import Any

from mcp.registry import AUTH_TOOL_NAMES, DOWNSTREAM_TOOL_NAMES


def visible_tools_from_context(
    ctx: dict[str, Any],
    access_requests: list[dict[str, Any]] | None = None,
    grants: list[dict[str, Any]] | None = None,
) -> list[str]:
    visible = set(AUTH_TOOL_NAMES)
    for tool in ctx.get("predicted_tools") or []:
        if tool in DOWNSTREAM_TOOL_NAMES:
            visible.add(tool)
    for req in access_requests or []:
        if req.get("status") in {"pending", "approved"}:
            tool = req.get("requested_tool_id")
            if tool in DOWNSTREAM_TOOL_NAMES:
                visible.add(tool)
    # Grants are scoped rather than tool-specific in the current Dolt model. The
    # predicted catalog remains the source for grant-backed tool visibility.
    _ = grants
    return sorted(visible)
