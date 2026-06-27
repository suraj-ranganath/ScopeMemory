#!/usr/bin/env python3
"""
ScopeMemory Demo UI — Streamlit frontend for the full platform stack.

Run (gateway must be up on :8080):
    cd platform && pip install -r requirements.txt
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from ui.client import GatewayClient
from ui.components import (
    decision_badge,
    hero,
    inject_css,
    init_session_state,
    json_block,
    metrics_row,
    rebac_tuples,
    show_decision,
)

DEFAULTS = {
    "gateway_url": "http://127.0.0.1:8080",
    "session_id": "sess_demo_001",
    "agent_id": "agent_renewal_01",
    "user_id": "user_alice",
    "team_id": "team_sales",
    "delegation_token": "",
    "goal": "Prepare renewal follow-up for Acme. Check Slack context and create a Linear issue.",
    "goal_class": "sales_renewal_prep",
}


def client() -> GatewayClient:
    return GatewayClient(st.session_state.gateway_url)


def ensure_token() -> str | None:
    token = st.session_state.delegation_token
    if token:
        return token
    try:
        token = client().mint_token(st.session_state.session_id)
        st.session_state.delegation_token = token
        return token
    except Exception as e:
        st.error(f"Could not mint JWT: {e}")
        return None


def sidebar() -> None:
    with st.sidebar:
        st.markdown("### ⚙ Connection")
        st.session_state.gateway_url = st.text_input(
            "Gateway URL", value=st.session_state.gateway_url,
        )
        st.session_state.session_id = st.text_input(
            "Session ID", value=st.session_state.session_id,
        )
        st.session_state.agent_id = st.text_input(
            "Agent ID", value=st.session_state.agent_id,
        )

        st.divider()
        st.markdown("### 🔑 Delegation JWT")
        if st.button("Mint JWT", use_container_width=True):
            try:
                st.session_state.delegation_token = client().mint_token(
                    st.session_state.session_id,
                )
                st.success("JWT minted")
            except Exception as e:
                st.error(GatewayClient.format_error(e))

        if st.session_state.delegation_token:
            st.caption(f"Token ({len(st.session_state.delegation_token)} chars)")
            with st.expander("View token"):
                st.code(st.session_state.delegation_token[:80] + "…")

        st.divider()
        if st.button("🔄 Reseed demo data", use_container_width=True):
            try:
                r = client().reseed()
                st.session_state.delegation_token = client().mint_token(
                    st.session_state.session_id,
                )
                st.success(f"Reseeded · {r.get('graph_engine')} · {r.get('synced_rows')} rows")
            except Exception as e:
                st.error(GatewayClient.format_error(e))

        try:
            h = client().health()
            st.caption(
                f"● {h.get('status')} · {h.get('graph_backend')} · "
                f"IAM {h.get('iam_mode')} · JWT {h.get('delegation_jwt_required')}"
            )
        except Exception:
            st.caption("● Gateway offline")


def page_overview() -> None:
    hero(
        "ScopeMemory",
        "Memory-informed authorization for MCP agents — ReBAC context paths, delegation JWT, policy proofs.",
    )

    try:
        h = client().health()
        metrics_row([
            ("Stack", h.get("stack", "—")),
            ("Graph", h.get("graph_backend", "—")),
            ("IAM mode", h.get("iam_mode", "—")),
            ("MCP", h.get("mcp_endpoint", "/mcp")),
        ])
        json_block(h, "Health response")
    except Exception as e:
        st.error(f"Gateway unreachable: {GatewayClient.format_error(e)}")
        st.info("Start the stack: `docker compose --profile gateway-docker up -d --build`")
        return

    st.markdown("### Architecture")
    st.markdown(
        """
        ```
        Agentic-IAM → Delegation JWT → Gateway (REST + MCP)
              ↓                              ↓
           Dolt (truth)              Memgraph (ReBAC + recipes)
              ↓                              ↓
                        Policy → ALLOW / DENY / ESCALATE
        ```
        """
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**RFC-08** · Agentic Identity")
        st.caption("JWT delegation + IAM adapter")
    with col2:
        st.markdown("**RFC-03** · MCP Gateway")
        st.caption("JSON-RPC tools/call with JWT")
    with col3:
        st.markdown("**RFC-06** · Person B")
        st.caption("Approval flows + recipe learning")


def page_identity() -> None:
    hero("Agentic Identity", "Who is the agent? Delegation chain and identity proof (RFC-08).")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Agent registry")
        if st.button("Lookup agent", key="lookup_agent"):
            try:
                agent = client().get_agent(st.session_state.agent_id)
                st.session_state["_agent"] = agent
            except Exception as e:
                st.error(GatewayClient.format_error(e))
        if "_agent" in st.session_state:
            a = st.session_state["_agent"]
            metrics_row([
                ("Display", a.get("display_name", "—")),
                ("Trust", str(a.get("trust_score", "—"))),
                ("Source", a.get("source", "—")),
            ])
            st.code(a.get("identity_ref", ""), language=None)
            json_block(a)

    with c2:
        st.markdown("#### Create delegation")
        goal = st.text_area("Goal", value=st.session_state.goal, height=80)
        if st.button("POST /iam/sessions", key="create_session"):
            try:
                r = client().create_session(
                    st.session_state.user_id,
                    st.session_state.agent_id,
                    st.session_state.team_id,
                    goal,
                    st.session_state.goal_class,
                )
                st.session_state.session_id = r["session"]["session_id"]
                st.session_state.delegation_token = r["delegation_token"]
                st.success(f"Session `{st.session_state.session_id}` created")
                json_block(r, "Session response")
            except Exception as e:
                st.error(GatewayClient.format_error(e))

    st.divider()
    st.markdown("#### Identity proof (ReBAC tuples)")
    if st.button("Load identity proof", key="id_proof"):
        try:
            proof = client().identity_proof(st.session_state.session_id)
            st.session_state["_proof"] = proof
        except Exception as e:
            st.error(GatewayClient.format_error(e))

    if "_proof" in st.session_state:
        p = st.session_state["_proof"]
        metrics_row([
            ("Agent", p.get("agent_id", "—")),
            ("Delegation", "yes" if p.get("delegation_present") else "no"),
            ("Trust", str(p.get("trust_score", "—"))),
        ])
        rebac_tuples(p.get("rebac_tuples", []))
        json_block(p)


def page_authorization() -> None:
    hero("Authorization", "Preflight goal → policy decision with proof (JWT required).")

    token = ensure_token()
    if not token:
        return

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Preflight")
        if st.button("Run preflight", key="preflight"):
            try:
                r = client().preflight(
                    st.session_state.session_id,
                    st.session_state.agent_id,
                    token,
                )
                st.session_state["_preflight"] = r
            except Exception as e:
                st.error(GatewayClient.format_error(e))

        if "_preflight" in st.session_state:
            pf = st.session_state["_preflight"]
            hits = pf.get("recipe_hits", [])
            st.markdown(f"**{len(hits)}** recipe hit(s)")
            for h in hits:
                st.markdown(
                    f"- **{h.get('title', h.get('recipe_id'))}** "
                    f"(score {h.get('score', '—')})"
                )
            st.markdown("**Predicted tools**")
            st.write(pf.get("predicted_tools", []))
            rebac_tuples(pf.get("rebac_tuples", []))

    with c2:
        st.markdown("#### Authorize tool call")
        tool_id = st.selectbox(
            "Tool",
            [
                "linear.create_issue",
                "slack.search_messages",
                "slack.post_message",
            ],
        )
        resource_defaults = {
            "linear.create_issue": "linear_team:SALES",
            "slack.search_messages": "slack_channel:sales-acme",
            "slack.post_message": "slack_channel:external-partners",
        }
        resource_id = st.text_input(
            "Resource ID", value=resource_defaults.get(tool_id, ""),
        )
        if st.button("Authorize", key="authorize"):
            try:
                r = client().authorize(
                    st.session_state.session_id,
                    st.session_state.agent_id,
                    tool_id,
                    resource_id,
                    token,
                )
                st.session_state["_last_auth"] = r
            except Exception as e:
                st.error(GatewayClient.format_error(e))

        if "_last_auth" in st.session_state:
            auth = st.session_state["_last_auth"]
            show_decision(auth.get("decision", ""), auth.get("reason"))
            proof = auth.get("proof", {})
            st.markdown("**Context path**")
            st.code(" → ".join(proof.get("context_path", [])))
            json_block(auth, "Full authorize response")

    st.divider()
    st.markdown("#### Audit trail")
    if st.button("Load proof trail", key="proof_trail"):
        try:
            st.session_state["_trail"] = client().proof_trail(st.session_state.session_id)
        except Exception as e:
            st.error(GatewayClient.format_error(e))
    if "_trail" in st.session_state:
        for d in st.session_state["_trail"].get("decisions", []):
            with st.expander(f"{d.get('tool_id')} · {d.get('decision')}"):
                st.markdown(
                    decision_badge(d.get("decision", "")),
                    unsafe_allow_html=True,
                )
                proof = d.get("proof_json")
                if isinstance(proof, str):
                    proof = json.loads(proof)
                st.json(proof)


def page_session() -> None:
    hero("Session dashboard", "Live session state — recipes, grants, requests, timeline.")

    if st.button("Refresh UI state", key="ui_refresh"):
        try:
            st.session_state["_ui"] = client().ui_state(st.session_state.session_id)
        except Exception as e:
            st.error(GatewayClient.format_error(e))

    if "_ui" not in st.session_state:
        try:
            st.session_state["_ui"] = client().ui_state(st.session_state.session_id)
        except Exception:
            st.warning("Could not load UI state — is the gateway running?")
            return

    state = st.session_state["_ui"]
    session = state.get("session", {})

    metrics_row([
        ("Session", session.get("session_id", "—")),
        ("Status", session.get("status", state.get("ui_status", "—"))),
        ("Goal class", session.get("goal_class", "—")),
        ("Mode", state.get("mode", "—")),
    ])
    st.caption(session.get("goal", ""))

    tab1, tab2, tab3, tab4 = st.tabs(["Recipes & scopes", "Access requests", "Decisions", "Timeline"])

    with tab1:
        for hit in state.get("recipe_hits", []):
            st.markdown(f"**{hit.get('title', hit.get('recipe_id'))}** · score {hit.get('score', '—')}")
        st.markdown("**Predicted tools:** " + ", ".join(state.get("predicted_tools", [])))
        st.markdown("**Predicted scopes:** " + ", ".join(state.get("predicted_scopes", [])))
        grants = state.get("grants", [])
        if grants:
            st.markdown("**Active grants**")
            for g in grants:
                st.markdown(f"- `{g.get('scope')}` → `{g.get('resource_id')}`")

    with tab2:
        for req in state.get("access_requests", []):
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(
                    f"**{req.get('requested_tool_id')}** → `{req.get('requested_resource')}`"
                )
                st.caption(req.get("reason", ""))
                st.markdown(
                    decision_badge(req.get("status", "pending").upper()),
                    unsafe_allow_html=True,
                )
            with cols[1]:
                if req.get("status") == "pending":
                    if st.button("Approve (Bob)", key=f"appr_{req.get('request_id')}"):
                        try:
                            client().approve_request(req["request_id"])
                            st.session_state.pop("_ui", None)
                            st.rerun()
                        except Exception as e:
                            st.error(GatewayClient.format_error(e))

    with tab3:
        for d in state.get("policy_decisions", []):
            with st.expander(
                f"{d.get('tool_id')} @ {d.get('resource_id')} — {d.get('decision')}",
            ):
                show_decision(d.get("decision", ""))
                proof = d.get("proof") or d.get("proof_json")
                if isinstance(proof, str):
                    proof = json.loads(proof)
                if proof:
                    st.json(proof)

    with tab4:
        for ev in state.get("timeline", []):
            st.markdown(f"**{ev.get('event_type')}**")
            payload = ev.get("payload") or ev.get("event_json")
            if isinstance(payload, str):
                payload = json.loads(payload)
            st.json(payload)


def page_scenarios() -> None:
    hero("Demo scenarios", "One-click Person B paths — happy, approval, denial, learning.")

    token = ensure_token()
    if not token:
        return

    sid = st.session_state.session_id
    aid = st.session_state.agent_id
    c = client()

    scenarios = [
        (
            "Path 1 · Happy (Linear ALLOW)",
            "linear.create_issue",
            "linear_team:SALES",
            "ALLOW",
        ),
        (
            "Path 2 · Approval (Slack ESCALATE)",
            "slack.search_messages",
            "slack_channel:sales-acme",
            "ESCALATE_HUMAN",
        ),
        (
            "Path 3 · Denial (external post)",
            "slack.post_message",
            "slack_channel:external-partners",
            "DENY",
        ),
    ]

    for label, tool, resource, expected in scenarios:
        with st.expander(label, expanded=False):
            if st.button(f"Run {label}", key=f"sc_{tool}_{resource}"):
                try:
                    r = c.authorize(sid, aid, tool, resource, token)
                    got = r.get("decision")
                    if got == expected:
                        st.success(f"Expected {expected}")
                    else:
                        st.warning(f"Got {got}, expected {expected}")
                    show_decision(got, r.get("reason"))
                    json_block(r)
                except Exception as e:
                    st.error(GatewayClient.format_error(e))

    st.divider()
    st.markdown("#### Path 4 · Learning")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sync graph index"):
            try:
                r = c.index_recipes()
                st.success(f"Indexed: {r.get('indexed')}")
                json_block(r)
            except Exception as e:
                st.error(GatewayClient.format_error(e))
    with col2:
        if st.button("Propose recipe v4"):
            try:
                r = c.propose_recipe(sid)
                st.success(f"Proposal: {r.get('proposal_id')}")
                json_block(r)
            except Exception as e:
                st.error(GatewayClient.format_error(e))

    st.divider()
    st.markdown("#### Slack fixture (prompt injection)")
    if st.button("Search #sales-acme"):
        try:
            r = c.slack_search("slack_channel:sales-acme")
            st.json(r.get("messages", []))
            if r.get("prompt_injection"):
                st.markdown(
                    f'<div class="injection-warning">⚠ Prompt injection detected: '
                    f'{r["prompt_injection"]}</div>',
                    unsafe_allow_html=True,
                )
        except Exception as e:
            st.error(GatewayClient.format_error(e))


def page_mcp() -> None:
    hero("MCP Gateway", "JSON-RPC meta-server — initialize, tools/list, tools/call (RFC-03).")

    token = ensure_token()
    c = client()

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### initialize")
        if st.button("MCP initialize", key="mcp_init"):
            try:
                r = c.mcp("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "streamlit-ui", "version": "1.0"},
                })
                st.session_state["_mcp_init"] = r
            except Exception as e:
                st.error(GatewayClient.format_error(e))
        if "_mcp_init" in st.session_state:
            json_block(st.session_state["_mcp_init"]["result"], "Initialize result")

    with c2:
        st.markdown("#### tools/list")
        if st.button("List tools (session-scoped)", key="mcp_list"):
            try:
                r = c.mcp(
                    "tools/list",
                    {"_meta": {
                        "session_id": st.session_state.session_id,
                        "agent_id": st.session_state.agent_id,
                    }},
                    token=token,
                    req_id=2,
                )
                st.session_state["_mcp_tools"] = r
            except Exception as e:
                st.error(GatewayClient.format_error(e))
        if "_mcp_tools" in st.session_state:
            tools = st.session_state["_mcp_tools"].get("result", {}).get("tools", [])
            for t in tools:
                st.markdown(f"- `{t.get('name')}` — {t.get('description', '')[:60]}…")

    st.divider()
    st.markdown("#### tools/call")
    mcp_tool = st.selectbox(
        "MCP tool",
        [
            "auth.preflight_goal",
            "linear.create_issue",
            "slack.search_messages",
            "slack.post_message",
        ],
    )
    resource = st.text_input("Resource / channel", value="linear_team:SALES")
    if st.button("Call tool (JWT required)", key="mcp_call"):
        if not token:
            st.error("Mint JWT first")
            return
        args: dict[str, Any] = {
            "session_id": st.session_state.session_id,
            "agent_id": st.session_state.agent_id,
        }
        if mcp_tool == "slack.search_messages":
            args["channel"] = resource
        elif mcp_tool == "linear.create_issue":
            args["resource_id"] = resource
            args["title"] = "Acme renewal follow-up"
        elif mcp_tool == "slack.post_message":
            args["resource_id"] = resource
            args["text"] = "demo message"
        try:
            r = c.mcp(
                "tools/call",
                {"name": mcp_tool, "arguments": args},
                token=token,
                req_id=3,
            )
            st.session_state["_mcp_call"] = r
        except Exception as e:
            st.error(GatewayClient.format_error(e))

    if "_mcp_call" in st.session_state:
        resp = st.session_state["_mcp_call"]
        if "error" in resp:
            st.error(resp["error"])
        else:
            result = resp.get("result", {})
            is_err = result.get("isError", False)
            text = result.get("content", [{}])[0].get("text", "")
            try:
                parsed = json.loads(text)
                if is_err:
                    show_decision(parsed.get("decision", "ERROR"), parsed.get("reason"))
                else:
                    show_decision(parsed.get("decision", "OK"))
                st.json(parsed)
            except json.JSONDecodeError:
                st.code(text)
        json_block(resp, "Raw JSON-RPC response")


def main() -> None:
    st.set_page_config(
        page_title="ScopeMemory Demo",
        page_icon="🛡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    init_session_state(DEFAULTS)
    sidebar()

    pages = {
        "Overview": page_overview,
        "Agentic Identity": page_identity,
        "Authorization": page_authorization,
        "Session dashboard": page_session,
        "Demo scenarios": page_scenarios,
        "MCP Gateway": page_mcp,
    }

    choice = st.radio(
        "Navigate",
        list(pages.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.divider()
    pages[choice]()


if __name__ == "__main__":
    main()
