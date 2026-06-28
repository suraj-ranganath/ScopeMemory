#!/usr/bin/env python3
"""Install ScopeMemory's local Codex MCP bridge and demo hook config.

The MCP bridge is the enforcement path: Codex calls ScopeMemory as a local
stdio MCP server, and the bridge proxies to the gateway with a session-scoped
delegation token. The hook is a visibility/safety adapter for local shell and
MCP intents, so the demo dashboard can show pre-tool-use traces.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


SESSION_ID = os.getenv("SCOPEMEMORY_SESSION_ID", "sess_demo_001")
AGENT_ID = os.getenv("SCOPEMEMORY_AGENT_ID", "agent_renewal_01")
GATEWAY_URL = os.getenv("SCOPEMEMORY_GATEWAY_URL", "http://127.0.0.1:8080")


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    codex_home = Path(os.getenv("CODEX_HOME", Path.home() / ".codex")).expanduser()
    codex_home.mkdir(parents=True, exist_ok=True)

    bridge_path = repo_root / "platform" / "codex_mcp_bridge.py"
    hook_path = repo_root / "platform" / "codex_hook.py"
    _install_mcp_config(codex_home / "config.toml", bridge_path)
    _install_hooks(codex_home / "hooks.json", hook_path)
    print(f"Installed ScopeMemory Codex demo config in {codex_home}")


def _install_mcp_config(config_path: Path, bridge_path: Path) -> None:
    snippet = f"""

[mcp_servers.scopememory]
command = "python3"
args = ["{bridge_path}"]

[mcp_servers.scopememory.env]
SCOPEMEMORY_GATEWAY_URL = "{GATEWAY_URL}"
SCOPEMEMORY_SESSION_ID = "{SESSION_ID}"
SCOPEMEMORY_AGENT_ID = "{AGENT_ID}"
"""
    existing = config_path.read_text() if config_path.exists() else ""
    if "[mcp_servers.scopememory]" in existing:
        print(f"ScopeMemory MCP server already present in {config_path}")
        return
    _backup(config_path)
    config_path.write_text(existing.rstrip() + snippet + "\n")


def _install_hooks(hooks_path: Path, hook_path: Path) -> None:
    hook_entry = {
        "matcher": "Bash|Shell|mcp__.*",
        "hooks": [
            {
                "type": "command",
                "command": (
                    f"SCOPEMEMORY_GATEWAY_URL={GATEWAY_URL} "
                    f"SCOPEMEMORY_SESSION_ID={SESSION_ID} "
                    f"python3 {hook_path}"
                ),
                "statusMessage": "ScopeMemory checking tool intent",
            }
        ],
    }
    if hooks_path.exists():
        payload = json.loads(hooks_path.read_text())
    else:
        payload = {"hooks": {}}
    hooks = payload.setdefault("hooks", {})
    pre_tool = hooks.setdefault("PreToolUse", [])
    rendered_command = hook_entry["hooks"][0]["command"]
    for entry in pre_tool:
        for hook in entry.get("hooks", []):
            if hook.get("command") == rendered_command:
                print(f"ScopeMemory PreToolUse hook already present in {hooks_path}")
                return
    _backup(hooks_path)
    pre_tool.append(hook_entry)
    hooks_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _backup(path: Path) -> None:
    if path.exists():
        backup = path.with_suffix(path.suffix + ".scopememory.bak")
        if not backup.exists():
            backup.write_text(path.read_text())


if __name__ == "__main__":
    main()
