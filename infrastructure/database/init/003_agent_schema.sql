-- =====================================================
-- DEVOPS COPILOT AGENT SYSTEM - DATABASE SCHEMA
-- =====================================================
-- This schema supports the autonomous agent system
-- Created: October 22, 2025
-- Version: 1.0.0
-- =====================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- AGENT EVENTS TABLE
-- =====================================================
-- Stores all events published by agents for auditing and analysis

CREATE TABLE IF NOT EXISTS agent_events (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50),
    agent VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    severity VARCHAR(20),
    data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_agent CHECK (agent IN ('monitoring', 'analyzer', 'auto-response', 'notifier', 'memory'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agent_events_incident_id ON agent_events(incident_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_timestamp ON agent_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_events_agent ON agent_events(agent);
CREATE INDEX IF NOT EXISTS idx_agent_events_event_type ON agent_events(event_type);
CREATE INDEX IF NOT EXISTS idx_agent_events_severity ON agent_events(severity);

-- JSONB GIN index for faster JSON queries
CREATE INDEX IF NOT EXISTS idx_agent_events_data_gin ON agent_events USING GIN (data);

-- Comment on table
COMMENT ON TABLE agent_events IS 'Stores all events from the autonomous agent system';
COMMENT ON COLUMN agent_events.incident_id IS 'UUID linking related events for an incident';
COMMENT ON COLUMN agent_events.agent IS 'Source agent name';
COMMENT ON COLUMN agent_events.event_type IS 'Type of event (incident_detected, analysis_complete, etc.)';
COMMENT ON COLUMN agent_events.data IS 'Event-specific payload in JSON format';

-- =====================================================
-- INCIDENT PATTERNS TABLE
-- =====================================================
-- Stores detected patterns for learning and optimization

CREATE TABLE IF NOT EXISTS incident_patterns (
    id SERIAL PRIMARY KEY,
    pattern_type VARCHAR(100) NOT NULL,
    metric VARCHAR(100),
    occurrence_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    recommendation TEXT,
    confidence_score FLOAT DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_pattern_type CHECK (pattern_type IN ('recurring_metric', 'time_based', 'service_specific', 'cascade_failure', 'resource_exhaustion')),
    CONSTRAINT chk_occurrence_count CHECK (occurrence_count > 0),
    CONSTRAINT chk_confidence_score CHECK (confidence_score >= 0 AND confidence_score <= 100)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_incident_patterns_metric ON incident_patterns(metric);
CREATE INDEX IF NOT EXISTS idx_incident_patterns_pattern_type ON incident_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_incident_patterns_last_seen ON incident_patterns(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_incident_patterns_active ON incident_patterns(is_active);

-- Comment on table
COMMENT ON TABLE incident_patterns IS 'Detected incident patterns for learning and prediction';
COMMENT ON COLUMN incident_patterns.pattern_type IS 'Type of pattern detected';
COMMENT ON COLUMN incident_patterns.occurrence_count IS 'Number of times this pattern has occurred';
COMMENT ON COLUMN incident_patterns.confidence_score IS 'Confidence in pattern detection (0-100)';

-- =====================================================
-- AGENT METRICS TABLE
-- =====================================================
-- Stores performance metrics for each agent

CREATE TABLE IF NOT EXISTS agent_metrics (
    id SERIAL PRIMARY KEY,
    agent VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    unit VARCHAR(20),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB,

    -- Constraints
    CONSTRAINT chk_agent_metrics_agent CHECK (agent IN ('monitoring', 'analyzer', 'auto-response', 'notifier', 'memory'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent ON agent_metrics(agent);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_timestamp ON agent_metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_metric_name ON agent_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent_metric ON agent_metrics(agent, metric_name, timestamp DESC);

-- Comment on table
COMMENT ON TABLE agent_metrics IS 'Performance metrics for autonomous agents';
COMMENT ON COLUMN agent_metrics.metric_name IS 'Name of the metric (e.g., detection_latency, accuracy)';
COMMENT ON COLUMN agent_metrics.metric_value IS 'Numeric value of the metric';
COMMENT ON COLUMN agent_metrics.unit IS 'Unit of measurement (seconds, percentage, count)';

-- =====================================================
-- INCIDENT RESOLUTIONS TABLE
-- =====================================================
-- Stores incident resolution history and effectiveness

CREATE TABLE IF NOT EXISTS incident_resolutions (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) NOT NULL UNIQUE,
    root_cause TEXT,
    solution_applied TEXT,
    action_type VARCHAR(50),
    target_service VARCHAR(100),
    executed_by VARCHAR(50),
    execution_timestamp TIMESTAMP,
    was_successful BOOLEAN DEFAULT FALSE,
    resolution_time_seconds INTEGER,
    required_approval BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(100),
    effectiveness_score FLOAT,
    lessons_learned TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT chk_action_type CHECK (action_type IN ('scale_deployment', 'restart_pods', 'rollback_deployment', 'manual', 'other')),
    CONSTRAINT chk_effectiveness_score CHECK (effectiveness_score IS NULL OR (effectiveness_score >= 0 AND effectiveness_score <= 100))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_incident_resolutions_incident_id ON incident_resolutions(incident_id);
CREATE INDEX IF NOT EXISTS idx_incident_resolutions_action_type ON incident_resolutions(action_type);
CREATE INDEX IF NOT EXISTS idx_incident_resolutions_success ON incident_resolutions(was_successful);
CREATE INDEX IF NOT EXISTS idx_incident_resolutions_timestamp ON incident_resolutions(execution_timestamp DESC);

-- Comment on table
COMMENT ON TABLE incident_resolutions IS 'History of incident resolutions and their effectiveness';
COMMENT ON COLUMN incident_resolutions.effectiveness_score IS 'Score measuring how effective the solution was (0-100)';
COMMENT ON COLUMN incident_resolutions.resolution_time_seconds IS 'Time taken to resolve the incident';

-- =====================================================
-- AGENT PROMPTS TABLE
-- =====================================================
-- Stores LLM prompts for agents (for version control and optimization)

CREATE TABLE IF NOT EXISTS agent_prompts (
    id SERIAL PRIMARY KEY,
    agent VARCHAR(50) NOT NULL,
    prompt_name VARCHAR(100) NOT NULL,
    prompt_version VARCHAR(20) NOT NULL,
    prompt_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    performance_score FLOAT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),

    -- Unique constraint
    UNIQUE(agent, prompt_name, prompt_version),

    -- Constraints
    CONSTRAINT chk_agent_prompts_agent CHECK (agent IN ('monitoring', 'analyzer', 'auto-response', 'notifier', 'memory')),
    CONSTRAINT chk_performance_score CHECK (performance_score IS NULL OR (performance_score >= 0 AND performance_score <= 100))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agent_prompts_agent ON agent_prompts(agent);
CREATE INDEX IF NOT EXISTS idx_agent_prompts_active ON agent_prompts(is_active);
CREATE INDEX IF NOT EXISTS idx_agent_prompts_version ON agent_prompts(prompt_version);

-- Comment on table
COMMENT ON TABLE agent_prompts IS 'Version-controlled LLM prompts for agents';
COMMENT ON COLUMN agent_prompts.performance_score IS 'Performance score of this prompt version';
COMMENT ON COLUMN agent_prompts.usage_count IS 'Number of times this prompt has been used';

-- =====================================================
-- APPROVAL REQUESTS (Extension of existing approvals table)
-- =====================================================
-- Add columns to existing approvals table for agent integration

-- Check if approvals table exists
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'approvals') THEN
        -- Add agent-related columns if they don't exist
        IF NOT EXISTS (SELECT FROM pg_attribute WHERE attrelid = 'approvals'::regclass AND attname = 'agent_generated') THEN
            ALTER TABLE approvals ADD COLUMN agent_generated BOOLEAN DEFAULT FALSE;
        END IF;

        IF NOT EXISTS (SELECT FROM pg_attribute WHERE attrelid = 'approvals'::regclass AND attname = 'incident_id') THEN
            ALTER TABLE approvals ADD COLUMN incident_id VARCHAR(50);
        END IF;

        IF NOT EXISTS (SELECT FROM pg_attribute WHERE attrelid = 'approvals'::regclass AND attname = 'action_type') THEN
            ALTER TABLE approvals ADD COLUMN action_type VARCHAR(50);
        END IF;

        IF NOT EXISTS (SELECT FROM pg_attribute WHERE attrelid = 'approvals'::regclass AND attname = 'confidence_score') THEN
            ALTER TABLE approvals ADD COLUMN confidence_score FLOAT;
        END IF;

        IF NOT EXISTS (SELECT FROM pg_attribute WHERE attrelid = 'approvals'::regclass AND attname = 'auto_execute_at') THEN
            ALTER TABLE approvals ADD COLUMN auto_execute_at TIMESTAMP;
        END IF;

        -- Create index on incident_id
        CREATE INDEX IF NOT EXISTS idx_approvals_incident_id ON approvals(incident_id);
        CREATE INDEX IF NOT EXISTS idx_approvals_agent_generated ON approvals(agent_generated);
    END IF;
END $$;

-- =====================================================
-- VIEWS FOR REPORTING
-- =====================================================

-- View: Recent incidents with full details
CREATE OR REPLACE VIEW v_recent_incidents AS
SELECT
    ae.incident_id,
    MIN(ae.timestamp) as detected_at,
    MAX(ae.timestamp) as last_updated,
    (SELECT severity FROM agent_events WHERE incident_id = ae.incident_id ORDER BY timestamp DESC LIMIT 1) as current_severity,
    (SELECT event_type FROM agent_events WHERE incident_id = ae.incident_id ORDER BY timestamp DESC LIMIT 1) as current_status,
    ir.root_cause,
    ir.solution_applied,
    ir.was_successful,
    ir.resolution_time_seconds,
    COUNT(*) as event_count
FROM agent_events ae
LEFT JOIN incident_resolutions ir ON ae.incident_id = ir.incident_id
WHERE ae.timestamp > NOW() - INTERVAL '7 days'
GROUP BY ae.incident_id, ir.root_cause, ir.solution_applied, ir.was_successful, ir.resolution_time_seconds
ORDER BY detected_at DESC;

-- View: Agent performance summary
CREATE OR REPLACE VIEW v_agent_performance AS
SELECT
    agent,
    COUNT(*) as total_events,
    COUNT(DISTINCT incident_id) as incidents_handled,
    AVG(CASE WHEN metric_name = 'response_time' THEN metric_value END) as avg_response_time,
    MAX(timestamp) as last_active
FROM agent_events ae
LEFT JOIN agent_metrics am ON ae.agent = am.agent
WHERE ae.timestamp > NOW() - INTERVAL '24 hours'
GROUP BY agent;

-- View: Pattern effectiveness
CREATE OR REPLACE VIEW v_pattern_effectiveness AS
SELECT
    ip.pattern_type,
    ip.metric,
    ip.occurrence_count,
    COUNT(ir.id) as resolutions_using_pattern,
    AVG(ir.effectiveness_score) as avg_effectiveness,
    AVG(ir.resolution_time_seconds) as avg_resolution_time
FROM incident_patterns ip
LEFT JOIN incident_resolutions ir ON ir.root_cause LIKE '%' || ip.metric || '%'
WHERE ip.is_active = TRUE
GROUP BY ip.id, ip.pattern_type, ip.metric, ip.occurrence_count;

-- =====================================================
-- FUNCTIONS
-- =====================================================

-- Function: Record agent event
CREATE OR REPLACE FUNCTION record_agent_event(
    p_incident_id VARCHAR(50),
    p_agent VARCHAR(50),
    p_event_type VARCHAR(100),
    p_severity VARCHAR(20),
    p_data JSONB
) RETURNS INTEGER AS $$
DECLARE
    v_event_id INTEGER;
BEGIN
    INSERT INTO agent_events (incident_id, agent, event_type, severity, data)
    VALUES (p_incident_id, p_agent, p_event_type, p_severity, p_data)
    RETURNING id INTO v_event_id;

    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Update pattern occurrence
CREATE OR REPLACE FUNCTION update_pattern_occurrence(
    p_pattern_type VARCHAR(100),
    p_metric VARCHAR(100)
) RETURNS VOID AS $$
BEGIN
    -- Insert or update pattern
    INSERT INTO incident_patterns (pattern_type, metric, occurrence_count, last_seen)
    VALUES (p_pattern_type, p_metric, 1, NOW())
    ON CONFLICT (pattern_type, metric)
    DO UPDATE SET
        occurrence_count = incident_patterns.occurrence_count + 1,
        last_seen = NOW();
END;
$$ LANGUAGE plpgsql;

-- Function: Get agent health status
CREATE OR REPLACE FUNCTION get_agent_health_status()
RETURNS TABLE (
    agent VARCHAR(50),
    status VARCHAR(20),
    last_heartbeat TIMESTAMP,
    events_last_hour INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.agent,
        CASE
            WHEN MAX(a.timestamp) > NOW() - INTERVAL '5 minutes' THEN 'healthy'
            WHEN MAX(a.timestamp) > NOW() - INTERVAL '15 minutes' THEN 'degraded'
            ELSE 'unhealthy'
        END as status,
        MAX(a.timestamp) as last_heartbeat,
        COUNT(CASE WHEN a.timestamp > NOW() - INTERVAL '1 hour' THEN 1 END)::INTEGER as events_last_hour
    FROM agent_events a
    GROUP BY a.agent;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Trigger: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
DROP TRIGGER IF EXISTS trigger_incident_patterns_updated_at ON incident_patterns;
CREATE TRIGGER trigger_incident_patterns_updated_at
    BEFORE UPDATE ON incident_patterns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_incident_resolutions_updated_at ON incident_resolutions;
CREATE TRIGGER trigger_incident_resolutions_updated_at
    BEFORE UPDATE ON incident_resolutions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trigger_agent_prompts_updated_at ON agent_prompts;
CREATE TRIGGER trigger_agent_prompts_updated_at
    BEFORE UPDATE ON agent_prompts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- INITIAL DATA / SEED DATA
-- =====================================================

-- Insert default agent prompts for Analyzer Agent
INSERT INTO agent_prompts (agent, prompt_name, prompt_version, prompt_text, is_active, created_by)
VALUES
(
    'analyzer',
    'root_cause_analysis',
    'v1.0',
    'You are a DevOps expert analyzing a production incident.

INCIDENT DETAILS:
- Metric: {{metric}}
- Current Value: {{current_value}}
- Threshold: {{threshold}}
- Severity: {{severity}}
- Affected Services: {{affected_services}}

RECENT LOGS:
{{logs}}

SIMILAR PAST INCIDENTS:
{{similar_incidents}}

TASKS:
1. Identify the root cause of this incident
2. Explain why this happened
3. Rate your confidence in this analysis (0-100%)
4. Suggest immediate actions to resolve this

Provide your analysis in JSON format:
{
  "root_cause": "description",
  "explanation": "detailed explanation",
  "confidence": 85,
  "contributing_factors": ["factor1", "factor2"],
  "immediate_actions": ["action1", "action2"]
}',
    TRUE,
    'system'
)
ON CONFLICT (agent, prompt_name, prompt_version) DO NOTHING;

-- =====================================================
-- GRANTS (Adjust based on your user)
-- =====================================================

-- Grant permissions to application user (adjust username as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO your_app_user;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Verify tables created
DO $$
BEGIN
    RAISE NOTICE 'Agent Events table rows: %', (SELECT COUNT(*) FROM agent_events);
    RAISE NOTICE 'Incident Patterns table rows: %', (SELECT COUNT(*) FROM incident_patterns);
    RAISE NOTICE 'Agent Metrics table rows: %', (SELECT COUNT(*) FROM agent_metrics);
    RAISE NOTICE 'Incident Resolutions table rows: %', (SELECT COUNT(*) FROM incident_resolutions);
    RAISE NOTICE 'Agent Prompts table rows: %', (SELECT COUNT(*) FROM agent_prompts);
    RAISE NOTICE '✓ Agent system database schema initialized successfully!';
END $$;
