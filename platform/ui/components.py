"""ScopeMemory Policy Console — product UI components."""

from __future__ import annotations

import html
import json
from typing import Any

import streamlit as st

DECISION_META = {
    "ALLOW": ("Allowed", "badge-allow", "#22c55e"),
    "DENY": ("Denied", "badge-deny", "#ef4444"),
    "ESCALATE_HUMAN": ("Needs approval", "badge-escalate", "#f59e0b"),
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 0.75rem; max-width: 1280px; }
        #MainMenu, footer, header { visibility: hidden; }

        .product-shell {
            background: linear-gradient(180deg, #070b14 0%, #0c1220 100%);
            min-height: 100vh;
        }

        .product-topbar {
            display: flex; align-items: center; justify-content: space-between;
            padding: 0.85rem 0 1.25rem 0;
            border-bottom: 1px solid #1e293b;
            margin-bottom: 1.25rem;
        }
        .brand { display: flex; align-items: center; gap: 0.85rem; }
        .brand-mark {
            width: 40px; height: 40px; border-radius: 10px;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; color: white; font-size: 1.1rem;
        }
        .brand-title { color: #f8fafc; font-size: 1.15rem; font-weight: 700; margin: 0; }
        .brand-sub { color: #64748b; font-size: 0.78rem; margin: 0; }

        .principle-banner {
            background: linear-gradient(90deg, rgba(99,102,241,0.12), rgba(139,92,246,0.08));
            border: 1px solid rgba(99,102,241,0.25);
            border-radius: 12px; padding: 0.9rem 1.15rem; margin-bottom: 1.25rem;
            color: #cbd5e1; font-size: 0.92rem; line-height: 1.5;
        }
        .principle-banner strong { color: #e2e8f0; }

        .section-title {
            color: #94a3b8; font-size: 0.72rem; font-weight: 600;
            text-transform: uppercase; letter-spacing: 0.08em; margin: 0 0 0.65rem 0;
        }

        .panel {
            background: #111827; border: 1px solid #1f2937;
            border-radius: 14px; padding: 1.1rem 1.2rem; margin-bottom: 1rem;
        }
        .panel-accent { border-color: rgba(99,102,241,0.35); }

        .metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1rem; }
        @media (max-width: 900px) { .metric-grid { grid-template-columns: repeat(2, 1fr); } }
        .metric {
            background: #0f172a; border: 1px solid #1e293b; border-radius: 12px;
            padding: 0.85rem 1rem;
        }
        .metric .k { color: #64748b; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em; }
        .metric .v { color: #f1f5f9; font-size: 1rem; font-weight: 600; margin-top: 0.25rem; }

        .badge {
            display: inline-flex; align-items: center; gap: 0.35rem;
            padding: 0.25rem 0.7rem; border-radius: 999px;
            font-size: 0.72rem; font-weight: 600;
        }
        .badge-allow { background: rgba(34,197,94,0.15); color: #86efac; border: 1px solid rgba(34,197,94,0.35); }
        .badge-deny { background: rgba(239,68,68,0.15); color: #fca5a5; border: 1px solid rgba(239,68,68,0.35); }
        .badge-escalate { background: rgba(245,158,11,0.15); color: #fcd34d; border: 1px solid rgba(245,158,11,0.35); }
        .badge-neutral { background: rgba(100,116,139,0.15); color: #94a3b8; border: 1px solid rgba(100,116,139,0.35); }
        .badge-live { background: rgba(34,197,94,0.12); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); }

        .identity-chain {
            display: flex; align-items: center; flex-wrap: wrap; gap: 0.35rem;
            padding: 0.85rem; background: #0b1020; border-radius: 10px;
            border: 1px dashed #334155; margin: 0.5rem 0;
        }
        .chain-node {
            background: #1e293b; border: 1px solid #334155; border-radius: 8px;
            padding: 0.45rem 0.75rem; font-size: 0.78rem; color: #e2e8f0;
        }
        .chain-node .type { color: #64748b; font-size: 0.65rem; text-transform: uppercase; }
        .chain-arrow { color: #6366f1; font-weight: 700; padding: 0 0.15rem; }

        .context-path {
            display: flex; flex-wrap: wrap; align-items: center; gap: 0.25rem;
            font-family: 'JetBrains Mono', monospace; font-size: 0.74rem;
        }
        .path-step {
            background: #1e293b; color: #cbd5e1; padding: 0.3rem 0.55rem;
            border-radius: 6px; border: 1px solid #334155;
        }
        .path-arrow { color: #475569; }

        .tuple-list {
            font-family: 'JetBrains Mono', monospace; font-size: 0.74rem;
            color: #94a3b8; line-height: 1.7; max-height: 200px; overflow-y: auto;
        }

        .decision-hero {
            text-align: center; padding: 1.25rem; border-radius: 12px; margin: 0.5rem 0;
        }
        .decision-hero.allow { background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.25); }
        .decision-hero.deny { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25); }
        .decision-hero.escalate { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25); }
        .decision-hero .label { font-size: 1.35rem; font-weight: 700; color: #f8fafc; }
        .decision-hero .reason { color: #94a3b8; font-size: 0.88rem; margin-top: 0.35rem; }

        .trust-bar {
            height: 6px; background: #1e293b; border-radius: 999px; overflow: hidden; margin-top: 0.4rem;
        }
        .trust-fill { height: 100%; background: linear-gradient(90deg, #6366f1, #22c55e); border-radius: 999px; }

        .approval-card {
            background: #0f172a; border: 1px solid #334155; border-left: 3px solid #f59e0b;
            border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.65rem;
        }

        .injection-warning {
            background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.35);
            border-radius: 10px; padding: 0.75rem 1rem; color: #fecaca; font-size: 0.85rem;
        }

        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #070b14 0%, #0f172a 100%);
            border-right: 1px solid #1e293b;
        }
        div[data-testid="stSidebar"] .stRadio label {
            font-size: 0.88rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def product_header() -> None:
    st.markdown(
        """
        <div class="product-topbar">
          <div class="brand">
            <div class="brand-mark">S</div>
            <div>
              <p class="brand-title">ScopeMemory</p>
              <p class="brand-sub">Agentic Identity Policy Console</p>
            </div>
          </div>
        </div>
        <div class="principle-banner">
          <strong>Agentic-IAM</strong> knows <em>who</em> the agent is.
          <strong>ScopeMemory</strong> decides <em>what</em> it may do — via relationship-based policy, not broad roles.
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(f'<p class="section-title">{html.escape(title)}</p>', unsafe_allow_html=True)


def metric_grid(items: list[tuple[str, str]]) -> None:
    cards = "".join(
        f'<div class="metric"><div class="k">{html.escape(k)}</div><div class="v">{html.escape(v)}</div></div>'
        for k, v in items
    )
    st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)


def decision_badge(decision: str, label: str | None = None) -> str:
    meta = DECISION_META.get(decision, (decision, "badge-neutral", "#94a3b8"))
    text = label or meta[0]
    return f'<span class="badge {meta[1]}">{html.escape(text)}</span>'


def live_badge(text: str = "Delegation active") -> str:
    return f'<span class="badge badge-live">● {html.escape(text)}</span>'


def decision_hero(decision: str, reason: str | None = None) -> None:
    css = {"ALLOW": "allow", "DENY": "deny", "ESCALATE_HUMAN": "escalate"}.get(decision, "escalate")
    label = DECISION_META.get(decision, (decision, "", ""))[0]
    reason_html = f'<div class="reason">{html.escape(reason)}</div>' if reason else ""
    st.markdown(
        f'<div class="decision-hero {css}"><div class="label">{html.escape(label)}</div>{reason_html}</div>',
        unsafe_allow_html=True,
    )


def identity_chain(user_id: str, agent_id: str, session_id: str, identity_ref: str | None = None) -> None:
    ref = f'<div class="type">identity</div>{html.escape(identity_ref or "—")}' if identity_ref else ""
    st.markdown(
        f"""
        <div class="identity-chain">
          <div class="chain-node"><div class="type">Human</div>{html.escape(user_id)}</div>
          <span class="chain-arrow">→ delegates →</span>
          <div class="chain-node"><div class="type">Agent</div>{html.escape(agent_id)}</div>
          {f'<span class="chain-arrow">→</span><div class="chain-node">{ref}</div>' if identity_ref else ''}
          <span class="chain-arrow">→ session →</span>
          <div class="chain-node"><div class="type">Session</div>{html.escape(session_id)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def agent_profile(name: str, agent_id: str, identity_ref: str, trust: float, source: str) -> None:
    pct = min(max(trust * 100, 0), 100)
    st.markdown(
        f"""
        <div class="panel panel-accent">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
              <div style="color:#f8fafc;font-weight:700;font-size:1.05rem;">{html.escape(name)}</div>
              <div style="color:#64748b;font-size:0.78rem;margin-top:0.2rem;">{html.escape(agent_id)}</div>
            </div>
            {live_badge("Verified agent")}
          </div>
          <div style="margin-top:0.75rem;color:#94a3b8;font-size:0.78rem;font-family:'JetBrains Mono',monospace;">
            {html.escape(identity_ref)}
          </div>
          <div style="margin-top:0.65rem;color:#64748b;font-size:0.72rem;">Trust score · IAM source: {html.escape(source)}</div>
          <div class="trust-bar"><div class="trust-fill" style="width:{pct}%;"></div></div>
          <div style="color:#e2e8f0;font-size:0.82rem;margin-top:0.25rem;">{trust:.0%}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def context_path_steps(steps: list[str]) -> None:
    if not steps:
        st.caption("No context path")
        return
    parts = []
    for i, step in enumerate(steps):
        if i:
            parts.append('<span class="path-arrow">→</span>')
        parts.append(f'<span class="path-step">{html.escape(step)}</span>')
    st.markdown(f'<div class="context-path">{"".join(parts)}</div>', unsafe_allow_html=True)


def rebac_tuples(tuples: list[str], title: str = "ReBAC policy tuples") -> None:
    section(title)
    if not tuples:
        st.info("No relationship tuples loaded.")
        return
    body = "<br>".join(html.escape(t) for t in tuples)
    st.markdown(f'<div class="tuple-list">{body}</div>', unsafe_allow_html=True)


def approval_card(tool: str, resource: str, scope: str, reason: str, status: str) -> None:
    st.markdown(
        f"""
        <div class="approval-card">
          <div style="color:#f8fafc;font-weight:600;">{html.escape(tool)}</div>
          <div style="color:#94a3b8;font-size:0.82rem;margin-top:0.25rem;">
            {html.escape(scope)} → {html.escape(resource)}
          </div>
          <div style="color:#64748b;font-size:0.78rem;margin-top:0.35rem;">{html.escape(reason[:120])}</div>
          <div style="margin-top:0.5rem;">{decision_badge(status.upper() if status != "pending" else "ESCALATE_HUMAN", status.title())}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def policy_row(tool: str, resource: str, decision: str, reason: str | None = None) -> None:
    reason_html = f'<div style="color:#64748b;font-size:0.78rem;margin-top:0.2rem;">{html.escape(reason or "")}</div>'
    st.markdown(
        f"""
        <div class="panel" style="padding:0.75rem 1rem;margin-bottom:0.5rem;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:0.5rem;">
            <div>
              <div style="color:#f1f5f9;font-weight:600;font-size:0.88rem;">{html.escape(tool)}</div>
              <div style="color:#64748b;font-size:0.76rem;font-family:'JetBrains Mono',monospace;">{html.escape(resource)}</div>
            </div>
            {decision_badge(decision)}
          </div>
          {reason_html if reason else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def dev_json(data: Any, label: str = "Developer · raw response") -> None:
    with st.expander(label):
        st.code(json.dumps(data, indent=2, default=str), language="json")


def init_session_state(defaults: dict[str, Any]) -> None:
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
