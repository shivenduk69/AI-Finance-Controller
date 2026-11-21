# Claude Code & Developer Guide (`CLAUDE.md`)

## 1. Project Overview

**AI Finance Controller** is an enterprise financial operations platform that performs three-way reconciliation (Internal Orders $\leftrightarrow$ Razorpay Gateway $\leftrightarrow$ Bank Statements), anomaly & exception detection, Section 194-O TDS & GST tax compliance auditing, cash flow forecasting, and RAG-grounded financial intelligence via Google Gemini.

The project is undergoing an architectural migration from a monolithic Python/Streamlit codebase (`app.py`) into three independently deployable services:
- **Frontend:** React 18 + Vite (JavaScript only, Tailwind CSS, Plotly.js, Axios, TanStack Query, Socket.IO Client).
- **Backend:** Node.js + Express.js (CommonJS only: `require` / `module.exports`, PostgreSQL, Redis, RabbitMQ, JWT, Argon2id, Socket.IO, Winston, Helmet).
- **AI & Data Processing Service:** Python 3.11 + FastAPI (Pandas, Polars, Google Gemini SDK, pgvector, PyPDF).
- **Independent Infrastructure:** PostgreSQL 16 with `pgvector`, Redis 7, RabbitMQ 3 on shared Docker network `finance-network`.

---

## 2. Command Quick-Reference

### A. Local Development (Manual Bare-Metal Execution)

#### 1. Infrastructure (PostgreSQL, Redis, RabbitMQ)
```bash
# Create shared external network (one-time)
docker network create finance-network

# Start infrastructure services
docker compose -f infrastructure/docker-compose.yml up -d

# Check health
docker compose -f infrastructure/docker-compose.yml ps
```

#### 2. Backend Service (Node.js / Express CommonJS)
```bash
cd backend
npm install
npm run dev
# Or direct execution:
node server.js
```
Runs on `http://localhost:5000`. Health check: `GET http://localhost:5000/api/health`.

#### 3. AI & Data Processing Service (Python / FastAPI)
```bash
cd ai-service
# Windows:
python -m venv venv
venv\Scripts\activate
# Linux/macOS:
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Runs on `http://localhost:8000`. Health check: `GET http://localhost:8000/internal/health`.

#### 4. Frontend Service (React / Vite)
```bash
cd frontend
npm install
npm run dev
```
Runs on `http://localhost:3000` with Vite proxy forwarding `/api` and `/socket.io` to `http://localhost:5000`.

---

### B. Containerized Execution (Independent Compose Files)

Every service can be started and stopped in isolation:
```bash
# Frontend
docker compose -f frontend/docker-compose.yml up -d --build
docker compose -f frontend/docker-compose.yml logs -f
docker compose -f frontend/docker-compose.yml down

# Backend
docker compose -f backend/docker-compose.yml up -d --build
docker compose -f backend/docker-compose.yml logs -f
docker compose -f backend/docker-compose.yml down

# AI Service
docker compose -f ai-service/docker-compose.yml up -d --build
docker compose -f ai-service/docker-compose.yml logs -f
docker compose -f ai-service/docker-compose.yml down

# Infrastructure
docker compose -f infrastructure/docker-compose.yml up -d
docker compose -f infrastructure/docker-compose.yml down
```

---

### C. Testing & Verification Commands

```bash
# Run existing Python unit test suite (Must always pass with 100% precision)
pytest tests/

# Run specific reconciliation test
pytest tests/test_reconciliation.py -v

# Run performance benchmark
python tests/benchmark_performance.py

# Backend unit tests (when inside backend/)
cd backend && npm test

# AI Service unit tests (when inside ai-service/)
cd ai-service && pytest tests/
```

---

## 3. Mandatory Code Style & Architectural Constraints

1. **1000-Line Limit:**
   - **No source code file may exceed 1000 lines.**
   - Split large components, controllers, and services into modular sub-files.
2. **Language Constraints:**
   - **Frontend:** Pure JavaScript (`.jsx`, `.js`). Never generate TypeScript (`.tsx`, `.ts`).
   - **Backend:** CommonJS only (`require()` and `module.exports`). Never generate ES Modules (`import`/`export`).
   - **Financial Calculations:** 100% Python in `ai-service/`. Never recalculate financial math in JavaScript.
   - **Database:** PostgreSQL only (`NUMERIC(15, 2)` for currency values). Never use floating-point types (`FLOAT`/`REAL`) for monetary amounts.
3. **Multi-Tenancy & Security:**
   - Every database query in `backend/` must scope records by `merchant_id` and `store_id` (unless the user has the verified `ADMIN` role).
   - Use separate DB users: `finance_backend_user` for Backend and `finance_ai_user` for AI Service.
4. **Zero Silent Modification:**
   - Never replace existing features, forms, or views with mocks or placeholders.
5. **Instruction & Priority Governance:**
   - Always follow the priority order:
     1. User's explicit requirements.
     2. Project architecture and migration specifications in `docs/`.
     3. `AGENTS.md`, `CLAUDE.md`, and `guidelines.md`.
     4. Personal preferences.
   - For all behavioral rules and operational standards, refer to [AGENTS.md](file:///d:/My%20Desktop/AI%20Finance%20Controller/AGENTS.md).
   - For mistake tracking and preventive instructions, refer to [guidelines.md](file:///d:/My%20Desktop/AI%20Finance%20Controller/guidelines.md).
