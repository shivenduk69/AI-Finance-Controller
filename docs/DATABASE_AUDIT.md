# Database Audit & PostgreSQL Migration Specification

## 1. Current SQLite Database Audit

The existing application uses an embedded SQLite database (`data/finance_controller.db`, ~491 KB) initialized via `src/database.py`. The schema contains 15 tables supporting multi-tenancy, transactional data, audit logs, and AI RAG chunks.

### 1.1 Existing Table Definitions & Weaknesses in Current SQLite

1. **`merchants`:**
   - Columns: `merchant_id` (PK), `name`, `status`, `created_at`.
   - Weakness: `created_at` stored as string; lacks foreign key cascades.
2. **`stores`:**
   - Columns: `store_id` (PK), `merchant_id`, `name`, `location`, `status`, `created_at`.
   - Weakness: `merchant_id` has no enforced foreign key constraint in SQLite.
3. **`users`:**
   - Columns: `user_id` (PK), `email`, `password_hash`, `role`, `merchant_id`, `store_id`, `created_at`.
   - Weakness: Uses custom `salt:sha256` hashing instead of industry-standard Argon2id.
4. **`transactions` (Gateway):**
   - Columns: `transaction_id` (PK), `order_id`, `type`, `status`, `method`, `amount_inr`, `fee_inr`, `tax_inr`, `settled_amount_inr`, `expected_settlement_date`, `timestamp`, `exception_flag`, `merchant_id`, `store_id`.
   - Weakness: Financial values stored as `REAL` (floating-point IEEE-754), vulnerable to rounding inaccuracies.
5. **`internal_orders`:**
   - Columns: `order_id` (PK), `amount_inr`, `status`, `created_at`, `customer_email`, `merchant_id`, `store_id`.
   - Weakness: `amount_inr` stored as `REAL`; no unique constraint on `(order_id, merchant_id)`.
6. **`bank_statements`:**
   - Columns: `date`, `amount_inr`, `bank_reference`, `merchant_id`, `store_id`, `status`.
   - Composite PK: `(date, merchant_id, store_id)`.
   - Weakness: `amount_inr` stored as `REAL`.
7. **`document_chunks`:**
   - Columns: `id` (PK Auto), `file_name`, `chunk_index`, `text_content`, `embedding`.
   - Weakness: `embedding` stored as JSON serialized string (`TEXT`), requiring in-memory deserialization and linear brute-force cosine scanning.
8. **`support_tickets`:**
   - Columns: `ticket_id` (PK Auto), `transaction_id`, `merchant_name`, `subject`, `message`, `status`, `resolution_comments`, `timestamp`, `merchant_id`, `store_id`, `user_id`, `category`, `priority`.
9. **`ai_conversations`:**
   - Columns: `conversation_id` (PK), `user_id`, `merchant_id`, `store_id`, `title`, `created_at`.
10. **`ai_messages`:**
    - Columns: `message_id` (PK Auto), `conversation_id`, `role`, `content`, `sources`, `timestamp`.
11. **`notifications`:**
    - Columns: `notification_id` (PK Auto), `user_id`, `merchant_id`, `store_id`, `role`, `title`, `message`, `is_read`, `created_at`.
12. **`audit_logs`:**
    - Columns: `log_id` (PK Auto), `user_id`, `action`, `details`, `timestamp`.
13. **`configuration`:**
    - Columns: `config_key` (PK), `config_value`.
14. **`user_sessions`:**
    - Columns: `session_token` (PK), `user_id`, `expires_at`.
15. **`exception_resolutions`:**
    - Columns: `resolution_id` (PK Auto), `transaction_id`, `order_id`, `merchant_id`, `store_id`, `amount_inr`, `issue_description`, `resolution_note`, `resolved_by_role`, `resolved_by_user`, `status`, `created_at`.

---

## 2. Target PostgreSQL Schema Architecture

The target schema replaces floating-point types with strict `NUMERIC(15, 2)`, adds foreign key cascades, enforces tenant constraints, and utilizes `pgvector` for native vector search.

```sql
-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Merchants Table
CREATE TABLE merchants (
    merchant_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Stores Table
CREATE TABLE stores (
    store_id VARCHAR(100) PRIMARY KEY,
    merchant_id VARCHAR(100) NOT NULL REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Users Table (Argon2id Hashed Passwords)
CREATE TABLE users (
    user_id VARCHAR(100) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('ADMIN', 'MERCHANT')),
    merchant_id VARCHAR(100) REFERENCES merchants(merchant_id) ON DELETE SET NULL,
    store_id VARCHAR(100) REFERENCES stores(store_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Gateway Transactions Table
CREATE TABLE transactions (
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

-- 5. Internal Orders Table
CREATE TABLE internal_orders (
    order_id VARCHAR(100) PRIMARY KEY,
    amount_inr NUMERIC(15, 2) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at VARCHAR(50),
    customer_email VARCHAR(255),
    merchant_id VARCHAR(100) NOT NULL REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE
);

-- 6. Bank Statements Table
CREATE TABLE bank_statements (
    date VARCHAR(50) NOT NULL,
    amount_inr NUMERIC(15, 2) NOT NULL,
    bank_reference VARCHAR(255),
    merchant_id VARCHAR(100) NOT NULL REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    store_id VARCHAR(100) NOT NULL REFERENCES stores(store_id) ON DELETE CASCADE,
    status VARCHAR(50),
    PRIMARY KEY (date, merchant_id, store_id)
);

-- 7. Document Chunks (pgvector Embedding Storage)
CREATE TABLE document_chunks (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    chunk_index INT NOT NULL,
    text_content TEXT NOT NULL,
    embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Support Tickets Table
CREATE TABLE support_tickets (
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

-- 9. AI Conversations & Message History
CREATE TABLE ai_conversations (
    conversation_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    merchant_id VARCHAR(100),
    store_id VARCHAR(100),
    title VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ai_messages (
    message_id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(100) NOT NULL REFERENCES ai_conversations(conversation_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    sources TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. Notifications Table
CREATE TABLE notifications (
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

-- 11. Immutable Audit Trail
CREATE TABLE audit_logs (
    log_id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    action VARCHAR(255) NOT NULL,
    details TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 12. System Configuration Table
CREATE TABLE configuration (
    config_key VARCHAR(100) PRIMARY KEY,
    config_value TEXT NOT NULL
);

-- 13. Exception Resolutions Table (Audit State Machine)
CREATE TABLE exception_resolutions (
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
```

---

## 3. High-Performance Indexing Strategy

```sql
-- Indexes for Transaction & Order Matching
CREATE INDEX idx_tx_merchant_store ON transactions (merchant_id, store_id);
CREATE INDEX idx_tx_order ON transactions (order_id);
CREATE INDEX idx_tx_status ON transactions (status);
CREATE INDEX idx_tx_settle_date ON transactions (expected_settlement_date);

CREATE INDEX idx_orders_merchant_store ON internal_orders (merchant_id, store_id);
CREATE INDEX idx_orders_status ON internal_orders (status);

-- Indexes for Bank Settlement Reconciliation
CREATE INDEX idx_bank_date ON bank_statements (date, merchant_id, store_id);

-- Indexes for Workflow State Machines
CREATE INDEX idx_tickets_status ON support_tickets (status, merchant_id, store_id);
CREATE INDEX idx_notifs_lookup ON notifications (role, merchant_id, store_id, is_read);
CREATE INDEX idx_exc_res_status ON exception_resolutions (status, merchant_id, store_id);
CREATE INDEX idx_ai_msgs_conv ON ai_messages (conversation_id);

-- IVFFlat Index for Vector Similarity Search (Cosine distance)
CREATE INDEX idx_doc_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

---

## 4. Role-Based Database Permissions (User Separation)

```sql
-- Create application-specific users
CREATE USER finance_backend_user WITH PASSWORD 'backend_secure_password';
CREATE USER finance_ai_user WITH PASSWORD 'ai_secure_password';

-- Grant connection permissions
GRANT CONNECT ON DATABASE finance_controller TO finance_backend_user;
GRANT CONNECT ON DATABASE finance_controller TO finance_ai_user;
GRANT USAGE ON SCHEMA public TO finance_backend_user;
GRANT USAGE ON SCHEMA public TO finance_ai_user;

-- Backend Service Permissions (owns app entities, reads financial tables)
GRANT ALL PRIVILEGES ON TABLE merchants, stores, users, support_tickets, notifications, audit_logs, configuration, ai_conversations TO finance_backend_user;
GRANT SELECT, UPDATE ON TABLE exception_resolutions TO finance_backend_user;
GRANT SELECT, INSERT ON TABLE ai_messages TO finance_backend_user;
GRANT SELECT ON TABLE transactions, internal_orders, bank_statements, document_chunks TO finance_backend_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO finance_backend_user;

-- AI & Data Processing Service Permissions (owns financial ingestion and vector chunks)
GRANT ALL PRIVILEGES ON TABLE transactions, internal_orders, bank_statements, document_chunks TO finance_ai_user;
GRANT SELECT, INSERT ON TABLE exception_resolutions TO finance_ai_user;
GRANT SELECT, INSERT ON TABLE ai_messages TO finance_ai_user;
GRANT SELECT ON TABLE merchants, stores, users, configuration, ai_conversations TO finance_ai_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO finance_ai_user;
```

---

## 5. Migration Execution & Seed Plan

1. **Pre-Migration Extraction:** Export existing SQLite data into JSON/CSV dumps.
2. **Schema DDL Application:** Execute `database/schema/01_init.sql` and `database/schema/02_roles_and_grants.sql` via superuser.
3. **Data Ingestion:**
   - Ingest `transactions_processed.csv`, `internal_orders.csv`, and `bank_statement.csv` via Python ingestion script.
   - Seed default merchants (`flipkart`, `amazon`), 8 stores, and default user accounts with Argon2id hashes.
   - Seed initial platform configurations (`sys_gateway_fee`, `sys_gst_rate`, `sys_settlement_delay`, `sys_gemini_model`).
4. **Validation Check:** Verify row counts against original SQLite database to ensure 100% data parity.
