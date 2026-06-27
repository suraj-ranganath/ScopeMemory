#!/usr/bin/env python3
"""Initialize Dolt remote user (run once after first docker compose up)."""

from __future__ import annotations

import subprocess
import sys


def main() -> None:
    sql = (
        "CREATE USER IF NOT EXISTS 'scope'@'%' IDENTIFIED BY ''; "
        "GRANT ALL ON *.* TO 'scope'@'%'; FLUSH PRIVILEGES;"
    )
    cmd = ["docker", "exec", "platform-dolt-1", "dolt", "sql", "-q", sql]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print("Dolt user 'scope' ready for gateway connections.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
