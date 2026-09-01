# AI Finance Controller
### Multi-Source Reconciliation & Financial Intelligence Agent

> **An AI-powered financial operations platform that reconciles Internal Orders → Razorpay → Bank Statements, detects financial exceptions, verifies settlements, audits tax/TDS compliance, forecasts cash flow, and provides evidence-grounded financial intelligence through RAG + Gemini.**

---

## Project Overview

Modern digital businesses receive financial data from multiple independent systems:

- Internal order management systems
- Payment gateways such as Razorpay
- Bank statements
- Tax and compliance records
- Merchant settlement records

These systems rarely remain perfectly synchronized.

A payment may be successful in the gateway but missing from the bank statement. An internal order may have a different amount from the payment gateway. A settlement may be delayed or deposited with an incorrect amount. Tax deductions may not match the expected calculation.

Manually identifying these issues is:

- time-consuming
- error-prone
- difficult to audit
- difficult to scale
- dependent on spreadsheet-based workflows

### AI Finance Controller solves this problem by creating a unified financial control layer.

```text
                    ┌─────────────────────┐
                    │   INTERNAL ORDERS   │
                    │  Merchant Ledger    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      RAZORPAY       │
                    │ Payment Transactions│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    BANK STATEMENT   │
                    │ Settlement Deposits │
                    └──────────┬──────────┘
                               │
                               ▼
                 ┌─────────────────────────────┐
                 │    AI FINANCE CONTROLLER    │
                 │                             │
                 │  • 3-Way Reconciliation     │
                 │  • Exception Detection      │
                 │  • Settlement Verification  │
                 │  • Tax/TDS Audit            │
                 │  • Cash Forecasting         │
                 │  • RAG Financial Assistant  │
                 │  • Resolution Workflow      │
                 └──────────────┬──────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │ Financial Dashboard │
                    │ & AI Insights       │
                    └─────────────────────┘
```

---

# Problem Statement

Financial reconciliation traditionally requires finance teams to compare multiple systems manually.

For example:

```text
Internal Order
    │
    │ ₹10,000
    ▼
Payment Gateway
    │
    │ ₹10,000 - fees
    ▼
Settlement
    │
    │ ₹9,800
    ▼
Bank
```

A small inconsistency at any stage can lead to:

- incorrect settlements
- revenue leakage
- unresolved payments
- missing bank credits
- incorrect fee calculations
- tax discrepancies
- delayed financial closing
- operational risk

The objective of this project is to automate this process and provide a **single source of financial truth**.

---

# Solution

AI Finance Controller acts as a financial control and reconciliation layer between the merchant's operational data, payment gateway transactions and bank settlements.

The system:

1. Ingests financial datasets.
2. Normalizes transaction records.
3. Matches transactions across systems.
4. Validates amounts, statuses, fees and settlements.
5. Detects exceptions automatically.
6. Calculates financial metrics.
7. Performs tax/TDS auditing.
8. Forecasts short-term cash flow.
9. Provides an evidence-grounded AI financial assistant.
10. Allows merchant/admin teams to investigate and resolve exceptions.
11. Maintains resolution and audit history.

---

# Key Features

## 1. 3-Way Financial Reconciliation

The core functionality of the project.

The system reconciles:

```text
Internal Orders
      │
      ▼
Razorpay Transactions
      │
      ▼
Bank Settlements
```

The reconciliation engine verifies:

- transaction identity
- order identity
- payment status
- transaction amount
- settlement amount
- gateway fees
- expected bank credit
- actual bank credit
- settlement timing
- tax-related values

Each transaction receives a reconciliation outcome.

Example:

```text
Transaction
    │
    ├── Internal Order ✓
    ├── Razorpay Payment ✓
    ├── Expected Settlement ✓
    ├── Bank Credit ✓
    │
    └── FINAL STATUS: RECONCILED
```

or:

```text
Transaction
    │
    ├── Internal Order ✓
    ├── Razorpay Payment ✓
    ├── Expected Settlement ✓
    ├── Bank Credit ✗
    │
    └── FINAL STATUS: NEEDS_REVIEW
```

---

# 2. Intelligent Exception Detection

The system automatically identifies financial inconsistencies.

Supported exception categories include:

| Exception | Meaning |
|---|---|
| Amount Mismatch | Amount differs between financial sources |
| Status Mismatch | Transaction status differs between systems |
| Missing Order | Gateway transaction has no corresponding internal order |
| Missing Bank Credit | Expected settlement is absent from bank statement |
| Tax Mismatch | Tax-related values do not match expected calculations |
| Settlement Mismatch | Actual settlement differs from expected settlement |
| Fee Mismatch | Gateway/settlement fee does not match configured rules |

Instead of simply showing an error, the platform provides an explainable exception state that finance teams can investigate.

---

# 3. Reconciliation Confidence

The system assigns a confidence score to reconciliation outcomes.

Conceptually:

```text
100% ─────────────── Fully reconciled
 │
 │
80%  ─────────────── High confidence
 │
 │
50%  ─────────────── Requires investigation
 │
 │
30%  ─────────────── Low confidence
 │
 │
0%   ─────────────── Unmatched / unresolved
```

The confidence score helps prioritize financial exceptions.

---

# 4. Settlement Verification

The system verifies whether expected gateway settlements are reflected correctly in the bank statement.

The settlement workflow can be represented as:

```text
Successful Payment
      │
      ▼
Gateway Processing
      │
      ▼
Gateway Fees
      │
      ▼
Expected Settlement
      │
      ▼
Bank Credit
      │
      ▼
Settlement Verification
```

The system can detect:

- missing deposits
- incorrect deposit amounts
- delayed settlements
- settlement amount differences
- unexpected bank entries

---

# 5. Bank Reconciliation

Bank transactions are compared against expected settlement batches.

Example:

```text
Expected Settlement     ₹9,900
Actual Bank Credit      ₹9,900
──────────────────────────────
Difference              ₹0
Status                  MATCHED
```

For a discrepancy:

```text
Expected Settlement     ₹10,000
Actual Bank Credit      ₹9,900
──────────────────────────────
Difference              -₹100
Status                  SETTLEMENT_AMOUNT_MISMATCH
```

This allows finance teams to immediately identify the financial impact.

---

# 6. Tax & TDS Audit

The platform contains a configurable tax audit engine.

It evaluates:

- GST-related anomalies
- TDS applicability
- recipient type
- TDS rate
- expected TDS
- actual TDS
- under-deduction
- over-deduction
- multiple tax issues

### TDS Calculation

Where TDS is applicable:

```text
Expected TDS = Applicable Amount × TDS Rate
```

Example:

```text
Transaction Amount = ₹50,000
TDS Rate           = 2%

Expected TDS
= ₹50,000 × 2%
= ₹1,000
```

The system compares the expected amount with the recorded deduction.

Possible outcomes:

```text
CORRECT
UNDER-DEDUCTION
OVER-DEDUCTION
NOT_APPLICABLE
MULTIPLE_TAX_ISSUES
```

The TDS configuration is designed to be configurable from the administrative control layer.

---

# 7. Cash Flow Forecasting

The platform provides short-term cash forecasting.

The forecast considers financial activity such as:

- gross collections
- gateway fees
- taxes
- payout/settlement effects
- expected inflows
- current cash position

Example conceptual flow:

```text
Historical Transactions
         │
         ▼
Financial Aggregation
         │
         ▼
Expected Inflows / Outflows
         │
         ▼
7-Day Cash Forecast
         │
         ▼
Projected Cash Position
```

The dashboard provides:

- projected collections
- expected net inflow
- cumulative cash
- daily forecast values

This transforms the system from a purely reactive reconciliation tool into a **proactive financial control system**.

---

# 8. AI Financial Assistant

The project contains an AI-powered financial assistant.

Users can ask questions such as:

```text
"Give me a summary of the daily close report."

"Why did transaction pay_24716857 fail reconciliation?"

"Explain the settlement issues on August 10 and 18."

"Which transactions require immediate attention?"

"What caused the bank settlement mismatch?"
```

The assistant combines:

```text
User Question
     │
     ▼
Query Understanding
     │
     ▼
Financial Transaction Evidence
     │
     +
     ▼
RAG Document Retrieval
     │
     ▼
Relevant Financial Context
     │
     ▼
Gemini
     │
     ▼
Evidence-Grounded Answer
```

---

# 9. RAG-Based Financial Knowledge

The AI assistant does not rely only on the language model.

The system uses Retrieval-Augmented Generation (RAG) to retrieve relevant information from financial documentation.

The knowledge base includes documentation related to:

- Razorpay settlement policies
- merchant fee agreements
- seller payout rules
- refund policies
- invoice/refund GST rules
- internal order data
- Razorpay transaction data
- bank statements
- tax reference information
- system calculation logic

### RAG Pipeline

```text
Financial Documents
      │
      ▼
Text Extraction
      │
      ▼
Text Chunking
      │
      ▼
Embeddings
      │
      ▼
Knowledge Index
      │
      ▼
User Question
      │
      ▼
Query Embedding
      │
      ▼
Similarity Retrieval
      │
      ▼
Relevant Context
      │
      ▼
Gemini
      │
      ▼
Financial Explanation
```

The assistant is instructed to:

- prioritize retrieved documentation
- use transaction evidence
- avoid inventing financial facts
- distinguish documented information from reasoning
- explain calculations when applicable
- state when required information is unavailable

---

# 10. Role-Based Access

The platform supports different operational roles.

### Merchant

A merchant can:

- view financial dashboards
- inspect transactions
- investigate exceptions
- view settlements
- review tax information
- use the AI financial assistant
- submit resolution information

### Administrator

The administrator can:

- monitor multiple merchants
- view cross-tenant metrics
- manage system configuration
- review merchant-submitted resolutions
- approve resolutions
- monitor support tickets
- inspect audit logs
- manage financial configuration

Conceptually:

```text
                   ┌───────────────┐
                   │ Authentication│
                   └───────┬───────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
            MERCHANT                ADMIN
                │                     │
                ▼                     ▼
         Merchant Portal       Admin Control Plane
```

---

# 11. Exception Resolution Workflow

The project does not stop at detecting an exception.

It provides a workflow for resolving it.

```text
Exception Detected
      │
      ▼
Needs Review
      │
      ▼
Investigation
      │
      ▼
Resolution Submitted
      │
      ▼
Admin Review
      │
      ▼
Approval
      │
      ▼
Resolved
```

The system also maintains notifications and resolution history.

This creates an operational loop:

```text
DETECT → INVESTIGATE → RESOLVE → VERIFY → AUDIT
```

---

# 12. Auditability

Financial systems require traceability.

The project maintains records related to:

- exception resolutions
- admin approvals
- merchant submissions
- notifications
- user actions
- audit logs
- conversation history

This makes it possible to understand:

```text
What happened?
     ↓
Why was it flagged?
     ↓
Who investigated it?
     ↓
What action was taken?
     ↓
Who approved it?
     ↓
What is the final status?
```

---

# System Architecture

```text
                        ┌─────────────────────┐
                        │      USER           │
                        │ Merchant / Admin    │
                        └──────────┬──────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │   STREAMLIT UI      │
                        │ Financial Dashboard │
                        └──────────┬──────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            │                      │                      │
            ▼                      ▼                      ▼
   ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
   │ Reconciliation │    │ Tax & Forecast │    │ AI Assistant   │
   │     Engine     │    │     Engine     │    │    + RAG       │
   └───────┬────────┘    └───────┬────────┘    └───────┬────────┘
           │                     │                     │
           └─────────────────────┼─────────────────────┘
                                 │
                                 ▼
                      ┌─────────────────────┐
                      │    Data Layer       │
                      │                     │
                      │ • SQLite            │
                      │ • CSV datasets      │
                      │ • Documents         │
                      └─────────────────────┘
```

---

# Complete Data Flow

```text
            ┌─────────────────────┐
            │ Internal Orders CSV │
            └──────────┬──────────┘
                       │
                       │
            ┌──────────▼──────────┐
            │ Razorpay Transactions│
            └──────────┬──────────┘
                       │
                       │
            ┌──────────▼──────────┐
            │  Bank Statement CSV │
            └──────────┬──────────┘
                       │
                       ▼
             ┌───────────────────┐
             │ Data Normalization │
             └─────────┬─────────┘
                       │
                       ▼
             ┌───────────────────┐
             │  Matching Engine   │
             └─────────┬─────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
     Reconciled    Exceptions    Unmatched
         │             │             │
         └─────────────┼─────────────┘
                       │
                       ▼
             ┌───────────────────┐
             │ Financial Metrics │
             └─────────┬─────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
      Dashboard     Tax Audit     Forecast
         │             │             │
         └─────────────┼─────────────┘
                       │
                       ▼
                AI Financial Layer
                       │
                       ▼
                Decision Support
```

---

# Core Reconciliation Logic

The reconciliation engine follows a deterministic rule-based approach.

At a high level:

```text
For every Razorpay transaction:

       ↓

Find corresponding Internal Order

       ↓

Validate Order ID

       ↓

Compare transaction amount

       ↓

Compare payment status

       ↓

Calculate expected settlement

       ↓

Find corresponding bank credit

       ↓

Compare expected vs actual settlement

       ↓

Check applicable financial/tax conditions

       ↓

Generate exceptions

       ↓

Calculate reconciliation confidence

       ↓

Assign final resolution status
```

The system therefore combines **deterministic financial rules** with **AI-assisted investigation**.

This separation is intentional:

> Financial calculations and reconciliation decisions are rule-driven, while generative AI is used primarily for explanation, investigation and knowledge retrieval.

---

# Example Reconciliation

Consider:

```text
Internal Order
Order ID: order_70291817
Amount: ₹5,000

         ↓

Razorpay
Transaction: pay_39587039
Amount: ₹5,500

         ↓

Bank
Expected settlement based on ₹5,000
Actual settlement based on ₹5,500
```

The system detects:

```text
INTERNAL_AMOUNT_MISMATCH
```

and marks the transaction:

```text
NEEDS_REVIEW
```

This makes the anomaly immediately visible to the finance team.

---

# Example Bank Settlement Exception

Suppose:

```text
Expected Settlement = ₹10,000
Actual Bank Credit  = ₹9,900
```

The system calculates:

```text
Difference = ₹9,900 - ₹10,000
           = -₹100
```

and produces:

```text
SETTLEMENT_AMOUNT_MISMATCH
Difference: -₹100
Status: NEEDS_REVIEW
```

This provides both the exception and its financial impact.

---

# Built-In Test Coverage

The project contains automated tests for critical financial logic.

The test suite validates areas including:

### Reconciliation

- total transactions
- reconciled transactions
- exception transactions
- gateway exceptions
- internal order discrepancies
- unmatched internal orders

### Bank

- settlement amount mismatch
- missing bank credit
- settlement difference calculations

### Forecasting

- forecast horizon
- forecast columns
- cumulative cash behavior

### Tax

- tax audit execution
- GST anomaly detection
- TDS anomaly detection
- tax compliance percentage
- configurable TDS calculations

### Resolution Workflow

- admin resolution
- merchant resolution submission
- notification synchronization
- admin approval
- resolution history

Run tests using:

```bash
python -m unittest tests/test_reconciliation.py
```

---

# Project Structure

```text
AI Finance Controller/
│
├── app.py
│   └── Main Streamlit application and UI
│
├── src/
│   ├── __init__.py
│   │
│   ├── reconciliation.py
│   │   └── 3-way reconciliation engine
│   │
│   ├── forecaster.py
│   │   └── Cash-flow forecasting logic
│   │
│   ├── tax_matcher.py
│   │   └── Tax and TDS audit engine
│   │
│   ├── rag_engine.py
│   │   └── RAG, document retrieval and embeddings
│   │
│   ├── heuristic_engine.py
│   │   └── Local fallback financial reasoning engine
│   │
│   ├── database.py
│   │   └── SQLite/database operations
│   │
│   ├── upload_pipeline.py
│   │   └── Data ingestion pipeline
│   │
│   └── mock_generator.py
│       └── Synthetic financial data generation
│
├── data/
│   ├── razorpay_synthetic_buildathon_data.csv
│   ├── internal_orders.csv
│   ├── bank_statement.csv
│   ├── transactions_processed.csv
│   └── finance_controller.db
│
├── documents/
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
├── tests/
│   ├── __init__.py
│   └── test_reconciliation.py
│
├── requirements.txt
├── .gitignore
├── logo.png
└── README.md
```

---

# Technology Stack

| Layer | Technology |
|---|---|
| Frontend / UI | Streamlit |
| Programming Language | Python |
| Data Processing | Pandas, NumPy |
| Visualization | Plotly |
| Database | SQLite |
| Generative AI | Google Gemini |
| RAG | Custom retrieval pipeline |
| Embeddings | Gemini Embeddings |
| Document Processing | PyPDF |
| Configuration | python-dotenv |
| Testing | Python unittest |
| Version Control | Git / GitHub |

---

# Security & Configuration

The project supports environment-based configuration.

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
```

The API key should **never be committed to GitHub**.

The application also supports providing the Gemini API key through its configuration interface.

---

# AI Architecture

The AI layer follows a hybrid approach.

```text
                     User Query
                         │
                         ▼
                ┌─────────────────┐
                │ Query Processing│
                └────────┬────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
      Transaction Evidence      RAG Retrieval
              │                     │
              │              Relevant Documents
              │                     │
              └──────────┬──────────┘
                         ▼
                  Context Assembly
                         │
                         ▼
                       Gemini
                         │
                         ▼
                 Financial Answer
```

If Gemini is unavailable, the application can fall back to a local heuristic engine for diagnostic functionality.

This provides resilience instead of making the entire application dependent on a single external API.

---

# Knowledge Base

The project contains domain-specific financial documentation covering:

### Payment Gateway

- Razorpay settlement policy
- Razorpay transaction records
- settlement behavior

### Merchant

- merchant fee agreement
- seller payout rules

### Refund & Tax

- refund policy
- invoice/refund GST rules
- India tax reference

### Internal Financial Data

- internal order records
- bank statements
- gateway transactions

### System Logic

- mathematical calculations
- reconciliation rules
- financial processing logic

This knowledge base allows the AI assistant to answer domain-specific questions rather than acting as a generic chatbot.

---

# Demo Accounts

The project contains predefined demonstration accounts.

## Merchant — Flipkart Delhi

```text
Email:    flipkart.delhi@merchant-demo.com
Password: flipkart123
Store:    Delhi
Store ID: fk_delhi
```

## Merchant — Amazon Delhi

```text
Email:    amazon.delhi@merchant-demo.com
Password: amazon123
Store:    Delhi
Store ID: az_delhi
```

## Administrator

```text
Email:    admin@razorpay-demo.com
Password: admin123
Role:     Global Administrator
```

> These credentials are intended only for the synthetic/demo environment included with this project.

---

# Installation

## 1. Clone Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd "AI Finance Controller"
```

## 2. Create Virtual Environment

### Windows

```bash
python -m venv .venv
```

Activate:

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

# Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Configure Gemini

Create a `.env` file:

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

Alternatively, configure the Gemini API key from the application's configuration interface.

---

# Run the Application

Start Streamlit:

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

---

# Generate Synthetic Data

The project contains a synthetic data generation utility.

Run:

```bash
python src/mock_generator.py
```

This can generate:

```text
data/internal_orders.csv
data/bank_statement.csv
```

The generated datasets intentionally contain financial discrepancies so that the reconciliation engine can demonstrate exception detection.

---

# Run Tests

```bash
python -m unittest tests/test_reconciliation.py
```

---

# Recommended Demo Flow

For reviewers evaluating the project, the following flow demonstrates the complete system.

### Step 1 — Login

Login as a merchant or administrator.

### Step 2 — Dashboard

Review:

- reconciliation health
- transaction metrics
- exception counts
- settlement status
- financial insights
- daily close information

### Step 3 — Transactions

Open transaction-level information.

Investigate transactions marked:

```text
NEEDS_REVIEW
```

### Step 4 — Exception Investigation

Select an exception and inspect:

- transaction ID
- order ID
- amount
- status
- settlement
- exception reason
- confidence
- financial impact

### Step 5 — Settlement / Bank

Inspect settlement batches and bank reconciliation.

Look for:

```text
SETTLEMENT_AMOUNT_MISMATCH
MISSING_BANK_CREDIT
```

### Step 6 — Tax Audit

Review:

- GST anomalies
- TDS anomalies
- expected TDS
- actual TDS
- tax compliance percentage

### Step 7 — Cash Forecast

Review the projected cash position for the upcoming days.

### Step 8 — AI Assistant

Ask:

```text
Why did transaction pay_24716857 fail reconciliation?
```

Then ask:

```text
Explain the settlement issues on August 10 and August 18.
```

The AI should use transaction evidence and the financial knowledge base to explain the issue.

### Step 9 — Resolution Workflow

Submit or review an exception resolution.

For administrator:

```text
Merchant Resolution
       ↓
Admin Review
       ↓
Approve
       ↓
Resolved
```

This demonstrates the complete financial operations lifecycle.

---

# Application Modules

The application is organized around financial operations rather than generic analytics.

```text
┌──────────────────────────────────────────────┐
│              AI FINANCE CONTROLLER           │
├──────────────────────────────────────────────┤
│                                              │
│  Dashboard                                   │
│  ├── Financial Overview                       │
│  ├── Reconciliation Health                   │
│  ├── Exceptions                              │
│  └── Daily Close                             │
│                                              │
│  Transactions                                │
│  ├── Payment Records                          │
│  ├── Matching                                │
│  └── Exception Investigation                 │
│                                              │
│  Reconciliation                              │
│  ├── Internal Orders                          │
│  ├── Razorpay                                │
│  └── Bank                                    │
│                                              │
│  Tax & Compliance                            │
│  ├── GST Audit                               │
│  └── TDS Audit                               │
│                                              │
│  Forecasting                                 │
│  └── Cash Flow Forecast                       │
│                                              │
│  AI Financial Assistant                      │
│  └── RAG + Gemini                            │
│                                              │
│  Admin Control Plane                         │
│  ├── Merchants                               │
│  ├── Resolutions                             │
│  ├── Configuration                           │
│  ├── Notifications                           │
│  └── Audit Logs                              │
│                                              │
└──────────────────────────────────────────────┘
```

---

# Financial Control Philosophy

A key design principle of this project is:

> **Use deterministic logic for financial truth and AI for financial intelligence.**

The system does not ask an LLM to decide whether ₹10,000 equals ₹9,900.

Instead:

```text
Financial Calculation
       ↓
Deterministic Rule Engine
       ↓
Correct Financial Result
       ↓
AI
       ↓
Explain / Investigate / Summarize
```

This architecture is important for financial applications because generative AI should assist decision-making without becoming the uncontrolled source of financial truth.

---

# Performance Architecture

Because Streamlit reruns application code whenever users interact with widgets, unnecessary recomputation can significantly impact responsiveness.

The project is designed to minimize this through:

- cached financial calculations
- reusable data processing
- efficient DataFrame operations
- cached resources
- controlled RAG indexing
- reduced duplicate API calls
- page-specific computation
- optimized database operations

The target architecture is:

```text
User Interaction
      │
      ▼
Streamlit Rerun
      │
      ▼
Check Cached Results
      │
      ├─────────────── Cache Hit ───────────────┐
      │                                         │
      │                                         ▼
      │                                  Render Quickly
      │
      └──────────── Cache Miss ────────────► Compute
                                                 │
                                                 ▼
                                              Cache
                                                 │
                                                 ▼
                                              Render
```

This allows expensive financial processing to happen only when relevant inputs change.

---

# Why This Project Is Different

This project is not simply a dashboard displaying financial data.

It combines multiple layers:

```text
                ┌──────────────────────┐
                │      UI / UX         │
                └──────────┬───────────┘
                           │
                ┌──────────▼───────────┐
                │ Financial Analytics  │
                └──────────┬───────────┘
                           │
                ┌──────────▼───────────┐
                │ Reconciliation Engine│
                └──────────┬───────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
      Payments            Bank              Tax
         │                 │                 │
         └─────────────────┼─────────────────┘
                           ▼
                ┌──────────────────────┐
                │     AI + RAG         │
                └──────────┬───────────┘
                           │
                           ▼
                Financial Intelligence
```

It combines:

**Data Engineering + Financial Rules + Analytics + AI + RAG + Workflow Automation + Role-Based Operations**

---

# AI vs Rule-Based Architecture

| Task | Approach |
|---|---|
| Amount comparison | Deterministic |
| Status comparison | Deterministic |
| Settlement calculation | Deterministic |
| Bank matching | Deterministic |
| Tax calculation | Deterministic |
| TDS calculation | Deterministic |
| Exception classification | Rule-based |
| Confidence scoring | Rule-based |
| Cash forecast calculations | Programmatic |
| Document retrieval | RAG |
| Financial explanation | Gemini |
| Natural-language questions | Gemini |
| Policy-based answers | RAG + Gemini |
| Fallback diagnostics | Local heuristic engine |

This separation improves reliability and explainability.

---

# Data Sources

The demonstration environment uses synthetic financial data.

The primary sources are:

```text
1. Internal Orders
2. Razorpay Transactions
3. Bank Statements
```

Additional documentation is used as the financial knowledge base for RAG.

The synthetic data intentionally contains known discrepancies to demonstrate the system's ability to detect real-world reconciliation scenarios.

---

# Example Questions for the AI Assistant

The following questions can be used to demonstrate the AI functionality:

### Reconciliation

```text
Why did transaction pay_24716857 fail reconciliation?
```

```text
What is the reason for the amount mismatch?
```

### Settlement

```text
Explain the settlement issue on August 10.
```

```text
Why is the August 18 bank settlement missing?
```

### Tax

```text
Explain the TDS discrepancy for the affected transaction.
```

```text
What caused the tax mismatch?
```

### Daily Close

```text
Give me a summary of the daily close report.
```

### Exceptions

```text
Which transactions require immediate attention?
```

---

# Example Financial Exception Lifecycle

```text
Transaction Received
       │
       ▼
Internal Order Matching
       │
       ▼
Gateway Matching
       │
       ▼
Settlement Verification
       │
       ▼
Bank Verification
       │
       ▼
Tax Validation
       │
 ┌─────┴─────┐
 │           │
 ▼           ▼
MATCHED     EXCEPTION
 │           │
 ▼           ▼
Reconciled  Needs Review
             │
             ▼
        Investigation
             │
             ▼
          Resolution
             │
             ▼
         Admin Review
             │
             ▼
          Resolved
```

---

# Future Scope

The current implementation demonstrates the core financial-control architecture using synthetic data.

Potential production extensions include:

## 1. Real Payment Gateway APIs

Connect directly to:

- Razorpay APIs
- settlement APIs
- payment webhooks

instead of relying on CSV ingestion.

## 2. Direct Bank Integration

Integrate with banking APIs or secure statement ingestion pipelines.

## 3. Event-Driven Architecture

Move from batch processing toward:

```text
Payment Event
    ↓
Webhook
    ↓
Reconciliation
    ↓
Exception Detection
    ↓
Notification
```

## 4. Advanced Anomaly Detection

Add ML models for:

- unusual transaction behavior
- settlement anomalies
- fraud indicators
- merchant risk scoring

## 5. Enterprise-Scale Data Layer

Move from local SQLite toward:

- PostgreSQL
- distributed data storage
- warehouse architecture

## 6. Advanced Forecasting

Use time-series models for:

- daily cash forecasting
- settlement forecasting
- revenue forecasting
- liquidity risk prediction

## 7. Automated Resolution

Introduce controlled automation for low-risk exceptions.

## 8. Human-in-the-Loop AI

AI could recommend:

```text
Exception
   ↓
AI Root Cause
   ↓
Recommended Action
   ↓
Human Approval
   ↓
Resolution
```

This preserves human control over financial decisions.

---

# Current Limitations

This project is a demonstration/prototype designed around synthetic buildathon data.

Current limitations include:

- payment gateway data is synthetic
- bank data is synthetic
- financial integrations are not connected to live production accounts
- AI responses depend on Gemini API availability when using generative mode
- local SQLite is intended for demonstration rather than large-scale production deployment
- cash forecasting is designed for short-term demonstration
- production deployment would require stronger secrets management and infrastructure controls

These limitations do not affect the demonstration of the underlying reconciliation and financial intelligence architecture.

---

# Deployment

The application can be deployed using Streamlit-compatible infrastructure.

For example:

```text
GitHub Repository
      │
      ▼
Streamlit Cloud / Server
      │
      ▼
AI Finance Controller
```

Gemini credentials should be supplied through secure environment variables or platform secrets rather than committed to the repository.

---

# Production Security Considerations

For production deployment, the following should be implemented:

- secure secret management
- encrypted credentials
- HTTPS
- stronger authentication
- role-based authorization enforcement
- database encryption where appropriate
- API rate limiting
- audit log protection
- PII masking
- secure document storage
- tenant isolation
- production-grade database infrastructure
- monitoring and alerting

---

# Demonstration Dataset

The repository contains synthetic data designed to simulate realistic financial operations.

The dataset intentionally contains scenarios such as:

```text
✓ Successful reconciliations
✓ Fee/settlement mismatches
✓ Missing internal orders
✓ Internal amount mismatch
✓ Internal status mismatch
✓ Missing bank credit
✓ Bank settlement amount mismatch
✓ Disputed transactions
✓ Tax discrepancies
✓ TDS under-deduction
✓ TDS over-deduction
```

This allows the complete reconciliation pipeline to be demonstrated without exposing real merchant financial information.

---

# Project Objective

The long-term vision of AI Finance Controller is to move financial operations from:

```text
Manual Reconciliation
       ↓
Spreadsheet Investigation
       ↓
Manual Exception Tracking
       ↓
Delayed Financial Close
```

toward:

```text
Automated Reconciliation
       ↓
Real-Time Exception Detection
       ↓
AI-Assisted Investigation
       ↓
Workflow-Based Resolution
       ↓
Continuous Financial Control
```

---

# Business Value

For a payment/fintech ecosystem, the system can potentially help reduce:

### Operational Cost

Automating repetitive reconciliation activities.

### Revenue Leakage

Detecting settlement and amount mismatches.

### Financial Risk

Identifying missing or inconsistent transactions.

### Investigation Time

Providing transaction-level explanations and AI-assisted investigation.

### Compliance Risk

Identifying tax/TDS inconsistencies.

### Closing Time

Supporting a more automated daily financial close.

### Human Error

Replacing repetitive manual comparison with deterministic rules.

---

# Design Principles

The project follows five major principles:

### 1. Accuracy First

Financial calculations are deterministic wherever possible.

### 2. Explainability

Every exception should have a reason that can be investigated.

### 3. AI as an Assistant

AI explains and assists rather than becoming the sole authority for financial calculations.

### 4. Human-in-the-Loop

Financial exceptions can be reviewed and resolved by authorized users.

### 5. Auditability

Important financial actions and resolutions are recorded for traceability.

---

# Summary

**AI Finance Controller** is an AI-powered financial operations and reconciliation platform designed to unify:

```text
Internal Orders
      +
Razorpay Transactions
      +
Bank Statements
      +
Tax Rules
      +
Financial Documentation
      ↓
AI FINANCE CONTROLLER
      ↓
Reconciliation
      +
Exception Detection
      +
Settlement Verification
      +
Tax/TDS Audit
      +
Cash Forecasting
      +
AI Financial Intelligence
      +
Resolution Workflow
```

The project demonstrates how deterministic financial systems and generative AI can work together:

> **Rules determine the financial truth. AI helps humans understand and act on it.**

---

# Author

**Shivendu Kumar**

B.Tech — Computer Science & Engineering  
AI/ML Specialization

Areas of interest:

- Artificial Intelligence
- Machine Learning
- Data Science
- Financial Technology
- Backend Development
- AI Agents
- Retrieval-Augmented Generation
- Automation

---

# If You Find This Project Interesting

This project was built as a demonstration of how AI can be applied to financial operations, reconciliation, compliance and decision support.

If you are reviewing this repository, the recommended starting points are:

```text
1. app.py
2. src/reconciliation.py
3. src/database.py
4. src/rag_engine.py
5. src/tax_matcher.py
6. src/forecaster.py
7. tests/test_reconciliation.py
```

The combination of these modules demonstrates the complete journey from:

**raw financial data → reconciliation → exception detection → financial analysis → AI-assisted investigation → resolution.**

---

# Quick Start

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>

cd "AI Finance Controller"

python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt

streamlit run app.py
```

Then open:

```text
http://localhost:8501
```

---

# Built for Financial Intelligence

### **Reconcile. Detect. Explain. Resolve.**

**AI Finance Controller — turning fragmented financial data into actionable financial intelligence.**