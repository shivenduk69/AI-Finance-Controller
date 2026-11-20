# Flipkart (Demo) — Customer Refund Policy
> **Note:** Synthetic demo document for a portfolio project, modeled on typical Indian e-commerce refund mechanics. Not a reproduction of any real Flipkart policy text.

**Applies to:** Marketplace orders fulfilled via Flipkart (Demo) | **Effective:** 01-Apr-2026

---

## 1. Refund Trigger Events
| Event | Refund Initiated When |
|---|---|
| Customer-initiated return (approved) | Within 24 hrs of return item reaching seller/warehouse (QC pass) |
| Order cancellation (pre-shipment) | Within 24 hrs of cancellation request |
| Order cancellation (post-shipment, RTO) | Within 24 hrs of RTO delivery confirmation to warehouse |
| Non-delivery / lost in transit | Within 48 hrs of investigation closure |
| Price protection / promo adjustment | Within 72 hrs of claim approval |

## 2. Refund Processing TAT by Payment Mode
| Original Payment Mode | Refund Method | TAT (post-approval) |
|---|---|---|
| UPI | Source UPI ID | 1–2 business days |
| Credit Card | Source card | 5–7 business days |
| Debit Card | Source card | 5–7 business days |
| Net Banking | Source bank account | 3–5 business days |
| Wallet | Source wallet | Instant–1 day |
| Cash on Delivery (COD) | Bank transfer (customer-provided IFSC + account) | 7–9 business days |
| EMI | Loan account credit adjustment | 7–10 business days (bank-dependent) |

**Important for reconciliation:** the refund TAT clock starts at **QC-pass / approval timestamp**, not at the return pickup date. Agents matching refunds to orders must use `refund_approved_at`, not `return_requested_at`.

## 3. Refund Amount Rules
- Full refund: product price + tax, **shipping charge refunded only if return reason is "defective/wrong item"** (seller fault). Customer-preference returns ("didn't like it," "size issue") do not get shipping refunded.
- Partial refund / deduction applies when:
  - Item returned damaged/used beyond standard wear → deduction up to 100% at seller discretion (documented via QC report).
  - Missing accessories/box → flat deduction per category (Electronics: ₹200–₹1,500 depending on item).
- COD orders: refund excludes COD collection fee (₹0–₹49 depending on order value slab), which is non-refundable.

## 4. Refund vs. Replacement
- Categories with **replacement-only** policy (no refund unless replacement stock unavailable): Mobiles & Electronics (7-day replacement window), Large Appliances (10-day).
- Categories with **refund-only**: Perishables, Personal care, Innerwear (subject to hygiene seal).
- If replacement is chosen but stock is unavailable, system auto-converts to refund — this conversion event must be captured as a **type change**, not a new transaction, to avoid double-counting in reconciliation.

## 5. Multi-Item Order Partial Returns
- For orders with multiple line items, refund is computed **per line item**, not pro-rated across the order total. Shipping refund logic (Section 3) applies per item based on that item's return reason.
- This is a major reconciliation complexity: one `order_id` can generate 1–N refund events, each tagged to a different `order_item_id`.

## 6. Refund Failure & Re-attempt
- If refund to source fails (closed account, expired card), customer is notified and refund is re-routed to **Flipkart wallet/gift balance** by default after **3 failed attempts** or 15 days, whichever is earlier.
- These wallet-routed refunds must reconcile against a **separate internal liability ledger**, not the bank settlement file — a common source of "unresolved" exceptions in reconciliation agents built on gateway data alone.

## 7. SLA Breach Compensation
- If refund TAT is breached by >3 business days, an automatic **goodwill credit (₹50–₹200)** may be issued — this appears as an unrelated small-value transaction in the ledger and should not be matched against any order/refund pair.
