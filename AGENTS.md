# AI Finance Controller — Project AI Agent Instructions (`AGENTS.md`)

## 1. Project Context & Objectives

**AI Finance Controller** is a production-grade multi-source financial reconciliation, exception resolution, and intelligence platform. It reconciles high-volume digital commerce data across:
1. **Internal Orders:** Merchant operational order ledger.
2. **Payment Gateway (Razorpay):** Captured payment transactions, fees, taxes, and refunds.
3. **Bank Statements:** Direct credit and nodal settlement records.

The system is undergoing an **architectural and technology stack migration** from a monolithic Python/Streamlit implementation (`app.py`, 6,079 lines) into three independently deployable services:
- **Frontend Service:** React.js (Vite, JavaScript, Tailwind CSS, Plotly.js, Axios, TanStack Query, Socket.IO Client).
- **Backend Service:** Node.js + Express.js (CommonJS: `require` / `module.exports`, PostgreSQL, Redis, RabbitMQ, JWT, Argon2id, Socket.IO, Winston, Helmet).
- **AI & Data Processing Service:** Python 3.11 + FastAPI (Pandas, Polars, Google Gemini SDK, pgvector, PyPDF).
- **Independent Infrastructure:** PostgreSQL 16 with `pgvector`, Redis 7, and RabbitMQ 3 managed via `infrastructure/docker-compose.yml` on an external shared network `finance-network`.

**Core Invariant:** This is a technology and architecture migration, NOT a product redesign or feature redevelopment. The migration must preserve 100% of existing UI appearance, business logic, calculations, features, workflows, and user experience.

---

## 2. Instruction Priority Hierarchy

If instructions or requirements appear to conflict, agents must strictly follow this priority order:

1. **User's explicit instructions and approved decisions.**
2. **Project architecture and migration specifications approved by the user** (in `docs/`).
3. **`AGENTS.md`**, **`CLAUDE.md`**, and **`guidelines.md`**.
4. **Agent's own implementation preferences.**

Never override an approved decision or make unverified assumptions without explicit user confirmation.

---

## 3. Mandatory Coding & Architecture Rules

Every AI agent, contributor, and automated tool working on this codebase must adhere strictly to these 10 rules:

1. **1000-Line Limit:**
   - **No individual source-code file may exceed 1000 lines.**
   - Keep files modular, focused, and single-purpose.
   - Proactively split large files, components, controllers, or route handlers into smaller, logically organized sub-modules before they approach this limit.
2. **Established Folder Structure & Service Separation:**
   - Follow the target repository structure (`frontend/`, `backend/`, `ai-service/`, `infrastructure/`, `database/`, `docs/`, `tests/`).
   - Respect strict service boundaries and the Table Ownership Matrix defined in `docs/DATABASE_AUDIT.md`.
3. **Approved Technology Stack Only:**
   - Frontend must use **JavaScript (JSX)**, never TypeScript.
   - Backend must use **CommonJS (`require()` and `module.exports`)**, never ES Module `import`/`export`.
   - Primary database is **PostgreSQL**; MongoDB/Mongoose is not permitted.
   - Do not introduce unapproved frameworks, databases, ORMs, or third-party libraries.
4. **Preserve All Existing Features & Logic:**
   - Preserve all 7 reconciliation matching rules, Section 194-O TDS & GST formulas, 7-day cash forecasting math, confidence scoring algorithms, exception workflows, and visual design tokens.
   - All Python financial calculation logic must remain in Python inside `ai-service/`; never rewrite financial algorithms in JavaScript.
5. **Never Invent Functionality or Schemas:**
   - Never invent APIs, database columns, environment variables, business logic, UI layouts, or third-party integrations that do not exist in the source application or approved specifications.
6. **Inspect Existing Code First:**
   - Always inspect the existing implementation (`app.py`, `src/`, `data/`, `documents/`, `tests/`, and `docs/`) before formulating assumptions or writing replacement code.
7. **Ask for Clarification on Ambiguities:**
   - Whenever an existing feature is ambiguous, broken, or undocumented, document the question and request user clarification instead of guessing.
8. **Never Silently Remove or Simplify Features:**
   - Do not replace complex features with mocks, stubs, placeholders, or simplified implementations simply because migration is challenging.
9. **Keep Documentation Synchronized:**
   - Update architecture documents, API contracts, and guides whenever implementation details evolve with approval.
10. **Test and Report Honestly:**
    - Execute automated and regression tests before reporting completion.
    - **Never claim a test passed without actually running it and inspecting the output.**

---

## 4. Execution Workflow & Phase Gate Rules

All work must proceed strictly phase-by-phase according to `docs/MIGRATION_PLAN.md`:

1. **Before Starting Each Phase:**
   - State the phase scope, files affected, dependencies, and acceptance criteria.
   - Read `guidelines.md` and review all accumulated preventive instructions.
   - **Wait for explicit user approval before writing or modifying any code.**
2. **During Phase Execution:**
   - Work within the approved scope only.
   - Keep files under the 1000-line ceiling.
   - Maintain dual-mode execution capability (local CLI and independent Docker Compose).
3. **After Phase Implementation:**
   - Execute relevant unit, integration, and parity tests.
   - Report completed work, test outputs, unresolved issues, and remaining risks.
   - **Do not proceed to the next phase without explicit user approval.**

---

## 5. Service Responsibilities & Boundaries

### A. Frontend Service (`frontend/`)
- Pure React 18 SPA created with Vite (JavaScript).
- Tailwind CSS with design tokens (`--primary: #0F4C75`, `--navy: #172B4D`, `--bg: #F7F9FC`, dark sidebar `#161f30`, fonts: `Inter`, `Outfit`).
- Plotly.js (`react-plotly.js`) for interactive financial charts.
- Axios and TanStack Query for caching and API data fetching.
- Socket.IO client for live exception resolutions, ticket alerts, and notifications.
- Recreates 11 Merchant views, 13 Admin views, and the global floating AI popover with pixel-accurate parity.
- Local startup: `cd frontend && npm install && npm run dev` (Port 3000).

### B. Backend Service (`backend/`)
- Node.js + Express.js using CommonJS.
- PostgreSQL connection pool using `finance_backend_user` credentials.
- Redis client for metric caching and rate limiting.
- RabbitMQ connection for queuing asynchronous processing jobs.
- JWT authentication in secure HttpOnly cookies + Argon2id password hashing.
- Role-Based Access Control (RBAC) middleware enforcing merchant/store scoping vs. admin access.
- Socket.IO server emitting real-time updates.
- Helmet security headers, Winston logging, and Joi/Zod request validation schemas.
- Local startup: `cd backend && npm install && npm run dev` or `node server.js` (Port 5000).

### C. AI & Data Processing Service (`ai-service/`)
- Python 3.11 + FastAPI.
- PostgreSQL connection using `finance_ai_user` credentials and `pgvector`.
- Houses core mathematical and algorithmic engines:
  - `reconciliation/`: 7-rule three-way reconciliation matching.
  - `tax/`: Section 194-O TDS & GST compliance auditor.
  - `forecasting/`: 7-day rolling cash flow projection.
  - `rag/`: Vector chunk retrieval, Gemini embeddings, semantic search, and TF-IDF fallback.
  - `ingestion/`: CSV parsing, normalization, and settlement date computation.
- Local startup: `cd ai-service && uvicorn main:app --reload --port 8000` (Port 8000).

### D. Independent Infrastructure (`infrastructure/`)
- `infrastructure/docker-compose.yml` orchestrating:
  - `finance-postgres`: PostgreSQL 16 + pgvector (`:5432`)
  - `finance-redis`: Redis 7 Alpine (`:6379`)
  - `finance-rabbitmq`: RabbitMQ 3 Management (`:5672`, `:15672`)
- Connected via external Docker bridge `finance-network`.
- Persistent Docker named volumes (`postgres_data`, `redis_data`, `rabbitmq_data`).
