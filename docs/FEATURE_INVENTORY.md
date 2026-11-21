# Complete Feature Inventory & Service Mapping

This inventory catalogs every functional capability, user interface component, computational algorithm, and operational workflow from the original monolithic application, mapping each to its target service in the three-service architecture:
1. **Frontend Service (React.js + Vite + Tailwind + Plotly.js)**
2. **Backend Service (Node.js + Express.js CommonJS + PostgreSQL + Redis + RabbitMQ)**
3. **AI & Data Processing Service (FastAPI + Python + Pandas + Gemini SDK + pgvector)**

---

## 1. Authentication, Sessions & RBAC

| Feature / UI Component | Monolithic Location | Target Service | Detailed Responsibilities & Invariants |
| :--- | :--- | :--- | :--- |
| **Split-Screen Sign-In Interface** | `app.py` (L491–L789) | **Frontend** | Recreate split-screen login page; left dark branding hero panel with glowing SVG preview, right clean white form container with email/password inputs and error alerts. |
| **User Authentication & Token Issuance** | `src/database.py`, `app.py` | **Backend** | Authenticate credentials against PostgreSQL `users` table using Argon2id. Issue secure, HttpOnly JWT cookies and session tokens. |
| **Predefined Demo Accounts Alert** | `app.py` (L745–L751) | **Frontend** | Informational pill referencing demo credentials (`admin@razorpay-demo.com`, `flipkart.delhi@merchant-demo.com`, `amazon.delhi@merchant-demo.com`). |
| **Forgot Password Security Protocol** | `app.py` (L781–L786) | **Frontend** | Alert banner informing users that self-service recovery is disabled for enterprise security and providing support contact. |
| **Role-Based Access Control (RBAC) Guard** | `app.py` (L2594–L2615) | **Frontend + Backend** | Enforce role isolation: `MERCHANT` role restricted strictly to their assigned `merchant_id` and `store_id`; `ADMIN` role granted platform-wide oversight. Backend middleware rejects unauthorized API calls. |
| **Session Lifecycle & Logout** | `app.py` (L2294–L2306) | **Frontend + Backend** | Header/sidebar profile badge with user initials, role label, and logout button. Revokes session token in database/Redis, clears cookie, and logs action. |

---

## 2. Common Layout, Navigation & Global Controls

| Feature / UI Component | Monolithic Location | Target Service | Detailed Responsibilities & Invariants |
| :--- | :--- | :--- | :--- |
| **Dark Enterprise Sidebar** | `app.py` (L2153–L2306) | **Frontend** | Collapsible dark navigation sidebar (`#161f30`) with brand logo, section headers, active route highlighting, and dynamic notification/ticket badges. |
| **Top Header Bar & User Profile** | `app.py` (L2277–L2293) | **Frontend** | Displays active user initials avatar, role badge, store designation, and date/time status. |
| **Date Range Filter & Presets** | `app.py` (L2526–L2592) | **Frontend** | Dropdown supporting presets (`All Available Dates`, `Closing Batch`, `Week 2 Batch`, `Week 1 Batch`) and custom date picker. Updates query state and triggers TanStack Query data refetch. |
| **Batch Dataset Switcher** | `app.py` (L2310–L2366) | **Frontend + Backend** | Allows switching between `Razorpay Synthetic Batch (60 records)` and `August 25 Example (96 records)`. |
| **Real-Time Notification Feed** | `src/database.py`, `app.py` | **Frontend + Backend** | Dropdown menu displaying unread notifications with unread badge counter. Emits live updates via Socket.IO. Supports marking notifications as read. |
| **Floating AI Assistant Popover** | `app.py` (L6024–L6079) | **Frontend** | Persistent floating button (`💬 Ask AI Assistant`) present on all pages. Opens a slide-out conversational panel with quick prompts and thread restart. |

---

## 3. Merchant Portal Features (11 Views)

### 3.1 Merchant Dashboard (`dashboard`)
- **Target Services:** Frontend (UI & Charts), Backend (Data Orchestration & Caching), AI Service (Metrics Computation).
- **5 KPI Metric Cards:** Total Transactions, Reconciled Count & Match %, Active Exceptions (Needs Review), Settled to Bank (₹), Expected T+2 Settlement (₹).
- **Reconciliation Health Card:** Visual progress bar and checklist (Gateway matched, Bank statement verified, Active review count).
- **Reconciliation Trend Chart:** Stacked Plotly bar chart displaying reconciled vs. exception volume across active date range.
- **Recent Exceptions Quick Table:** Compact table of top active exceptions with severity pills and "View All" deep link.
- **Recent Settlements Quick Table:** Compact table of recent bank deposits with status badges.
- **AI Finance Insights Card:** Automated executive summary highlighting primary error drivers, financial impact, and recommended action.
- **Daily Close Workflow Status:** Card indicating batch closure eligibility (`READY TO CLOSE` vs `PENDING ACTIONS`) with operational checklist.

### 3.2 Transactions Ledger & Deep Audit (`transactions`)
- **Target Services:** Frontend (DataGrid & Audit Graph), Backend (Query & Pagination), AI Service (3-Way Verification Payload).
- **Transactions DataGrid:** Search by transaction ID / order ID, filter by status (`captured`, `refunded`, `failed`, `disputed`) and method (`card`, `upi`, `netbanking`, `wallet`), with CSV export.
- **Single-Transaction Visual 3-Way Audit:**
  - **Node 1 (Internal Orders):** Order ID, amount, order status, timestamp.
  - **Node 2 (Gateway Razorpay):** Transaction ID, payment amount, fee charged, GST charged, net settled amount.
  - **Node 3 (Bank Credit):** Date, credit status, bank UTR reference, deposited amount.
- **Mathematical Verification Card:** Step-by-step formula breakdown checking if $\text{Settled} = \text{Amount} - \text{Fee} - \text{GST}$.
- **RAG-Powered Root Cause Explanation:** Contextual explanation of discrepancies derived from indexed policy guidelines.
- **Resolution Action Button:** Allows store manager to open resolution drawer and submit corrective note.

### 3.3 Exception Investigation Queue (`exceptions`)
- **Target Services:** Frontend (3-Tab Workflow), Backend (State Machine & Sockets), AI Service (Exception Re-scoring).
- **Tab 1 — Active Exceptions:** List of unresolved exceptions filtered by severity (`HIGH`, `MEDIUM`, `LOW`) and anomaly type.
- **Tab 2 — Pending Admin Verification:** List of store-submitted resolutions awaiting administrative approval.
- **Tab 3 — Resolution History & Backup:** Historical audit log of approved and closed exceptions.
- **Store Resolution Submission Modal:** Input form for store manager to explain resolution, attach proof reference, and submit for Admin sign-off (transitions status to `PENDING_ADMIN` and dispatches notification).

### 3.4 Settlements Ledger (`settlements`)
- **Target Services:** Frontend, Backend.
- **Settlement Ledger Table:** Daily store nodal clearing records, expected settlement dates, net amounts, and gateway batch status.

### 3.5 Bank Reconciliation (`bank`)
- **Target Services:** Frontend, Backend, AI Service.
- **Bank Statement Matching Table:** Side-by-side comparison of expected daily deposits vs actual bank statement credits. Highlights `MISSING_BANK_CREDIT` and `SETTLEMENT_AMOUNT_MISMATCH`.

### 3.6 Tax & TDS Compliance Audit (`tax`)
- **Target Services:** Frontend (UI), AI Service (Section 194-O Computation).
- **Tax Summary Metrics:** Compliance score %, total audited records, GST anomalies count, TDS anomalies count.
- **Configurable TDS Table:** UI view displaying active TDS rates across recipient types (`Individual`, `Company`, `Non-Resident`).
- **Audited Tax Table:** Transaction-by-transaction tax line audit flagging under/over deductions and GST variance.

### 3.7 AI Assistant Chat Console (`insights`)
- **Target Services:** Frontend (Chat UI), Backend (Thread Persistence), AI Service (RAG & Gemini Streaming).
- **Multi-Turn Chat Console:** Generative auditor answering queries regarding settlement rules, refund policies, and transaction discrepancies.
- **RAG Source Citation Accordion:** Expandable source references displaying the exact document chunks and page numbers used to ground the answer.
- **Saved Threads Panel:** Left/right drawer listing previous conversational threads with thread creation, deletion, and auto-titling.

### 3.8 Cash Flow Forecasting (`forecast`)
- **Target Services:** Frontend (Plotly Line Chart), AI Service (7-Day Projection Algorithm).
- **7-Day Rolling Cash Table:** Daily breakdown of gross collections, refunds, payouts, fees, net inflows, and cumulative bank balance.
- **Committed vs Projected Queue Indicator:** Distinguishes between $T+1$/$T+2$ committed gateway queue and $T+3$..$T+7$ moving average projections.
- **Cumulative Treasury Chart:** Plotly line chart displaying projected treasury trajectory.

### 3.9 Reports & Exports (`reports`)
- **Target Services:** Frontend, Backend.
- **Export Center:** One-click CSV and JSON exports of reconciled ledgers, exception reports, and tax compliance audits.

### 3.10 Store Settings (`settings`)
- **Target Services:** Frontend, Backend.
- **Store Configuration:** Read-only view of active gateway fee rates, GST rates, settlement delay parameters, and store location metadata.

### 3.11 Support Helpdesk (`tickets`)
- **Target Services:** Frontend (Form & List), Backend (CRUD & Notifications).
- **Ticket Creation Form:** Submit ticket linked to a specific transaction ID, category, and priority (`Low`, `Medium`, `High`, `Urgent`).
- **Store Tickets List:** View status (`OPEN`, `PENDING`, `RESOLVED`) and administrator reply comments.

---

## 4. Platform Admin Console Features (13 Views)

### 4.1 Admin Overview Dashboard (`admin`)
- **Target Services:** Frontend (UI), Backend (Aggregation), AI Service (Platform Metrics).
- **6 KPI Metric Cards:** Total Merchants, Active Stores, Total Platform Transactions, Processing Volume (₹), Unresolved Exceptions, Open Tickets.
- **Volume Trend Dual-Line Chart:** Plotly chart comparing current period daily volume with previous period moving average.
- **Store Performance Matrix:** Tabular summary of all stores showing transaction count, match rate, volume, and open exceptions.

### 4.2 Merchants Registry (`admin_merchants`)
- **Target Services:** Frontend, Backend.
- **Merchant Management:** Register new merchants (`Flipkart`, `Amazon`), toggle active status, and view aggregate volume.

### 4.3 Stores Management (`admin_stores`)
- **Target Services:** Frontend, Backend.
- **Store Hierarchy:** Add, edit, and assign stores to merchants with location and status metadata.

### 4.4 Platform Transactions Ledger (`admin_transactions`)
- **Target Services:** Frontend, Backend.
- **Multi-Tenant Global Ledger:** Platform-wide transaction explorer with merchant and store filter dropdowns.

### 4.5 Central Exceptions Review Desk (`admin_exceptions`)
- **Target Services:** Frontend, Backend (Approval Engine), AI Service.
- **Verification Workflow:** Review merchant store submissions in `PENDING_ADMIN` status.
- **Action Buttons:**
  - **Approve Resolution:** Marks status as `RESOLVED`, updates reconciliation metrics, and dispatches notification to store.
  - **Reject Resolution:** Reopens exception and notifies store with admin notes.
  - **Direct Admin Resolve:** Resolves any exception directly without requiring store submission.

### 4.6 Central Settlements Oversight (`admin_settlements`)
- **Target Services:** Frontend, Backend.
- **Nodal Account Ledger:** Platform-level settlement overview tracking nodal account clearing to merchant bank accounts.

### 4.7 Support Ticket Center (`admin_tickets`)
- **Target Services:** Frontend, Backend.
- **Ticket Helpdesk Queue:** Filter by status, merchant, priority. Reply modal to input resolution comments and close tickets.

### 4.8 Notifications & Webhooks (`admin_notifications`)
- **Target Services:** Frontend, Backend.
- **Broadcast & Alerts:** Send system-wide announcements to merchants or targeted stores; trigger webhook events.

### 4.9 AI & RAG Operations Center (`admin_ai`)
- **Target Services:** Frontend, Backend (Config Save), AI Service (Document Embedding).
- **Gemini Configuration:** Update API key, select model (`gemini-2.0-flash`, `gemini-1.5-flash`, etc.), test live API connection.
- **Document Uploader:** Drag-and-drop PDF and Markdown policy documents; trigger automated chunking and embedding generation into pgvector.

### 4.10 Knowledge Base Document Hub (`admin_kb`)
- **Target Services:** Frontend, Backend, AI Service.
- **Vector Document Inspector:** View indexed documents, chunk counts, and preview chunk contents.

### 4.11 User Access Management (`admin_users`)
- **Target Services:** Frontend, Backend.
- **User Provisioning:** Create store and admin users, assign roles, reset passwords with Argon2id hashing.

### 4.12 Immutable Audit Trail (`admin_audit`)
- **Target Services:** Frontend, Backend.
- **Audit Logs Table:** Chronological, tamper-evident log of all system actions (logins, exception resolutions, config edits, ticket closures).

### 4.13 Platform Settings (`admin_settings`)
- **Target Services:** Frontend, Backend, AI Service.
- **System Rules Editor:** Configure global parameters (Gateway Fee %, GST %, Payout Fee, Settlement Delay $T+N$, Section 194-O TDS rates).
