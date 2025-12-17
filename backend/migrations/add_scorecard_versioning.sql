-- Migration: Add Scorecard Version Management
-- Description: Creates scorecard_versions table for versioned scorecard storage
-- The scorecard is the source of truth for scoring; ML updates create new versions.

-- Scorecard versions table
CREATE TABLE IF NOT EXISTS scorecard_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, retired, failed
    weights JSONB NOT NULL,  -- Feature weights
    base_score INTEGER NOT NULL DEFAULT 300,
    max_score INTEGER NOT NULL DEFAULT 900,
    scaling_config JSONB,  -- Feature scaling configuration
    
    -- Metrics from ML training (if ML-refined)
    source VARCHAR(20) NOT NULL DEFAULT 'expert',  -- expert, ml_refined
    ml_model_id INTEGER,  -- FK to model_registry if ML-refined
    ml_auc FLOAT,
    ml_f1 FLOAT,
    
    -- Audit fields
    created_at TIMESTAMP DEFAULT NOW(),
    activated_at TIMESTAMP,
    retired_at TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system',
    notes TEXT
);

-- Index for active version lookup
CREATE INDEX IF NOT EXISTS idx_scorecard_versions_status 
    ON scorecard_versions(status);

-- Index for version lookup
CREATE INDEX IF NOT EXISTS idx_scorecard_versions_version 
    ON scorecard_versions(version);

-- Ensure only one active version
CREATE UNIQUE INDEX IF NOT EXISTS idx_scorecard_one_active 
    ON scorecard_versions(status) WHERE status = 'active';

-- Add scorecard_version_id to score_requests for tracking
ALTER TABLE score_requests 
    ADD COLUMN IF NOT EXISTS scorecard_version_id INTEGER 
    REFERENCES scorecard_versions(id);

-- Update model_registry to track scorecard refinement
ALTER TABLE model_registry 
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
    
-- Add check for model status
-- Valid statuses: active, challenger, failed, retired
COMMENT ON COLUMN model_registry.status IS 'Model lifecycle: active, challenger, failed, retired';

-- Insert initial expert scorecard (v1.0)
INSERT INTO scorecard_versions (
    version, 
    status, 
    weights, 
    base_score, 
    max_score, 
    source,
    notes
) VALUES (
    '1.0',
    'active',
    '{
        "kyc_verified": 15,
        "has_tax_id": 10,
        "company_age_years": 10,
        "transaction_count_6m": 20,
        "avg_transaction_amount": 15,
        "recent_activity_flag": 25,
        "transaction_regularity_score": 15,
        "network_size": 10,
        "direct_counterparty_count": 10
    }'::jsonb,
    300,
    900,
    'expert',
    'Initial expert-defined scorecard'
) ON CONFLICT (version) DO NOTHING;
