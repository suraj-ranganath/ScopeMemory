"""Policy engine — deterministic rules aligned with RFC-02 demo policy."""

from __future__ import annotations

from typing import Any

from config import TRUST_SCORE_SENSITIVE


def evaluate(facts: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Deterministic ALLOW / DENY / ESCALATE."""
    rules: list[str] = []

    if not facts.get("delegation_present"):
        return "DENY", "no delegation for agent on session", ["deny_no_delegation"]

    trust = facts.get("agent_trust_score")
    if trust is not None and trust < 0.5:
        return "DENY", "agent trust score below minimum", ["deny_low_trust"]

    if not facts.get("same_team"):
        return "DENY", "resource not owned by session team", ["deny_wrong_team"]

    if not facts.get("recipe_predicts_tool"):
        return "DENY", "recipe did not predict this tool", ["deny_unpredicted_tool"]

    if facts.get("resource_external") and facts.get("access_kind") == "write":
        if trust is not None and trust < TRUST_SCORE_SENSITIVE:
            rules.append("escalate_low_trust_external")
            return "ESCALATE_HUMAN", "external write requires higher agent trust", rules
        if not facts.get("grant_present"):
            return "DENY", "external write not granted", ["deny_external_write"]

    if facts.get("grant_present"):
        rules.append("allow_grant")
        return "ALLOW", "grant exists for scope@resource", rules

    if facts.get("scope_approval_mode") == "human_required" and not facts.get("grant_present"):
        rules.append("escalate_human")
        return "ESCALATE_HUMAN", "scope requires human approval", rules

    if facts.get("scope_approval_mode") == "auto_approve" and facts.get("recipe_predicts_tool") and facts.get("same_team"):
        rules.append("auto_approve_recipe")
        return "ALLOW", "recipe auto-approves scope for team resource", rules

    return "DENY", "no grant and scope not auto-approved", ["deny_default"]


def export_facts(facts: dict[str, Any]) -> list[str]:
    keys = (
        "delegation_present", "recipe_predicts_tool", "same_team",
        "grant_present", "resource_external", "access_kind", "scope_approval_mode",
        "agent_trust_score",
    )
    out = []
    for k in keys:
        v = facts.get(k)
        if isinstance(v, bool):
            out.append(f"{k}={int(v)}")
        elif v is None:
            out.append(f"{k}=null")
        else:
            out.append(f"{k}={v!r}")
    return out
