# Database Setup, Schema Architecture & Role Isolation Guide

## 1. Overview & Core Standards

The **AI Finance Controller** uses **PostgreSQL 16** with the **`pgvector`** extension as its unified relational and semantic data store.

### Key Database Standards:
1. **Precision Rule:** All financial currency amounts are strictly stored as `NUMERIC(15, 2)` (or `NUMERIC(15, 4)` for fee/GST/TDS rates). Floating-point types (`FLOAT`, `REAL`, `DOUBLE`) are strictly prohibited to prevent IEEE-754 decimal rounding drift.
2. **Role Isolation Rule:** The Backend Service and the AI Service connect using separate database credentials with strictly limited permissions defined in the Table Ownership Matrix.
3. **Dual-Mode Connectivity:**
   - **Local Bare-Metal Development:** Connects via `localhost` and the configured host port (`5434`).
   - **Docker Container Execution:** Connects via the internal service hostname (`finance-postgres:5432`) on the shared Docker network `finance-network`.

---

## 2. Infrastructure Startup & Initialization

### Step 1: Start PostgreSQL via Infrastructure Docker Compose
```bash
# Create shared external network (one-time setup)
docker network create finance-network

# Start database and supporting infrastructure
docker compose -f infrastructure/docker-compose.yml up -d postgres
```

The database container automatically runs all scripts in `docker-entrypoint-initdb.d/` on first startup:
1. `database/schema/01_init.sql`: Creates extensions (`vector`, `uuid-ossp`), tables, foreign keys, and performance indexes.
2. `database/schema/02_roles_and_grants.sql`: Creates application roles `finance_backend_user` and `finance_ai_user` with isolated permissions.
3. `database/seeds/01_seed.sql`: Seeds default merchants, stores, users with Argon2id password hashes, platform settings, support tickets, and notifications.

### Step 2: Ingest Source CSV Datasets
To load the primary transaction datasets into PostgreSQL:
```bash
python database/seeds/02_import_csv.py
```
This script populates:
- `transactions`: 120 gateway records with precomputed settlement dates.
- `internal_orders`: 89 merchant operational orders.
- `bank_statements`: 83 daily settlement deposits.

---

## 3. Database Roles & Table Ownership Matrix

```
                      POSTGRESQL 16 (finance_controller)
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            │                                                   │
            ▼                                                   ▼
  finance_backend_user                                   finance_ai_user
  (Backend Service Node.js)                             (AI Service FastAPI)
  ├── merchants (CRUD)                                  ├── transactions (CRUD)
  ├── stores (CRUD)                                     ├── internal_orders (CRUD)
  ├── users (CRUD)                                      ├── bank_statements (CRUD)
  ├── support_tickets (CRUD)                            ├── document_chunks (CRUD)
  ├── notifications (CRUD)                              ├── exception_resolutions (CR)
  ├── audit_logs (CR)                                   ├── ai_messages (CR)
  ├── configuration (CRUD)                              └── Reads: entities & configs
  ├── ai_conversations (CRUD)
  ├── exception_resolutions (RU)
  └── Reads: financial tables
```

---

## 4. Database Verification & Diagnostic Commands

```bash
# Connect to PostgreSQL via psql CLI inside container
docker exec -it finance-postgres psql -U postgres -d finance_controller

# Verify pgvector extension
SELECT '[1, 2, 3]'::vector;

# Verify all tables exist
\dt

# Verify table row counts
SELECT 'transactions' AS tbl, count(*) FROM transactions
UNION ALL SELECT 'internal_orders', count(*) FROM internal_orders
UNION ALL SELECT 'bank_statements', count(*) FROM bank_statements
UNION ALL SELECT 'merchants', count(*) FROM merchants
UNION ALL SELECT 'stores', count(*) FROM stores
UNION ALL SELECT 'users', count(*) FROM users;

# Verify user permissions
\du
```

---

## 5. Backup & Disaster Recovery

### Creating a Full Database Backup:
```bash
docker exec -t finance-postgres pg_dump -U postgres -d finance_controller -F c -b -v -f /tmp/backup.dump
docker cp finance-postgres:/tmp/backup.dump ./database/backups/backup_$(date +%Y%m%d).dump
```

### Restoring from a Backup:
```bash
docker cp ./database/backups/backup_20261113.dump finance-postgres:/tmp/restore.dump
docker exec -t finance-postgres pg_restore -U postgres -d finance_controller -v --clean --if-exists /tmp/restore.dump
```
