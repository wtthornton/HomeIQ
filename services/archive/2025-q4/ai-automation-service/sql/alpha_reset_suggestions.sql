-- ============================================================================
-- Alpha Reset Script: Conversational Automation Suggestions
-- ============================================================================
-- Story: AI1.23 - Conversational Suggestion Refinement
-- Date: 2025-10-17
-- 
-- ⚠️ WARNING: This will DELETE ALL existing automation suggestions!
-- This is acceptable in Alpha but should NOT be used in production.
--
-- Purpose: Drop and recreate automation_suggestions table with new schema
-- for conversational refinement system (description-first, YAML on approval)
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: Backup existing suggestions (optional, for reference)
-- ============================================================================
-- Uncomment to create backup table before deletion:
-- CREATE TABLE IF NOT EXISTS automation_suggestions_backup_20251017 AS 
-- SELECT * FROM automation_suggestions;

-- ============================================================================
-- STEP 2: Delete all existing suggestions
-- ============================================================================
DO $$ 
DECLARE
    suggestion_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO suggestion_count FROM automation_suggestions;
    RAISE NOTICE 'Deleting % existing suggestions...', suggestion_count;
    DELETE FROM automation_suggestions;
    RAISE NOTICE '✓ Deleted % suggestions', suggestion_count;
END $$;

-- ============================================================================
-- STEP 3: Drop existing table and constraints
-- ============================================================================
DROP TABLE IF EXISTS automation_suggestions CASCADE;
RAISE NOTICE '✓ Dropped automation_suggestions table';

-- ============================================================================
-- STEP 4: Create new table with conversational schema
-- ============================================================================
CREATE TABLE automation_suggestions (
    -- Primary key
    id VARCHAR(50) PRIMARY KEY,
    
    -- Pattern reference
    pattern_id VARCHAR(50) NOT NULL,
    
    -- ===== NEW: Description-First Fields =====
    description_only TEXT NOT NULL,              -- Human-readable description (required)
    conversation_history JSONB DEFAULT '[]',     -- Array of edit history
    device_capabilities JSONB DEFAULT '{}',      -- Cached device features
    refinement_count INTEGER DEFAULT 0,          -- Number of user edits
    
    -- ===== YAML Generation (only after approval) =====
    automation_yaml TEXT,                        -- NULL until user approves
    yaml_generated_at TIMESTAMP,                 -- When YAML was created
    
    -- ===== Status Tracking (NEW) =====
    status VARCHAR(50) DEFAULT 'draft' NOT NULL, -- draft|refining|yaml_generated|deployed|rejected
    
    -- ===== Legacy Fields (kept for compatibility) =====
    title VARCHAR(255),                          -- Short title for display
    category VARCHAR(50),                        -- energy|comfort|security|convenience
    priority VARCHAR(50),                        -- high|medium|low
    confidence FLOAT,                            -- Pattern confidence score (0-1)
    
    -- ===== Timestamps =====
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW() NOT NULL,
    approved_at TIMESTAMP,                       -- When user approved
    deployed_at TIMESTAMP,                       -- When deployed to HA
    
    -- ===== Constraints =====
    CONSTRAINT fk_pattern
        FOREIGN KEY (pattern_id) 
        REFERENCES patterns(id) 
        ON DELETE CASCADE,
    
    CONSTRAINT chk_status 
        CHECK (status IN ('draft', 'refining', 'yaml_generated', 'deployed', 'rejected')),
    
    CONSTRAINT chk_refinement_count 
        CHECK (refinement_count >= 0),
    
    CONSTRAINT chk_confidence 
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

RAISE NOTICE '✓ Created automation_suggestions table with new schema';

-- ============================================================================
-- STEP 5: Create indexes for performance
-- ============================================================================
CREATE INDEX idx_suggestions_status ON automation_suggestions(status);
RAISE NOTICE '✓ Created index: idx_suggestions_status';

CREATE INDEX idx_suggestions_created ON automation_suggestions(created_at DESC);
RAISE NOTICE '✓ Created index: idx_suggestions_created';

CREATE INDEX idx_suggestions_pattern ON automation_suggestions(pattern_id);
RAISE NOTICE '✓ Created index: idx_suggestions_pattern';

CREATE INDEX idx_suggestions_refinement_count ON automation_suggestions(refinement_count);
RAISE NOTICE '✓ Created index: idx_suggestions_refinement_count';

-- ============================================================================
-- STEP 6: Create helpful view for summary statistics
-- ============================================================================
CREATE OR REPLACE VIEW suggestion_status_summary AS
SELECT 
    status,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    AVG(refinement_count) as avg_refinements,
    MIN(created_at) as oldest,
    MAX(created_at) as newest
FROM automation_suggestions
GROUP BY status;

RAISE NOTICE '✓ Created view: suggestion_status_summary';

-- ============================================================================
-- STEP 7: Add helpful comments
-- ============================================================================
COMMENT ON TABLE automation_suggestions IS 
'Conversational automation suggestions (Story AI1.23). Generates descriptions first, YAML only after user approval.';

COMMENT ON COLUMN automation_suggestions.description_only IS 
'Human-readable description shown to user. No YAML. Example: "When motion detected in Living Room after 6PM, turn on lights to 50%"';

COMMENT ON COLUMN automation_suggestions.conversation_history IS 
'Array of edit history: [{"timestamp": "...", "user_input": "...", "updated_description": "...", "validation_result": {...}}]';

COMMENT ON COLUMN automation_suggestions.device_capabilities IS 
'Cached device features: {"entity_id": {"supported_features": ["brightness", "rgb_color"], "friendly_capabilities": [...]}}';

COMMENT ON COLUMN automation_suggestions.status IS 
'Workflow status: draft (initial) → refining (editing) → yaml_generated (approved) → deployed (active in HA)';

COMMENT ON COLUMN automation_suggestions.automation_yaml IS 
'Home Assistant YAML. NULL until user approves. Generated only after refinement complete.';

-- ============================================================================
-- STEP 8: Verify schema
-- ============================================================================
DO $$ 
DECLARE
    column_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO column_count 
    FROM information_schema.columns 
    WHERE table_name = 'automation_suggestions';
    
    RAISE NOTICE '✓ Table has % columns', column_count;
    
    IF column_count < 15 THEN
        RAISE EXCEPTION 'Schema creation failed: expected at least 15 columns, got %', column_count;
    END IF;
END $$;

-- ============================================================================
-- COMPLETION
-- ============================================================================
COMMIT;

RAISE NOTICE '
============================================================================
✅ Alpha reset complete!
============================================================================
Next steps:
1. Restart ai-automation-service
2. Run: python scripts/reprocess_patterns.py
3. Verify: SELECT * FROM suggestion_status_summary;

Expected result: 0 suggestions initially, all will be in "draft" status after reprocessing
============================================================================
';

-- ============================================================================
-- Rollback command (if needed):
-- ROLLBACK;
-- ============================================================================

