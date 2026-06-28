"""CozoDB-backed Datalog policy engine for ScopeMemory authorization."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from config import TRUST_SCORE_MIN, TRUST_SCORE_SENSITIVE
from policy_contracts import (
    AuthorizationCheckState,
    Decision,
    PolicyDecision,
    PolicyProofTrace,
    Session,
    ToolIntent,
    stable_hash,
)


LOW_PRECEDENCE_DEFAULT_DENY = 10
TRUST_SENSITIVE_ESCALATION_PRECEDENCE = 75
PRECEDENCE = {
    Decision.DENY.value: 100,
    Decision.REPAIR.value: 80,
    Decision.ALLOW.value: 70,
    Decision.AUTO_APPROVE_EPHEMERAL_GRANT.value: 60,
    Decision.ESCALATE_HUMAN.value: 50,
}

DEFAULT_TOOL_RISK = {
    "linear.create_issue": "medium",
    "linear.search_issues": "low",
    "linear.add_comment": "medium",
    "slack.search_messages": "medium",
    "slack.post_message": "high",
}

HARD_DENY_PRECEDENCE = {
    "deny_low_trust": 110,
    "deny_direct_secret_read": 109,
    "deny_secret_exposure": 108,
    "deny_bulk_export": 107,
    "deny_goal_expansion": 106,
    "deny_admin_scope": 105,
    "deny_external_write": 104,
    "deny_unreified_recipe_hit": 103,
    "deny_missing_context_path": 102,
    "deny_no_delegation": 101,
    "deny_wrong_team": 100,
    "deny_unpredicted_tool": 99,
    "deny_schema_invalid": 98,
}

SECRET_MARKERS = (
    "password",
    "secret",
    "token",
    "private_key",
    "client_secret",
    "bearer",
)


@dataclass(frozen=True)
class CompiledPolicyFacts:
    session: Session
    intent: ToolIntent
    rows: dict[str, list[list[Any]]]
    facts: list[str]
    context_path: list[str]
    context_snapshot_id: str = ""
    dolt_commit: str = "demo-fixture"
    recipe_index_commit: str = "demo-fixture"
    fact_set_hash: str = ""


@dataclass(frozen=True)
class PolicyEvaluation:
    decision: Decision
    reason: str
    rule: str
    precedence: int
    candidates: list[dict[str, Any]] = field(default_factory=list)
    policy_engine: str = "cozo-datalog"


COZO_POLICY_RULES = """
session[s, user, team, agent, goal_class] <- $session
requested_tool[s, tool] <- $requested_tool
requested_resource[s, resource] <- $requested_resource
schema_state[s, tool, valid, repairable] <- $schema_state
tool_scope[tool, scope, access_kind, risk] <- $tool_scope
resource[resource, team, sensitivity, external] <- $resource
delegation[s, user, agent] <- $delegation
similar_recipe[s, recipe, score, status, reified] <- $similar_recipe
recipe_tool[recipe, tool] <- $recipe_tool
recipe_scope[recipe, scope, approval_mode] <- $recipe_scope
current_grant[s, scope, resource] <- $current_grant
context_path[s, tool, resource, scope, path_hash] <- $context_path
tool_credential_required[tool, credential_class] <- $tool_credential_required
credential_binding[binding, tool, scope, credential_ref, provider, ref_status, injection_mode, owner_team, exposes_secret] <- $credential_binding
judge_fact[s, tool, fact_name, fact_value, confidence] <- $judge_fact
violation[s, tool, resource, violation_type] <- $violation
policy_flag[s, flag_name, flag_value] <- $policy_flag
agent_trust_state[s, score, below_minimum, below_sensitive] <- $agent_trust_state

required_scope[s, tool, scope] :=
  requested_tool[s, tool],
  tool_scope[tool, scope, _access_kind, _risk]

recipe_predicts_tool[s, tool] :=
  similar_recipe[s, recipe, score, "accepted", true],
  score >= 0.82,
  recipe_tool[recipe, tool]

recipe_predicts_scope[s, scope] :=
  similar_recipe[s, recipe, score, "accepted", true],
  score >= 0.82,
  recipe_scope[recipe, scope, _approval_mode]

memory_consistent[s, tool, resource, scope] :=
  context_path[s, tool, resource, scope, _path_hash]

same_team_resource[s, resource] :=
  session[s, _user, team, _agent, _goal_class],
  resource[resource, team, _sensitivity, _external]

low_agent_trust[s] :=
  agent_trust_state[s, _score, true, _below_sensitive]

low_trust_external_write[s, tool, resource] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  required_scope[s, tool, scope],
  tool_scope[tool, scope, "write", _risk],
  resource[resource, _team, _sensitivity, true],
  agent_trust_state[s, _score, _below_minimum, true]

risk_auto_approvable[risk] <- [["low"], ["medium"]]

resource_auto_approvable[resource] :=
  resource[resource, _team, sensitivity, false],
  sensitivity in ["low", "normal"]

credential_ok[tool, scope] :=
  tool_scope[tool, scope, _access_kind, _risk],
  not tool_credential_required[tool, _credential_class]

credential_ok[tool, scope] :=
  tool_credential_required[tool, _credential_class],
  credential_binding[_binding, tool, scope, _credential_ref, _provider, "active", _injection_mode, _owner_team, false]

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  schema_state[s, tool, false, false],
  hard_precedence = 98,
  reason = "schema invalid and not safely repairable",
  rule = "deny_schema_invalid"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  session[s, user, _team, agent, _goal_class],
  not delegation[s, user, agent],
  hard_precedence = 101,
  reason = "no delegation for agent on session",
  rule = "deny_no_delegation"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  low_agent_trust[s],
  hard_precedence = 110,
  reason = "agent trust score below minimum",
  rule = "deny_low_trust"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  session[s, _user, team, _agent, _goal_class],
  resource[resource, resource_team, _sensitivity, _external],
  team != resource_team,
  hard_precedence = 100,
  reason = "resource not owned by session team",
  rule = "deny_wrong_team"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  schema_state[s, tool, true, _repairable],
  not recipe_predicts_tool[s, tool],
  hard_precedence = 99,
  reason = "recipe did not predict this tool",
  rule = "deny_unpredicted_tool"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  required_scope[s, tool, scope],
  tool_scope[tool, scope, "write", _risk],
  resource[resource, _team, _sensitivity, true],
  not policy_flag[s, "external_write_predicted", true],
  not low_trust_external_write[s, tool, resource],
  hard_precedence = 104,
  reason = "external write not predicted as safe",
  rule = "deny_external_write"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  required_scope[s, tool, scope],
  scope in ["admin", "linear:admin", "slack:admin", "scopememory:admin"],
  not policy_flag[s, "break_glass", true],
  hard_precedence = 105,
  reason = "admin scope requires break-glass approval",
  rule = "deny_admin_scope"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  violation[s, tool, resource, "direct_secret_read"],
  hard_precedence = 109,
  reason = "direct password-manager secret read bypasses broker",
  rule = "deny_direct_secret_read"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  violation[s, tool, resource, "secret_exposure"],
  hard_precedence = 108,
  reason = "request would expose secret material to the agent",
  rule = "deny_secret_exposure"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  violation[s, tool, resource, "bulk_export"],
  hard_precedence = 107,
  reason = "request attempts bulk export of protected data",
  rule = "deny_bulk_export"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  violation[s, tool, resource, "goal_expansion"],
  hard_precedence = 106,
  reason = "tool output attempted to expand the signed session goal",
  rule = "deny_goal_expansion"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  similar_recipe[s, _recipe, _score, "accepted", false],
  hard_precedence = 103,
  reason = "recipe retrieval hit was not reified against Dolt commit",
  rule = "deny_unreified_recipe_hit"

hard_deny[s, tool, resource, hard_precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  required_scope[s, tool, scope],
  policy_flag[s, "context_snapshot_present", true],
  not memory_consistent[s, tool, resource, scope],
  hard_precedence = 102,
  reason = "missing context path for graph-backed decision",
  rule = "deny_missing_context_path"

candidate[s, tool, resource, decision, precedence, reason, rule] :=
  hard_deny[s, tool, resource, precedence, reason, rule],
  decision = "DENY"

candidate[s, tool, resource, decision, precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  schema_state[s, tool, false, true],
  not hard_deny[s, tool, resource, _hard_precedence, _reason, _rule],
  decision = "REPAIR",
  precedence = 80,
  reason = "tool arguments can be safely repaired",
  rule = "repair_schema_args"

candidate[s, tool, resource, decision, precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  required_scope[s, tool, _scope],
  schema_state[s, tool, true, _repairable],
  recipe_predicts_tool[s, tool],
  same_team_resource[s, resource],
  low_trust_external_write[s, tool, resource],
  not hard_deny[s, tool, resource, _hard_precedence, _hard_reason, _hard_rule],
  decision = "ESCALATE_HUMAN",
  precedence = 75,
  reason = "external write requires higher agent trust",
  rule = "escalate_low_trust_external"

candidate[s, tool, resource, decision, precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  required_scope[s, tool, scope],
  schema_state[s, tool, true, _repairable],
  current_grant[s, scope, resource],
  same_team_resource[s, resource],
  recipe_predicts_tool[s, tool],
  memory_consistent[s, tool, resource, scope],
  not hard_deny[s, tool, resource, _hard_precedence, _reason, _rule],
  decision = "ALLOW",
  precedence = 70,
  reason = "grant exists for scope@resource",
  rule = "allow_current_grant"

candidate[s, tool, resource, decision, precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  required_scope[s, tool, scope],
  schema_state[s, tool, true, _repairable],
  recipe_predicts_tool[s, tool],
  recipe_predicts_scope[s, scope],
  recipe_scope[_recipe, scope, "auto_approve"],
  same_team_resource[s, resource],
  tool_scope[tool, scope, _access_kind, risk],
  risk_auto_approvable[risk],
  resource_auto_approvable[resource],
  credential_ok[tool, scope],
  not current_grant[s, scope, resource],
  not hard_deny[s, tool, resource, _hard_precedence, _reason, _rule],
  decision = "AUTO_APPROVE_EPHEMERAL_GRANT",
  precedence = 60,
  reason = "accepted recipe auto-approves a bounded ephemeral grant",
  rule = "auto_approve_recipe_scope"

candidate[s, tool, resource, decision, precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  required_scope[s, tool, scope],
  schema_state[s, tool, true, _repairable],
  recipe_predicts_tool[s, tool],
  recipe_predicts_scope[s, scope],
  recipe_scope[_recipe, scope, "human_required"],
  same_team_resource[s, resource],
  memory_consistent[s, tool, resource, scope],
  not current_grant[s, scope, resource],
  not hard_deny[s, tool, resource, _hard_precedence, _reason, _rule],
  decision = "ESCALATE_HUMAN",
  precedence = 50,
  reason = "scope requires human approval",
  rule = "escalate_human_required_scope"

candidate[s, tool, resource, decision, precedence, reason, rule] :=
  requested_tool[s, tool],
  requested_resource[s, resource],
  decision = "DENY",
  precedence = 10,
  reason = "no grant, auto-approval, or human approval path matched",
  rule = "deny_default"

max_precedence[max(precedence)] :=
  candidate[_s, _tool, _resource, _decision, precedence, _reason, _rule]
"""

COZO_EFFECTIVE_QUERY = (
    COZO_POLICY_RULES
    + """
?[decision, reason, rule, precedence] :=
  candidate[_s, _tool, _resource, decision, precedence, reason, rule],
  max_precedence[precedence]
"""
)

COZO_CANDIDATES_QUERY = (
    COZO_POLICY_RULES
    + """
?[decision, reason, rule, precedence] :=
  candidate[_s, _tool, _resource, decision, precedence, reason, rule]
:sort -precedence
"""
)


def compile_policy_facts(ctx: dict[str, Any]) -> CompiledPolicyFacts:
    raw_facts = dict(ctx.get("facts") or {})
    context_path = [str(v) for v in ctx.get("context_path") or [] if v is not None]
    session_id = str(ctx.get("session_id") or raw_facts.get("session_id") or "sess_unknown")
    tool_id = str(ctx.get("tool_id") or raw_facts.get("tool_id") or "tool.unknown")
    resource_id = str(ctx.get("resource_id") or raw_facts.get("resource_id") or "resource:unknown")

    recipe_id = str(ctx.get("recipe_id") or _path_at(context_path, 1, "recipe_unknown"))
    scope = str(ctx.get("scope") or raw_facts.get("scope") or _path_at(context_path, 3, "scope:unknown"))
    team_id = str(ctx.get("team_id") or raw_facts.get("session_team") or _path_at(context_path, 5, "team_unknown"))
    resource_team = str(ctx.get("resource_team") or raw_facts.get("resource_team") or (team_id if raw_facts.get("same_team") else "team_mismatch"))
    user_id = str(ctx.get("user_id") or raw_facts.get("user_id") or _path_at(context_path, 6, "user_unknown"))
    agent_id = str(ctx.get("agent_id") or raw_facts.get("agent_id") or _path_at(context_path, 7, "agent_unknown"))
    goal_class = str(ctx.get("goal_class") or raw_facts.get("goal_class") or "sales_renewal_prep")

    schema_valid = bool(raw_facts.get("schema_valid", True))
    schema_repairable = bool(raw_facts.get("schema_repairable", False))
    access_kind = str(ctx.get("access_kind") or raw_facts.get("access_kind") or "read")
    tool_risk = str(raw_facts.get("tool_risk") or DEFAULT_TOOL_RISK.get(tool_id, "medium"))
    resource_external = bool(raw_facts.get("resource_external", False))
    resource_sensitivity = str(raw_facts.get("resource_sensitivity") or ("high" if resource_external else "normal"))
    grant_present = bool(raw_facts.get("grant_present", False))
    delegation_present = bool(raw_facts.get("delegation_present", False))
    recipe_predicts_tool = bool(raw_facts.get("recipe_predicts_tool", False))
    approval_mode = raw_facts.get("scope_approval_mode")
    similarity_reified = bool(raw_facts.get("similarity_reified", True))
    similarity_score = float(raw_facts.get("similarity_score", 1.0 if recipe_id != "recipe_unknown" else 0.0))
    context_snapshot_present = bool(raw_facts.get("context_snapshot_present", bool(context_path)))
    agent_trust_score = _optional_float(raw_facts.get("agent_trust_score"))

    session = Session(
        session_id=session_id,
        user_id=user_id,
        team_id=team_id,
        agent_id=agent_id,
        goal_class=goal_class,
        goal_hash=str(raw_facts.get("goal_hash") or ""),
        agent_host=str(raw_facts.get("agent_host") or "scopememory-demo"),
    )
    intent = ToolIntent(
        session_id=session_id,
        tool_id=tool_id,
        resource_id=resource_id,
        schema_valid=schema_valid,
        schema_repairable=schema_repairable,
        requested_scope=scope,
        access_kind=access_kind,
        idempotency_key=str(raw_facts.get("idempotency_key") or ""),
        signed_goal_hash=str(raw_facts.get("signed_goal_hash") or session.goal_hash),
    )

    path_hash = _hash_path(context_path)
    rows: dict[str, list[list[Any]]] = {
        "session": [[session_id, user_id, team_id, agent_id, goal_class]],
        "requested_tool": [[session_id, tool_id]],
        "requested_resource": [[session_id, resource_id]],
        "schema_state": [[session_id, tool_id, schema_valid, schema_repairable]],
        "tool_scope": [[tool_id, scope, access_kind, tool_risk]],
        "resource": [[resource_id, resource_team, resource_sensitivity, resource_external]],
        "delegation": [[session_id, user_id, agent_id]] if delegation_present else [],
        "similar_recipe": [[session_id, recipe_id, similarity_score, "accepted", similarity_reified]] if recipe_id != "recipe_unknown" else [],
        "recipe_tool": [[recipe_id, tool_id]] if recipe_predicts_tool and recipe_id != "recipe_unknown" else [],
        "recipe_scope": [[recipe_id, scope, str(approval_mode)]] if approval_mode and recipe_id != "recipe_unknown" else [],
        "current_grant": [[session_id, scope, resource_id]] if grant_present else [],
        "context_path": [[session_id, tool_id, resource_id, scope, path_hash]] if context_path else [],
        "tool_credential_required": _credential_required_rows(tool_id, raw_facts),
        "credential_binding": _credential_binding_rows(tool_id, scope, raw_facts),
        "judge_fact": _judge_rows(session_id, tool_id, raw_facts),
        "violation": _violation_rows(session_id, tool_id, resource_id, raw_facts),
        "policy_flag": _policy_flag_rows(session_id, raw_facts, context_snapshot_present),
        "agent_trust_state": _agent_trust_state_rows(session_id, agent_trust_score),
    }

    facts = _fact_strings(rows)
    fact_set_hash = stable_hash({"rows": rows, "facts": facts})
    return CompiledPolicyFacts(
        session=session,
        intent=intent,
        rows=rows,
        facts=facts,
        context_path=context_path,
        context_snapshot_id=str(ctx.get("context_snapshot_id") or raw_facts.get("context_snapshot_id") or ""),
        dolt_commit=str(ctx.get("dolt_commit") or raw_facts.get("dolt_commit") or "demo-fixture"),
        recipe_index_commit=str(ctx.get("recipe_index_commit") or raw_facts.get("recipe_index_commit") or "demo-fixture"),
        fact_set_hash=fact_set_hash,
    )


def decide(ctx: dict[str, Any]) -> PolicyDecision:
    compiled = compile_policy_facts(ctx)
    evaluation = evaluate_compiled(compiled)
    required_scope = compiled.intent.requested_scope

    proof = PolicyProofTrace(
        decision=evaluation.decision,
        session_id=compiled.session.session_id,
        tool=compiled.intent.tool_id,
        required_scope=required_scope,
        resource=compiled.intent.resource_id,
        reason=evaluation.reason,
        context_snapshot_id=compiled.context_snapshot_id,
        context_path=compiled.context_path,
        facts=compiled.facts,
        rules=_proof_rules(evaluation.rule),
        dolt_commit=compiled.dolt_commit,
        recipe_index_commit=compiled.recipe_index_commit,
        candidate_decisions=evaluation.candidates,
        policy_engine=evaluation.policy_engine,
    )
    proof_payload = {
        "decision": proof.decision.value,
        "session_id": proof.session_id,
        "tool": proof.tool,
        "required_scope": proof.required_scope,
        "resource": proof.resource,
        "reason": proof.reason,
        "rules": proof.rules,
        "facts": proof.facts,
        "context_path": proof.context_path,
        "dolt_commit": proof.dolt_commit,
        "recipe_index_commit": proof.recipe_index_commit,
        "candidate_decisions": proof.candidate_decisions,
        "fact_set_hash": compiled.fact_set_hash,
    }
    proof = PolicyProofTrace(**{**proof.__dict__, "proof_hash": stable_hash(proof_payload)})

    return PolicyDecision(
        decision=evaluation.decision,
        reason=evaluation.reason,
        session_id=compiled.session.session_id,
        tool_id=compiled.intent.tool_id,
        resource_id=compiled.intent.resource_id,
        required_scope=required_scope,
        proof=proof,
        check_state=_state_for_decision(evaluation.decision),
    )


def evaluate_compiled(compiled: CompiledPolicyFacts) -> PolicyEvaluation:
    return _evaluate_with_cozo(compiled)


def evaluate(facts: dict[str, Any]) -> tuple[str, str, list[str]]:
    """Backward-compatible tuple API for older demo callers."""
    ctx = {
        "session_id": facts.get("session_id", "sess_compat"),
        "tool_id": facts.get("tool_id", "tool.compat"),
        "resource_id": facts.get("resource_id", "resource:compat"),
        "context_path": facts.get("context_path", ["sess_compat", "recipe_compat", "tool.compat", facts.get("scope", "scope:compat"), "resource:compat"]),
        "facts": {**facts, "context_snapshot_present": facts.get("context_snapshot_present", False)},
    }
    decision = decide(ctx)
    return decision.decision.value, decision.reason, decision.proof.rules


def export_facts(facts: dict[str, Any]) -> list[str]:
    """Backward-compatible fact projection for proof rendering."""
    ctx = {
        "session_id": facts.get("session_id", "sess_compat"),
        "tool_id": facts.get("tool_id", "tool.compat"),
        "resource_id": facts.get("resource_id", "resource:compat"),
        "context_path": facts.get("context_path", []),
        "facts": facts,
    }
    return compile_policy_facts(ctx).facts


def _evaluate_with_cozo(compiled: CompiledPolicyFacts) -> PolicyEvaluation:
    from pycozo import Client

    client = Client(dataframe=False)
    try:
        effective = client.run(COZO_EFFECTIVE_QUERY, compiled.rows)
        candidate_result = client.run(COZO_CANDIDATES_QUERY, compiled.rows)
    finally:
        client.close()

    rows = effective["rows"]
    if len(rows) != 1:
        raise RuntimeError(f"policy query returned {len(rows)} effective decisions")
    decision, reason, rule, precedence = rows[0]
    return PolicyEvaluation(
        decision=Decision(decision),
        reason=reason,
        rule=rule,
        precedence=int(precedence),
        candidates=_candidate_dicts(candidate_result["rows"]),
        policy_engine="cozo-datalog",
    )


def _evaluate_with_python(compiled: CompiledPolicyFacts, fallback_error: Exception | None = None) -> PolicyEvaluation:
    rows = compiled.rows
    session = rows["session"][0]
    session_id, user_id, team_id, agent_id, _goal_class = session
    tool_id = rows["requested_tool"][0][1]
    resource_id = rows["requested_resource"][0][1]
    scope = rows["tool_scope"][0][1]
    access_kind = rows["tool_scope"][0][2]
    risk = rows["tool_scope"][0][3]
    resource_team = rows["resource"][0][1]
    sensitivity = rows["resource"][0][2]
    external = rows["resource"][0][3]
    schema_valid, schema_repairable = rows["schema_state"][0][2], rows["schema_state"][0][3]

    has_delegation = [session_id, user_id, agent_id] in rows["delegation"]
    grant_present = [session_id, scope, resource_id] in rows["current_grant"]
    recipe_predicts_tool = any(row[1] == tool_id for row in rows["recipe_tool"])
    recipe_predicts_scope = any(row[1] == scope for row in rows["recipe_scope"])
    approval_mode = next((row[2] for row in rows["recipe_scope"] if row[1] == scope), None)
    memory_consistent = bool(rows["context_path"])
    credential_required = any(row[0] == tool_id for row in rows["tool_credential_required"])
    credential_ok = not credential_required or any(
        row[1] == tool_id and row[2] == scope and row[5] == "active" and row[8] is False
        for row in rows["credential_binding"]
    )
    flags = {(row[1], row[2]) for row in rows["policy_flag"]}
    violations = {row[3] for row in rows["violation"]}
    trust_row = rows["agent_trust_state"][0] if rows["agent_trust_state"] else None
    below_trust_minimum = bool(trust_row[2]) if trust_row else False
    below_sensitive_trust = bool(trust_row[3]) if trust_row else False
    low_trust_external_write = bool(external and access_kind == "write" and below_sensitive_trust)

    candidates: list[dict[str, Any]] = []

    def add(decision: Decision, precedence: int, reason: str, rule: str) -> None:
        candidates.append({
            "decision": decision.value,
            "precedence": precedence,
            "reason": reason,
            "rule": rule,
        })

    hard_denies: list[tuple[str, str]] = []
    if not schema_valid and not schema_repairable:
        hard_denies.append(("schema invalid and not safely repairable", "deny_schema_invalid"))
    if not has_delegation:
        hard_denies.append(("no delegation for agent on session", "deny_no_delegation"))
    if below_trust_minimum:
        hard_denies.append(("agent trust score below minimum", "deny_low_trust"))
    if team_id != resource_team:
        hard_denies.append(("resource not owned by session team", "deny_wrong_team"))
    if schema_valid and not recipe_predicts_tool:
        hard_denies.append(("recipe did not predict this tool", "deny_unpredicted_tool"))
    if external and access_kind == "write" and ("external_write_predicted", True) not in flags and not low_trust_external_write:
        hard_denies.append(("external write not predicted as safe", "deny_external_write"))
    if scope in {"admin", "linear:admin", "slack:admin", "scopememory:admin"} and ("break_glass", True) not in flags:
        hard_denies.append(("admin scope requires break-glass approval", "deny_admin_scope"))
    if "direct_secret_read" in violations:
        hard_denies.append(("direct password-manager secret read bypasses broker", "deny_direct_secret_read"))
    if "secret_exposure" in violations:
        hard_denies.append(("request would expose secret material to the agent", "deny_secret_exposure"))
    if "bulk_export" in violations:
        hard_denies.append(("request attempts bulk export of protected data", "deny_bulk_export"))
    if "goal_expansion" in violations:
        hard_denies.append(("tool output attempted to expand the signed session goal", "deny_goal_expansion"))
    if any(row[4] is False for row in rows["similar_recipe"]):
        hard_denies.append(("recipe retrieval hit was not reified against Dolt commit", "deny_unreified_recipe_hit"))
    if ("context_snapshot_present", True) in flags and not memory_consistent:
        hard_denies.append(("missing context path for graph-backed decision", "deny_missing_context_path"))

    for reason, rule in hard_denies:
        add(Decision.DENY, HARD_DENY_PRECEDENCE[rule], reason, rule)

    if not hard_denies and not schema_valid and schema_repairable:
        add(Decision.REPAIR, PRECEDENCE[Decision.REPAIR.value], "tool arguments can be safely repaired", "repair_schema_args")

    if (
        not hard_denies
        and schema_valid
        and recipe_predicts_tool
        and team_id == resource_team
        and low_trust_external_write
    ):
        add(
            Decision.ESCALATE_HUMAN,
            TRUST_SENSITIVE_ESCALATION_PRECEDENCE,
            "external write requires higher agent trust",
            "escalate_low_trust_external",
        )

    if (
        not hard_denies
        and schema_valid
        and grant_present
        and team_id == resource_team
        and recipe_predicts_tool
        and memory_consistent
    ):
        add(Decision.ALLOW, PRECEDENCE[Decision.ALLOW.value], "grant exists for scope@resource", "allow_current_grant")

    if (
        not hard_denies
        and schema_valid
        and not grant_present
        and recipe_predicts_tool
        and recipe_predicts_scope
        and approval_mode == "auto_approve"
        and team_id == resource_team
        and risk in {"low", "medium"}
        and sensitivity in {"low", "normal"}
        and not external
        and credential_ok
    ):
        add(
            Decision.AUTO_APPROVE_EPHEMERAL_GRANT,
            PRECEDENCE[Decision.AUTO_APPROVE_EPHEMERAL_GRANT.value],
            "accepted recipe auto-approves a bounded ephemeral grant",
            "auto_approve_recipe_scope",
        )

    if (
        not hard_denies
        and schema_valid
        and not grant_present
        and recipe_predicts_tool
        and recipe_predicts_scope
        and approval_mode == "human_required"
        and team_id == resource_team
        and memory_consistent
    ):
        add(Decision.ESCALATE_HUMAN, PRECEDENCE[Decision.ESCALATE_HUMAN.value], "scope requires human approval", "escalate_human_required_scope")

    add(Decision.DENY, LOW_PRECEDENCE_DEFAULT_DENY, "no grant, auto-approval, or human approval path matched", "deny_default")
    selected = max(candidates, key=lambda item: item["precedence"])
    engine = "python-datalog-fallback"
    if fallback_error:
        engine += f":{fallback_error.__class__.__name__}"
    return PolicyEvaluation(
        decision=Decision(selected["decision"]),
        reason=str(selected["reason"]),
        rule=str(selected["rule"]),
        precedence=int(selected["precedence"]),
        candidates=candidates,
        policy_engine=engine,
    )


def _path_at(path: list[str], index: int, default: str) -> str:
    return path[index] if len(path) > index else default


def _hash_path(path: list[str]) -> str:
    return "sha256:" + hashlib.sha256("|".join(path).encode("utf-8")).hexdigest()


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _agent_trust_state_rows(session_id: str, trust_score: float | None) -> list[list[Any]]:
    if trust_score is None:
        return []
    return [
        [
            session_id,
            trust_score,
            trust_score < TRUST_SCORE_MIN,
            trust_score < TRUST_SCORE_SENSITIVE,
        ]
    ]


def _credential_required_rows(tool_id: str, facts: dict[str, Any]) -> list[list[Any]]:
    credential_class = facts.get("credential_class")
    if not facts.get("credential_required", bool(credential_class)):
        return []
    return [[tool_id, str(credential_class or f"{tool_id}.credential")]]


def _credential_binding_rows(tool_id: str, scope: str, facts: dict[str, Any]) -> list[list[Any]]:
    if not facts.get("credential_binding_available", False):
        return []
    credential_ref = str(facts.get("credential_ref") or f"credref:{tool_id}:{scope}")
    return [[
        str(facts.get("credential_binding_id") or f"binding:{tool_id}:{scope}"),
        tool_id,
        scope,
        credential_ref,
        str(facts.get("credential_provider") or "1password"),
        str(facts.get("credential_ref_status") or "active"),
        str(facts.get("credential_injection_mode") or "gateway_header"),
        str(facts.get("credential_owner_team") or "team_sales_ops"),
        bool(facts.get("secret_exposed_to_agent", False)),
    ]]


def _judge_rows(session_id: str, tool_id: str, facts: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for key in ("goal_consistent", "resource_consistent", "exfiltration_risk"):
        value_key = f"judge_{key}"
        if value_key in facts:
            rows.append([session_id, tool_id, value_key, bool(facts[value_key]), float(facts.get(f"{value_key}_confidence", 0.0))])
    return rows


def _violation_rows(session_id: str, tool_id: str, resource_id: str, facts: dict[str, Any]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    flag_to_violation = {
        "attempted_direct_secret_read": "direct_secret_read",
        "direct_secret_read": "direct_secret_read",
        "writes_decrypted_credential": "secret_exposure",
        "hook_would_expose_secret": "secret_exposure",
        "bulk_export": "bulk_export",
        "goal_expansion": "goal_expansion",
    }
    for flag, violation_type in flag_to_violation.items():
        if facts.get(flag, False):
            rows.append([session_id, tool_id, resource_id, violation_type])
    for key, value in facts.items():
        if any(marker in str(key).lower() for marker in SECRET_MARKERS) and value and key not in {
            "credential_required",
            "credential_ref_status",
            "credential_provider",
            "credential_injection_mode",
            "credential_owner_team",
            "secret_exposed_to_agent",
        }:
            rows.append([session_id, tool_id, resource_id, "secret_exposure"])
            break
    return rows


def _policy_flag_rows(session_id: str, facts: dict[str, Any], context_snapshot_present: bool) -> list[list[Any]]:
    rows = [[session_id, "context_snapshot_present", context_snapshot_present]]
    for name in ("break_glass", "external_write_predicted"):
        if name in facts:
            rows.append([session_id, name, bool(facts[name])])
    return rows


def _fact_strings(rows: dict[str, list[list[Any]]]) -> list[str]:
    facts: list[str] = []
    for relation in sorted(rows):
        for row in rows[relation]:
            rendered = ", ".join(_render_fact_value(value) for value in row)
            facts.append(f"{relation}({rendered})")
    return facts


def _render_fact_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _candidate_dicts(rows: list[list[Any]]) -> list[dict[str, Any]]:
    return [
        {"decision": decision, "reason": reason, "rule": rule, "precedence": int(precedence)}
        for decision, reason, rule, precedence in rows
    ]


def _proof_rules(rule: str) -> list[str]:
    rule_dependencies = {
        "allow_current_grant": [
            "required_scope",
            "same_team_resource",
            "recipe_predicts_tool",
            "memory_consistent",
            "allow_current_grant",
        ],
        "auto_approve_recipe_scope": [
            "required_scope",
            "recipe_predicts_tool",
            "recipe_predicts_scope",
            "same_team_resource",
            "risk_auto_approvable",
            "resource_auto_approvable",
            "credential_ok",
            "auto_approve_recipe_scope",
        ],
        "escalate_human_required_scope": [
            "required_scope",
            "recipe_predicts_tool",
            "recipe_predicts_scope",
            "same_team_resource",
            "memory_consistent",
            "escalate_human_required_scope",
        ],
        "escalate_low_trust_external": [
            "required_scope",
            "recipe_predicts_tool",
            "same_team_resource",
            "agent_trust_state",
            "low_trust_external_write",
            "escalate_low_trust_external",
        ],
        "repair_schema_args": ["schema_state", "repair_schema_args"],
    }
    if rule.startswith("deny_"):
        return [rule, "hard_deny", "policy_precedence"]
    return rule_dependencies.get(rule, [rule, "policy_precedence"])


def _state_for_decision(decision: Decision) -> AuthorizationCheckState:
    if decision == Decision.ALLOW:
        return AuthorizationCheckState.APPROVED
    if decision == Decision.AUTO_APPROVE_EPHEMERAL_GRANT:
        return AuthorizationCheckState.AUTO_APPROVED
    if decision == Decision.ESCALATE_HUMAN:
        return AuthorizationCheckState.WAITING_FOR_HUMAN
    if decision == Decision.REPAIR:
        return AuthorizationCheckState.REPAIRABLE
    return AuthorizationCheckState.DENIED
