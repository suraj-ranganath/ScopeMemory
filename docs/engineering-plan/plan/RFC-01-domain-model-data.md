# RFC-01: Domain Model And Data

## Status

Plan ready for implementation authorization.

## Core Domain Terms

### Session

A bounded agent run with a user, team, agent identity, signed goal, visible tools, grants, credential leases, events, and final outcome.

### Workflow Authorization Recipe

A governed memory record that says: for this team and goal class, agents normally use these tools, scopes, resources, credential classes, approval modes, limits, and evidence.

### Access Request

A request to grant a missing scope or resource constraint for a session. It can be auto-approved, human-approved, denied, expired, or revoked.

### Grant

A short-lived authorization object bound to session, scope, resource constraint, tool, TTL, issuer, and proof.

### Credential Reference

An opaque pointer to a secret in a provider such as 1Password. The reference is metadata, not the secret value.

### Credential Binding

A policy object that maps a tool/scope/resource class to an acceptable credential reference or provider class.

### Credential Lease

A short-lived runtime permission for the broker to resolve a credential reference for a specific session, tool, scope, resource, and execution adapter.

## Dolt Tables

The schema below is binding at the concept level. Names and relationships should survive implementation; exact SQL types may change.

```sql
CREATE TABLE users (
  user_id VARCHAR(128) PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  display_name VARCHAR(255),
  status VARCHAR(32) NOT NULL
);

CREATE TABLE teams (
  team_id VARCHAR(128) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  owner_team_id VARCHAR(128),
  status VARCHAR(32) NOT NULL
);

CREATE TABLE user_teams (
  user_id VARCHAR(128) NOT NULL,
  team_id VARCHAR(128) NOT NULL,
  role VARCHAR(64) NOT NULL,
  PRIMARY KEY (user_id, team_id)
);

CREATE TABLE mcp_servers (
  server_id VARCHAR(128) PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  transport VARCHAR(64) NOT NULL,
  base_url TEXT,
  status VARCHAR(32) NOT NULL
);

CREATE TABLE mcp_tools (
  tool_id VARCHAR(128) PRIMARY KEY,
  server_id VARCHAR(128) NOT NULL,
  tool_name VARCHAR(255) NOT NULL,
  input_schema_json JSON NOT NULL,
  output_sensitivity VARCHAR(64) NOT NULL,
  risk_level VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL
);

CREATE TABLE tool_required_scopes (
  tool_id VARCHAR(128) NOT NULL,
  scope VARCHAR(255) NOT NULL,
  resource_kind VARCHAR(128) NOT NULL,
  access_kind VARCHAR(64) NOT NULL,
  PRIMARY KEY (tool_id, scope, resource_kind)
);

CREATE TABLE workflow_recipes (
  recipe_id VARCHAR(128) PRIMARY KEY,
  title TEXT NOT NULL,
  team_id VARCHAR(128) NOT NULL,
  goal_class VARCHAR(128) NOT NULL,
  goal_pattern TEXT NOT NULL,
  status VARCHAR(32) NOT NULL,
  confidence DOUBLE NOT NULL,
  risk_level VARCHAR(32) NOT NULL,
  owner_team_id VARCHAR(128) NOT NULL,
  valid_from DATETIME NOT NULL,
  valid_until DATETIME,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);

CREATE TABLE recipe_tools (
  recipe_id VARCHAR(128) NOT NULL,
  tool_id VARCHAR(128) NOT NULL,
  typical_order INT,
  required BOOLEAN NOT NULL,
  PRIMARY KEY (recipe_id, tool_id)
);

CREATE TABLE recipe_scopes (
  recipe_id VARCHAR(128) NOT NULL,
  scope VARCHAR(255) NOT NULL,
  approval_mode VARCHAR(64) NOT NULL,
  resource_constraint_json JSON NOT NULL,
  max_ttl_seconds INT NOT NULL,
  max_call_count INT,
  PRIMARY KEY (recipe_id, scope)
);

CREATE TABLE recipe_credentials (
  recipe_id VARCHAR(128) NOT NULL,
  credential_class VARCHAR(128) NOT NULL,
  binding_mode VARCHAR(64) NOT NULL,
  required BOOLEAN NOT NULL,
  notes TEXT,
  PRIMARY KEY (recipe_id, credential_class)
);

CREATE TABLE recipe_evidence (
  recipe_id VARCHAR(128) NOT NULL,
  session_id VARCHAR(128) NOT NULL,
  evidence_type VARCHAR(64) NOT NULL,
  summary TEXT NOT NULL,
  score DOUBLE,
  accepted_by VARCHAR(128),
  created_at DATETIME NOT NULL,
  PRIMARY KEY (recipe_id, session_id, evidence_type)
);

CREATE TABLE credential_providers (
  provider_id VARCHAR(128) PRIMARY KEY,
  provider_type VARCHAR(64) NOT NULL,
  display_name VARCHAR(255) NOT NULL,
  trust_boundary VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL
);

CREATE TABLE credential_refs (
  credential_ref_id VARCHAR(128) PRIMARY KEY,
  provider_id VARCHAR(128) NOT NULL,
  credential_class VARCHAR(128) NOT NULL,
  owner_team_id VARCHAR(128) NOT NULL,
  secret_ref_ciphertext_or_handle TEXT NOT NULL,
  secret_ref_hash VARCHAR(128) NOT NULL,
  display_hint TEXT,
  rotation_hint DATETIME,
  sensitivity VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL
);

CREATE TABLE credential_bindings (
  binding_id VARCHAR(128) PRIMARY KEY,
  credential_ref_id VARCHAR(128) NOT NULL,
  tool_id VARCHAR(128) NOT NULL,
  scope VARCHAR(255) NOT NULL,
  resource_constraint_json JSON NOT NULL,
  injection_mode VARCHAR(64) NOT NULL,
  max_ttl_seconds INT NOT NULL,
  status VARCHAR(32) NOT NULL
);

CREATE TABLE sessions (
  session_id VARCHAR(128) PRIMARY KEY,
  user_id VARCHAR(128) NOT NULL,
  team_id VARCHAR(128) NOT NULL,
  agent_id VARCHAR(128) NOT NULL,
  goal TEXT NOT NULL,
  goal_hash VARCHAR(128) NOT NULL,
  goal_signature TEXT,
  started_at DATETIME NOT NULL,
  ended_at DATETIME,
  status VARCHAR(64) NOT NULL
);

CREATE TABLE access_requests (
  request_id VARCHAR(128) PRIMARY KEY,
  session_id VARCHAR(128) NOT NULL,
  user_id VARCHAR(128) NOT NULL,
  agent_id VARCHAR(128) NOT NULL,
  requested_scope VARCHAR(255) NOT NULL,
  requested_resource TEXT NOT NULL,
  requested_tool_id VARCHAR(128) NOT NULL,
  credential_binding_id VARCHAR(128),
  reason TEXT NOT NULL,
  recipe_id VARCHAR(128),
  status VARCHAR(64) NOT NULL,
  approver_type VARCHAR(64),
  approver_id VARCHAR(128),
  expires_at DATETIME,
  created_at DATETIME NOT NULL
);

CREATE TABLE grants (
  grant_id VARCHAR(128) PRIMARY KEY,
  session_id VARCHAR(128) NOT NULL,
  scope VARCHAR(255) NOT NULL,
  resource_constraint_json JSON NOT NULL,
  tool_id VARCHAR(128),
  issued_by VARCHAR(128) NOT NULL,
  issued_reason TEXT NOT NULL,
  max_call_count INT,
  used_call_count INT NOT NULL,
  expires_at DATETIME NOT NULL,
  revoked_at DATETIME
);

CREATE TABLE credential_leases (
  lease_id VARCHAR(128) PRIMARY KEY,
  session_id VARCHAR(128) NOT NULL,
  grant_id VARCHAR(128) NOT NULL,
  credential_ref_id VARCHAR(128) NOT NULL,
  credential_binding_id VARCHAR(128) NOT NULL,
  injection_mode VARCHAR(64) NOT NULL,
  issued_by VARCHAR(128) NOT NULL,
  provider_request_id VARCHAR(255),
  expires_at DATETIME NOT NULL,
  used_at DATETIME,
  revoked_at DATETIME,
  secret_exposed_to_agent BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE policy_decisions (
  decision_id VARCHAR(128) PRIMARY KEY,
  session_id VARCHAR(128) NOT NULL,
  tool_id VARCHAR(128),
  decision VARCHAR(64) NOT NULL,
  proof_json JSON NOT NULL,
  dolt_commit_hash VARCHAR(128) NOT NULL,
  qdrant_hits_json JSON,
  credential_lease_id VARCHAR(128),
  created_at DATETIME NOT NULL
);

CREATE TABLE session_events (
  event_id VARCHAR(128) PRIMARY KEY,
  session_id VARCHAR(128) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  event_json JSON NOT NULL,
  prev_event_hash VARCHAR(128),
  event_hash VARCHAR(128) NOT NULL,
  created_at DATETIME NOT NULL
);
```

## Secret Reference Rules

`credential_refs.secret_ref_ciphertext_or_handle` may contain:

- A provider handle encrypted to the broker.
- A provider-specific stable ID.
- A secret reference such as `op://vault/item/field` only when policy allows that metadata to be stored.

It must not contain a decrypted token, password, private key, `.env` file, or bearer credential.

## Qdrant Payloads

Qdrant points are derived from accepted recipe chunks. Payloads may include:

- `recipe_id`
- `team_id`
- `goal_class`
- `tools`
- `scopes`
- `credential_classes`
- `risk_level`
- `owner_team_id`
- `status`
- `valid_until`
- `dolt_commit`
- `content_hash`
- `embedding_model`
- `embedding_version`

Payloads must not include:

- secret references if sensitive.
- decrypted credentials.
- raw session transcript.
- raw customer content.
- unreviewed proposed recipes in the normal retrieval collection.

## Branch Model

```text
main
  accepted policies, tool mappings, recipes, and credential metadata

proposal/recipe-sales-renewal-v4
  candidate recipe from learning worker

proposal/policy-external-slack-deny
  policy change under review

proposal/credential-binding-linear-sales
  credential binding metadata under owner/security review
```

Only `main` feeds the normal authorization retrieval index. Proposal branches are visible in review UI but not used for auto-approval.
