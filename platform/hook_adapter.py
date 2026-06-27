"""Claude Code and Codex PreToolUse adapter helpers.

Hooks are only adapters into ScopeMemory policy. This module normalizes the
host payload and produces safe host-specific responses without ever embedding a
credential value in hook output.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from policy_contracts import Decision


SECRET_KEY_MARKERS = (
    "authorization",
    "bearer",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)

DIRECT_SECRET_READ_PATTERNS = (
    re.compile(r"(^|[;&|]\s*)op\s+read\b"),
    re.compile(r"(^|[;&|]\s*)op\s+item\s+get\b.*(--field|--fields|password|token|secret)"),
    re.compile(r"(^|[;&|]\s*)op\s+inject\b.*(--out-file|-o)\b"),
    re.compile(r"\bcat\s+\.env(\b|$)"),
    re.compile(r"\b(printenv|env)\b.*(TOKEN|SECRET|PASSWORD|PRIVATE_KEY|AUTHORIZATION)"),
    re.compile(r"\becho\s+\$[A-Z0-9_]*(TOKEN|SECRET|PASSWORD|PRIVATE_KEY|AUTHORIZATION)[A-Z0-9_]*\b"),
)


class HookHost(str, Enum):
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    UNKNOWN = "unknown"


class SecretAccessPattern(str, Enum):
    NONE = "none"
    DIRECT_SECRET_READ = "direct_secret_read"
    SECRET_IN_INPUT = "secret_in_input"
    ENV_PRINT = "env_print"
    SECRET_FILE_WRITE = "secret_file_write"


@dataclass(frozen=True)
class NormalizedHookIntent:
    agent_host: HookHost
    hook_event: str
    session_id: str
    tool_name: str
    tool_input: dict[str, Any]
    cwd: str = ""
    access_kind: str = "execute"
    secret_access_pattern: SecretAccessPattern = SecretAccessPattern.NONE
    resource_hints: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class HookAdapterDecision:
    decision: Decision
    safe_reason: str
    updated_input: dict[str, Any] | None = None
    lease_id: str = ""
    access_request_id: str = ""


def normalize_pre_tool_use(host: str, payload: dict[str, Any]) -> NormalizedHookIntent:
    tool_name = _string_at(payload, "tool_name") or _nested_string(payload, ("tool", "name")) or _string_at(payload, "name") or "unknown"
    raw_tool_input = payload.get("tool_input", payload.get("input", payload.get("arguments", {})))
    tool_input = raw_tool_input if isinstance(raw_tool_input, dict) else {"value": raw_tool_input}
    session_id = _string_at(payload, "session_id") or _nested_string(payload, ("session", "id")) or ""
    hook_event = _string_at(payload, "hook_event_name") or _string_at(payload, "event") or "PreToolUse"
    cwd = _string_at(payload, "cwd") or _nested_string(payload, ("workspace", "cwd")) or ""

    return NormalizedHookIntent(
        agent_host=_host(host),
        hook_event=hook_event,
        session_id=session_id,
        tool_name=tool_name,
        tool_input=tool_input,
        cwd=cwd,
        access_kind=_infer_access_kind(tool_name, tool_input),
        secret_access_pattern=detect_secret_access_pattern(tool_name, tool_input),
        resource_hints=_resource_hints(tool_name, tool_input),
    )


def evaluate_hook_intent(intent: NormalizedHookIntent) -> HookAdapterDecision:
    if intent.secret_access_pattern == SecretAccessPattern.DIRECT_SECRET_READ:
        return HookAdapterDecision(
            decision=Decision.DENY,
            safe_reason="direct password-manager secret reads must go through the ScopeMemory credential broker",
        )
    if intent.secret_access_pattern == SecretAccessPattern.SECRET_IN_INPUT:
        return HookAdapterDecision(
            decision=Decision.DENY,
            safe_reason="tool input appears to contain credential material; use an opaque credential lease instead",
        )
    if intent.secret_access_pattern == SecretAccessPattern.ENV_PRINT:
        return HookAdapterDecision(
            decision=Decision.DENY,
            safe_reason="command appears to print environment variables that may contain credentials",
        )
    if intent.secret_access_pattern == SecretAccessPattern.SECRET_FILE_WRITE:
        return HookAdapterDecision(
            decision=Decision.DENY,
            safe_reason="command appears to write decrypted credentials to a file",
        )
    return HookAdapterDecision(decision=Decision.ALLOW, safe_reason="no broker bypass detected")


def claude_pre_tool_use_output(decision: HookAdapterDecision) -> dict[str, Any]:
    permission = _claude_permission(decision.decision)
    output: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission,
            "permissionDecisionReason": decision.safe_reason,
        }
    }
    if decision.updated_input is not None and decision.decision == Decision.ALLOW:
        output["hookSpecificOutput"]["updatedInput"] = decision.updated_input
    return output


def codex_pre_tool_use_output(decision: HookAdapterDecision) -> dict[str, Any]:
    permission = "allow" if decision.decision == Decision.ALLOW else "deny"
    output: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": permission,
            "permissionDecisionReason": decision.safe_reason,
        }
    }
    if decision.updated_input is not None and decision.decision == Decision.ALLOW:
        output["hookSpecificOutput"]["updatedInput"] = decision.updated_input
    return output


def detect_secret_access_pattern(tool_name: str, tool_input: dict[str, Any]) -> SecretAccessPattern:
    command = _command_text(tool_name, tool_input)
    if command:
        lowered_command = command.lower()
        if "op inject" in lowered_command and ("--out-file" in lowered_command or " -o " in lowered_command):
            return SecretAccessPattern.SECRET_FILE_WRITE
        if any(pattern.search(command) for pattern in DIRECT_SECRET_READ_PATTERNS):
            if "printenv" in lowered_command or re.search(r"\benv\b", lowered_command):
                return SecretAccessPattern.ENV_PRINT
            if "op inject" in lowered_command:
                return SecretAccessPattern.SECRET_FILE_WRITE
            return SecretAccessPattern.DIRECT_SECRET_READ

    if _contains_secret_like_input(tool_input):
        return SecretAccessPattern.SECRET_IN_INPUT
    return SecretAccessPattern.NONE


def _host(value: str) -> HookHost:
    normalized = value.strip().lower().replace("-", "_")
    if normalized in {"claude", "claude_code"}:
        return HookHost.CLAUDE_CODE
    if normalized == "codex":
        return HookHost.CODEX
    return HookHost.UNKNOWN


def _claude_permission(decision: Decision) -> str:
    if decision == Decision.ALLOW:
        return "allow"
    if decision == Decision.ESCALATE_HUMAN:
        return "ask"
    if decision == Decision.REPAIR:
        return "defer"
    return "deny"


def _command_text(tool_name: str, tool_input: dict[str, Any]) -> str:
    if tool_name.lower() not in {"bash", "shell", "exec"}:
        return ""
    for key in ("command", "cmd", "script"):
        value = tool_input.get(key)
        if isinstance(value, str):
            return value
    return ""


def _contains_secret_like_input(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            lower_key = str(key).lower()
            if any(marker in lower_key for marker in SECRET_KEY_MARKERS) and nested:
                return True
            if _contains_secret_like_input(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_like_input(item) for item in value)
    elif isinstance(value, str):
        lowered = value.lower()
        return "authorization: bearer " in lowered or "op://" in lowered and any(marker in lowered for marker in SECRET_KEY_MARKERS)
    return False


def _infer_access_kind(tool_name: str, tool_input: dict[str, Any]) -> str:
    lowered_tool = tool_name.lower()
    if lowered_tool == "bash":
        command = _command_text(tool_name, tool_input).lower()
        if re.search(r"\b(post|create|update|delete|write|send|curl\s+-x\s+post)\b", command):
            return "write"
        return "execute"
    if any(word in lowered_tool for word in ("create", "post", "update", "delete", "send", "write")):
        return "write"
    return "read"


def _resource_hints(tool_name: str, tool_input: dict[str, Any]) -> list[str]:
    hints = [tool_name]
    for key in ("resource_id", "team", "channel", "project", "workspace"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            hints.append(f"{key}:{value}")
    return hints


def _string_at(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else ""


def _nested_string(payload: dict[str, Any], path: tuple[str, ...]) -> str:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return current if isinstance(current, str) else ""


def safe_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
