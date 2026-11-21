# Migration Risks, Compatibility & Mitigation Strategies

This document identifies potential technical risks, architectural challenges, and compatibility issues associated with migrating the monolithic Streamlit application to the target three-service architecture, accompanied by explicit mitigation strategies.

---

## 1. Risk Matrix

| Risk ID | Risk Description | Severity | Likelihood | Impact Area | Primary Mitigation Strategy |
| :---: | :--- | :---: | :---: | :--- | :--- |
| **RSK-01** | **Financial Math Precision Drift:** JavaScript IEEE-754 floating point causing sub-cent discrepancy. | **CRITICAL** | **HIGH** | Financial Calculations & Reconciliation | Keep all calculations in Python; store all monetary values as PostgreSQL `NUMERIC(15, 2)`. Never perform financial rounding in JavaScript. |
| **RSK-02** | **Test Regression Discrepancy:** Migrated engines failing existing unit tests in `tests/test_reconciliation.py`. | **CRITICAL** | **LOW** | System Correctness | Port Python logic verbatim into FastAPI; run existing pytest suite against PostgreSQL to guarantee 100% test pass. |
| **RSK-03** | **Multi-Tenant Data Leakage:** Merchant user accessing another store's transactions or documents. | **HIGH** | **MEDIUM** | Security & Privacy | Enforce database-level `WHERE merchant_id = ... AND store_id = ...` in all repository queries; validate token claims in backend middleware; enforce tenant RAG isolation. |
| **RSK-04** | **CORS & Cookie Session Failure:** Browser rejecting HttpOnly cookies across `localhost:3000` and `localhost:5000`. | **HIGH** | **MEDIUM** | Authentication | Configure Vite development server reverse proxy (`/api` $\to$ `http://localhost:5000`) so requests are same-origin during local development; set `SameSite=Lax`. |
| **RSK-05** | **pgvector Dependency on Windows:** Developer lacking pgvector compiler on Windows local machine. | **MEDIUM** | **HIGH** | Local Development | Run PostgreSQL with pgvector via Docker Compose (`pgvector/pgvector:pg16`); implement Python fallback to in-memory cosine similarity if connecting to bare-metal PG. |
| **RSK-06** | **Gemini API Quota or Key Expiration:** RAG assistant failing if user has no API key or exceeds quota. | **MEDIUM** | **MEDIUM** | AI Assistant | Retain and migrate `src/heuristic_engine.py` as an automated deterministic fallback when Gemini is unavailable. |
| **RSK-07** | **UI Parity Drift:** React interface deviating visually or functionally from the Streamlit layout. | **HIGH** | **MEDIUM** | User Experience | Extract exact CSS tokens, fonts (`Inter`, `Outfit`), and color hex codes from `app.py`; compare side-by-side using component screenshots. |
| **RSK-08** | **RabbitMQ / Redis Downtime:** Ingestion or cache failure blocking API responses. | **MEDIUM** | **LOW** | Availability | Implement graceful degradation: if Redis is offline, backend queries PostgreSQL directly; if RabbitMQ is offline, fall back to synchronous ingestion with a warning. |

---

## 2. In-Depth Analysis of Critical Risks & Safeguards

### 2.1 Financial Correctness & Precision Drift (RSK-01)
- **The Danger:** In standard JavaScript, `0.1 + 0.2 === 0.30000000000000004`. If fee percentages (2% gateway fee, 18% GST) or net settled values are recalculated on the frontend or backend in Node.js, slight decimal drift will cause false-positive exception flags (`FEE_MISMATCH`, `SETTLED_AMOUNT_MISMATCH`).
- **The Safeguard:**
  1. All calculation formulas remain strictly within the Python AI & Data Processing service (`ai-service/`).
  2. The Node.js Backend acts solely as an orchestrator and never recalculates reconciliation math.
  3. PostgreSQL tables use `NUMERIC(15, 2)` for currency values and `NUMERIC(15, 4)` for fee/tax percentages.
  4. Node.js processes currency values as strings or using decimal-safe libraries (`decimal.js`) when formatting, never bare JavaScript floats.

### 2.2 Test Suite Parity (RSK-02)
- **The Danger:** The existing 8 unit tests in `tests/test_reconciliation.py` test specific boundary conditions:
  - Total payments processed = 45, total transactions = 60.
  - Identification of 5 exact transaction IDs (`pay_24716857`, `pay_16789850`, `pay_99639081`, `pay_33357554`, `pay_92228802`).
  - Expected bank settlement mismatch of exactly -₹100.00 on 10-08-2026.
  - Missing bank credit of exactly -₹4,407.40 on 18-08-2026.
  - TDS under-deduction on `pay_95822412` and over-deduction on `pay_81016525`.
- **The Safeguard:**
  - The Python test suite will be retained and run directly against the extracted FastAPI service modules.
  - No changes will be made to synthetic test datasets or tolerance thresholds ($0.05$ INR tolerance).
  - CI verification will assert that all 8 tests pass before Phase 4 is marked complete.

### 2.3 Cross-Origin Authentication & Session Cookies (RSK-04)
- **The Danger:** In a multi-service development setup where the React frontend runs on `http://localhost:3000` and the Node.js backend runs on `http://localhost:5000`, browsers will treat requests as cross-origin. Browsers may drop `Set-Cookie` headers if `SameSite` or `Secure` attributes are mismatched.
- **The Safeguard:**
  - In Vite development mode (`frontend/vite.config.js`), a proxy route will forward all `/api` and `/socket.io` calls to `http://localhost:5000`. The browser will communicate exclusively with port 3000 as same-origin.
  - In production, Nginx reverse proxy routes traffic: `/` $\to$ Frontend, `/api` $\to$ Backend, `/socket.io` $\to$ Backend.

### 2.4 Tenant Isolation in RAG & Vector Search (RSK-03)
- **The Danger:** If vector embeddings from private store exports (e.g., `documents/07_internal_orders_data_flipkart_fk_delhi.md`) are searched globally, a query by an Amazon store user might retrieve confidential Flipkart transaction details.
- **The Safeguard:**
  - Replicate the tenant isolation filter from `src/rag_engine.py`:
    ```sql
    SELECT text_content, file_name, 1 - (embedding <=> query_vector) AS similarity
    FROM document_chunks
    WHERE (file_name NOT LIKE '%_data_%' AND file_name NOT LIKE '07_%' AND file_name NOT LIKE '08_%' AND file_name NOT LIKE '09_%')
       OR file_name LIKE '%' || :merchant_id || '%'
    ORDER BY embedding <=> query_vector
    LIMIT :top_n;
    ```
  - Shared policy documents (settlement rules, refund policies, GST rules) remain accessible to all merchants, while exported store datasets are strictly isolated by `merchant_id`.

---

## 3. Rollback & Contingency Plan

If an unresolvable defect or architectural blocker arises during any phase:
1. **Preservation of Existing Monolith:** The existing `app.py`, `src/`, `data/`, and `tests/` directories remain completely untouched throughout the migration until final Phase 10 verification.
2. **Safe Fallback:** The original Streamlit application can be run at any point during development via `streamlit run app.py` on port 8501.
3. **Phase Rollback:** Each phase is isolated in dedicated git branches or directories. Reverting a phase requires only resetting the specific service directory without affecting the working baseline.
