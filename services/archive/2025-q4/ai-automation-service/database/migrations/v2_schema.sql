-- Home Assistant Conversation Integration v2.0 Database Schema
-- Migration from v1.x to v2.0
-- Created: 2025-01-XX

-- Core conversation tracking
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    conversation_type TEXT NOT NULL,  -- 'automation', 'clarification', 'action', 'information'
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'completed', 'abandoned'
    initial_query TEXT NOT NULL,
    context TEXT,  -- JSON stored as TEXT in SQLite
    metadata TEXT,  -- JSON stored as TEXT in SQLite
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    role TEXT NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    response_type TEXT,  -- 'automation_generated', 'clarification_needed', 'action_done', 'error', etc.
    intent TEXT,
    extracted_entities TEXT,  -- JSON stored as TEXT in SQLite
    confidence FLOAT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

-- Enhanced confidence tracking
CREATE TABLE IF NOT EXISTS confidence_factors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    factor_name TEXT NOT NULL,  -- 'entity_match', 'ambiguity_penalty', 'historical_success', etc.
    factor_score FLOAT NOT NULL,
    factor_weight FLOAT NOT NULL,
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

-- Function call tracking
CREATE TABLE IF NOT EXISTS function_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    function_name TEXT NOT NULL,
    parameters TEXT NOT NULL,  -- JSON stored as TEXT in SQLite
    result TEXT,  -- JSON stored as TEXT in SQLite
    execution_time_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

-- Enhanced automation suggestions
CREATE TABLE IF NOT EXISTS automation_suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    suggestion_id TEXT UNIQUE NOT NULL,
    conversation_id TEXT NOT NULL,
    turn_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    automation_yaml TEXT,
    confidence FLOAT NOT NULL,
    response_type TEXT NOT NULL,
    validated_entities TEXT,  -- JSON stored as TEXT in SQLite
    test_results TEXT,  -- JSON stored as TEXT in SQLite
    status TEXT DEFAULT 'draft',  -- 'draft', 'tested', 'approved', 'deployed', 'rejected'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_turns_conversation ON conversation_turns(conversation_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_suggestions_conversation ON automation_suggestions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_confidence_conversation ON confidence_factors(conversation_id, turn_id);
CREATE INDEX IF NOT EXISTS idx_function_calls_conversation ON function_calls(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_type ON conversations(conversation_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_suggestions_status ON automation_suggestions(status, created_at DESC);

-- Note: Existing tables (ask_ai_queries, clarification_sessions, entity_aliases, etc.) 
-- are kept for backward reference and read-only access after migration

