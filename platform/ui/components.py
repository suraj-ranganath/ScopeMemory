"""ScopeMemory Streamlit UI components."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

DECISION_COLORS = {
    "ALLOW": "#22c55e",
    "DENY": "#ef4444",
    "ESCALATE_HUMAN": "#f59e0b",
}


def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=JetBrains+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {
            font-family: 'DM Sans', sans-serif;
        }

        .block-container { padding-top: 1.5rem; max-width: 1200px; }

        .hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 1.75rem 2rem;
            margin-bottom: 1.5rem;
        }
        .hero h1 { color: #f8fafc; font-size: 1.75rem; margin: 0 0 0.35rem 0; font-weight: 700; }
        .hero p { color: #94a3b8; margin: 0; font-size: 0.95rem; }

        .metric-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin: 1rem 0; }
        .metric-card {
            flex: 1; min-width: 140px;
            background: #1e293b; border: 1px solid #334155;
            border-radius: 12px; padding: 0.85rem 1rem;
        }
        .metric-card .label { color: #64748b; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
        .metric-card .value { color: #f1f5f9; font-size: 1.05rem; font-weight: 600; margin-top: 0.2rem; }

        .badge {
            display: inline-block; padding: 0.2rem 0.65rem; border-radius: 999px;
            font-size: 0.75rem; font-weight: 600; letter-spacing: 0.02em;
        }
        .badge-allow { background: #14532d; color: #86efac; }
        .badge-deny { background: #450a0a; color: #fca5a5; }
        .badge-escalate { background: #451a03; color: #fcd34d; }

        .tuple-box {
            background: #0f172a; border: 1px solid #334155; border-radius: 8px;
            padding: 0.75rem 1rem; font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem; color: #cbd5e1; line-height: 1.6;
            max-height: 220px; overflow-y: auto;
        }

        .injection-warning {
            background: #450a0a; border: 1px solid #dc2626; border-radius: 8px;
            padding: 0.75rem 1rem; color: #fecaca; font-size: 0.85rem; margin-top: 0.5rem;
        }

        div[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def metrics_row(items: list[tuple[str, str]]) -> None:
    cards = "".join(
        f'<div class="metric-card"><div class="label">{label}</div><div class="value">{value}</div></div>'
        for label, value in items
    )
    st.markdown(f'<div class="metric-row">{cards}</div>', unsafe_allow_html=True)


def decision_badge(decision: str) -> str:
    css = {
        "ALLOW": "badge-allow",
        "DENY": "badge-deny",
        "ESCALATE_HUMAN": "badge-escalate",
    }.get(decision, "badge-escalate")
    return f'<span class="badge {css}">{decision}</span>'


def show_decision(decision: str, reason: str | None = None) -> None:
    st.markdown(decision_badge(decision), unsafe_allow_html=True)
    if reason:
        st.caption(reason)


def rebac_tuples(tuples: list[str]) -> None:
    if not tuples:
        st.info("No ReBAC tuples")
        return
    body = "<br>".join(tuples)
    st.markdown(f'<div class="tuple-box">{body}</div>', unsafe_allow_html=True)


def json_block(data: Any, label: str = "Response") -> None:
    with st.expander(label, expanded=False):
        st.code(json.dumps(data, indent=2, default=str), language="json")


def init_session_state(defaults: dict[str, Any]) -> None:
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
