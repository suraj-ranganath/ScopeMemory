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
  resource_id VARCHAR(128) NOT NULL
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
