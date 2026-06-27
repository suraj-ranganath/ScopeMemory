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
from dolt_store import (
    approve_access_request,
    get_session,
    init_schema,
    list_access_requests,
    seed_demo,
)
from gateway_service import run_authorize, run_preflight
from graph_backend import backend_name, sync_graph
from mcp.router import router as mcp_router

WEB_DIR = Path(__file__).parent / "web"
WEB_DIST_DIR = WEB_DIR / "dist"
WEB_ASSETS_DIR = WEB_DIST_DIR / "assets"
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
app.include_router(mcp_router)
if WEB_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_ASSETS_DIR)), name="assets")
else:
    app.mount("/src", StaticFiles(directory=str(WEB_DIR / "src")), name="react-src")


def _recipe_hits_for_session(session: dict[str, Any], session_id: str) -> tuple[list[dict[str, Any]], str]:
    from gateway_service import recipe_hits_for_session
    return recipe_hits_for_session(session, session_id)


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
        "stack": "dolt+graph+policy+mcp",
        "graph_backend": backend_name(),
        "recipe_retrieval": backend_name(),
        "iam_mode": AGENTIC_IAM_MODE,
        "delegation_jwt_required": str(DELEGATION_JWT_REQUIRED).lower(),
        "mcp_endpoint": "/mcp",
    }


@app.get("/")
def demo_ui() -> FileResponse:
    index_path = WEB_DIST_DIR / "index.html"
    if not index_path.exists():
        index_path = WEB_DIR / "index.html"
    return FileResponse(index_path)


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

    result = run_preflight(req.session_id, req.agent_id, jwt_claims)
    return result


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

    try:
        return run_authorize(
            req.session_id, req.agent_id, req.tool_id, req.resource_id, jwt_claims,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@app.get("/auth/proof/{session_id}")
def get_proof(session_id: str) -> dict[str, Any]:
    from gateway_service import list_policy_decisions
    rows = list_policy_decisions(session_id)
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
