-- ScopeMemory 2-hour demo schema (RFC-07 binding subset)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
  team_id TEXT PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_teams (
  user_id TEXT NOT NULL REFERENCES users(user_id),
  team_id TEXT NOT NULL REFERENCES teams(team_id),
  role TEXT NOT NULL,
  PRIMARY KEY (user_id, team_id)
);

CREATE TABLE IF NOT EXISTS agents (
  agent_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  identity_ref TEXT NOT NULL,
  trust_score REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(user_id),
  team_id TEXT NOT NULL REFERENCES teams(team_id),
  agent_id TEXT NOT NULL REFERENCES agents(agent_id),
  goal TEXT NOT NULL,
  goal_class TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'preflighted'
);

CREATE TABLE IF NOT EXISTS delegations (
  session_id TEXT PRIMARY KEY REFERENCES sessions(session_id),
  user_id TEXT NOT NULL REFERENCES users(user_id),
  agent_id TEXT NOT NULL REFERENCES agents(agent_id),
  delegated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workflow_recipes (
  recipe_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  team_id TEXT NOT NULL REFERENCES teams(team_id),
  goal_class TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'accepted'
);

CREATE TABLE IF NOT EXISTS recipe_tools (
  recipe_id TEXT NOT NULL REFERENCES workflow_recipes(recipe_id),
  tool_id TEXT NOT NULL,
  required INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (recipe_id, tool_id)
);

CREATE TABLE IF NOT EXISTS recipe_scopes (
  recipe_id TEXT NOT NULL REFERENCES workflow_recipes(recipe_id),
  scope TEXT NOT NULL,
  approval_mode TEXT NOT NULL,
  PRIMARY KEY (recipe_id, scope)
);

CREATE TABLE IF NOT EXISTS resources (
  resource_id TEXT PRIMARY KEY,
  team_id TEXT NOT NULL REFERENCES teams(team_id),
  sensitivity TEXT NOT NULL DEFAULT 'normal',
  external INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS grants (
  grant_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(session_id),
  scope TEXT NOT NULL,
  resource_id TEXT NOT NULL REFERENCES resources(resource_id),
  expires_at TEXT
);

-- Static tool → scope mapping for demo (production: mcp_tools + tool_required_scopes)
CREATE TABLE IF NOT EXISTS tool_scopes (
  tool_id TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  access_kind TEXT NOT NULL
);
