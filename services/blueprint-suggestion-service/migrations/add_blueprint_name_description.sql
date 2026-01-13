-- Migration: Add blueprint_name and blueprint_description columns
-- Date: 2026-01-13
-- Description: Adds blueprint_name and blueprint_description columns to blueprint_suggestions table
--              to store descriptive names and descriptions for blueprint suggestions

-- Add blueprint_name column (nullable, can be backfilled later)
ALTER TABLE blueprint_suggestions 
ADD COLUMN IF NOT EXISTS blueprint_name VARCHAR(255) NULL;

-- Add blueprint_description column (nullable, can be backfilled later)
ALTER TABLE blueprint_suggestions 
ADD COLUMN IF NOT EXISTS blueprint_description TEXT NULL;

-- Create index on blueprint_name for faster lookups (optional)
CREATE INDEX IF NOT EXISTS idx_blueprint_suggestions_name 
ON blueprint_suggestions(blueprint_name) 
WHERE blueprint_name IS NOT NULL;

-- Note: Existing suggestions will have NULL values for these columns
-- They will be populated:
-- 1. When new suggestions are generated (automatic)
-- 2. When suggestions are fetched and enriched (on-demand fallback)
