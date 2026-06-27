#!/usr/bin/env python3
"""
ScopeMemory Policy Console — Agentic Identity product UI.

Run (gateway on :8080):
    cd platform && ./run_ui.sh
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from ui.client import GatewayClient
from ui.components import (
    agent_profile,
    approval_card,
    context_path_steps,
    decision_hero,
    dev_json,
    identity_chain,
    init_session_state,
    inject_css,
    live_badge,
    metric_grid,
    policy_row,
    product_header,
    rebac_tuples,
    section,
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

NAV = [
    "Policy Console",
    "Delegation & Identity",
    "Tool Authorization",
    "Human Approvals",
    "Audit Trail",
    "Advanced",
]


def client() -> GatewayClient:
    return GatewayClient(st.session_state.gateway_url)


def ensure_token() -> str | None:
    if st.session_state.delegation_token:
        return st.session_state.delegation_token
    try:
        st.session_state.delegation_token = client().mint_token(st.session_state.session_id)
        return st.session_state.delegation_token
    except Exception:
        return None


def load_console_data(force: bool = False) -> None:
    if st.session_state.get("_console_loaded") and not force:
        return
    c = client()
    sid = st.session_state.session_id
    aid = st.session_state.agent_id
    try:
        st.session_state["_health"] = c.health()
        st.session_state["_agent"] = c.get_agent(aid)
        st.session_state["_proof"] = c.identity_proof(sid)
        st.session_state["_ui"] = c.ui_state(sid)
        ensure_token()
        token = st.session_state.delegation_token
        if token:
            st.session_state["_preflight"] = c.preflight(sid, aid, token)
        st.session_state["_console_loaded"] = True
    except Exception as e:
        st.session_state["_console_error"] = GatewayClient.format_error(e)


def sidebar() -> str:
    with st.sidebar:
        st.markdown(
            """
            <div style="padding:0.5rem 0 1rem 0;">
              <div style="color:#f8fafc;font-weight:700;font-size:1rem;">Policy Console</div>
              <div style="color:#64748b;font-size:0.75rem;">Agentic Identity · ReBAC</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        page = st.radio("Navigate", NAV, label_visibility="collapsed")

        st.divider()
        section("Active session")
        st.session_state.session_id = st.text_input("Session", st.session_state.session_id, label_visibility="collapsed")
        st.session_state.agent_id = st.text_input("Agent", st.session_state.agent_id, label_visibility="collapsed")

        if st.session_state.delegation_token:
            st.markdown(live_badge("JWT delegation active"), unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge badge-neutral">No delegation token</span>', unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Refresh", use_container_width=True):
                st.session_state.pop("_console_loaded", None)
                load_console_data(force=True)
                st.rerun()
        with col_b:
            if st.button("Reseed", use_container_width=True):
                try:
                    client().reseed()
                    st.session_state.delegation_token = client().mint_token(st.session_state.session_id)
                    st.session_state.pop("_console_loaded", None)
                    load_console_data(force=True)
                    st.rerun()
                except Exception as e:
                    st.error(GatewayClient.format_error(e))

        with st.expander("Connection"):
            st.session_state.gateway_url = st.text_input("Gateway URL", st.session_state.gateway_url)
            if st.button("Mint delegation JWT", use_container_width=True):
                try:
                    st.session_state.delegation_token = client().mint_token(st.session_state.session_id)
                    st.rerun()
                except Exception as e:
                    st.error(GatewayClient.format_error(e))

        try:
            h = st.session_state.get("_health") or client().health()
            st.caption(f"● Online · {h.get('graph_backend')} · IAM {h.get('iam_mode')}")
        except Exception:
            st.caption("● Gateway offline")

        return page


def page_console() -> None:
    if st.session_state.get("_console_error"):
        st.error(f"Could not connect: {st.session_state['_console_error']}")
        st.info("Start backend: `docker compose --profile gateway-docker up -d --build`")
        return

    agent = st.session_state.get("_agent", {})
    proof = st.session_state.get("_proof", {})
    ui = st.session_state.get("_ui", {})
    session = ui.get("session", {})
    pf = st.session_state.get("_preflight", {})

    metric_grid([
        ("Agent trust", f"{agent.get('trust_score', 0):.0%}" if agent else "—"),
        ("Delegation", "Verified" if proof.get("delegation_present") else "Missing"),
        ("Recipe match", str(len(pf.get("recipe_hits", [])))),
        ("Pending approvals", str(len([r for r in ui.get("access_requests", []) if r.get("status") == "pending"]))),
    ])

    left, right = st.columns([1.1, 1])

    with left:
        section("Identity chain")
        identity_chain(
            st.session_state.user_id,
            st.session_state.agent_id,
            st.session_state.session_id,
            agent.get("identity_ref") or proof.get("identity_ref"),
        )

        section("Session goal")
        st.markdown(
            f'<div class="panel"><div style="color:#e2e8f0;font-size:0.92rem;">{session.get("goal", st.session_state.goal)}</div>'
            f'<div style="color:#64748b;font-size:0.78rem;margin-top:0.5rem;">Class: {session.get("goal_class", st.session_state.goal_class)} · Team: {st.session_state.team_id}</div></div>',
            unsafe_allow_html=True,
        )

        section("Matched workflow recipe")
        for hit in pf.get("recipe_hits", ui.get("recipe_hits", [])):
            st.markdown(
                f'<div class="panel" style="padding:0.75rem 1rem;">'
                f'<div style="color:#f1f5f9;font-weight:600;">{hit.get("title", hit.get("recipe_id"))}</div>'
                f'<div style="color:#64748b;font-size:0.78rem;">Score {hit.get("score", "—")} · predicts {", ".join(hit.get("predicted_tools", [])[:2])}</div></div>',
                unsafe_allow_html=True,
            )

    with right:
        if agent:
            agent_profile(
                agent.get("display_name", st.session_state.agent_id),
                st.session_state.agent_id,
                agent.get("identity_ref", ""),
                float(agent.get("trust_score", 0)),
                agent.get("source", "iam"),
            )

        section("Recent policy decisions")
        decisions = ui.get("policy_decisions", [])
        if not decisions:
            st.info("Run tool authorization to see policy outcomes.")
        for d in reversed(decisions[-5:]):
            policy_row(d.get("tool_id", ""), d.get("resource_id", ""), d.get("decision", ""))

        pending = [r for r in ui.get("access_requests", []) if r.get("status") == "pending"]
        if pending:
            section("Awaiting human approval")
            for r in pending[:2]:
                approval_card(
                    r.get("requested_tool_id", ""),
                    r.get("requested_resource", ""),
                    r.get("requested_scope", ""),
                    r.get("reason", ""),
                    r.get("status", "pending"),
                )


def page_delegation() -> None:
    section("Agent registry · Agentic-IAM")
    c1, c2 = st.columns(2)

    with c1:
        if st.button("Refresh agent profile", use_container_width=True):
            try:
                st.session_state["_agent"] = client().get_agent(st.session_state.agent_id)
            except Exception as e:
                st.error(GatewayClient.format_error(e))

        agent = st.session_state.get("_agent")
        if agent:
            agent_profile(
                agent.get("display_name", ""),
                agent.get("agent_id", ""),
                agent.get("identity_ref", ""),
                float(agent.get("trust_score", 0)),
                agent.get("source", ""),
            )
            dev_json(agent)

    with c2:
        section("Create new delegation")
        goal = st.text_area("Task goal", st.session_state.goal, height=90)
        if st.button("Delegate agent to task", type="primary", use_container_width=True):
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
                st.session_state.pop("_console_loaded", None)
                st.success("Delegation created — signed JWT issued")
                dev_json(r)
                st.rerun()
            except Exception as e:
                st.error(GatewayClient.format_error(e))

    st.divider()
    section("Identity proof · ReBAC chain")

    if st.button("Load identity proof", use_container_width=True):
        try:
            st.session_state["_proof"] = client().identity_proof(st.session_state.session_id)
        except Exception as e:
            st.error(GatewayClient.format_error(e))

    proof = st.session_state.get("_proof", {})
    if proof:
        identity_chain(
            proof.get("user_id", st.session_state.user_id),
            proof.get("agent_id", st.session_state.agent_id),
            st.session_state.session_id,
            proof.get("identity_ref"),
        )
        rebac_tuples(proof.get("rebac_tuples", []))
        dev_json(proof)


def page_authorization() -> None:
    token = ensure_token()
    if not token:
        st.warning("Mint a delegation JWT from the sidebar to authorize tool calls.")
        return

    section("Step 1 · Preflight goal memory")
    if st.button("Run preflight", use_container_width=True):
        try:
            st.session_state["_preflight"] = client().preflight(
                st.session_state.session_id, st.session_state.agent_id, token,
            )
        except Exception as e:
            st.error(GatewayClient.format_error(e))

    pf = st.session_state.get("_preflight", {})
    if pf:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Predicted tools**")
            for t in pf.get("predicted_tools", []):
                st.markdown(f"- `{t}`")
        with c2:
            st.markdown("**Predicted scopes**")
            for s in pf.get("predicted_scopes", []):
                st.markdown(f"- `{s}`")
        rebac_tuples(pf.get("rebac_tuples", []), "Preflight ReBAC context")

    st.divider()
    section("Step 2 · Evaluate tool call policy")

    tool_id = st.selectbox(
        "MCP tool",
        ["linear.create_issue", "slack.search_messages", "slack.post_message"],
        format_func=lambda t: {
            "linear.create_issue": "Linear · Create issue",
            "slack.search_messages": "Slack · Search messages",
            "slack.post_message": "Slack · Post message",
        }.get(t, t),
    )
    defaults = {
        "linear.create_issue": "linear_team:SALES",
        "slack.search_messages": "slack_channel:sales-acme",
        "slack.post_message": "slack_channel:external-partners",
    }
    resource_id = st.text_input("Target resource", defaults.get(tool_id, ""))

    if st.button("Evaluate policy", type="primary", use_container_width=True):
        try:
            r = client().authorize(
                st.session_state.session_id,
                st.session_state.agent_id,
                tool_id,
                resource_id,
                token,
            )
            st.session_state["_last_auth"] = r
            st.session_state.pop("_console_loaded", None)
            load_console_data(force=True)
        except Exception as e:
            st.error(GatewayClient.format_error(e))

    if "_last_auth" in st.session_state:
        auth = st.session_state["_last_auth"]
        decision_hero(auth.get("decision", ""), auth.get("reason"))
        section("Context path · proof trace")
        context_path_steps(auth.get("proof", {}).get("context_path", []))
        rebac_tuples(auth.get("proof", {}).get("rebac_tuples", []), "Policy ReBAC tuples")
        dev_json(auth)

    st.divider()
    section("Guided policy scenarios")
    scenarios = [
        ("Auto-approved Linear write", "linear.create_issue", "linear_team:SALES", "ALLOW"),
        ("Slack read needs approval", "slack.search_messages", "slack_channel:sales-acme", "ESCALATE_HUMAN"),
        ("External post blocked", "slack.post_message", "slack_channel:external-partners", "DENY"),
    ]
    cols = st.columns(3)
    for i, (label, tool, res, _) in enumerate(scenarios):
        with cols[i]:
            if st.button(label, key=f"sc_{i}", use_container_width=True):
                try:
                    r = client().authorize(
                        st.session_state.session_id, st.session_state.agent_id,
                        tool, res, token,
                    )
                    st.session_state["_last_auth"] = r
                    st.rerun()
                except Exception as e:
                    st.error(GatewayClient.format_error(e))


def page_approvals() -> None:
    section("Human-in-the-loop · scope approvals")
    st.caption("When policy returns ESCALATE, a human approver grants scoped access.")

    ui = st.session_state.get("_ui") or {}
    try:
        ui = client().ui_state(st.session_state.session_id)
        st.session_state["_ui"] = ui
    except Exception as e:
        st.error(GatewayClient.format_error(e))
        return

    requests = ui.get("access_requests", [])
    pending = [r for r in requests if r.get("status") == "pending"]
    resolved = [r for r in requests if r.get("status") != "pending"]

    metric_grid([
        ("Pending", str(len(pending))),
        ("Resolved", str(len(resolved))),
        ("Active grants", str(len(ui.get("grants", [])))),
        ("Session status", ui.get("session", {}).get("status", "—")),
    ])

    if pending:
        for r in pending:
            approval_card(
                r.get("requested_tool_id", ""),
                r.get("requested_resource", ""),
                r.get("requested_scope", ""),
                r.get("reason", ""),
                "pending",
            )
            if st.button(f"Approve as Bob · {r.get('request_id')}", key=f"appr_{r.get('request_id')}"):
                try:
                    client().approve_request(r["request_id"])
                    st.session_state.pop("_console_loaded", None)
                    st.success("Scope approved — grant recorded in Dolt")
                    st.rerun()
                except Exception as e:
                    st.error(GatewayClient.format_error(e))
    else:
        st.success("No pending approval requests.")

    if resolved:
        st.divider()
        section("Resolved requests")
        for r in resolved:
            approval_card(
                r.get("requested_tool_id", ""),
                r.get("requested_resource", ""),
                r.get("requested_scope", ""),
                r.get("reason", ""),
                r.get("status", ""),
            )

    grants = ui.get("grants", [])
    if grants:
        st.divider()
        section("Active scope grants")
        for g in grants:
            st.markdown(
                f'<div class="panel" style="padding:0.65rem 1rem;">'
                f'<code>{g.get("scope")}</code> → <code>{g.get("resource_id")}</code></div>',
                unsafe_allow_html=True,
            )


def page_audit() -> None:
    section("Policy audit trail · Dolt-backed proofs")

    try:
        trail = client().proof_trail(st.session_state.session_id)
        ui = client().ui_state(st.session_state.session_id)
    except Exception as e:
        st.error(GatewayClient.format_error(e))
        return

    decisions = trail.get("decisions", []) or ui.get("policy_decisions", [])

    if not decisions:
        st.info("No policy decisions recorded yet. Authorize a tool call first.")
        return

    for d in reversed(decisions):
        proof_raw = d.get("proof_json") or d.get("proof")
        proof = json.loads(proof_raw) if isinstance(proof_raw, str) else (proof_raw or {})
        with st.expander(
            f"{d.get('tool_id')} · {d.get('decision')} · {d.get('resource_id', '')}",
            expanded=len(decisions) <= 3,
        ):
            decision_hero(d.get("decision", ""), proof.get("reason"))
            context_path_steps(proof.get("context_path", []))
            rebac_tuples(proof.get("rebac_tuples", []))
            if proof.get("rules"):
                st.markdown("**Rules fired:** " + ", ".join(proof["rules"]))
            dev_json(proof, "Full proof JSON")

    st.divider()
    section("Session timeline")
    for ev in ui.get("timeline", []):
        payload = ev.get("payload") or ev.get("event_json")
        if isinstance(payload, str):
            payload = json.loads(payload)
        st.markdown(f"**{ev.get('event_type')}**")
        dev_json(payload, "Event payload")


def page_advanced() -> None:
    section("MCP gateway · JSON-RPC transport")
    st.caption("Agents connect to ScopeMemory as a meta-MCP server. JWT required on tools/call.")

    token = ensure_token()
    c = client()

    if st.button("MCP initialize"):
        try:
            st.session_state["_mcp_init"] = c.mcp("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "policy-console", "version": "1.0"},
            })
        except Exception as e:
            st.error(GatewayClient.format_error(e))

    if st.button("List session tools"):
        try:
            st.session_state["_mcp_tools"] = c.mcp(
                "tools/list",
                {"_meta": {"session_id": st.session_state.session_id, "agent_id": st.session_state.agent_id}},
                token=token,
                req_id=2,
            )
        except Exception as e:
            st.error(GatewayClient.format_error(e))

    if "_mcp_tools" in st.session_state:
        tools = st.session_state["_mcp_tools"].get("result", {}).get("tools", [])
        for t in tools:
            st.markdown(f"- `{t.get('name')}`")

    st.divider()
    section("Recipe learning · graph index")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Sync recipe index"):
            try:
                dev_json(client().index_recipes())
            except Exception as e:
                st.error(GatewayClient.format_error(e))
    with c2:
        if st.button("Propose recipe v4"):
            try:
                dev_json(client().propose_recipe(st.session_state.session_id))
            except Exception as e:
                st.error(GatewayClient.format_error(e))

    st.divider()
    section("Prompt injection fixture")
    if st.button("Load Slack #sales-acme"):
        try:
            r = client().slack_search("slack_channel:sales-acme")
            st.json(r.get("messages", []))
            if r.get("prompt_injection"):
                st.markdown(
                    f'<div class="injection-warning">⚠ Injection in tool output (must not affect policy): '
                    f'{r["prompt_injection"]}</div>',
                    unsafe_allow_html=True,
                )
        except Exception as e:
            st.error(GatewayClient.format_error(e))

    if st.session_state.get("_health"):
        dev_json(st.session_state["_health"], "Gateway health")


def main() -> None:
    st.set_page_config(
        page_title="ScopeMemory · Policy Console",
        page_icon="🛡",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    init_session_state(DEFAULTS)

    try:
        load_console_data()
    except Exception:
        pass

    page = sidebar()
    product_header()

    routes = {
        "Policy Console": page_console,
        "Delegation & Identity": page_delegation,
        "Tool Authorization": page_authorization,
        "Human Approvals": page_approvals,
        "Audit Trail": page_audit,
        "Advanced": page_advanced,
    }
    routes[page]()


if __name__ == "__main__":
    main()
