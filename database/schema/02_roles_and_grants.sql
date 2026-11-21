-- ====================================================================
-- AI Finance Controller — Database Roles & Permissions (02_roles_and_grants.sql)
-- Enforces Table Ownership Matrix and Service Privilege Isolation
-- ====================================================================

-- 1. Create Application Database Roles (Idempotent)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'finance_backend_user') THEN
        CREATE ROLE finance_backend_user WITH LOGIN PASSWORD 'backend_secure_password';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'finance_ai_user') THEN
        CREATE ROLE finance_ai_user WITH LOGIN PASSWORD 'ai_secure_password';
    END IF;
END
$$;

-- 2. Basic Schema Usage
GRANT CONNECT ON DATABASE finance_controller TO finance_backend_user;
GRANT CONNECT ON DATABASE finance_controller TO finance_ai_user;
GRANT USAGE ON SCHEMA public TO finance_backend_user;
GRANT USAGE ON SCHEMA public TO finance_ai_user;

-- 3. Backend Service Permissions (finance_backend_user)
-- Owns: merchants, stores, users, support_tickets, notifications, audit_logs, configuration, ai_conversations
GRANT ALL PRIVILEGES ON TABLE merchants, stores, users, support_tickets, notifications, audit_logs, configuration, ai_conversations TO finance_backend_user;

-- Reads financial datasets
GRANT SELECT ON TABLE transactions, internal_orders, bank_statements, document_chunks TO finance_backend_user;

-- Exception Resolutions: Backend reads and updates status/approval
GRANT SELECT, INSERT, UPDATE ON TABLE exception_resolutions TO finance_backend_user;

-- AI Messages: Backend reads and inserts user messages
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE ai_messages TO finance_backend_user;

-- Sequence usage for serial IDs
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO finance_backend_user;

-- 4. AI & Data Processing Service Permissions (finance_ai_user)
-- Owns: transactions, internal_orders, bank_statements, document_chunks
GRANT ALL PRIVILEGES ON TABLE transactions, internal_orders, bank_statements, document_chunks TO finance_ai_user;

-- Reads entity & config tables for tenant validation and dynamic parameter loading
GRANT SELECT ON TABLE merchants, stores, users, configuration, ai_conversations TO finance_ai_user;

-- Exception Resolutions: AI Service inserts newly detected exceptions
GRANT SELECT, INSERT, UPDATE ON TABLE exception_resolutions TO finance_ai_user;

-- AI Messages: AI Service reads context and inserts assistant answers & source chunks
GRANT SELECT, INSERT ON TABLE ai_messages TO finance_ai_user;

-- Sequence usage for serial IDs
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO finance_ai_user;
