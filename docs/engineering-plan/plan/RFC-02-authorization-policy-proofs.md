# RFC-02: Authorization Policy And Proofs

## Status

Plan ready for implementation authorization.

## Policy Contract

Policy is the only authority for runtime access. It decides over typed facts. Facts can come from:

- signed session goal.
- user/team membership.
- tool registry.
- MCP tool schema validation.
- resource metadata.
- Qdrant recipe hits tied to Dolt commits.
- Dolt recipes and policies.
- current grants.
- human approvals.
- credential binding metadata.
- credential broker lease state.
- LLM judge candidate facts.

LLM judge facts are treated as untrusted inputs with confidence, never as decisions.

## Fact Classes

### Session Facts

```prolog
session_user("sess_123", "user_alice").
session_team("sess_123", "sales").
session_goal_hash("sess_123", "sha256:...").
session_goal_class("sess_123", "sales_renewal_prep").
agent_host("sess_123", "claude_code").
```

### Tool Facts

```prolog
requested_tool("sess_123", "linear.create_issue").
schema_valid("sess_123", "linear.create_issue").
tool_requires_scope("linear.create_issue", "linear:issues:create").
tool_risk("linear.create_issue", "medium").
tool_access_kind("linear.create_issue", "write").
```

### Resource Facts

```prolog
requested_resource("sess_123", "linear_team:SALES").
resource_team("linear_team:SALES", "sales").
resource_sensitivity("linear_team:SALES", "normal").
destination_external("slack_channel:C_EXT", true).
```

### Recipe Facts

```prolog
similar_recipe("sess_123", "recipe_sales_renewal_prep_v3", 0.89).
recipe_status("recipe_sales_renewal_prep_v3", "accepted").
recipe_scope("recipe_sales_renewal_prep_v3", "linear:issues:create").
recipe_tool("recipe_sales_renewal_prep_v3", "linear.create_issue").
recipe_credential_class("recipe_sales_renewal_prep_v3", "linear.oauth_token").
```

### Grant Facts

```prolog
current_grant("sess_123", "linear:issues:create", "linear_team:SALES").
grant_expires_after_now("grant_123").
grant_call_count_remaining("grant_123").
```

### Credential Facts

```prolog
tool_requires_credential_class("linear.create_issue", "linear.oauth_token").
credential_binding("binding_linear_sales", "linear.create_issue", "linear:issues:create", "credref_linear_sales").
credential_provider("credref_linear_sales", "1password").
credential_ref_status("credref_linear_sales", "active").
credential_injection_mode("binding_linear_sales", "gateway_header").
credential_owner_team("credref_linear_sales", "sales-ops").
credential_lease_valid("lease_123", "sess_123", "credref_linear_sales").
secret_exposed_to_agent("lease_123", false).
```

### Judge Facts

```prolog
judge_goal_consistent("request_123", true, 0.91).
judge_resource_consistent("request_123", true, 0.88).
judge_exfiltration_risk("request_123", false, 0.80).
```

## Decision Rules

The initial implementation uses CozoDB for the policy engine. ScopeMemory still owns the typed fact compiler, decision API, and proof/audit contract; CozoDB evaluates the Datalog-like policy rules over those facts.

```prolog
required_scope(Session, Scope) :-
  requested_tool(Session, Tool),
  tool_requires_scope(Tool, Scope).

recipe_predicts_scope(Session, Scope) :-
  similar_recipe(Session, Recipe, Score),
  Score >= 0.82,
  recipe_status(Recipe, "accepted"),
  recipe_scope(Recipe, Scope).

recipe_predicts_tool(Session, Tool) :-
  similar_recipe(Session, Recipe, Score),
  Score >= 0.82,
  recipe_status(Recipe, "accepted"),
  recipe_tool(Recipe, Tool).

same_team_resource(Session, Resource) :-
  session_team(Session, Team),
  resource_team(Resource, Team).

credential_binding_available(Session, Tool, Scope) :-
  tool_requires_credential_class(Tool, CredentialClass),
  credential_binding(Binding, Tool, Scope, CredentialRef),
  credential_ref_status(CredentialRef, "active").

allow(Session, Tool) :-
  schema_valid(Session, Tool),
  requested_tool(Session, Tool),
  required_scope(Session, Scope),
  current_grant(Session, Scope, Resource),
  requested_resource(Session, Resource),
  same_team_resource(Session, Resource),
  recipe_predicts_tool(Session, Tool),
  not hard_deny(Session, Tool).

auto_approve_ephemeral_grant(Session, Scope) :-
  required_scope(Session, Scope),
  recipe_predicts_scope(Session, Scope),
  team_allowed_scope(Session, Scope),
  requested_resource(Session, Resource),
  same_team_resource(Session, Resource),
  requested_tool(Session, Tool),
  tool_risk(Tool, Risk),
  risk_auto_approvable(Risk),
  credential_binding_available(Session, Tool, Scope),
  no_secret_exposure_required(Session, Tool),
  not high_risk_resource(Session, Resource),
  not external_destination(Resource).

escalate_human(Session, Scope) :-
  required_scope(Session, Scope),
  not current_grant(Session, Scope, _),
  not auto_approve_ephemeral_grant(Session, Scope),
  not hard_deny_scope(Session, Scope).

deny(Session, Tool) :-
  hard_deny(Session, Tool).

repair(Session, Tool) :-
  requested_tool(Session, Tool),
  not schema_valid(Session, Tool).
```

## Hard Denies

Hard deny when any is true:

- tool call violates schema in a non-repairable way.
- requested scope is admin without security break-glass.
- resource is external and the recipe did not explicitly predict external posting.
- request attempts bulk export of customer/private data.
- tool output attempts to expand the signed session goal.
- command directly reads password-manager secrets outside the broker.
- command writes decrypted credentials to disk.
- hook rewrite would expose a secret to agent-visible input.
- Qdrant hit is not tied to the current accepted Dolt commit or allowed index build.

## Auto-Approval Requirements

Auto-approval requires all of:

- accepted recipe.
- score at or above threshold.
- tool and scope predicted.
- user belongs to team.
- resource belongs to team or org-default boundary.
- scope is team-delegable.
- tool risk low or medium.
- resource sensitivity not restricted.
- no external destination.
- credential binding active.
- credential lease can be issued without exposing the secret to the agent.
- TTL and call count under policy limits.

## Proof Trace

A proof trace is a structured explanation, not necessarily a formal proof object in v1.

```json
{
  "decision": "AUTO_APPROVE_EPHEMERAL_GRANT",
  "session_id": "sess_123",
  "tool": "linear.create_issue",
  "required_scope": "linear:issues:create",
  "resource": "linear_team:SALES",
  "facts": [
    "session_team(sess_123, sales)",
    "similar_recipe(sess_123, recipe_sales_renewal_prep_v3, 0.89)",
    "recipe_scope(recipe_sales_renewal_prep_v3, linear:issues:create)",
    "team_allowed_scope(sales, linear:issues:create)",
    "resource_team(linear_team:SALES, sales)",
    "credential_binding(binding_linear_sales, linear.create_issue, linear:issues:create, credref_linear_sales)",
    "secret_exposed_to_agent(lease_123, false)"
  ],
  "rules": [
    "required_scope",
    "recipe_predicts_scope",
    "same_team_resource",
    "credential_binding_available",
    "auto_approve_ephemeral_grant"
  ],
  "dolt_commit": "abc123",
  "qdrant_index_commit": "abc123",
  "proof_hash": "sha256:..."
}
```

## Repair Versus Deny

Use `REPAIR` when the agent can safely fix arguments:

- missing required field.
- invalid enum.
- malformed date.
- resource ID not resolved.

Use `DENY` when intent is unsafe:

- external exfiltration.
- direct secret read.
- admin scope.
- bypass gateway.
- repeated repair attempts that appear adversarial.
