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

# Agentic-IAM integration
AGENTIC_IAM_MODE = os.getenv("AGENTIC_IAM_MODE", "mock")  # mock | http
AGENTIC_IAM_URL = os.getenv("AGENTIC_IAM_URL", "")
AGENTIC_IAM_API_KEY = os.getenv("AGENTIC_IAM_API_KEY", "")
TRUST_SCORE_MIN = float(os.getenv("TRUST_SCORE_MIN", "0.5"))
TRUST_SCORE_SENSITIVE = float(os.getenv("TRUST_SCORE_SENSITIVE", "0.8"))

# Delegation JWT (Priority 1)
DELEGATION_JWT_SECRET = os.getenv(
    "DELEGATION_JWT_SECRET",
    "scopememory-demo-secret-change-in-production",
)
DELEGATION_JWT_ISSUER = os.getenv("DELEGATION_JWT_ISSUER", "scopememory")
DELEGATION_JWT_AUDIENCE = os.getenv("DELEGATION_JWT_AUDIENCE", "scopememory-gateway")
DELEGATION_JWT_TTL_SECONDS = int(os.getenv("DELEGATION_JWT_TTL_SECONDS", "3600"))
DELEGATION_JWT_REQUIRED = os.getenv("DELEGATION_JWT_REQUIRED", "true").lower() in ("1", "true", "yes")
