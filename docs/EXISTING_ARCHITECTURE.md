# Existing Architecture Analysis

## 1. Executive Summary

The **AI Finance Controller** is a production-grade financial reconciliation, exception resolution, and intelligence platform. The current implementation is a Python-based monolith centered around a comprehensive Streamlit user interface (`app.py`), supported by a suite of domain-specific processing engines in `src/`.

The application reconciles high-volume transaction data across three independent financial sources:
1. **Internal Orders:** The merchant's internal order ledger.
2. **Payment Gateway (Razorpay):** Captured payment transactions, fees, taxes, and refunds.
3. **Bank Statements:** Direct credit and nodal settlement records.

In addition to core three-way reconciliation, the platform provides automated exception classification and confidence scoring, Section 194-O TDS and GST tax compliance auditing, rolling cash flow forecasting, multi-store merchant workflows, administrator control desks, and a Retrieval-Augmented Generation (RAG) financial assistant grounded in financial policy documents.

---

## 2. Codebase Topology & Module Responsibilities

```
AI-Finance-Controller/
│
├── app.py                         # Monolithic Streamlit application (6,079 lines)
├── requirements.txt               # Dependencies: Streamlit, Pandas, NumPy, Plotly, Gemini SDK, etc.
├── logo.png                       # Platform branding asset
├── AI Finance Controller...mp4    # Reference walkthrough video
│
├── src/                           # Core business logic and computational engines
│   ├── database.py                # Database abstraction layer (1,492 lines)
│   ├── reconciliation.py          # Three-way reconciliation engine (368 lines)
│   ├── forecaster.py              # Cash flow projection model (151 lines)
│   ├── tax_matcher.py             # Section 194-O & GST tax audit engine (185 lines)
│   ├── rag_engine.py              # Vector embeddings and RAG retrieval (353 lines)
│   ├── heuristic_engine.py        # Rule-based search fallback (70 lines)
│   ├── upload_pipeline.py         # Data ingestion and normalization pipeline (240 lines)
│   └── mock_generator.py          # Multi-store synthetic data generator (336 lines)
│
├── data/                          # Operational datasets and local SQLite database
│   ├── finance_controller.db      # Pre-populated SQLite database (491 KB)
│   ├── internal_orders.csv        # Internal orders source dataset
│   ├── transactions_processed.csv # Normalized Razorpay transactions dataset
│   ├── bank_statement.csv         # Bank statement deposits dataset
│   └── razorpay_synthetic...csv   # Raw buildathon synthetic transactions
│
├── documents/                     # Fintech policies and data catalogues for RAG
│   ├── 01_razorpay_settlement_policy.md
│   ├── 02_refund_policy.md
│   ├── 03_merchant_fee_agreement.md
│   ├── 04_seller_payout_rules.md
│   ├── 05_invoice_refund_gst_rules.md
│   ├── 06_system_logic_and_math_calculations.md
│   ├── 07_internal_orders_data*.md
│   ├── 08_razorpay_transactions_data*.md
│   ├── 09_bank_statements_data*.md
│   └── india_tax_reference_FY2026-27.md
│
├── tests/                         # Unit tests and performance benchmarks
│   ├── test_reconciliation.py     # 8 unit tests verifying all calculations (224 lines)
│   └── benchmark_performance.py   # Benchmark test script
│
└── .streamlit/
    └── config.toml                # Base theme configuration
```

---

## 3. Detailed Component Breakdown

### 3.1 Presentation Layer (`app.py` — 6,079 lines)

The Streamlit application contains extensive custom styling, routing, and UI rendering logic:
1. **Design System & CSS Injection:**
   - Overrides default Streamlit styles with custom CSS tokens:
     - `--primary: #0F4C75`
     - `--navy: #172B4D`
     - `--bg: #F7F9FC`
     - `--card: #FFFFFF`
     - `--text-sec: #6B7C93`
     - `--success: #10B981`
     - `--warning: #F59E0B`
     - `--error: #EF4444`
     - `--border: #E2E8F0`
     - Dark Sidebar: `#161f30`
   - Custom fonts loaded from Google Fonts: `Inter` (body/data) and `Outfit` (headings/branding).
2. **Split-Screen Authentication (`app.py` L436–L803):**
   - Left hero pane with SVG glowing metrics preview and branding.
   - Right form pane with corporate email/password inputs, pre-filled demo credential alerts, and error handling.
   - Cookie-based session token persistence via `streamlit.components.v1.html`.
3. **Role-Based Access Control (RBAC):**
   - Two distinct roles: `MERCHANT` and `ADMIN`.
   - Route guard prevents `MERCHANT` from accessing any admin pages or parameters, automatically redirecting to `dashboard`.
   - Route guard prevents `ADMIN` from navigating to merchant store pages, redirecting to `admin`.
4. **Interactive Global Widgets:**
   - **Header Bar:** Store profile initials, role label, and logout button.
   - **Date Range Filter:** Presets (`All Available Dates`, `Closing Batch`, `Week 2 Batch`, `Week 1 Batch`, `Custom Date Range`) with automatic data re-filtering.
   - **Dataset Batch Switcher:** Supports switching between the primary batch (`Razorpay Synthetic Batch - 60 records`) and the example batch (`August 25 Example - 96 records`).
   - **Notifications Menu:** Real-time unread badge counts for both Merchant and Admin consoles.
   - **Floating AI Assistant Popover:** Persistent Meta AI-style button on all pages triggering an inline conversational popover.

---

### 3.2 Three-Way Reconciliation Engine (`src/reconciliation.py`)

The engine takes data from `transactions`, `internal_orders`, and `bank_statements` and applies **seven sequential validation rules**:

```
[Gateway Transactions] ──┬──► Rule 1: Duplicate Transaction ID Check
                         ├──► Rule 2: Missing Order ID (Gateway Orphan) Check
                         ├──► Rule 3: Disputed Transaction Status Check
                         ├──► Rule 4: Dynamic Gateway Fee & 18% GST Recalculation
                         ├──► Rule 5: Mathematical Settled Amount Balance Check
                         ├──► Rule 6: Internal Order Cross-Verification (Amount & Status)
                         └──► Rule 7: Bank Settlement Deposit Verification (T+2 delay)
                                      │
                                      ▼
                        [Reconciled Records Output]
                        ├── Status: AUTO_RESOLVED (Confidence = 1.0)
                        └── Status: NEEDS_REVIEW  (Confidence <= 0.4)
```

#### Detailed Rule Implementation:
- **Rule 1 (Duplicate TX IDs):** Uses `set()` lookup to detect duplicate gateway IDs; sets confidence to `0%`.
- **Rule 2 (Missing Order ID):** Flags records where `order_id` is null, empty string, or `"NaN"`; sets confidence to `0%`.
- **Rule 3 (Disputed Status):** Flags transactions where status is `'disputed'`; sets confidence to `0%`.
- **Rule 4 (Fee & Tax Recalculation):**
  - For `PAYMENT`: Expected Fee = $\text{Amount} \times \text{gateway\_fee\_rate}$ (default 2%); Expected GST = $\text{Fee} \times \text{gst\_rate}$ (default 18%). Netbanking exception: zero fee if recorded fee $< 0.01$. Tolerance: ₹0.05.
  - For `PAYOUT`: Expected Fee = ₹5.00 fixed; Expected GST = $\text{Fee} \times 18\%$.
  - For `REFUND`: Expected Fee = $\text{Amount} \times 2\%$; Expected GST = $\text{Fee} \times 18\%$.
  - Failure flags: `FEE_MISMATCH`, `TAX_MISMATCH`, confidence lowered to `30%`.
- **Rule 5 (Settled Amount Balance):**
  - For `PAYMENT`: Expected Settled = $\text{Amount} - \text{Fee} - \text{GST}$.
  - For `PAYOUT`: Expected Settled = $-(\text{Amount} + \text{Fee} + \text{GST})$.
  - For `REFUND`: Expected Settled = $-\text{Amount}$.
  - Failure flags: `SETTLED_AMOUNT_MISMATCH`, confidence lowered to `10%`.
- **Rule 6 (Internal Order Cross-Verification):**
  - Looks up `order_id` in `internal_orders` using an indexed dictionary ($O(1)$).
  - Checks if internal order exists: `INTERNAL_ORDER_NOT_FOUND` (confidence `0%`).
  - Checks amount: $| \text{Order Amount} - \text{Gateway Amount} | > 0.05 \implies \text{INTERNAL_AMOUNT_MISMATCH}$ (confidence `30%`).
  - Checks status: Expected order status `'completed'` for `'captured'`/`'disputed'`; else `'failed'`. Failure $\implies \text{INTERNAL_STATUS_MISMATCH}$ (confidence `40%`).
- **Rule 7 (Bank Statement Settlement Matching):**
  - Computes expected settlement date: Payments settle $T + \text{delay\_days}$ (default 2 days); Payouts & Refunds settle $T + 0$.
  - Aggregates daily expected amounts and joins with `bank_statements` by date.
  - Missing bank credit $\implies \text{BANK_CREDIT_MISSING}$ (confidence `10%`).
  - Bank credit difference $> 0.05 \implies \text{BANK_SETTLEMENT_MISMATCH}$ (confidence `20%`).

#### Output Metrics:
- `total_payments_processed`: Count of payment transactions.
- `total_transactions`: Total gateway records.
- `auto_resolved_count`: Records with 0 exceptions.
- `needs_review_count`: Active exceptions (gateway + unmatched orders).
- `auto_match_accuracy_pct`: $(\text{Auto Resolved} / \text{Total Elements}) \times 100$.
- `gross_collections_inr`: Sum of captured payments.
- `refunds_inr`: Sum of refund amounts.
- `fees_gst_inr`: Sum of fees + GST.
- `settled_to_bank_inr`: Sum of bank statement deposits.
- `expected_next_2_days_inr`: Payments in $T+2$ queue whose settlement date exceeds latest bank statement date.

---

### 3.3 Tax & TDS Audit Engine (`src/tax_matcher.py`)

Audits every transaction against Indian financial compliance standards:
- **GST Audit:** Expected GST on Gateway Fee = $\text{Fee} \times 18\%$. Discrepancy flagged if $|\text{Actual GST} - \text{Expected GST}| > 0.05$.
- **Section 194-O TDS Audit:**
  - Recipient type deterministically derived or extracted from transaction (`Individual`, `Company`, `Non-Resident`).
  - Dynamic configurable rates (Default: Individual = 1%, Company = 2%, Non-Resident = 0%).
  - Expected TDS = $\text{Amount} \times \text{Rate}$ if applicable, else 0.
  - Detects anomalies: `TDS_UNDER_DEDUCTION`, `TDS_OVER_DEDUCTION`, `GST_MISMATCH`, `MULTIPLE_TAX_ISSUES`.
- **Outputs:** Audited records table and summary object with compliance score percentage (`tax_compliance_pct`).

---

### 3.4 Cash Flow Forecaster (`src/forecaster.py`)

Generates a rolling 7-day cash flow projection:
- **Baseline Bank Balance:** Sum of actual bank deposits (default ₹75,000 baseline treasury if empty).
- **Days 1 & 2 (Committed Queue):** Built from actual captured transactions awaiting $T+2$ bank settlement.
- **Days 3 to 7 (Projected Moving Average):**
  - Computes historical daily average of captured payments, refunds, and payouts.
  - Applies dynamic fee and GST rates to project estimated fees.
  - Calculates daily net inflow: $\text{Payments} - \text{Refunds} - \text{Payouts} - \text{Fees/GST}$.
  - Computes day-by-day cumulative cash balance.

---

### 3.5 RAG & Generative Assistant Engine (`src/rag_engine.py`)

- **Document Ingestion:** Scans `documents/` for `.md` and `.pdf` files.
- **Chunking:** Character-level chunker (size 800, overlap 150) with sentence boundary detection.
- **Embeddings:** Google Gemini `models/text-embedding-004` (fallback to `models/embedding-001`).
- **Hybrid Search:**
  - Semantic Cosine Similarity: When API key is present and embeddings are loaded.
  - Exact Token Boost: Adds $+100.0$ to chunk similarity if transaction or order IDs appear in query.
  - TF-IDF Keyword Fallback: When API key is absent or quota exhausted.
- **Tenant Isolation:** Enforces tenant privacy by filtering out other merchants' data export chunks while preserving common compliance policy documents.

---

### 3.6 Data Ingestion & Storage (`src/upload_pipeline.py` & `src/database.py`)

- **Schema:** 15 relational tables (Merchants, Stores, Users, Transactions, Internal Orders, Bank Statements, Document Chunks, Support Tickets, AI Conversations, AI Messages, Notifications, Audit Logs, Configuration, User Sessions, Exception Resolutions).
- **Multi-Engine Support:** Supports SQLite, PostgreSQL, and MySQL using standard connection drivers.
- **Data Ingestion:** Normalizes source CSVs (`transactions_processed.csv`, `internal_orders.csv`, `bank_statement.csv`), computes expected settlement dates, and bulk-inserts records with conflict handling.

---

## 4. Verification Baseline & Test Coverage

The test suite (`tests/test_reconciliation.py`) verifies the entire business logic across 8 test suites:
1. `test_metrics_integrity`: Validates metric keys and totals (45 payments, 60 total transactions).
2. `test_original_gateway_exceptions`: Verifies detection of 5 original exceptions (`pay_24716857`, `pay_16789850`, `pay_99639081`, `pay_33357554`, `pay_92228802`).
3. `test_internal_order_discrepancies`: Verifies amount mismatch, status mismatch, and unmatched orphan order (`order_99999999`).
4. `test_bank_statement_discrepancies`: Verifies bank settlement mismatch (-₹100 on 10-08-2026) and omitted settlement batch (-₹4,407.40 on 18-08-2026).
5. `test_cash_forecaster`: Verifies 7-day forecast output, columns, and cumulative treasury calculation.
6. `test_tax_matcher`: Verifies Section 194-O TDS and GST anomaly tags (`TDS_UNDER_DEDUCTION`, `TDS_OVER_DEDUCTION`, `MULTIPLE_TAX_ISSUES`).
7. `test_configurable_tds`: Verifies that custom configuration dynamically changes computed Expected TDS.
8. `test_exception_resolution_and_notification_sync`: Verifies end-to-end exception resolution lifecycle between Merchant and Admin with live notification dispatch.

**Current Test Status:** `8 passed in 1.99s` (100% pass rate).
