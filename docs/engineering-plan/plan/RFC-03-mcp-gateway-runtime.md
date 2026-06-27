# RFC-03: MCP Gateway Runtime

## Status

Plan ready for implementation authorization.

## Gateway Role

ScopeMemory is a meta-MCP server. Agents connect to ScopeMemory rather than directly to every downstream MCP server. The gateway exposes a narrowed catalog of tools and enforces policy on every call.

## Tool Catalog

Core tools:

```text
auth.preflight_goal
auth.request_scope
auth.show_decision_proof
auth.explain_denial
auth.submit_workflow_feedback
```

Demo downstream tools:

```text
linear.search_issues
linear.create_issue
linear.add_comment
slack.search_messages
slack.post_message
```

## `auth.preflight_goal`

Input:

```json
{
  "goal": "Prepare renewal follow-up for Acme. Check Slack context and create a Linear issue.",
  "user_id": "user_alice",
  "team_id": "sales",
  "agent_id": "agent_sales_01",
  "available_servers": ["linear", "slack"]
}
```

Output:

```json
{
  "session_id": "sess_123",
  "context_snapshot_id": "snap_preflight_001",
  "matched_recipes": [
    {
      "recipe_id": "recipe_sales_renewal_prep_v3",
      "score": 0.89,
      "dolt_commit": "abc123",
      "similarity_reified": true
    }
  ],
  "context_path_preview": [
    "sess_123",
    "recipe_sales_renewal_prep_v3",
    "linear.create_issue",
    "linear:issues:create",
    "linear_team:SALES"
  ],
  "predicted_tools": [
    "linear.search_issues",
    "linear.create_issue",
    "slack.search_messages"
  ],
  "predicted_scopes": [
    "linear:read",
    "linear:issues:create",
    "slack:channels:history"
  ],
  "auto_approved_grants": [
    "grant_linear_create_123"
  ],
  "human_required_requests": [
    "request_slack_history_123"
  ],
  "visible_tools": [
    "linear.search_issues",
    "linear.create_issue",
    "auth.request_scope",
    "auth.show_decision_proof"
  ]
}
```

## `tools/list`

The gateway returns tools based on the session:

- Always include auth/explanation tools.
- Include read-only safe tools when policy allows.
- Include predicted tools when grant exists or no grant is needed.
- Hide tools that require missing high-risk grants unless `auth.request_scope` is the correct path.
- Update the catalog after approvals or expirations.

## `tools/call`

Pipeline:

1. Resolve session.
2. Validate tool name is in current catalog or eligible for request path.
3. Validate schema.
4. Normalize arguments.
5. Detect resource, destination, access kind, and data sensitivity.
6. Build or update session context subgraph for `tool_call` phase.
7. Persist `session_context_snapshots` row.
8. Compile policy facts including graph edges and context paths.
9. Decide.
10. If `ALLOW`, execute.
11. If `AUTO_APPROVE_EPHEMERAL_GRANT`, create grant, maybe create credential lease, then execute.
12. If `ESCALATE_HUMAN`, create or update access request and pause.
13. If `DENY`, return safe denial.
14. If `REPAIR`, return schema/argument repair instructions.
15. Append audit event and new graph edges (`invoked`, `produced`).

## Downstream Execution

### HTTP API Tools

Gateway attaches credentials as headers or SDK configuration inside the gateway process. The agent never sees those headers.

### Stdio MCP Tools

Prefer gateway proxy. If direct stdio is required, launch the stdio server through the credential broker so environment is set before process start.

### Shell Tools

Use hook adapter plus `scopememory exec` wrapper. The gateway should not assume arbitrary shell commands are safe just because a credential lease exists.

## Result Redaction

Every downstream result passes through output classification:

- secret-like strings.
- OAuth tokens.
- private keys.
- customer PII.
- access URLs.
- external destinations.

Redaction policy is part of the tool registry and can be adjusted by risk level.

## Session Lifecycle

States:

```text
created
preflighted
waiting_for_human
running
blocked
completed
expired
revoked
```

Grant and lease expiration can move a session back to `waiting_for_human` or `blocked`.

## Prompt Injection Defense

Tool output can influence task execution but not authorization state. The gateway rejects any attempt to treat tool output as:

- a new session goal.
- an approval.
- a grant.
- a credential reference.
- a recipe acceptance.
- a reason to expose a new tool.

## Error Model

Use structured errors:

```json
{
  "error": "scope_required",
  "decision": "ESCALATE_HUMAN",
  "request_id": "request_slack_history_123",
  "required_scope": "slack:channels:history",
  "proof_id": "proof_123",
  "safe_summary": "Slack channel history requires approval for this customer-private channel."
}
```

The agent receives enough to proceed safely, not raw internal policy state or secret metadata.
