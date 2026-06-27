"""Safe MCP response views that do not depend on the runtime stack."""

from __future__ import annotations

import json
from typing import Any


def redact_decision_rows(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted = []
    for row in decisions:
        item = dict(row)
        proof = item.get("proof_json")
        if isinstance(proof, str):
            try:
                item["proof_json"] = json.loads(proof)
            except json.JSONDecodeError:
                item["proof_json"] = {"unparsed": True}
        redacted.append(item)
    return redacted


def explain_denial(decisions: list[dict[str, Any]], decision_id: str | None = None) -> dict[str, Any]:
    selected = None
    for decision in decisions:
        if decision_id and decision.get("decision_id") != decision_id:
            continue
        if decision_id or decision.get("decision") in {"DENY", "ESCALATE_HUMAN", "REPAIR"}:
            selected = decision
            break
    if selected is None:
        return {
            "found": False,
            "message": "no denied, repairable, or escalated policy decision found for this session",
        }
    proof = selected.get("proof_json") if isinstance(selected.get("proof_json"), dict) else {}
    rules = proof.get("rules") or []
    return {
        "found": True,
        "decision_id": selected.get("decision_id"),
        "tool_id": selected.get("tool_id"),
        "resource_id": selected.get("resource_id"),
        "reason": proof.get("reason") or "policy denied this call",
        "primary_rule": rules[0] if rules else "",
        "required_scope": proof.get("required_scope", ""),
        "context_path": proof.get("context_path", []),
        "repair": "use auth.request_scope only when the decision is ESCALATE_HUMAN; denied calls require a recipe/policy change",
    }


def redact_text(value: Any) -> str:
    text = str(value)
    lowered = text.lower()
    if "authorization: bearer " in lowered or "op://" in lowered:
        return "[redacted]"
    return text
