# ScopeMemory

Memory-Informed Authorization for MCP Agents — with ReBAC context paths for Agentic Identity.

## Platform stack (Dolt + Memgraph + Gateway)

```bash
cd platform
python3 init_dolt_user.py          # once
docker compose --profile gateway-docker up -d --build
python3 run_demo.py
```

See [platform/README.md](platform/README.md).

## Quick demo (SQLite, 2 hours)

```bash
cd demo
python run_demo.py all
```

See [RFC-07](docs/engineering-plan/plan/RFC-07-2-hour-agentic-identity-demo.md).

**Agentic Identity story:** Agentic-IAM knows who the agent is. ScopeMemory decides what it may do — via relationship traversal, not a broad role.
