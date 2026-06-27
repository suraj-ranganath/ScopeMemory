-- ScopeMemory canonical schema (Dolt / MySQL wire protocol)

CREATE TABLE IF NOT EXISTS users (
  user_id VARCHAR(128) PRIMARY KEY,
  display_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
  team_id VARCHAR(128) PRIMARY KEY,
  name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS user_teams (
  user_id VARCHAR(128) NOT NULL,
  team_id VARCHAR(128) NOT NULL,
  role VARCHAR(64) NOT NULL,
  PRIMARY KEY (user_id, team_id)
);

CREATE TABLE IF NOT EXISTS agents (
  agent_id VARCHAR(128) PRIMARY KEY,
  display_name VARCHAR(255) NOT NULL,
  identity_ref VARCHAR(255) NOT NULL,
  trust_score DOUBLE NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id VARCHAR(128) PRIMARY KEY,
  user_id VARCHAR(128) NOT NULL,
  team_id VARCHAR(128) NOT NULL,
  agent_id VARCHAR(128) NOT NULL,
  goal TEXT NOT NULL,
  goal_class VARCHAR(128) NOT NULL,
  status VARCHAR(64) NOT NULL DEFAULT 'preflighted',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS delegations (
  session_id VARCHAR(128) PRIMARY KEY,
  user_id VARCHAR(128) NOT NULL,
  agent_id VARCHAR(128) NOT NULL,
  delegated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workflow_recipes (
  recipe_id VARCHAR(128) PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  team_id VARCHAR(128) NOT NULL,
  goal_class VARCHAR(128) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'accepted'
);

CREATE TABLE IF NOT EXISTS recipe_tools (
  recipe_id VARCHAR(128) NOT NULL,
  tool_id VARCHAR(128) NOT NULL,
  required TINYINT NOT NULL DEFAULT 1,
  PRIMARY KEY (recipe_id, tool_id)
);

CREATE TABLE IF NOT EXISTS recipe_scopes (
  recipe_id VARCHAR(128) NOT NULL,
  scope VARCHAR(255) NOT NULL,
  approval_mode VARCHAR(64) NOT NULL,
  PRIMARY KEY (recipe_id, scope)
);

CREATE TABLE IF NOT EXISTS resources (
  resource_id VARCHAR(128) PRIMARY KEY,
  team_id VARCHAR(128) NOT NULL,
  sensitivity VARCHAR(64) NOT NULL DEFAULT 'normal',
  external_flag TINYINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tool_scopes (
  tool_id VARCHAR(128) PRIMARY KEY,
  scope VARCHAR(255) NOT NULL,
  access_kind VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS grants (
  grant_id VARCHAR(128) PRIMARY KEY,
  session_id VARCHAR(128) NOT NULL,
  scope VARCHAR(255) NOT NULL,
  resource_id VARCHAR(128) NOT NULL,
  issuer VARCHAR(128) NOT NULL DEFAULT 'policy',
  proof_id VARCHAR(128),
  reason TEXT,
  ttl_seconds INT NOT NULL DEFAULT 900,
  call_count_remaining INT NOT NULL DEFAULT 1,
  expires_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS policy_decisions (
  decision_id VARCHAR(128) PRIMARY KEY,
  session_id VARCHAR(128) NOT NULL,
  tool_id VARCHAR(128) NOT NULL,
  resource_id VARCHAR(128) NOT NULL,
  decision VARCHAR(64) NOT NULL,
  proof_json LONGTEXT NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sync_metadata (
  sync_key VARCHAR(64) PRIMARY KEY,
  last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  row_count INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS access_requests (
  request_id VARCHAR(128) PRIMARY KEY,
  session_id VARCHAR(128) NOT NULL,
  user_id VARCHAR(128) NOT NULL,
  requested_scope VARCHAR(255) NOT NULL,
  requested_resource VARCHAR(128) NOT NULL,
  requested_tool_id VARCHAR(128) NOT NULL,
  reason TEXT NOT NULL,
  recipe_id VARCHAR(128),
  status VARCHAR(64) NOT NULL DEFAULT 'pending',
  approver_id VARCHAR(128),
  proof_id VARCHAR(128),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_proposals (
  proposal_id VARCHAR(128) PRIMARY KEY,
  base_recipe_id VARCHAR(128) NOT NULL,
  title VARCHAR(255) NOT NULL,
  goal_class VARCHAR(128) NOT NULL,
  proposal_json LONGTEXT NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'proposed',
  evidence_session_id VARCHAR(128),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_events (
  event_id VARCHAR(128) PRIMARY KEY,
  session_id VARCHAR(128) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  event_json LONGTEXT NOT NULL,
  prev_event_hash VARCHAR(128),
  event_hash VARCHAR(128),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS slack_fixtures (
  fixture_id VARCHAR(128) PRIMARY KEY,
  channel_id VARCHAR(128) NOT NULL,
  payload_json LONGTEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_index_meta (
  recipe_id VARCHAR(128) PRIMARY KEY,
  graph_node_id VARCHAR(128),
  dolt_commit_hash VARCHAR(128) NOT NULL DEFAULT 'main',
  content_hash VARCHAR(128) NOT NULL,
  indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
