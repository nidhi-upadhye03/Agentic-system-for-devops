-- ============================================================================
-- AI DevOps Platform - Initial Database Schema
-- Version: 1.0.0
-- Description: Creates all necessary tables for the DevOps Platform
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable timestamp extension
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'viewer' CHECK (role IN ('admin', 'approver', 'viewer', 'developer')),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on users table
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_created_at ON users(created_at);

-- ============================================================================
-- APPROVALS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS approvals (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    request_type VARCHAR(100) CHECK (request_type IN ('deployment', 'infrastructure', 'code_change', 'configuration', 'access', 'deletion', 'scaling', 'other')),
    requested_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    requested_by_name VARCHAR(255),  -- Cached for performance
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled', 'expired')),
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    metadata JSONB,  -- Flexible storage for additional data
    approved_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_by_name VARCHAR(255),
    approved_at TIMESTAMP,
    rejected_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    rejected_by_name VARCHAR(255),
    rejected_at TIMESTAMP,
    rejection_reason TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on approvals table
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_approvals_priority ON approvals(priority);
CREATE INDEX idx_approvals_request_type ON approvals(request_type);
CREATE INDEX idx_approvals_requested_by ON approvals(requested_by);
CREATE INDEX idx_approvals_created_at ON approvals(created_at DESC);
CREATE INDEX idx_approvals_expires_at ON approvals(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_approvals_metadata ON approvals USING GIN (metadata);

-- ============================================================================
-- APPROVAL_COMMENTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS approval_comments (
    id SERIAL PRIMARY KEY,
    approval_id INTEGER REFERENCES approvals(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    user_name VARCHAR(255),  -- Cached for performance
    comment TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT FALSE,  -- Internal notes vs. public comments
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on approval_comments table
CREATE INDEX idx_approval_comments_approval_id ON approval_comments(approval_id);
CREATE INDEX idx_approval_comments_user_id ON approval_comments(user_id);
CREATE INDEX idx_approval_comments_created_at ON approval_comments(created_at DESC);

-- ============================================================================
-- AUDIT_LOGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,  -- e.g., 'user.login', 'approval.create', 'approval.approve'
    resource_type VARCHAR(100),  -- e.g., 'approval', 'user', 'deployment'
    resource_id INTEGER,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB,  -- Flexible storage for action-specific data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on audit_logs table
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_resource_id ON audit_logs(resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_metadata ON audit_logs USING GIN (metadata);

-- ============================================================================
-- NOTIFICATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) CHECK (type IN ('info', 'success', 'warning', 'error', 'approval_request', 'approval_response')),
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    link VARCHAR(500),  -- Link to related resource
    metadata JSONB,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on notifications table
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_notifications_expires_at ON notifications(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================================
-- TASKS TABLE (for worker service tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,  -- UUID from worker
    task_type VARCHAR(100) NOT NULL,  -- e.g., 'llm_request', 'document_ingestion', 'approval_notification'
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    priority INTEGER DEFAULT 5,  -- 1-10, higher = more priority
    payload JSONB,  -- Task input data
    result JSONB,  -- Task output data
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on tasks table
CREATE INDEX idx_tasks_task_id ON tasks(task_id);
CREATE INDEX idx_tasks_task_type ON tasks(task_type);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority DESC);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_payload ON tasks USING GIN (payload);

-- ============================================================================
-- LLM_REQUESTS TABLE (for tracking LLM API usage)
-- ============================================================================
CREATE TABLE IF NOT EXISTS llm_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    provider VARCHAR(50),  -- 'openai', 'anthropic', 'gemini'
    model VARCHAR(100),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost DECIMAL(10, 6),  -- Estimated cost in USD
    latency_ms INTEGER,  -- Response time in milliseconds
    status VARCHAR(50),  -- 'success', 'error', 'rate_limited'
    error_message TEXT,
    cache_hit BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on llm_requests table
CREATE INDEX idx_llm_requests_user_id ON llm_requests(user_id);
CREATE INDEX idx_llm_requests_provider ON llm_requests(provider);
CREATE INDEX idx_llm_requests_model ON llm_requests(model);
CREATE INDEX idx_llm_requests_status ON llm_requests(status);
CREATE INDEX idx_llm_requests_created_at ON llm_requests(created_at DESC);

-- ============================================================================
-- DOCUMENTS TABLE (for RAG/vector store tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(255) UNIQUE NOT NULL,  -- UUID
    title VARCHAR(500),
    content TEXT,
    source VARCHAR(255),  -- URL, file path, or identifier
    document_type VARCHAR(100),  -- 'pdf', 'markdown', 'text', 'code'
    metadata JSONB,
    chunk_count INTEGER DEFAULT 0,
    embedding_status VARCHAR(50) DEFAULT 'pending' CHECK (embedding_status IN ('pending', 'processing', 'completed', 'failed')),
    indexed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on documents table
CREATE INDEX idx_documents_document_id ON documents(document_id);
CREATE INDEX idx_documents_source ON documents(source);
CREATE INDEX idx_documents_document_type ON documents(document_type);
CREATE INDEX idx_documents_embedding_status ON documents(embedding_status);
CREATE INDEX idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX idx_documents_metadata ON documents USING GIN (metadata);

-- ============================================================================
-- SESSIONS TABLE (for authentication sessions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    refresh_token VARCHAR(500),
    ip_address INET,
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on sessions table
CREATE INDEX idx_sessions_session_id ON sessions(session_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_sessions_refresh_token ON sessions(refresh_token);

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at column
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_approvals_updated_at BEFORE UPDATE ON approvals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_approval_comments_updated_at BEFORE UPDATE ON approval_comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View for pending approvals with requester details
CREATE OR REPLACE VIEW pending_approvals AS
SELECT
    a.*,
    u.email as requested_by_email,
    u.avatar_url as requested_by_avatar
FROM approvals a
LEFT JOIN users u ON a.requested_by = u.id
WHERE a.status = 'pending' AND (a.expires_at IS NULL OR a.expires_at > CURRENT_TIMESTAMP)
ORDER BY
    CASE a.priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    a.created_at ASC;

-- View for user approval statistics
CREATE OR REPLACE VIEW user_approval_stats AS
SELECT
    u.id,
    u.email,
    u.full_name,
    COUNT(CASE WHEN a.status = 'pending' THEN 1 END) as pending_count,
    COUNT(CASE WHEN a.status = 'approved' THEN 1 END) as approved_count,
    COUNT(CASE WHEN a.status = 'rejected' THEN 1 END) as rejected_count,
    COUNT(*) as total_requests
FROM users u
LEFT JOIN approvals a ON u.id = a.requested_by
GROUP BY u.id, u.email, u.full_name;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================

-- Grant all permissions to the devops user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO devops;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO devops;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO devops;

-- ============================================================================
-- SCHEMA VERSION TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_version (version, description) VALUES ('1.0.0', 'Initial schema creation');

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
