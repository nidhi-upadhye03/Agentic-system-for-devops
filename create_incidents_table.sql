-- Create incidents table for monitoring agent
CREATE TABLE IF NOT EXISTS incidents (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(255) UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value FLOAT,
    threshold FLOAT,
    message TEXT,
    labels JSONB,
    metadata JSONB,
    source VARCHAR(100) DEFAULT 'monitoring-agent',
    status VARCHAR(50) DEFAULT 'detected',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT chk_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_status CHECK (status IN ('detected', 'analyzing', 'resolved', 'failed'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_incidents_incident_id ON incidents(incident_id);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_metric_name ON incidents(metric_name);
CREATE INDEX IF NOT EXISTS idx_incidents_created_at ON incidents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_labels ON incidents USING GIN (labels);
CREATE INDEX IF NOT EXISTS idx_incidents_metadata ON incidents USING GIN (metadata);
