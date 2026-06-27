"""Policy engine — CozoDB-compatible rules; Python evaluator for reliable demo."""

from __future__ import annotations

from typing import Any


def evaluate(facts: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Deterministic ALLOW / DENY / ESCALATE (same rules as RFC-02 demo policy)."""
    rules: list[str] = []

    if not facts.get("delegation_present"):
        return "DENY", "no delegation for agent on session", ["deny_no_delegation"]

    if not facts.get("same_team"):
        return "DENY", "resource not owned by session team", ["deny_wrong_team"]

    if not facts.get("recipe_predicts_tool"):
        return "DENY", "recipe did not predict this tool", ["deny_unpredicted_tool"]

    if facts.get("resource_external") and facts.get("access_kind") == "write" and not facts.get("grant_present"):
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
    """Facts snapshot for proof (CozoDB projection in Phase 2)."""
    keys = (
        "delegation_present", "recipe_predicts_tool", "same_team",
        "grant_present", "resource_external", "access_kind", "scope_approval_mode",
    )
    return [f"{k}={int(bool(facts.get(k))) if isinstance(facts.get(k), bool) else facts.get(k)!r}" for k in keys]
