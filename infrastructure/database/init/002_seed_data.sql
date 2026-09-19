-- ============================================================================
-- AI DevOps Platform - Seed Data
-- Version: 1.0.0
-- Description: Seeds initial data for development and testing
-- ============================================================================

-- WARNING: This file contains default passwords for development only.
-- NEVER use these credentials in production!

-- ============================================================================
-- SEED USERS
-- ============================================================================

-- Admin user
-- Email: admin@devops.local
-- Password: Admin@123
INSERT INTO users (email, password_hash, full_name, role, is_active, is_verified)
VALUES (
    'admin@devops.local',
    '$2b$10$rZ8K9QZGvN2xYhKpH3z/xOX3TkE7nRvJqY6FmH4K8sX9gL2vB3wH6',  -- Admin@123
    'System Administrator',
    'admin',
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Approver user
-- Email: approver@devops.local
-- Password: Approver@123
INSERT INTO users (email, password_hash, full_name, role, is_active, is_verified)
VALUES (
    'approver@devops.local',
    '$2b$10$tA7B9YZGvN2xYhKpH3z/xOX3TkE7nRvJqY6FmH4K8sX9gL2vB3wH7',  -- Approver@123
    'Lead Approver',
    'approver',
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Developer user
-- Email: developer@devops.local
-- Password: Developer@123
INSERT INTO users (email, password_hash, full_name, role, is_active, is_verified)
VALUES (
    'developer@devops.local',
    '$2b$10$uC8C0YZGvN2xYhKpH3z/xOX3TkE7nRvJqY6FmH4K8sX9gL2vB3wH8',  -- Developer@123
    'John Developer',
    'developer',
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Viewer user
-- Email: viewer@devops.local
-- Password: Viewer@123
INSERT INTO users (email, password_hash, full_name, role, is_active, is_verified)
VALUES (
    'viewer@devops.local',
    '$2b$10$vD9D1YZGvN2xYhKpH3z/xOX3TkE7nRvJqY6FmH4K8sX9gL2vB3wH9',  -- Viewer@123
    'Jane Viewer',
    'viewer',
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- ============================================================================
-- SEED SAMPLE APPROVALS (for testing)
-- ============================================================================

-- DISABLED: All dummy approval data commented out to show only real-time live data
-- Approvals will be created dynamically by auto-response agent when incidents require approval

-- -- Sample pending approval (high priority)
-- INSERT INTO approvals (
--     title,
--     description,
--     request_type,
--     requested_by,
--     requested_by_name,
--     status,
--     priority,
--     metadata,
--     expires_at
-- )
-- SELECT
--     'Deploy New Microservice to Production',
--     'Request to deploy the new payment processing microservice to production environment. All tests have passed and code review is complete.',
--     'deployment',
--     u.id,
--     u.full_name,
--     'pending',
--     'high',
--     '{"service": "payment-processor", "version": "v2.1.0", "environment": "production", "estimated_downtime": "0 minutes"}'::jsonb,
--     CURRENT_TIMESTAMP + INTERVAL '48 hours'
-- FROM users u
-- WHERE u.email = 'developer@devops.local'
-- LIMIT 1;

-- -- Sample pending approval (critical priority)
-- INSERT INTO approvals (
--     title,
--     description,
--     request_type,
--     requested_by,
--     requested_by_name,
--     status,
--     priority,
--     metadata,
--     expires_at
-- )
-- SELECT
--     'Scale Up Database Instances',
--     'Critical: Database performance degradation detected. Request to scale up PostgreSQL instances from db-t3.medium to db-r5.xlarge to handle increased load.',
--     'infrastructure',
--     u.id,
--     u.full_name,
--     'pending',
--     'critical',
--     '{"resource": "postgresql-primary", "current_size": "db-t3.medium", "requested_size": "db-r5.xlarge", "cost_impact": "+$150/month"}'::jsonb,
--     CURRENT_TIMESTAMP + INTERVAL '24 hours'
-- FROM users u
-- WHERE u.email = 'developer@devops.local'
-- LIMIT 1;

-- -- Sample pending approval (medium priority)
-- INSERT INTO approvals (
--     title,
--     description,
--     request_type,
--     requested_by,
--     requested_by_name,
--     status,
--     priority,
--     metadata
-- )
-- SELECT
--     'Update API Rate Limits',
--     'Request to update API rate limits for premium tier customers from 1000 req/min to 5000 req/min.',
--     'configuration',
--     u.id,
--     u.full_name,
--     'pending',
--     'medium',
--     '{"api": "v2/customers", "current_limit": 1000, "new_limit": 5000, "tier": "premium"}'::jsonb
-- FROM users u
-- WHERE u.email = 'developer@devops.local'
-- LIMIT 1;

-- -- Sample approved approval
-- INSERT INTO approvals (
--     title,
--     description,
--     request_type,
--     requested_by,
--     requested_by_name,
--     status,
--     priority,
--     metadata,
--     approved_by,
--     approved_by_name,
--     approved_at
-- )
-- SELECT
--     d.id as requested_by,
--     d.full_name as requested_by_name,
--     'approved',
--     'low',
--     '{"service": "user-authentication", "version": "v1.2.3", "environment": "staging"}'::jsonb,
--     a.id as approved_by,
--     a.full_name as approved_by_name,
--     CURRENT_TIMESTAMP - INTERVAL '2 hours'
-- FROM users d
-- CROSS JOIN users a
-- WHERE d.email = 'developer@devops.local' AND a.email = 'approver@devops.local'
-- LIMIT 1;

-- -- Sample rejected approval
-- INSERT INTO approvals (
--     title,
--     description,
--     request_type,
--     requested_by,
--     requested_by_name,
--     status,
--     priority,
--     metadata,
--     rejected_by,
--     rejected_by_name,
--     rejected_at,
--     rejection_reason
-- )
-- SELECT
--     'Delete Production Database Backup',
--     'Request to delete old database backups from production environment to save storage costs.',
--     'deletion',
--     d.id as requested_by,
--     d.full_name as requested_by_name,
--     'rejected',
--     'high',
--     '{"backups": ["backup-2024-01-01", "backup-2024-01-02"], "storage_saved": "500GB"}'::jsonb,
--     a.id as rejected_by,
--     a.full_name as rejected_by_name,
--     CURRENT_TIMESTAMP - INTERVAL '1 day',
--     'Cannot approve deletion of production backups. Backups are critical for disaster recovery and must be retained according to company policy.'
-- FROM users d
-- CROSS JOIN users a
-- WHERE d.email = 'developer@devops.local' AND a.email = 'approver@devops.local'
-- LIMIT 1;

-- ============================================================================
-- SEED APPROVAL COMMENTS
-- ============================================================================

INSERT INTO approval_comments (approval_id, user_id, user_name, comment, is_internal)
SELECT
    a.id,
    u.id,
    u.full_name,
    'This deployment looks good. All the tests have passed and the code review is complete. Approving now.',
    FALSE
FROM approvals a
CROSS JOIN users u
WHERE a.title = 'Deploy User Authentication Service' AND u.email = 'approver@devops.local'
LIMIT 1;

INSERT INTO approval_comments (approval_id, user_id, user_name, comment, is_internal)
SELECT
    a.id,
    u.id,
    u.full_name,
    'Internal note: Need to verify with compliance team before approving this.',
    TRUE
FROM approvals a
CROSS JOIN users u
WHERE a.title = 'Delete Production Database Backup' AND u.email = 'approver@devops.local'
LIMIT 1;

-- ============================================================================
-- SEED NOTIFICATIONS
-- ============================================================================

INSERT INTO notifications (user_id, title, message, type, priority, link)
SELECT
    u.id,
    'New Approval Request',
    'A new critical approval request "Scale Up Database Instances" requires your attention.',
    'approval_request',
    'urgent',
    '/approvals/2'
FROM users u
WHERE u.role IN ('admin', 'approver')
LIMIT 1;

INSERT INTO notifications (user_id, title, message, type, priority, link)
SELECT
    u.id,
    'Your Approval Request was Approved',
    'Your approval request "Deploy User Authentication Service" has been approved by Lead Approver.',
    'approval_response',
    'normal',
    '/approvals/4'
FROM users u
WHERE u.email = 'developer@devops.local'
LIMIT 1;

INSERT INTO notifications (user_id, title, message, type, priority, link)
SELECT
    u.id,
    'Your Approval Request was Rejected',
    'Your approval request "Delete Production Database Backup" has been rejected.',
    'approval_response',
    'normal',
    '/approvals/5'
FROM users u
WHERE u.email = 'developer@devops.local'
LIMIT 1;

-- ============================================================================
-- SEED AUDIT LOGS
-- ============================================================================

INSERT INTO audit_logs (user_id, user_email, action, resource_type, resource_id, metadata)
SELECT
    u.id,
    u.email,
    'user.login',
    'user',
    u.id,
    '{"method": "email", "success": true}'::jsonb
FROM users u
WHERE u.email = 'admin@devops.local'
LIMIT 1;

INSERT INTO audit_logs (user_id, user_email, action, resource_type, resource_id, metadata)
SELECT
    u.id,
    u.email,
    'approval.create',
    'approval',
    1,
    '{"approval_title": "Deploy New Microservice to Production"}'::jsonb
FROM users u
WHERE u.email = 'developer@devops.local'
LIMIT 1;

INSERT INTO audit_logs (user_id, user_email, action, resource_type, resource_id, metadata)
SELECT
    u.id,
    u.email,
    'approval.approve',
    'approval',
    4,
    '{"approval_title": "Deploy User Authentication Service"}'::jsonb
FROM users u
WHERE u.email = 'approver@devops.local'
LIMIT 1;

-- ============================================================================
-- SEED SAMPLE TASKS
-- ============================================================================

INSERT INTO tasks (task_id, task_type, status, priority, payload, result)
VALUES
    (uuid_generate_v4()::varchar, 'llm_request', 'completed', 7, '{"prompt": "Explain microservices architecture", "model": "gpt-4"}'::jsonb, '{"response": "Microservices architecture is...", "tokens": 250}'::jsonb),
    (uuid_generate_v4()::varchar, 'document_ingestion', 'processing', 5, '{"document_id": "doc-123", "source": "technical-docs.pdf"}'::jsonb, NULL),
    (uuid_generate_v4()::varchar, 'approval_notification', 'completed', 9, '{"approval_id": 1, "notification_type": "email"}'::jsonb, '{"sent": true, "timestamp": "2024-01-15T10:30:00Z"}'::jsonb),
    (uuid_generate_v4()::varchar, 'llm_request', 'failed', 5, '{"prompt": "Test prompt", "model": "gpt-4"}'::jsonb, NULL);

UPDATE tasks SET error_message = 'Rate limit exceeded' WHERE status = 'failed';

-- ============================================================================
-- SEED LLM REQUEST HISTORY
-- ============================================================================

INSERT INTO llm_requests (user_id, provider, model, prompt_tokens, completion_tokens, total_tokens, cost, latency_ms, status, cache_hit)
SELECT
    u.id,
    'openai',
    'gpt-4',
    150,
    100,
    250,
    0.0075,
    1200,
    'success',
    FALSE
FROM users u
WHERE u.email = 'developer@devops.local'
LIMIT 1;

INSERT INTO llm_requests (user_id, provider, model, prompt_tokens, completion_tokens, total_tokens, cost, latency_ms, status, cache_hit)
SELECT
    u.id,
    'anthropic',
    'claude-3-opus-20240229',
    200,
    150,
    350,
    0.0105,
    1500,
    'success',
    FALSE
FROM users u
WHERE u.email = 'developer@devops.local'
LIMIT 1;

INSERT INTO llm_requests (user_id, provider, model, prompt_tokens, completion_tokens, total_tokens, cost, latency_ms, status, cache_hit)
SELECT
    u.id,
    'openai',
    'gpt-4',
    150,
    100,
    250,
    0.0,
    50,
    'success',
    TRUE
FROM users u
WHERE u.email = 'developer@devops.local'
LIMIT 1;

-- ============================================================================
-- SEED SAMPLE DOCUMENTS
-- ============================================================================

INSERT INTO documents (document_id, title, content, source, document_type, metadata, chunk_count, embedding_status, indexed_at)
VALUES
    (uuid_generate_v4()::varchar, 'API Documentation v2.0', 'This is the API documentation for version 2.0...', 'https://docs.company.com/api/v2', 'markdown', '{"version": "2.0", "category": "api"}'::jsonb, 15, 'completed', CURRENT_TIMESTAMP),
    (uuid_generate_v4()::varchar, 'Deployment Guidelines', 'Guidelines for deploying services to production...', 'internal-wiki/deployment', 'markdown', '{"category": "guidelines"}'::jsonb, 8, 'completed', CURRENT_TIMESTAMP),
    (uuid_generate_v4()::varchar, 'Architecture Overview', 'System architecture and design patterns...', 'confluence/architecture', 'markdown', '{"category": "architecture"}'::jsonb, 12, 'completed', CURRENT_TIMESTAMP),
    (uuid_generate_v4()::varchar, 'Security Best Practices', 'Security guidelines and best practices...', 'internal-docs/security.pdf', 'pdf', '{"category": "security", "confidential": true}'::jsonb, 0, 'pending', NULL);

-- ============================================================================
-- PRINT SEED DATA SUMMARY
-- ============================================================================

-- Display summary of seeded data
DO $$
BEGIN
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Seed data successfully inserted!';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Users created: %', (SELECT COUNT(*) FROM users);
    RAISE NOTICE 'Approvals created: %', (SELECT COUNT(*) FROM approvals);
    RAISE NOTICE 'Notifications created: %', (SELECT COUNT(*) FROM notifications);
    RAISE NOTICE 'Audit logs created: %', (SELECT COUNT(*) FROM audit_logs);
    RAISE NOTICE 'Tasks created: %', (SELECT COUNT(*) FROM tasks);
    RAISE NOTICE 'LLM requests created: %', (SELECT COUNT(*) FROM llm_requests);
    RAISE NOTICE 'Documents created: %', (SELECT COUNT(*) FROM documents);
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'DEFAULT LOGIN CREDENTIALS (Development Only):';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Admin:';
    RAISE NOTICE '  Email: admin@devops.local';
    RAISE NOTICE '  Password: Admin@123';
    RAISE NOTICE '';
    RAISE NOTICE 'Approver:';
    RAISE NOTICE '  Email: approver@devops.local';
    RAISE NOTICE '  Password: Approver@123';
    RAISE NOTICE '';
    RAISE NOTICE 'Developer:';
    RAISE NOTICE '  Email: developer@devops.local';
    RAISE NOTICE '  Password: Developer@123';
    RAISE NOTICE '';
    RAISE NOTICE 'Viewer:';
    RAISE NOTICE '  Email: viewer@devops.local';
    RAISE NOTICE '  Password: Viewer@123';
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'WARNING: Change these passwords in production!';
    RAISE NOTICE '==============================================';
END $$;

-- ============================================================================
-- UPDATE SCHEMA VERSION
-- ============================================================================

INSERT INTO schema_version (version, description) VALUES ('1.0.1', 'Seed data inserted');

-- ============================================================================
-- END OF SEED DATA
-- ============================================================================
