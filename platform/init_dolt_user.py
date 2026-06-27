#!/usr/bin/env python3
"""Initialize Dolt remote user (run once after first docker compose up)."""

from __future__ import annotations

import subprocess
import sys


def _dolt_container() -> str:
    import os
    if name := os.getenv("DOLT_CONTAINER"):
        return name
    result = subprocess.run(
        ["docker", "ps", "--filter", "ancestor=dolthub/dolt-sql-server:latest", "--format", "{{.Names}}"],
        capture_output=True, text=True, check=False,
    )
    names = [n.strip() for n in result.stdout.splitlines() if n.strip()]
    if not names:
        raise RuntimeError("No Dolt container found — run: docker compose up -d dolt")
    return names[0]


def main() -> None:
    container = _dolt_container()
    sql = (
        "CREATE USER IF NOT EXISTS 'scope'@'%' IDENTIFIED BY ''; "
        "GRANT ALL ON *.* TO 'scope'@'%'; FLUSH PRIVILEGES;"
    )
    cmd = ["docker", "exec", container, "dolt", "sql", "-q", sql]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Dolt user 'scope' ready (container: {container}).")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(getattr(e, "returncode", 1) or 1)
