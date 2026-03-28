-- Claude Code Analyzer - Database Schema
-- SQLite DDL for sessions.db

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  start_time DATETIME NOT NULL,
  end_time DATETIME,
  duration_seconds INTEGER,
  language TEXT NOT NULL,
  project_name TEXT,
  file_path TEXT,
  total_tokens_used INTEGER,
  acceptance_rate FLOAT,
  status TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interactions (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  sequence_number INTEGER NOT NULL,
  timestamp DATETIME NOT NULL,
  human_prompt TEXT NOT NULL,
  claude_response TEXT NOT NULL,
  response_length INTEGER,
  was_accepted BOOLEAN NOT NULL,
  was_modified BOOLEAN NOT NULL,
  modification_count INTEGER,
  tokens_used INTEGER,
  interaction_type TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS errors (
  id TEXT PRIMARY KEY,
  interaction_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  error_type TEXT NOT NULL,
  error_message TEXT NOT NULL,
  language TEXT NOT NULL,
  severity TEXT NOT NULL,
  was_resolved_in_next_interaction BOOLEAN,
  recovery_interactions_count INTEGER,
  timestamp DATETIME NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (interaction_id) REFERENCES interactions(id),
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS code_metrics (
  id TEXT PRIMARY KEY,
  interaction_id TEXT NOT NULL,
  cyclomatic_complexity FLOAT,
  lines_of_code INTEGER,
  function_count INTEGER,
  class_count INTEGER,
  max_nesting_depth INTEGER,
  has_type_hints BOOLEAN,
  code_quality_score FLOAT,
  language TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (interaction_id) REFERENCES interactions(id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_sessions_language ON sessions(language);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

CREATE INDEX IF NOT EXISTS idx_interactions_session_id ON interactions(session_id);
CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_interactions_type ON interactions(interaction_type);

CREATE INDEX IF NOT EXISTS idx_errors_session_id ON errors(session_id);
CREATE INDEX IF NOT EXISTS idx_errors_interaction_id ON errors(interaction_id);
CREATE INDEX IF NOT EXISTS idx_errors_type ON errors(error_type);

CREATE INDEX IF NOT EXISTS idx_code_metrics_interaction_id ON code_metrics(interaction_id);
