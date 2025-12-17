-- Migration: Add scorecard tracking columns to ground_truth_labels
-- Date: 2024-12-16
-- Description: Supports scorecard-based label generation (FIX #0A)

-- Add scorecard_version column
ALTER TABLE ground_truth_labels 
ADD COLUMN IF NOT EXISTS scorecard_version VARCHAR(20) NULL;

-- Add scorecard_raw_score column  
ALTER TABLE ground_truth_labels 
ADD COLUMN IF NOT EXISTS scorecard_raw_score FLOAT NULL;

-- Update label_source comment (no schema change needed, just documentation)
-- Valid values: 'scorecard', 'observed', 'mixed'

-- Add index for scorecard queries
CREATE INDEX IF NOT EXISTS idx_gtl_scorecard_version 
ON ground_truth_labels(scorecard_version);

-- Note: Run this migration inside the postgres container:
-- docker exec -i kycc-postgres-1 psql -U kycc_user -d kycc_db < migrations/add_scorecard_columns.sql
