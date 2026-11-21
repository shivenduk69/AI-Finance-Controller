# AI Coding Guidelines & Hallucination / Mistake Tracking Log

## 1. Purpose & Operating Protocol

This document serves as the **operational compliance guide and immutable mistake ledger** for all AI agents and engineers working on the AI Finance Controller migration.

### Mandatory Pre-Phase Protocol:
> [!IMPORTANT]
> **Before starting any new migration phase or writing code, every AI agent MUST read this entire file and explicitly apply all accumulated preventive instructions.**

Whenever an agent:
1. Makes an unsupported assumption.
2. Invents or incorrectly describes an existing feature, schema, API, or rule.
3. Uses an unapproved language, module system, library, or database driver.
4. Misinterprets the existing business logic, calculations, or architecture.
5. Generates code based on unverified information.
6. Encounters any other AI-generated hallucination or factual error.

The agent must **immediately record a new structured entry** in Section 3 of this document.

---

## 2. Core Operational Guidelines

1. **Modular Code Architecture (1000-Line Limit):**
   - No source code file may exceed 1000 lines under any circumstance.
   - If a React component, Express route collection, or Python utility grows beyond 600 lines, immediately plan its modular decomposition into sub-components, helper services, or focused routers.
2. **Strict Technology Constraints:**
   - **Frontend:** React + Vite in pure JavaScript (`.jsx` / `.js`). Do NOT generate TypeScript (`.tsx` / `.ts`).
   - **Backend:** Node.js + Express in CommonJS (`require` / `module.exports`). Do NOT generate ES Module `import`/`export`.
   - **Database:** PostgreSQL 16 + `pgvector`. Do NOT introduce MongoDB, Mongoose, SQLite, or unapproved ORMs.
   - **Financial Processing:** Python 3.11 + FastAPI + Pandas. Do NOT port financial calculations into JavaScript.
3. **Truthful Verification:**
   - Never report a test as passed or a command as succeeded unless the tool was executed, output was inspected, and exit code was 0.
4. **Zero Silent Modification:**
   - Never omit, stub, mock, or simplify existing features or calculations to expedite migration.

---

## 3. Hallucination & Mistake Tracking Ledger

*All entries are permanent. Do not delete previous entries to keep the file short; update an entry only when its correction has been fully verified.*

---

### Entry 001: Legacy Monolithic File Size vs. Modularity Limit
- **Date:** 2026-11-13
- **What was incorrect / Trap Identified:** Assuming that existing Streamlit components can be ported as single large React page files or monolithic route handlers (legacy `app.py` is 6,079 lines; `src/database.py` is 1,419 lines).
- **Why it was incorrect:** Violates the mandatory **1000-line limit** rule. Large monolithic files create cognitive bloat, make automated testing brittle, and hinder parallel service development.
- **Correct information:** Every React page must be partitioned into focused sub-components (e.g., metric cards, chart containers, table drawers, filter bars) stored under `frontend/src/components/`. Backend controllers must be broken into domain routers (e.g., `authController.js`, `reconciliationController.js`, `ticketController.js`).
- **Preventive instruction:**
  - Before creating any source file, outline its expected line count and dependencies.
  - If a file approaches 700 lines, split sub-components or utility functions into distinct files immediately.
  - Include an automated line-count check during test verification steps.

---

### Entry 002: Module System & Language Typing Constraints
- **Date:** 2026-11-13
- **What was incorrect / Trap Identified:** Risk of modern AI defaults generating TypeScript (`.tsx`/`.ts`) for the React frontend or ES Modules (`import`/`export`, `"type": "module"`) for the Node.js backend.
- **Why it was incorrect:** The user's master prompt explicitly mandates:
  - Frontend: JavaScript only (not TypeScript).
  - Backend: Node.js / Express CommonJS only (`require()` and `module.exports`, not ES Module imports).
- **Correct information:**
  - Frontend: `package.json` must NOT use TypeScript dependencies; all files must use `.jsx` and `.js`.
  - Backend: `package.json` must NOT have `"type": "module"`. All files must use `require()` and `module.exports`.
- **Preventive instruction:**
  - Audit package.json and import statements on every created file before committing.
  - Verify that no `.ts` or `.tsx` files exist in `frontend/`.
  - Verify that no `import ... from ...` statements exist in `backend/`.

---

### Entry 003: Financial Calculation Re-implementation Trap
- **Date:** 2026-11-13
- **What was incorrect / Trap Identified:** Risk of attempting to re-implement or simplify reconciliation formulas, fee logic, GST rates, or cash flow math in Node.js or React to reduce inter-service latency.
- **Why it was incorrect:** JavaScript numbers are 64-bit binary floating-point (IEEE-754). Calculating fees and GST in JavaScript introduces sub-cent rounding errors (e.g., `0.1 + 0.2 != 0.3`). Furthermore, re-writing tested Python algorithms violates the migration rule against modifying business logic.
- **Correct information:**
  - 100% of the three-way reconciliation matching rules (Rules 1–7), Section 194-O TDS rules, and 7-day rolling cash flow forecasting algorithms must remain in Python within `ai-service/`.
  - PostgreSQL columns for financial amounts must be strictly `NUMERIC(15, 2)` (or `NUMERIC(15, 4)` for fee rates), never `FLOAT` or `REAL`.
  - Backend and Frontend only display and transport calculated values; they never recompute math.
- **Preventive instruction:**
  - Any pull request or code addition in `backend/` or `frontend/` that calculates fees, GST, net settlement, or forecasting must be rejected immediately.
  - Always verify that unit tests in `tests/test_reconciliation.py` continue to pass directly against the Python service.

---

### Entry 004: Dual-Mode Execution & Network Resolution Trap
- **Date:** 2026-11-13
- **What was incorrect / Trap Identified:** Assuming that application services will only run inside Docker containers and hardcoding container hostnames (e.g., `http://finance-backend:5000` or `http://finance-postgres:5432`) in application code.
- **Why it was incorrect:** The system has a strict requirement for **manual local execution** (`npm run dev`, `uvicorn main:app`) where services run bare-metal on the host machine and connect via `localhost`, while also supporting independent Docker Compose execution where services communicate across `finance-network`.
- **Correct information:**
  - All hostnames, ports, and connection strings must be read exclusively from environment variables (`.env`).
  - Separate `.env.example` templates must be maintained for local execution (`localhost`) versus Docker execution (`finance-postgres`, `finance-redis`, `finance-backend`).
  - Frontend browser API requests must always target a browser-accessible URL (e.g., `http://localhost:5000/api` or Vite proxy), never an internal Docker network alias.
- **Preventive instruction:**
  - Never hardcode `localhost` or Docker service names in application source code.
  - Test both manual local commands (`npm run dev`, `uvicorn`) and Docker Compose commands before declaring any phase complete.

---

### Entry 005: Shared Database Write & Role Isolation Trap
- **Date:** 2026-11-13
- **What was incorrect / Trap Identified:** Assuming that Backend and AI Service can share the same database superuser or perform unrestricted shared writes across all tables.
- **Why it was incorrect:** Unrestricted shared writes across multi-service architectures lead to race conditions, untracked mutations, and schema corruption.
- **Correct information:**
  - Backend and AI Service use **separate PostgreSQL users**: `finance_backend_user` and `finance_ai_user`.
  - Strict Table Ownership Matrix (defined in `docs/DATABASE_AUDIT.md`): Backend owns application/user tables (`merchants`, `stores`, `users`, `tickets`, `notifications`, `audit_logs`, `config`); AI Service owns data tables (`transactions`, `internal_orders`, `bank_statements`, `document_chunks`).
  - Shared tables (`exception_resolutions`, `ai_messages`) use strictly controlled CRUD lifecycle permissions.
- **Preventive instruction:**
  - Verify that database connection pools in `backend/` use `finance_backend_user` credentials.
  - Verify that database connection engines in `ai-service/` use `finance_ai_user` credentials.
  - Test that `finance_ai_user` cannot drop or alter backend-owned tables, and vice versa.

---

## 4. Maintenance & Continuous Audit

1. **New entries must be logged immediately** upon discovering any hallucination, false assumption, or incorrect code generation.
2. **Every entry must be assigned a sequential number** (`Entry 00X`) and follow the exact required schema.
3. **No entry may be deleted.**
4. **Pre-Phase Verification:** At the start of every phase, the active agent must explicitly confirm in chat that it has reviewed this file.
