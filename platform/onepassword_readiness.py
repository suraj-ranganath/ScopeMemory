"""1Password readiness checks for the ScopeMemory credential broker.

This module only inspects local tooling and environment shape. It never reads,
prints, or resolves a secret value.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping


MAC_APP_PATH = Path("/Applications/1Password.app")
MAC_MCP_PATH = Path("/Applications/1Password.app/Contents/MacOS/onepassword-mcp")


class OnePasswordProviderStatus(str, Enum):
    READY = "ready"
    SETUP_REQUIRED = "setup_required"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class OnePasswordReadiness:
    platform_name: str
    desktop_app_present: bool
    op_cli_path: str | None
    op_cli_version: str | None
    onepassword_mcp_path: str | None
    service_account_token_present: bool
    status: OnePasswordProviderStatus
    provider_modes: list[str] = field(default_factory=list)
    setup_required: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @property
    def can_resolve_live_secrets(self) -> bool:
        return self.status == OnePasswordProviderStatus.READY


def detect_onepassword_readiness(
    env: Mapping[str, str] | None = None,
    op_path: str | None = None,
    mcp_path: Path = MAC_MCP_PATH,
    app_path: Path = MAC_APP_PATH,
) -> OnePasswordReadiness:
    """Return non-secret provider readiness for broker planning."""

    checked_env = env if env is not None else os.environ
    platform_name = platform.system()
    desktop_app_present = app_path.exists() if platform_name == "Darwin" else False

    resolved_op_path = op_path or shutil.which("op")
    op_cli_version = _safe_op_version(resolved_op_path) if resolved_op_path else None
    resolved_mcp_path = str(mcp_path) if mcp_path.exists() and os.access(mcp_path, os.X_OK) else None
    service_account_token_present = bool(checked_env.get("OP_SERVICE_ACCOUNT_TOKEN"))

    provider_modes: list[str] = []
    setup_required: list[str] = []
    notes: list[str] = []

    if resolved_mcp_path:
        provider_modes.append("onepassword_mcp_environment")
    else:
        setup_required.append("enable or install the 1Password local MCP server")

    if resolved_op_path:
        provider_modes.extend(["op_cli_secret_reference", "op_run_process_env"])
    else:
        setup_required.append("install the 1Password CLI and make op available on PATH")

    if service_account_token_present:
        provider_modes.append("onepassword_sdk_service_account")
    else:
        notes.append("OP_SERVICE_ACCOUNT_TOKEN is not set; service-account mode is unavailable")

    if desktop_app_present:
        notes.append("1Password desktop app is present; desktop-auth SDK mode may be possible after app developer integration is enabled")
    else:
        setup_required.append("install the 1Password desktop app for local human-in-the-loop auth")

    status = _status_for(provider_modes, desktop_app_present, service_account_token_present)
    if status != OnePasswordProviderStatus.READY:
        notes.append("credential broker must fail closed until at least one real provider mode is ready")

    return OnePasswordReadiness(
        platform_name=platform_name,
        desktop_app_present=desktop_app_present,
        op_cli_path=resolved_op_path,
        op_cli_version=op_cli_version,
        onepassword_mcp_path=resolved_mcp_path,
        service_account_token_present=service_account_token_present,
        status=status,
        provider_modes=provider_modes,
        setup_required=setup_required,
        notes=notes,
    )


def _safe_op_version(op_path: str) -> str | None:
    try:
        result = subprocess.run(
            [op_path, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _status_for(
    provider_modes: list[str],
    desktop_app_present: bool,
    service_account_token_present: bool,
) -> OnePasswordProviderStatus:
    if "onepassword_mcp_environment" in provider_modes:
        return OnePasswordProviderStatus.READY
    if service_account_token_present:
        return OnePasswordProviderStatus.READY
    if desktop_app_present and any(mode.startswith("op_") for mode in provider_modes):
        return OnePasswordProviderStatus.READY
    if desktop_app_present:
        return OnePasswordProviderStatus.SETUP_REQUIRED
    return OnePasswordProviderStatus.UNAVAILABLE


if __name__ == "__main__":
    print(json.dumps(detect_onepassword_readiness().to_dict(), indent=2, sort_keys=True))
