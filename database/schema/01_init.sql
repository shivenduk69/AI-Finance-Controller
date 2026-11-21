-- ====================================================================
-- AI Finance Controller — Database Initialization Schema (01_init.sql)
-- Architecture Target: PostgreSQL 16 + pgvector
-- Invariant: Financial values stored as NUMERIC(15, 2)
-- ====================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. Merchants Table
CREATE TABLE IF NOT EXISTS merchants (
    merchant_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Stores Table
CREATE TABLE IF NOT EXISTS stores (
    store_id VARCHAR(100) PRIMARY KEY,
    merchant_id VARCHAR(100) NOT NULL REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Corporate Users Table (Argon2id Hash Storage)
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(100) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('ADMIN', 'MERCHANT')),
    merchant_id VARCHAR(100) REFERENCES merchants(merchant_id) ON DELETE SET NULL,
    store_id VARCHAR(100) REFERENCES stores(store_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Gateway Transactions Table (Razorpay Records)
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(100) PRIMARY KEY,
    order_id VARCHAR(100),
    type VARCHAR(50) NOT NULL CHECK (type IN ('PAYMENT', 'REFUND', 'PAYOUT')),
    status VARCHAR(50) NOT NULL,
    method VARCHAR(50),
    amount_inr NUMERIC(15, 2) NOT NULL,
    fee_inr NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    tax_inr NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    settled_amount_inr NUMERIC(15, 2) NOT NULL DEFAULT 0.00,
    expected_settlement_date VARCHAR(50),
    timestamp VARCHAR(50),
    exception_flag VARCHAR(50),
    merchant_id VARCHAR(100) NOT NULL REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Internal Orders Table (Merchant Ledger)
CREATE TABLE IF NOT EXISTS internal_orders (
    order_id VARCHAR(100) PRIMARY KEY,
    amount_inr NUMERIC(15, 2) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at VARCHAR(50),
    customer_email VARCHAR(255),
    merchant_id VARCHAR(100) NOT NULL REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE
);

-- 7. Bank Statements Table (Nodal Deposits)
CREATE TABLE IF NOT EXISTS bank_statements (
    date VARCHAR(50) NOT NULL,
    amount_inr NUMERIC(15, 2) NOT NULL,
    bank_reference VARCHAR(255),
    merchant_id VARCHAR(100) NOT NULL REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    status VARCHAR(50),
    PRIMARY KEY (date, merchant_id, store_id)
);

-- 8. Document Chunks Table (RAG Embeddings via pgvector)
CREATE TABLE IF NOT EXISTS document_chunks (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    chunk_index INT NOT NULL,
    text_content TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Support Tickets Table
CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100),
    merchant_name VARCHAR(100),
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'PENDING', 'RESOLVED')),
    resolution_comments TEXT,
    merchant_id VARCHAR(100) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    store_id VARCHAR(100) REFERENCES stores(store_id) ON DELETE CASCADE,
    user_id VARCHAR(100) REFERENCES users(user_id) ON DELETE SET NULL,
    category VARCHAR(100),
    priority VARCHAR(50) DEFAULT 'Medium',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. AI Conversations Table
CREATE TABLE IF NOT EXISTS ai_conversations (
    conversation_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    merchant_id VARCHAR(100),
    store_id VARCHAR(100),
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 11. AI Messages Table
CREATE TABLE IF NOT EXISTS ai_messages (
    message_id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) NOT NULL REFERENCES ai_conversations(conversation_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 12. Real-Time Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    notification_id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) REFERENCES users(user_id) ON DELETE CASCADE,
    merchant_id VARCHAR(100),
    store_id VARCHAR(100),
    role VARCHAR(50) CHECK (role IN ('ADMIN', 'MERCHANT')),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    is_read INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 13. Audit Logs Table (Tamper-evident append-only)
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    action VARCHAR(255) NOT NULL,
    details TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 14. System Configuration Table
CREATE TABLE IF NOT EXISTS configuration (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value TEXT NOT NULL
);

-- 15. Exception Resolutions Table (Audit State Machine)
CREATE TABLE IF NOT EXISTS exception_resolutions (
    resolution_id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) NOT NULL,
    order_id VARCHAR(100),
    merchant_id VARCHAR(100) NOT NULL REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    amount_inr NUMERIC(15, 2) NOT NULL,
    issue_description TEXT,
    resolution_note TEXT,
    resolved_by_role VARCHAR(50) NOT NULL,
    resolved_by_user VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING_ADMIN' CHECK (status IN ('PENDING_ADMIN', 'RESOLVED', 'REJECTED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================================
-- Performance Indexes
-- ====================================================================
CREATE INDEX IF NOT EXISTS idx_tx_merchant_store ON transactions (merchant_id, store_id);
CREATE INDEX IF NOT EXISTS idx_tx_order ON transactions (order_id);
CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions (status);
CREATE INDEX IF NOT EXISTS idx_tx_settle_date ON transactions (expected_settlement_date);

CREATE INDEX IF NOT EXISTS idx_orders_merchant_store ON internal_orders (merchant_id, store_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON internal_orders (status);

CREATE INDEX IF NOT EXISTS idx_bank_date ON bank_statements (date, merchant_id, store_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets (status, merchant_id, store_id);
CREATE INDEX IF NOT EXISTS idx_notifs_lookup ON notifications (role, merchant_id, store_id, is_read);
CREATE INDEX IF NOT EXISTS idx_exc_res_status ON exception_resolutions (status, merchant_id, store_id);
CREATE INDEX IF NOT EXISTS idx_ai_msgs_conv ON ai_messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_file ON document_chunks (file_name);
