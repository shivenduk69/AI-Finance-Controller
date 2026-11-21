# API Contracts & Inter-Service Communication Specification

This document details the RESTful HTTP API contracts, WebSocket events, and internal service communication interfaces for the three-service architecture:
1. **Public/Client APIs:** Frontend $\leftrightarrow$ Backend (`http://localhost:5000/api`)
2. **Internal AI APIs:** Backend $\leftrightarrow$ AI Service (`http://localhost:8000/internal`)
3. **Real-Time WebSocket Events:** Socket.IO (`ws://localhost:5000`)

---

## 1. Authentication & Session APIs (Backend)

### 1.1 `POST /api/auth/login`
- **Description:** Authenticates user credentials using Argon2id, creates persistent session, and sets secure HttpOnly cookie.
- **Request Body:**
  ```json
  {
    "email": "flipkart.delhi@merchant-demo.com",
    "password": "flipkart123"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "user": {
      "user_id": "fk_user_delhi",
      "email": "flipkart.delhi@merchant-demo.com",
      "role": "MERCHANT",
      "merchant_id": "flipkart",
      "store_id": "fk_delhi"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Error (401 Unauthorized):**
  ```json
  {
    "success": false,
    "error": "Invalid email or password"
  }
  ```

### 1.2 `GET /api/auth/me`
- **Description:** Retrieves the authenticated user profile based on JWT cookie or Bearer header.
- **Response (200 OK):** Returns current user object.

### 1.3 `POST /api/auth/logout`
- **Description:** Invalidates session token, logs action, and clears session cookie.
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "message": "Logged out successfully"
  }
  ```

---

## 2. Reconciliation & Transactions APIs (Backend & AI Service)

### 2.1 `GET /api/reconciliation/summary`
- **Description:** Retrieves dashboard summary KPI metrics with Redis caching.
- **Query Parameters:** `start_date`, `end_date`, `merchant_id` (Admin only), `store_id` (Admin only).
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "data": {
      "total_payments_processed": 45,
      "total_transactions": 60,
      "auto_resolved_count": 52,
      "needs_review_count": 8,
      "auto_match_accuracy_pct": 86.7,
      "gross_collections_inr": 82450.00,
      "refunds_inr": 4200.00,
      "fees_gst_inr": 1945.82,
      "settled_to_bank_inr": 76304.18,
      "expected_next_2_days_inr": 18350.00,
      "unreconciled_review_inr": 0.0
    }
  }
  ```

### 2.2 `GET /api/reconciliation/transactions`
- **Description:** Paginated and filtered gateway transaction ledger.
- **Query Parameters:** `page` (default: 1), `limit` (default: 50), `status`, `type`, `method`, `search`, `start_date`, `end_date`.
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "data": [
      {
        "transaction_id": "pay_24716857",
        "order_id": "order_11223344",
        "type": "PAYMENT",
        "status": "captured",
        "method": "card",
        "amount_inr": 2500.00,
        "fee_inr": 75.00,
        "tax_inr": 13.50,
        "settled_amount_inr": 2411.50,
        "expected_settlement_date": "10-08-2026",
        "calculated_exceptions": ["FEE_MISMATCH (Expected: ₹50.00, Recorded: ₹75.00)"],
        "resolution_status": "NEEDS_REVIEW",
        "confidence_score": 0.30,
        "merchant_id": "flipkart",
        "store_id": "fk_delhi"
      }
    ],
    "pagination": { "page": 1, "limit": 50, "total": 60 }
  }
  ```

### 2.3 `GET /api/reconciliation/transactions/:id/audit`
- **Description:** Returns the complete 3-Way verification payload for the visual audit drawer.
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "transaction_id": "pay_24716857",
    "nodes": {
      "internal_order": {
        "order_id": "order_11223344",
        "amount_inr": 2500.00,
        "status": "COMPLETED",
        "state": "active-node"
      },
      "gateway": {
        "transaction_id": "pay_24716857",
        "amount_inr": 2500.00,
        "fee_inr": 75.00,
        "tax_inr": 13.50,
        "settled_amount_inr": 2411.50,
        "state": "error-node"
      },
      "bank_credit": {
        "date": "10-08-2026",
        "bank_reference": "UTR8921829102",
        "amount_inr": 6705.21,
        "status": "SETTLEMENT_MISMATCH",
        "state": "error-node"
      }
    },
    "math_check": {
      "passed": false,
      "expected_fee": 50.00,
      "recorded_fee": 75.00,
      "expected_tax": 9.00,
      "recorded_tax": 13.50,
      "expected_settled": 2441.00,
      "recorded_settled": 2411.50
    },
    "exceptions": ["FEE_MISMATCH", "TAX_MISMATCH"],
    "rag_explanation": "Gateway contracted MDR for card transactions is 2% under Merchant Agreement Clause 4.2. Recorded fee reflects 3% MDR."
  }
  ```

---

## 3. Exceptions & Workflow Resolution APIs

### 3.1 `GET /api/exceptions`
- **Description:** Retrieves active exceptions, pending approvals, and resolution history.
- **Query Parameters:** `tab` (`active`, `pending_admin`, `resolved`), `severity`, `category`, `search`.
- **Response (200 OK):** Returns filtered list of exception records.

### 3.2 `POST /api/exceptions/:id/resolve`
- **Description:** Submits or approves an exception resolution note.
- **Request Body:**
  ```json
  {
    "resolution_note": "Store confirmed bank deposit receipt manually.",
    "action": "SUBMIT_FOR_APPROVAL" // or "APPROVE", "REJECT", "DIRECT_RESOLVE"
  }
  ```
- **Behavior:**
  - If caller is `MERCHANT`: Sets status to `PENDING_ADMIN`, creates notification for Admin, emits `exception_submitted` WebSocket event.
  - If caller is `ADMIN`: Sets status to `RESOLVED` (or `REJECTED`), updates metric cache, creates notification for Store, emits `exception_resolved` WebSocket event.

---

## 4. Tax & Cash Flow APIs

### 4.1 `POST /api/tax/audit`
- **Description:** Runs Section 194-O TDS and GST tax compliance audit.
- **Request Body (Optional custom config):**
  ```json
  {
    "tds_config": {
      "PAYMENT": {
        "Individual": { "applicable": true, "rate": 0.01 },
        "Company": { "applicable": true, "rate": 0.02 },
        "Non-Resident": { "applicable": false, "rate": 0.00 }
      }
    }
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "summary": {
      "total_audited_records": 60,
      "gst_anomalies_count": 2,
      "tds_anomalies_count": 3,
      "total_tax_discrepancies": 5,
      "tax_compliance_pct": 91.7,
      "total_gst_collected_inr": 1945.82,
      "total_tds_deducted_inr": 824.50
    },
    "audited_records": [ /* Transaction tax rows */ ]
  }
  ```

### 4.2 `GET /api/forecast/cashflow`
- **Description:** Computes 7-day rolling cash flow projection.
- **Query Parameters:** `days` (default: 7), `gateway_fee_rate` (default: 0.02), `gst_rate` (default: 0.18).
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "data": [
      {
        "date": "24-08-2026",
        "status": "COMMITTED (T+2 queue)",
        "gross_collections": 14200.00,
        "refunds": 0.00,
        "payouts": 0.00,
        "fees_gst": 335.12,
        "net_inflow": 13864.88,
        "cumulative_cash": 88864.88
      }
    ]
  }
  ```

---

## 5. AI Assistant & RAG APIs

### 5.1 `POST /api/ai/chat`
- **Description:** Generates RAG-grounded response for user query with source citations.
- **Request Body:**
  ```json
  {
    "conversation_id": "conv_89123891",
    "query": "Why did transaction pay_24716857 fail reconciliation?"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "answer": "Transaction pay_24716857 failed reconciliation due to a FEE_MISMATCH and TAX_MISMATCH...",
    "sources": [
      {
        "file_name": "03_merchant_fee_agreement.md",
        "chunk_index": 2,
        "excerpt": "Standard MDR fee charged on domestic credit cards is fixed at 2.00%..."
      }
    ]
  }
  ```

### 5.2 `GET /api/ai/conversations` & `POST /api/ai/conversations`
- **Description:** List, create, and manage persistent conversation threads.

---

## 6. Support Tickets & Notifications APIs

### 6.1 `GET /api/tickets` & `POST /api/tickets`
- **Description:** List and create support helpdesk queries.
- **Creation Body:**
  ```json
  {
    "transaction_id": "pay_95822412",
    "subject": "Gateway fee charged at 3% instead of contracted 2%",
    "message": "We noticed fee discrepancy on order_24942603...",
    "category": "Gateway Exception Review",
    "priority": "High"
  }
  ```

### 6.2 `PUT /api/tickets/:id/resolve` (Admin)
- **Request Body:**
  ```json
  {
    "status": "RESOLVED",
    "resolution_comments": "Credit adjustment of ₹25.00 scheduled in next nodal payout batch."
  }
  ```

### 6.3 `GET /api/notifications` & `PUT /api/notifications/:id/read`
- **Description:** Retrieve unread notifications and mark items as read.

---

## 7. Real-Time Socket.IO Event Dictionary

| Event Name | Direction | Payload | Functional Trigger |
| :--- | :--- | :--- | :--- |
| `exception_submitted` | Client $\to$ Server $\to$ Admins | `{ transaction_id, store_id, note }` | Merchant store submits resolution note. |
| `exception_resolved` | Server $\to$ Store & Admins | `{ transaction_id, status: 'RESOLVED', note }` | Admin approves or directly resolves exception. |
| `notification_dispatched` | Server $\to$ User/Role | `{ id, title, message, role }` | Platform alert or ticket update triggered. |
| `batch_reconciled` | Server $\to$ All | `{ batch_id, auto_match_rate }` | Ingestion pipeline finishes reconciliation. |

---

## 8. Internal Service APIs (Backend $\leftrightarrow$ AI Service)

All internal calls require the `x-internal-secret` header.

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `POST /internal/reconciliation/run` | POST | Triggers 3-way reconciliation on specified store/merchant records. |
| `POST /internal/tax/audit` | POST | Executes Section 194-O TDS & GST calculations. |
| `POST /internal/forecast/cashflow` | POST | Executes rolling cash flow algorithm. |
| `POST /internal/ai/query` | POST | Runs pgvector semantic search and Gemini response generation. |
| `POST /internal/ai/index` | POST | Triggers document ingestion and vector embedding into pgvector. |
| `GET /internal/health` | GET | AI Service liveness and model connectivity check. |
