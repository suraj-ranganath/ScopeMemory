"""Platform configuration."""

from __future__ import annotations

import os

DOLT_HOST = os.getenv("DOLT_HOST", "127.0.0.1")
DOLT_PORT = int(os.getenv("DOLT_PORT", "3306"))
DOLT_USER = os.getenv("DOLT_USER", "scope")
DOLT_PASSWORD = os.getenv("DOLT_PASSWORD", "")
DOLT_DATABASE = os.getenv("DOLT_DATABASE", "scopememory")

MEMGRAPH_URI = os.getenv("MEMGRAPH_URI", "bolt://127.0.0.1:7687")
MEMGRAPH_USER = os.getenv("MEMGRAPH_USER", "")
MEMGRAPH_PASSWORD = os.getenv("MEMGRAPH_PASSWORD", "")
