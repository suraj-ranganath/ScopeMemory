"""ScopeMemory MCP Gateway — preflight, authorize, proof."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agentic_iam import router as iam_router, verify_agent_active
from cozo_policy import evaluate, export_facts
from dolt_store import get_session, init_schema, save_policy_decision, seed_demo
from memgraph_queries import authorize_context, preflight_context
from memgraph_sync import sync_to_memgraph


def _wait_for_dolt(max_attempts: int = 30) -> None:
    import pymysql
    from config import DOLT_HOST, DOLT_PASSWORD, DOLT_PORT, DOLT_USER
    for _ in range(max_attempts):
        try:
            pymysql.connect(
                host=DOLT_HOST, port=DOLT_PORT, user=DOLT_USER, password=DOLT_PASSWORD,
            ).close()
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Dolt not reachable")


def _wait_for_memgraph(max_attempts: int = 30) -> None:
    from neo4j import GraphDatabase
    from config import MEMGRAPH_URI, MEMGRAPH_USER, MEMGRAPH_PASSWORD
    auth = (MEMGRAPH_USER, MEMGRAPH_PASSWORD) if MEMGRAPH_USER else None
    for _ in range(max_attempts):
        try:
            driver = GraphDatabase.driver(MEMGRAPH_URI, auth=auth)
            with driver.session() as s:
                s.run("RETURN 1")
            driver.close()
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Memgraph not reachable")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _wait_for_dolt()
    _wait_for_memgraph()
    init_schema()
    seed_demo()
    sync_to_memgraph()
    yield


app = FastAPI(title="ScopeMemory Gateway", lifespan=lifespan)
app.include_router(iam_router)


class PreflightRequest(BaseModel):
    session_id: str = "sess_demo_001"
    agent_id: str = "agent_renewal_01"


class AuthorizeRequest(BaseModel):
    session_id: str = "sess_demo_001"
    agent_id: str = "agent_renewal_01"
    tool_id: str
    resource_id: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "stack": "dolt+memgraph+cozo"}


@app.post("/auth/preflight")
def preflight(req: PreflightRequest) -> dict[str, Any]:
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(404, "session not found in Dolt")
    agent = verify_agent_active(req.agent_id)
    if session["agent_id"] != req.agent_id:
        raise HTTPException(400, "agent does not match session")

    sync_to_memgraph()
    ctx = preflight_context(req.session_id)
    return {
        "session_id": req.session_id,
        "agentic_iam": {
            "agent_id": agent["agent_id"],
            "identity_ref": agent["identity_ref"],
            "trust_score": agent["trust_score"],
        },
        "source_of_truth": "dolt",
        "query_engine": "memgraph",
        **ctx,
    }


@app.post("/auth/authorize")
def authorize(req: AuthorizeRequest) -> dict[str, Any]:
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(404, "session not found in Dolt")
    verify_agent_active(req.agent_id)

    sync_to_memgraph()
    ctx = authorize_context(req.session_id, req.tool_id, req.resource_id)
    if "error" in ctx:
        raise HTTPException(404, ctx["error"])

    decision, reason, rules = evaluate(ctx["facts"])
    cozo_facts = export_facts(ctx["facts"])

    proof = {
        "decision": decision,
        "reason": reason,
        "context_path": ctx["context_path"],
        "rebac_tuples": ctx["rebac_tuples"],
        "memgraph_facts": ctx["facts"],
        "cozo_facts": cozo_facts,
        "rules": rules,
        "policy_engine": "cozo",
    }

    decision_id = save_policy_decision(
        req.session_id, req.tool_id, req.resource_id, decision, proof,
    )

    return {
        "decision_id": decision_id,
        "decision": decision,
        "reason": reason,
        "proof": proof,
        "audit_store": "dolt",
    }


@app.get("/auth/proof/{session_id}")
def get_proof(session_id: str) -> dict[str, Any]:
    import pymysql
    from config import DOLT_DATABASE, DOLT_HOST, DOLT_PASSWORD, DOLT_PORT, DOLT_USER
    from pymysql.cursors import DictCursor

    conn = pymysql.connect(
        host=DOLT_HOST, port=DOLT_PORT, user=DOLT_USER, password=DOLT_PASSWORD,
        database=DOLT_DATABASE, cursorclass=DictCursor,
    )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT * FROM policy_decisions WHERE session_id = %s ORDER BY created_at DESC",
            (session_id,),
        )
        rows = cur.fetchall()
    conn.close()
    return {"session_id": session_id, "decisions": rows}


@app.post("/admin/sync")
def admin_sync() -> dict[str, Any]:
    count = sync_to_memgraph()
    return {"synced_rows": count, "target": "memgraph"}
