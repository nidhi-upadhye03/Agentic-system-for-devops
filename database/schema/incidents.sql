-- Incidents table schema for DevOps Copilot
-- Stores all detected incidents from monitoring agent

CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    metric_name VARCHAR(255),
    metric_value FLOAT,
    threshold FLOAT,
    message TEXT,
    labels JSONB,
    metadata JSONB,
    source VARCHAR(100) DEFAULT 'monitoring-agent',
    status VARCHAR(50) DEFAULT 'detected',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on incident_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_incidents_incident_id ON incidents(incident_id);

-- Create index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at DESC);

-- Create index on severity for filtering
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);

-- Create index on status for filtering
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);

-- Analysis results table
CREATE TABLE IF NOT EXISTS incident_analysis (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(255) NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    analysis_id VARCHAR(255) UNIQUE NOT NULL,
    root_cause TEXT,
    impact_analysis TEXT,
    recommendations TEXT[],
    confidence_score FLOAT,
    llm_provider VARCHAR(50),
    llm_model VARCHAR(100),
    analysis_time_ms INTEGER,
    similar_incidents JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on incident_id for joining with incidents
CREATE INDEX IF NOT EXISTS idx_analysis_incident_id ON incident_analysis(incident_id);

-- Create index on analysis_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_analysis_analysis_id ON incident_analysis(analysis_id);

-- Create index on created_at
CREATE INDEX IF NOT EXISTS idx_analysis_created_at ON incident_analysis(created_at DESC);

-- Actions table (for auto-response agent)
CREATE TABLE IF NOT EXISTS incident_actions (
    id SERIAL PRIMARY KEY,
    action_id VARCHAR(255) UNIQUE NOT NULL,
    incident_id VARCHAR(255) NOT NULL REFERENCES incidents(incident_id) ON DELETE CASCADE,
    analysis_id VARCHAR(255) REFERENCES incident_analysis(analysis_id) ON DELETE SET NULL,
    action_type VARCHAR(100) NOT NULL,
    action_params JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    result TEXT,
    error TEXT,
    requires_approval BOOLEAN DEFAULT false,
    approval_id VARCHAR(255),
    executed_by VARCHAR(100) DEFAULT 'auto-response-agent',
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for actions
CREATE INDEX IF NOT EXISTS idx_actions_incident_id ON incident_actions(incident_id);
CREATE INDEX IF NOT EXISTS idx_actions_action_id ON incident_actions(action_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON incident_actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_created_at ON incident_actions(created_at DESC);

-- Update timestamp triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_incidents_updated_at BEFORE UPDATE ON incidents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_incident_analysis_updated_at BEFORE UPDATE ON incident_analysis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_incident_actions_updated_at BEFORE UPDATE ON incident_actions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT ALL PRIVILEGES ON incidents TO devops;
GRANT ALL PRIVILEGES ON incident_analysis TO devops;
GRANT ALL PRIVILEGES ON incident_actions TO devops;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO devops;
