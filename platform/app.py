"""ScopeMemory MCP Gateway — preflight, authorize, proof + Person B demo surface."""

from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agentic_iam import mock_router, router as iam_router, verify_agent_active
from agentic_identity.auth import resolve_delegation_token
from config import AGENTIC_IAM_MODE, DELEGATION_JWT_REQUIRED
from cozo_policy import evaluate, export_facts
from dolt_store import (
    approve_access_request,
    get_session,
    init_schema,
    list_access_requests,
    save_policy_decision,
    seed_demo,
)
from graph_backend import authorize_context, backend_name, preflight_context, sync_graph

WEB_DIR = Path(__file__).parent / "web"
FIXTURES_DIR = Path(__file__).parent / "person_b" / "fixtures"


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


def _wait_for_memgraph(max_attempts: int = 10) -> None:
    """Best-effort; gateway falls back to in-memory graph if unavailable."""
    from graph_backend import _probe_memgraph
    for _ in range(max_attempts):
        if _probe_memgraph():
            return
        time.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _wait_for_dolt()
    _wait_for_memgraph()
    init_schema()
    seed_demo()
    sync_graph()
    yield


app = FastAPI(title="ScopeMemory Gateway", lifespan=lifespan)
app.include_router(iam_router)
app.include_router(mock_router)
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def _recipe_hits_for_session(session: dict[str, Any], session_id: str) -> tuple[list[dict[str, Any]], str]:
    from graph_backend import backend_name, search_recipe_hits
    hits = search_recipe_hits(
        team_id=session["team_id"],
        goal_class=session["goal_class"],
        goal_text=session["goal"],
        session_id=session_id,
    )
    return hits, backend_name()


class PreflightRequest(BaseModel):
    session_id: str = "sess_demo_001"
    agent_id: str = "agent_renewal_01"
    delegation_token: str | None = None


class AuthorizeRequest(BaseModel):
    session_id: str = "sess_demo_001"
    agent_id: str = "agent_renewal_01"
    tool_id: str
    resource_id: str
    delegation_token: str | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "stack": "dolt+graph+policy",
        "graph_backend": backend_name(),
        "recipe_retrieval": backend_name(),
        "iam_mode": AGENTIC_IAM_MODE,
        "delegation_jwt_required": str(DELEGATION_JWT_REQUIRED).lower(),
    }


@app.get("/")
def demo_ui() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.post("/auth/preflight")
def preflight(
    req: PreflightRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(404, "session not found in Dolt")
    agent = verify_agent_active(req.agent_id)
    if session["agent_id"] != req.agent_id:
        raise HTTPException(400, "agent does not match session")

    jwt_claims = resolve_delegation_token(
        req.session_id, req.agent_id, req.delegation_token, authorization,
    )

    rows, engine = sync_graph()
    ctx = preflight_context(req.session_id)
    recipe_hits, retrieval_engine = _recipe_hits_for_session(session, req.session_id)
    identity = {
        "identity_ref": agent["identity_ref"],
        "trust_score": agent["trust_score"],
        "delegation_required": True,
        "delegation_verified": True,
        "iam_source": agent.get("source", AGENTIC_IAM_MODE),
    }
    return {
        "session_id": req.session_id,
        "agentic_iam": {
            "agent_id": agent["agent_id"],
            "identity_ref": agent["identity_ref"],
            "trust_score": agent["trust_score"],
            "source": agent.get("source"),
        },
        "delegation_jwt": {
            "verified": True,
            "session_id": jwt_claims.get("session_id"),
            "user_id": jwt_claims.get("user_id"),
            "legacy": jwt_claims.get("legacy", False),
        },
        "agentic_identity": identity,
        "source_of_truth": "dolt",
        "query_engine": engine,
        "synced_rows": rows,
        "recipe_hits": recipe_hits,
        "recipe_retrieval": retrieval_engine,
        **ctx,
    }


@app.post("/auth/authorize")
def authorize(
    req: AuthorizeRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    session = get_session(req.session_id)
    if not session:
        raise HTTPException(404, "session not found in Dolt")
    verify_agent_active(req.agent_id)
    if session["agent_id"] != req.agent_id:
        raise HTTPException(400, "agent does not match session")

    jwt_claims = resolve_delegation_token(
        req.session_id, req.agent_id, req.delegation_token, authorization,
    )

    sync_graph()
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
        "policy_engine": "deterministic-rules",
        "delegation_jwt": {
            "verified": True,
            "user_id": jwt_claims.get("user_id"),
            "identity_ref": jwt_claims.get("identity_ref"),
            "legacy": jwt_claims.get("legacy", False),
        },
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
    rows, engine = sync_graph()
    return {"synced_rows": rows, "target": engine}


@app.post("/admin/reseed")
def admin_reseed() -> dict[str, Any]:
    """Reset demo seed data and re-sync graph (safe to call between demo runs)."""
    seed_demo()
    rows, engine = sync_graph()
    return {"status": "reseeded", "synced_rows": rows, "graph_engine": engine}


# --- Person B (RFC-06): demo surface, fixtures, Memgraph recipe index, learning ---


@app.get("/demo/ui-state/{session_id}")
def demo_ui_state(session_id: str, fixtures: bool = False) -> dict[str, Any]:
    from person_b.ui_state import build_ui_state
    try:
        return build_ui_state(session_id, use_fixtures=fixtures)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/fixtures/{name}")
def get_fixture(name: str) -> Any:
    path = FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(404, f"fixture not found: {name}")
    return json.loads(path.read_text())


@app.get("/demo/access-requests")
def demo_access_requests(session_id: str | None = None) -> dict[str, Any]:
    return {"requests": list_access_requests(session_id)}


class ApproveRequest(BaseModel):
    approver_id: str = "user_bob"


@app.post("/demo/access-requests/{request_id}/approve")
def demo_approve_request(request_id: str, body: ApproveRequest) -> dict[str, Any]:
    try:
        return approve_access_request(request_id, body.approver_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/demo/slack/search")
def demo_slack_search(channel: str = Query(..., alias="channel")) -> dict[str, Any]:
    from person_b.slack_fixtures import search_slack
    return search_slack(channel)


@app.post("/index/recipes")
def index_recipes() -> dict[str, Any]:
    from person_b.memgraph_recipe_index import index_accepted_recipes
    return index_accepted_recipes()


@app.get("/index/status")
def index_status() -> dict[str, Any]:
    import pymysql
    from config import DOLT_DATABASE, DOLT_HOST, DOLT_PASSWORD, DOLT_PORT, DOLT_USER
    from pymysql.cursors import DictCursor
    conn = pymysql.connect(
        host=DOLT_HOST, port=DOLT_PORT, user=DOLT_USER, password=DOLT_PASSWORD,
        database=DOLT_DATABASE, cursorclass=DictCursor,
    )
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM recipe_index_meta")
        rows = cur.fetchall()
    conn.close()
    return {"indexed": len(rows), "recipes": rows}


@app.post("/demo/recipes/propose")
def demo_propose_recipe(session_id: str = "sess_demo_001") -> dict[str, Any]:
    from person_b.learning_worker import propose_recipe_from_session
    try:
        return propose_recipe_from_session(session_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
