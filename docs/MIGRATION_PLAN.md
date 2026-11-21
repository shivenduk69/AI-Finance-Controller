# Technology Stack & Architecture Migration Plan

## 1. Migration Philosophy & Invariants

This migration transforms the monolithic Python/Streamlit application into three independently deployable services:
1. **Frontend Service:** React.js + Vite + Tailwind CSS + Plotly.js
2. **Backend Service:** Node.js + Express.js (CommonJS) + PostgreSQL + Redis + RabbitMQ
3. **AI & Data Processing Service:** Python 3.11 + FastAPI + Pandas + Gemini SDK + pgvector

### Critical Migration Invariants:
1. **Zero UI Disruption:** Visual appearance, layout, dark sidebar (`#161f30`), typography (`Outfit`, `Inter`), color palette (`#0F4C75`, `#172B4D`, `#F7F9FC`), and interactions must match Streamlit 1:1.
2. **Zero Computational Modification:** The 7-rule three-way reconciliation formulas, Section 194-O tax auditing formulas, and 7-day cash forecasting formulas remain in Python and must yield mathematically identical outputs.
3. **Independent Operation:** Every service must be capable of running bare-metal via standard CLI commands (`npm run dev`, `uvicorn`) as well as in containerized mode via independent Docker Compose files.
4. **Data Integrity:** All financial figures are stored as PostgreSQL `NUMERIC(15, 2)` to eliminate IEEE-754 floating-point inaccuracies.
5. **No Big-Bang Rewrite:** Incremental phase-wise execution with verification checkpoints after every phase.

---

## 2. Phase-by-Phase Roadmap

```
Phase 1: Audit & Baseline ──────────► Phase 2: Infrastructure & Schema
                                                 │
      ┌──────────────────────────────────────────┴──────────────────────────────────────────┐
      ▼                                                                                     ▼
Phase 3: Backend Service (Express)                                              Phase 4: AI Service (FastAPI)
      │                                                                                     │
      └──────────────────────────────────────────┬──────────────────────────────────────────┘
                                                 ▼
                                   Phase 5: Frontend Service (React)
                                                 │
                                                 ▼
                                   Phase 6: Integration & Real-Time Sync
                                                 │
                                                 ▼
                                   Phase 7: Regression & Parity Verification
                                                 │
                                                 ▼
                                   Phase 8: Dockerization & Multi-Compose
                                                 │
                                                 ▼
                                   Phase 9: Live Data & Resilience
                                                 │
                                                 ▼
                                   Phase 10: Production Deployment & Sign-Off
```

---

### Phase 1: Audit and Baseline (Current Phase)
- **Scope:** Complete analysis of existing monolith, feature cataloging, schema audit, API contracts definition, and risk identification.
- **Affected Files:** `docs/*`
- **Dependencies:** None.
- **Acceptance Criteria:**
  - `docs/EXISTING_ARCHITECTURE.md` created.
  - `docs/FEATURE_INVENTORY.md` created.
  - `docs/DATABASE_AUDIT.md` created.
  - `docs/MIGRATION_PLAN.md` created.
  - `docs/API_CONTRACTS.md` created.
  - `docs/MIGRATION_RISKS.md` created.
  - All existing unit tests verified passing (`tests/test_reconciliation.py`).

---

### Phase 2: Architecture & Database Design
- **Scope:**
  - Create `infrastructure/docker-compose.yml` orchestrating PostgreSQL (with pgvector), Redis 7, and RabbitMQ 3.
  - Create `database/schema/01_init.sql` (schema DDL, constraints, indexes).
  - Create `database/schema/02_roles_and_grants.sql` (user permissions for `finance_backend_user` and `finance_ai_user`).
  - Create `database/seeds/01_seed.sql` and data import script from existing CSVs.
  - Create `docs/DOCKER_ARCHITECTURE.md` and `docs/DATABASE_SETUP.md`.
- **Dependencies:** Approval of Phase 1.
- **Acceptance Criteria:**
  - Docker network `finance-network` created.
  - `infrastructure/docker-compose.yml` starts PostgreSQL, Redis, RabbitMQ with passing health checks.
  - Tables created with proper constraints and roles.
  - Seed records populated and verified against original SQLite data.

---

### Phase 3: Backend Development (Node.js/Express)
- **Scope:**
  - Scaffold `backend/` using Node.js CommonJS (`require`/`module.exports`).
  - Configure Helmet, Winston logging, CORS, and cookie parser.
  - Implement Argon2id password hashing and JWT authentication middleware.
  - Implement RBAC guard middleware (`MERCHANT` vs `ADMIN`).
  - Implement PostgreSQL repository pool connecting as `finance_backend_user`.
  - Implement controllers and routes for auth, merchants, stores, users, audit logs, configuration, tickets, and notifications.
  - Implement Socket.IO server for real-time exception resolution updates.
  - Configure `backend/package.json` (`npm run dev`, `node server.js`).
  - Create `backend/Dockerfile`, `backend/docker-compose.yml`, and `backend/.env.example`.
- **Dependencies:** Phase 2 database available.
- **Acceptance Criteria:**
  - Backend starts manually via `npm run dev` and `node server.js` on port 5000.
  - `POST /api/auth/login` validates credentials with Argon2id and sets JWT cookie.
  - RBAC correctly blocks merchant access to admin routes.
  - Socket.IO connects and emits live notifications.
  - Unit/integration tests pass for backend routes.

---

### Phase 4: AI & Data Processing Service Extraction (FastAPI/Python)
- **Scope:**
  - Scaffold `ai-service/` using Python 3.11 and FastAPI.
  - Port Python processing modules without formula modification:
    - `reconciliation/engine.py` (ported from `src/reconciliation.py`).
    - `forecasting/engine.py` (ported from `src/forecaster.py`).
    - `tax/engine.py` (ported from `src/tax_matcher.py`).
    - `rag/engine.py` (ported from `src/rag_engine.py` with pgvector support).
    - `ingestion/pipeline.py` (ported from `src/upload_pipeline.py`).
    - `core/heuristic_engine.py` (ported from `src/heuristic_engine.py`).
  - Connect to PostgreSQL as `finance_ai_user`.
  - Expose internal REST endpoints:
    - `POST /internal/reconciliation/run`
    - `POST /internal/tax/audit`
    - `POST /internal/forecast/cashflow`
    - `POST /internal/ai/chat`
    - `POST /internal/ai/index`
  - Create `ai-service/Dockerfile`, `ai-service/docker-compose.yml`, and `ai-service/.env.example`.
- **Dependencies:** Phase 2 database and Phase 3 API specifications.
- **Acceptance Criteria:**
  - AI Service starts manually via `uvicorn main:app --reload --port 8000`.
  - All 8 unit tests in `tests/test_reconciliation.py` pass against the new service.
  - Identical outputs returned for synthetic batch and August 25 example batch.

---

### Phase 5: Frontend Migration (React.js + Vite + Tailwind + Plotly.js)
- **Scope:**
  - Initialize Vite React project (JavaScript, not TypeScript).
  - Configure Tailwind CSS with the design system tokens (`--primary: #0F4C75`, `--navy: #172B4D`, `--bg: #F7F9FC`, fonts `Inter`, `Outfit`).
  - Build common layout components: Dark Sidebar (`#161f30`), Top Header, Date Range Filter dropdown, Notification Popover, Floating AI Assistant button.
  - Build Split-Screen Sign-In page matching original layout and glowing metrics preview.
  - Build 11 Merchant Pages/Views:
    - Dashboard, Transactions Ledger, 3-Way Audit Node Drawer, Exceptions Queue (3 Tabs), Settlements Ledger, Bank Statement Reconciliation, Tax & TDS Compliance, AI Assistant Chat, Cash Forecast, Reports, Store Settings, Support Tickets.
  - Build 13 Admin Pages/Views:
    - Admin Dashboard, Merchants Registry, Stores Registry, Global Transactions, Central Exceptions Desk, Central Settlements, Support Helpdesk Queue, Notification Broadcasts, AI & RAG Center, Knowledge Base Hub, User Provisioning, Audit Trail, Platform Settings.
  - Wire Axios and TanStack Query to consume Backend REST endpoints.
  - Configure `frontend/package.json` (`npm run dev`).
  - Create `frontend/Dockerfile`, `frontend/docker-compose.yml`, and `frontend/.env.example`.
- **Dependencies:** Backend and AI Service operational.
- **Acceptance Criteria:**
  - Frontend starts independently via `npm run dev` on port 3000.
  - Pixel-accurate visual parity with original Streamlit application.
  - Zero TypeScript; standard JavaScript only.

---

### Phase 6: End-to-End Integration & Real-Time Sync
- **Scope:**
  - Connect Socket.IO client in React to Backend for real-time exception approval sync and alerts.
  - Configure Redis caching for dashboard metrics in Backend.
  - Set up RabbitMQ event bus for asynchronous CSV ingestion and heavy batch reconciliation.
  - Verify tenant isolation across all endpoints.
  - Document inter-service protocol in `docs/SERVICE_COMMUNICATION.md`.
- **Dependencies:** Phases 3, 4, 5.
- **Acceptance Criteria:**
  - Store submits exception $\to$ Admin sees update live via Socket.IO $\to$ Admin approves $\to$ Store view updates to `RESOLVED` live without page reload.
  - Redis cache hits confirmed on repeated metric requests.

---

### Phase 7: Regression, Mathematical Verification & Parity Testing
- **Scope:**
  - Side-by-side verification between original Streamlit application and new React frontend.
  - Compare metric values, table numbers, chart data points, and date filtering outputs.
  - Execute automated API regression test suite.
- **Dependencies:** Phase 6 complete.
- **Acceptance Criteria:**
  - Match accuracy %, gross collections, bank settled amount, expected T+2 numbers match to the penny.
  - Zero discrepancies in exception categories, confidence scores, or tax tags.

---

### Phase 8: Dockerization & Multi-Compose Validation
- **Scope:**
  - Verify container builds for `frontend`, `backend`, `ai-service`, `infrastructure`.
  - Validate that each service can be started and stopped using its own Compose file.
  - Validate container healthchecks and persistent volume data survival across restarts.
  - Document in `docs/DOCKER_ARCHITECTURE.md`.
- **Dependencies:** All services implemented.
- **Acceptance Criteria:**
  - `docker compose -f <service>/docker-compose.yml up -d` works independently for every service on `finance-network`.

---

### Phase 9: Live Data Processing & Resilience
- **Scope:**
  - Implement idempotent ingestion ensuring re-uploading identical transactions causes zero duplicate records.
  - Implement database transaction rollbacks on failure.
  - Implement RabbitMQ retry policy with dead-letter queue (DLQ).
- **Dependencies:** Phase 8 complete.
- **Acceptance Criteria:**
  - Repeated CSV uploads do not duplicate transactions or alter calculated metrics.

---

### Phase 10: Production Deployment Preparation & Final Documentation
- **Scope:**
  - Create production Nginx reverse proxy configurations.
  - Create `docs/DEPLOYMENT_GUIDE.md` and `docs/LOCAL_DEVELOPMENT.md`.
  - Overhaul root `README.md` with complete installation, manual execution, and Docker commands.
- **Dependencies:** Phases 1–9 verified.
- **Acceptance Criteria:**
  - Final project sign-off.
