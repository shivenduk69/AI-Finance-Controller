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

# System Architecture (Production-Grade Microservices)

The platform is engineered as a **distributed, multi-service financial control architecture** separating user presentation, API orchestration, and mathematical computation into independently scalable services:

```text
                           ┌───────────────────────────────┐
                           │      CLIENT / WEB BROWSER     │
                           │   Merchant & Admin Portals    │
                           └───────────────┬───────────────┘
                                           │
                                           │ HTTP / WebSocket (Socket.IO)
                                           ▼
                           ┌───────────────────────────────┐
                           │       FRONTEND SERVICE        │
                           │  • React 18 + Vite + Tailwind │
                           │  • Plotly.js Financial Charts │
                           │  • TanStack Query + Axios     │
                           │  • Port: 3000                 │
                           └───────────────┬───────────────┘
                                           │
                                           │ REST API (JSON) + HttpOnly JWT
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                     BACKEND SERVICE                                      │
│  • Node.js + Express.js (CommonJS)                                                       │
│  • RBAC & Tenant Isolation (Merchant vs Admin Scoping)                                   │
│  • Argon2id Security, Helmet, Winston Logger, Zod Validation                             │
│  • Socket.IO Real-Time Exception & Notification Broadcasts                               │
│  • Port: 5000                                                                            │
└───────────┬───────────────────────────────┬──────────────────────────────┬───────────────┘
            │                               │                              │
            │ Cache & Rate Limiting         │ Async Message Queues         │ Internal RPC / REST
            ▼                               ▼                              ▼
┌────────────────────────┐      ┌────────────────────────┐      ┌──────────────────────────┐
│   REDIS 7 (IN-MEMORY)  │      │  RABBITMQ 3 (MESSAGING)│      │  AI & COMPUTING SERVICE  │
│ • Dashboard Metric TTL │      │ • Reconciliation Jobs  │      │ • Python 3.11 + FastAPI  │
│ • Ephemeral Sessions   │      │ • Ingestion Event Bus  │      │ • 7-Rule Matching Engine │
│ • Port: 6380           │      │ • Dead-Letter Queue    │      │ • Section 194-O Tax Engine│
└────────────────────────┘      │ • Ports: 5672, 15672   │      │ • 7-Day Cash Forecaster  │
                                └────────────────────────┘      │ • Gemini RAG + pgvector  │
                                                                │ • Port: 8000             │
                                                                └────────────┬─────────────┘
                                                                             │
            ┌────────────────────────────────────────────────────────────────┘
            │ Data Persistence & Vector Storage
            ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                       POSTGRESQL 16 + PGVECTOR DATABASE CLUSTER                          │
│ • Transactions, Orders, Settlements, Exceptions, Audit Logs                              │
│ • pgvector 768-dim embeddings for financial RAG semantic search                          │
│ • Strictly Scoped RBAC Roles: finance_backend_user & finance_ai_user                     │
│ • Host Port: 5434 (Internal: 5432)                                                       │
└──────────────────────────────────────────────────────────────────────────────────────────┘
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
├── frontend/                     # Service 1: React 18 Single Page Application
│   ├── public/                   # Static branding assets (logo.png)
│   ├── src/
│   │   ├── components/           # Reusable UI (Sidebar, Header, AI Popover, Charts)
│   │   ├── views/                # 11 Merchant Views & 13 Admin Views
│   │   ├── services/             # Axios API Client & Socket.IO WebSockets
│   │   ├── context/              # Authentication & App State Providers
│   │   ├── App.jsx               # Route Declarations & RBAC Route Guards
│   │   └── main.jsx              # React DOM Entrypoint
│   ├── package.json              # React 18, Vite 5, Tailwind CSS, Plotly.js
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
│
├── backend/                      # Service 2: Node.js + Express API Service
│   ├── config/                   # PostgreSQL Pool, Redis Client, RabbitMQ Worker
│   ├── controllers/              # Auth, Admin, Reconciliation, Exceptions, Ingestion
│   ├── middleware/               # Argon2id Auth, JWT Verification, RBAC Tenant Scoping
│   ├── repositories/             # PostgreSQL Query Abstractions
│   ├── routes/                   # REST Route Definitions (/api/auth, /api/reconciliation, etc.)
│   ├── services/                 # Business Logic & Socket.IO Event Broadcasting
│   ├── utils/                    # Password Hashing, Token Generation, Logger
│   ├── tests/                    # Jest Automated Integration Suite (15/15 tests)
│   ├── server.js                 # Express Application Entrypoint (:5000)
│   ├── package.json
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
│
├── ai-service/                   # Service 3: Python 3.11 + FastAPI Processing Engine
│   ├── app/
│   │   ├── api/                  # FastAPI Routers (/internal/reconciliation, /tax, /forecasting, /rag)
│   │   ├── core/                 # PostgreSQL Connector, pgvector Engine, RabbitMQ Listener
│   │   ├── forecasting/          # 7-Day Rolling Cash Inflow Projection Engine
│   │   ├── ingestion/            # High-Throughput CSV Parser & Normalization
│   │   ├── rag/                  # Gemini 2.0 Flash + pgvector Semantic Knowledge Base
│   │   ├── reconciliation/       # 7-Rule 3-Way Reconciliation Matching Engine
│   │   └── tax/                  # Section 194-O TDS (1%) & GST (18%) Compliance Auditor
│   ├── tests/                    # FastAPI Pytest Suite (9/9 tests)
│   ├── main.py                   # FastAPI Application Entrypoint (:8000)
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
│
├── database/                     # PostgreSQL 16 + pgvector Cluster Configuration
│   ├── schema/                   # 01_init.sql (DDL for tables, indexes, pgvector)
│   ├── seeds/                    # 02_seed.sql (Users, Stores, Transactions, Orders, Statements)
│   └── roles/                    # 03_roles.sql (finance_backend_user & finance_ai_user RBAC)
│
├── infrastructure/               # Shared Multi-Container Orchestration
│   └── docker-compose.yml        # PostgreSQL 16 (:5434), Redis 7 (:6380), RabbitMQ 3 (:5672, :15672)
│
├── data/                         # Verified Financial Ingestion Datasets
│   ├── bank_statement.csv        # Bank credits & nodal settlements
│   ├── internal_orders.csv       # Merchant operational order ledger
│   └── transactions_processed.csv# Payment gateway captured transactions, fees, refunds
│
├── documents/                    # Corporate Financial Intelligence Knowledge Base (RAG)
│   ├── GST_Rulebook_2024.md
│   ├── Gateway_Dispute_Playbook.md
│   ├── Merchant_Reconciliation_SOP.md
│   └── Section_194O_Compliance.md
│
├── tests/                        # Root-Level Regression & Parity Verification Suite
│   ├── benchmark_performance.py  # Pipeline Throughput & Latency Benchmark
│   ├── test_parity.py            # Phase 7 Mathematical Parity Suite (6/6 tests)
│   └── test_reconciliation.py    # Multi-Rule Reconciliation Verification (8/8 tests)
│
├── docs/                         # Synchronized Migration & Architectural Specs
│   ├── API_CONTRACTS.md          # REST API Request/Response Schemas
│   ├── DATABASE_AUDIT.md         # Database Schema & Table Ownership Matrix
│   ├── DOCKER_ARCHITECTURE.md    # Multi-Compose & Networking Architecture
│   ├── MANUAL_TESTING_REPORT.md  # End-to-End Browser Manual Verification Log
│   ├── MIGRATION_PLAN.md         # 10-Phase Technology Migration Roadmap
│   ├── SERVICE_COMMUNICATION.md  # Inter-Service Communication Protocols
│   └── UI_SPECIFICATION.md       # Component Specs & Visual Design Tokens
│
├── .gitignore
├── AGENTS.md                     # Mandatory AI Coding Rules & Architectural Invariants
├── CLAUDE.md                     # Quick Reference Architecture Guide
├── guidelines.md                 # Preventive Instructions & Mistake Tracker
├── logo.png                      # Application Branding Asset
├── README.md                     # Master Project Guide & Architecture Documentation
└── requirements.txt              # Minimal Root Pip Pointer (-r ai-service/requirements.txt)
```

---

# Technology Stack

| Layer | Technology | Key Capabilities / Purpose |
|---|---|---|
| **Frontend UI** | React 18, Vite 5, Tailwind CSS | Single Page App, Responsive Modern UI, Dark Navy Sidebar (`#161f30`) |
| **Interactive Visualization** | Plotly.js (`react-plotly.js`) | Financial volume, exception breakdown, and cash projection charts |
| **State & API Client** | TanStack Query v5, Axios | Declarative data fetching, cache synchronization, HTTP clients |
| **Real-Time WebSockets** | Socket.IO Client v4 | Instant exception status sync, live alerts, ticket broadcasts |
| **Backend API Gateway** | Node.js 20+, Express.js (CommonJS) | REST API endpoints, Role-Based Access Control, JWT auth cookies |
| **Authentication & Security** | Argon2id, JsonWebToken, Helmet | Cryptographically secure password hashing, HttpOnly cookies, CORS |
| **AI & Mathematical Engine** | Python 3.11+, FastAPI, Uvicorn | 7-Rule 3-way matching, Section 194-O tax auditing, cash forecasting |
| **Data Processing** | Pandas, Polars, NumPy | High-performance vectorized DataFrame computation |
| **Relational Database** | PostgreSQL 16 + `pgvector` | ACID transactions, NUMERIC(15,2) currency math, HNSW vector search |
| **In-Memory Cache** | Redis 7 Alpine (`ioredis`) | Dashboard metric caching with TTL, rate-limiting, session store |
| **Message Broker** | RabbitMQ 3 Management Alpine | Asynchronous reconciliation queues, CSV ingestion event bus |
| **Generative AI & LLM** | Google Gemini 2.0 Flash SDK | Evidence-grounded natural language financial reasoning & chat |
| **Vector Embeddings** | Google `text-embedding-004` | 768-dimensional semantic embeddings for financial policy retrieval |
| **Containerization** | Docker & Docker Compose | Independent service containers on shared bridge `finance-network` |
| **Automated Testing** | Jest, Pytest, Supertest, Unittest | Parity validation, integration tests, mathematical correctness |

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

# Installation & Setup Guide

The application can be run in two primary modes:
1. **Local Multi-Terminal Development Mode** (Recommended for development, code inspection, and debugging).
2. **Independent Docker Compose Mode** (Recommended for containerized deployment).

---

## Prerequisites

Before starting, ensure you have the following installed on your machine:
- **Git**
- **Docker Desktop** (running with Docker Engine enabled)
- **Node.js 20+** and **npm**
- **Python 3.11+**

---

## Step 1: Clone Repository & Setup Environment Files

Clone the repository and inspect the project directory:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd "AI Finance Controller"
```

The repository includes pre-configured environment template files for every service:
- `backend/.env.example`
- `ai-service/.env.example`
- `frontend/.env.example`

If `.env` files are not already created, copy each template:

```bash
# Windows (PowerShell)
Copy-Item backend\.env.example backend\.env
Copy-Item ai-service\.env.example ai-service\.env
Copy-Item frontend\.env.example frontend\.env

# Linux / macOS
cp backend/.env.example backend/.env
cp ai-service/.env.example ai-service/.env
cp frontend/.env.example frontend/.env
```

Ensure your `ai-service/.env` contains a valid Google Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## Step 2: Install Dependencies

### 1. AI Service Python Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r ai-service/requirements.txt

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r ai-service/requirements.txt
```

### 2. Backend Service Node.js Dependencies
```bash
cd backend
npm install
cd ..
```

### 3. Frontend Service React Dependencies
```bash
cd frontend
npm install
cd ..
```

---

# How to Run the Application (Local Development)

Open **4 separate terminal windows** (or split terminals in VS Code / Windows Terminal) and run the following:

### Terminal 1 — Infrastructure (PostgreSQL 16 + Redis + RabbitMQ)
```powershell
cd "AI Finance Controller"
docker compose -f infrastructure/docker-compose.yml up -d
```
> **Services Started:**
> - `finance-postgres`: PostgreSQL 16 + pgvector on port **`5434`** (auto-seeds schemas, tables, and test data).
> - `finance-redis`: Redis 7 on port **`6380`**.
> - `finance-rabbitmq`: RabbitMQ on port **`5672`** (Management UI on **`15672`**).

### Terminal 2 — AI & Data Processing Service (FastAPI)
```powershell
cd "AI Finance Controller\ai-service"
..\.venv\Scripts\python.exe -m uvicorn main:app --port 8000 --reload
```
> **Service Running:** FastAPI on `http://localhost:8000`  
> Interactive OpenAPI documentation available at: `http://localhost:8000/docs`

### Terminal 3 — Backend API Gateway (Express.js)
```powershell
cd "AI Finance Controller\backend"
node server.js
```
> **Service Running:** Node.js + Express on `http://localhost:5000`  
> Connects to PostgreSQL (:5434), Redis (:6380), RabbitMQ (:5672), and AI Service (:8000).

### Terminal 4 — Frontend Web App (React 18 + Vite)
```powershell
cd "AI Finance Controller\frontend"
npm run dev
```
> **Service Running:** React Vite SPA on `http://localhost:3000`

---

# Accessing the Web Application

Open **Google Chrome** and navigate to:

👉 **[http://localhost:3000](http://localhost:3000)**

### Pre-Seeded Login Credentials

| Role | Username | Password | Purpose & Scope |
| :--- | :--- | :--- | :--- |
| **Merchant Store Manager** | `store_manager` | `password123` | Merchant portal, 3-way reconciliation, exception notes, cash forecasting, support tickets |
| **System Administrator** | `admin` | `password123` | Global admin dashboard, cross-tenant transactions, live exception approval, AI & RAG center |

*(Optional Management Portals)*:
- **FastAPI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **RabbitMQ Dashboard:** [http://localhost:15672](http://localhost:15672) (User: `finance_admin`, Password: `rabbitmq_secure_password`)

---

# Automated Test Suite & Parity Verification

The repository contains an enterprise testing suite across backend, AI service, and root parity verification:

### 1. Root Mathematical Parity & Multi-Rule Test Suite
```bash
# Verify 7-rule reconciliation, 100% mathematical parity against verified baselines
python -m pytest tests/ -v
```

### 2. Backend Integration Test Suite (Jest)
```bash
# Verify auth, Argon2id, RBAC, Redis caching, RabbitMQ queuing, Socket.IO
npm test --prefix backend
```

### 3. AI Service Test Suite (Pytest)
```bash
# Verify FastAPI health, tax audit, cash forecasting, pgvector RAG, internal auth
pytest ai-service/tests/ -v
```

### 4. Throughput & Latency Performance Benchmark
```bash
# Execute end-to-end processing pipeline benchmark
python tests/benchmark_performance.py
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

# Performance & Scalability Architecture

In enterprise financial operations, sub-second latency is required for dashboards, while heavy batch reconciliation and ingestion must not block user interactions.

The platform achieves high throughput and resilience through a multi-tiered performance architecture:

```text
User Request / Query
       │
       ▼
React SPA (TanStack Query Cache) ──[ Cache Hit: Instant Client Render (<5ms) ]
       │
       │ HTTP / Socket.IO
       ▼
Express API Gateway (Backend)
       │
       ▼
Redis 7 In-Memory Cache ───────────[ Cache Hit: Return Stored JSON (<10ms) ]
       │
       │ Cache Miss
       ▼
PostgreSQL Connection Pool & FastAPI AI Service
       │
       ├─► Heavy Batch Processing ──► Offload to RabbitMQ Queue (Worker Threads)
       │
       └─► Vectorized Computation ──► Polars / Pandas C-Engine (<150ms)
                                             │
                                             ▼
                                     Store Result in Redis
                                             │
                                             ▼
                                    Stream Response to Client
```

### Core Performance Highlights:
- **Redis Metric Caching:** Aggregated KPI metrics (GMV, auto-match rates, cash flow summaries) are cached in Redis with configurable TTLs and automated invalidation when new exceptions or transactions are resolved.
- **RabbitMQ Asynchronous Task Queues:** File ingestion and multi-thousand transaction batch reconciliations are offloaded from HTTP threads into background worker queues with Dead-Letter Queues (DLQ) for retries.
- **Optimized PostgreSQL 16 & pgvector:** Database queries utilize composite B-tree indexes for tenant lookup (`store_id`, `merchant_id`, `transaction_date`) and HNSW index structures for rapid nearest-neighbor vector similarity searches.
- **FastAPI Vectorized Math:** Python financial reconciliation engines run vectorized column operations in Pandas and Polars, processing 120+ multi-source records in under 13ms (total pipeline latency <130ms).
- **Socket.IO Event Stream:** Real-time state synchronizations (e.g. admin exception resolution approvals) are broadcasted directly via WebSockets, eliminating periodic client polling.

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

The platform now natively runs on:

- PostgreSQL 16 with `pgvector` for vector chunk storage and hybrid SQL querying
- Redis 7 for high-speed sub-millisecond metric caching
- RabbitMQ 3 for asynchronous batch reconciliation and ingestion queues

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

- payment gateway and bank transactions are synthetic demonstration datasets
- financial integrations are currently simulated via normalized CSV uploads rather than live gateway webhooks
- AI responses require a valid Gemini API key for live generative mode, with deterministic heuristic fallbacks available
- cash forecasting is designed for short-term demonstration
- production deployment would require stronger secrets management and infrastructure controls

These limitations do not affect the demonstration of the underlying reconciliation and financial intelligence architecture.

---

# Deployment Architecture (Docker & Containerization)

The platform is designed for enterprise deployment with independent container builds across all tiers:

```text
                               ┌───────────────────────────┐
                               │  REVERSE PROXY / INGRESS  │
                               │  Nginx / AWS ALB / Cloud  │
                               └─────────────┬─────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │
                       ▼ :3000                                     ▼ :5000
       ┌───────────────────────────────┐           ┌───────────────────────────────┐
       │     frontend (Docker)         │           │      backend (Docker)         │
       │  React 18 SPA (Vite / Nginx)  │           │   Node.js 20+ Express API     │
       └───────────────────────────────┘           └───────────────┬───────────────┘
                                                                   │
                                           ┌───────────────────────┼───────────────────────┐
                                           │                       │                       │
                                           ▼ :8000                 ▼ :6379                 ▼ :5672
                           ┌───────────────────────────────┐ ┌───────────┐           ┌───────────┐
                           │      ai-service (Docker)      │ │   redis   │           │ rabbitmq  │
                           │ Python 3.11 + FastAPI Engine  │ │  (Docker) │           │  (Docker) │
                           └───────────────┬───────────────┘ └───────────┘           └───────────┘
                                           │
                                           ▼ :5432
                               ┌───────────────────────────┐
                               │     postgres (Docker)     │
                               │   PostgreSQL 16+pgvector  │
                               └───────────────────────────┘
```

Each service contains its own `Dockerfile` and `docker-compose.yml` communicating over an isolated shared Docker bridge network (`finance-network`):
- `frontend/Dockerfile` & `frontend/docker-compose.yml`
- `backend/Dockerfile` & `backend/docker-compose.yml`
- `ai-service/Dockerfile` & `ai-service/docker-compose.yml`
- `infrastructure/docker-compose.yml` (Postgres, Redis, RabbitMQ)

---

# Enterprise Security Architecture

The migration implements multi-layered security controls designed for financial data protection:

- **Argon2id Password Hashing:** User passwords are encrypted using memory-hard Argon2id algorithms resisting GPU brute-force attacks.
- **Stateless JWT in HttpOnly Cookies:** Authentication tokens are stored in secure, HttpOnly, SameSite cookies preventing cross-site scripting (XSS) token theft.
- **Role-Based Access Control (RBAC):** Strict policy middleware ensures Merchants can only view their own store data (`store_id`, `merchant_id`), while Admins hold cross-tenant governance authority.
- **Dedicated Database User Roles:** Enforces PostgreSQL privilege separation via `finance_backend_user` (owns users, tickets, notifications) and `finance_ai_user` (owns reconciliation transactions and audit ledgers).
- **Service-to-Service Authentication:** Internal RPC calls between Backend and AI Service are secured with pre-shared cryptographic bearer secrets (`INTERNAL_API_SECRET`).
- **Security Headers & Sanitization:** Armed with Helmet middleware, CORS domain restriction, and strict Zod/Pydantic request payload validation schemas.

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

# Code Review & Recommended Starting Points

If you are reviewing this codebase, the recommended entry points illustrating the distributed architecture are:

```text
1. frontend/src/views/ReconciliationView.jsx   ──► 3-Way Reconciliation Interactive UI
2. backend/server.js                            ──► Express, Socket.IO & Event Bus Wiring
3. backend/controllers/reconciliationController.js ──► Tenant-Scoped API & Cache Handler
4. ai-service/app/reconciliation/engine.py      ──► Core 7-Rule Financial Reconciliation Engine
5. ai-service/app/tax/engine.py                 ──► Section 194-O TDS & GST Compliance Auditor
6. ai-service/app/rag/engine.py                 ──► pgvector Semantic Search & Gemini RAG
7. database/schema/01_init.sql                  ──► Relational Financial DDL & pgvector Extension
8. tests/test_parity.py                         ──► Mathematical Parity Verification Suite
```

---

# Rapid Quick Start (In 4 Terminals)

Clone the repository and run all services in 4 separate terminal tabs:

```bash
# Terminal 1: Shared Infrastructure
docker compose -f infrastructure/docker-compose.yml up -d

# Terminal 2: AI & Calculation Service (FastAPI)
cd ai-service
..\.venv\Scripts\python.exe -m uvicorn main:app --port 8000 --reload

# Terminal 3: Backend API Gateway (Node.js / Express)
cd backend
node server.js

# Terminal 4: Frontend Web App (React / Vite)
cd frontend
npm run dev
```

Open your browser at:

👉 **[http://localhost:3000](http://localhost:3000)**

### Login Credentials
- **Merchant Store Manager:** `store_manager` / `password123`
- **System Administrator:** `admin` / `password123`

---

# Built for Financial Intelligence

### **Reconcile. Detect. Explain. Resolve.**

**AI Finance Controller — turning fragmented financial data into actionable financial intelligence.**