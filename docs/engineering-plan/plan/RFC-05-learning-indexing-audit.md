# RFC-05: Learning, Indexing, And Audit

## Status

Plan ready for implementation authorization.

## Learning Loop

ScopeMemory learns authorization recipes from repeated successful sessions. It does not learn directly into runtime policy.

```text
session completes
  -> session events and outcomes are summarized
  -> recipe proposal judge emits candidate recipe facts
  -> evidence_from edges link proposal to source sessions
  -> proposal branch is created in Dolt
  -> human/security review accepts, edits, or rejects
  -> accepted recipe lands on Dolt main
  -> graph_nodes/graph_edges updated for recipe lineage
  -> indexer refreshes Memgraph recipe nodes and retrieval metadata
  -> future preflights can retrieve the accepted recipe and reify matches_recipe edges
```

## Recipe Proposal Judge

Input:

- session goal.
- tools used.
- scopes requested.
- grants issued.
- credential classes used.
- human approvals and denials.
- policy decisions.
- success or failure signal.
- similar existing recipes.

Output:

```json
{
  "should_propose_recipe": true,
  "title": "Sales renewal prep with Slack and Linear",
  "goal_class": "sales_renewal_prep",
  "tools": ["slack.search_messages", "linear.create_issue"],
  "scopes": ["slack:channels:history", "linear:issues:create"],
  "credential_classes": ["slack.oauth_token", "linear.oauth_token"],
  "approval_modes": {
    "linear:issues:create": "auto_approve",
    "slack:channels:history": "human_required"
  },
  "confidence": 0.84,
  "evidence_sessions": ["sess_123", "sess_456"],
  "safety_notes": "External posting remains human-required or denied."
}
```

This output is a proposal. It is not runtime policy.

## Access Request Judge

Runs when a request is not obviously allowed or denied.

It emits facts:

```json
{
  "goal_consistent": true,
  "resource_consistent": true,
  "scope_predictable": true,
  "credential_binding_consistent": true,
  "exfiltration_risk": false,
  "confidence": 0.86
}
```

Policy decides.

## Audit Summarizer

Turns proof traces into human-readable explanations:

```text
Allowed because Alice is in Sales, the session goal matched the accepted
Sales Renewal Prep recipe at 0.89, Linear issue creation is delegated for
Sales, the target team is SALES, the credential lease was issued through
the broker without exposing the token to the agent, and the grant expires
in 20 minutes.
```

Summaries are derived from proofs. They are not the proof.

## Recipe Indexing

Index accepted recipes only in the Dolt/Memgraph-derived graph. No separate vector store is required for the MVP.

Chunk types:

- goal pattern.
- tool sequence.
- scope/resource policy.
- credential class/binding summary.
- evidence summary.
- denial/escalation examples.

Graph node ID:

```text
recipe_id + chunk_kind + content_hash + recipe_index_commit
```

Payload:

```json
{
  "recipe_id": "recipe_sales_renewal_prep_v3",
  "chunk_kind": "goal",
  "team_id": "sales",
  "goal_class": "sales_renewal_prep",
  "tools": ["slack.search_messages", "linear.create_issue"],
  "scopes": ["slack:channels:history", "linear:issues:create"],
  "credential_classes": ["slack.oauth_token", "linear.oauth_token"],
  "risk_level": "medium",
  "status": "accepted",
  "dolt_commit": "abc123",
  "content_hash": "sha256:...",
  "graph_node_id": "recipe_sales_renewal_prep_v3:goal:sha256...",
  "recipe_index_commit": "abc123"
}
```

## Retrieval

Query:

- goal-class and goal-text scoring over accepted recipe nodes.
- graph traversal over services, tools, scopes, and resource names.
- filters for team, status, visibility, valid time, and tool availability.

Post-filter:

- require accepted status.
- require index commit compatible with policy commit.
- drop expired recipes.
- drop recipes whose tool set is unavailable.
- drop recipes marked human-required for the requested scope unless building an access request.

## Index Refresh

```text
Dolt commit lands on main
  -> indexer reads changed recipes
  -> refreshes canonical recipe summary rows
  -> computes content hashes
  -> updates Memgraph recipe nodes and edges
  -> marks indexed_commit_hash
```

If a recipe is deprecated, update graph metadata status and exclude it from normal retrieval. If rejected or deleted, remove the derived graph nodes/edges.

## Audit Log

Every event is hash-chained:

```text
event_hash = sha256(prev_event_hash + normalized_event_json)
```

Events:

- session created.
- preflight requested.
- recipe hits returned.
- access request created.
- grant issued.
- credential lease issued.
- tool call requested.
- policy decision made.
- downstream call executed.
- downstream result redacted.
- denial returned.
- recipe proposal created.

## Audit Invariants

- Every policy decision points to a Dolt commit.
- Every recipe hit points to a Dolt commit, recipe index commit, and content hash.
- Every credential use points to a credential lease.
- Every credential lease records `secret_exposed_to_agent=false`.
- Every event hash links to the prior session event.
- UI displays redacted arguments and proof summaries, not secrets.

## Review UI

Recipe review shows:

- old and new recipe rows.
- evidence sessions.
- scopes and approval modes.
- credential classes, not secret refs by default.
- denial examples.
- reviewer actions: merge, reject, edit, request more evidence.
