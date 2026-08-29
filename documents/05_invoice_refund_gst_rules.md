# Invoice & Credit Note (GST) Rules — Flipkart Marketplace (Demo)
> **Note:** Synthetic demo document for a portfolio project, modeled on standard Indian GST invoicing requirements (CGST Act, 2017 and related rules) as applied to marketplace e-commerce. Not a reproduction of any real Flipkart or Razorpay document.

**Effective:** 01-Apr-2026

---

## 1. Tax Invoice Requirements
Every order must generate a **tax invoice** at the time of shipment (not order placement), containing:
- Invoice number (unique, sequential, per GSTIN, per financial year)
- Seller GSTIN, buyer GSTIN (if B2B) or "unregistered" (B2C)
- HSN/SAC code per line item
- Taxable value, GST rate, CGST+SGST (intra-state) or IGST (inter-state) split
- Place of supply (determines intra vs inter-state tax split)
- Invoice date, order ID, shipment ID

## 2. Invoice Numbering Format
`FSN/<Seller Code>/<FY>/<Sequential Number>` — e.g., `FSN/SLR88213/2526/000451`
- Numbering must be **sequential without gaps** per GST rules; a cancelled/failed order does **not** consume an invoice number (invoice is generated only post-shipment, not post-order).
- This means `order_id` and `invoice_number` sequences will **not align 1:1** — reconciliation agents should not assume monotonic correspondence.

## 3. GST Rate Application
| Category | GST Rate |
|---|---|
| Mobiles | 18% |
| Fashion/Apparel (≤₹1,000) | 5% |
| Fashion/Apparel (>₹1,000) | 12% |
| Electronics (general) | 18% |
| Books | 0% (exempt) |
| Footwear (≤₹1,000) | 5% |
| Footwear (>₹1,000) | 18% |

- GST is computed on **taxable value = selling price − seller discount**, before TCS.
- E-invoicing (IRN generation via IRP) is mandatory for sellers with aggregate turnover > ₹5 crore — invoices from such sellers carry an additional `irn` and `qr_code` field.

## 4. Credit Notes (Refunds/Returns)
- A **credit note**, not a reversed invoice, is issued against the original tax invoice when a return/refund is processed.
- Credit note must reference the **original invoice number** and be issued within the GST-prescribed window: **by 30th November of the following financial year**, or before filing the annual return, whichever is earlier — far longer than the customer-facing refund TAT (Doc 02), but the customer-facing refund happens immediately while the credit note may be batch-generated later.
- Credit note reduces the seller's output tax liability in the GST return of the period it's issued in, **not** the period of the original sale.

## 5. Partial Return / Partial Credit Note
- For partial line-item returns (see Doc 02, Section 5), a credit note is issued only for the **returned portion's taxable value + proportional tax**, not the full invoice.
- One invoice can have **multiple credit notes** issued against it over time (multiple partial returns) — reconciliation must support one-to-many invoice-to-credit-note mapping.

## 6. Cancellation vs. Return — Documentary Difference
| Event | Document Generated |
|---|---|
| Cancelled before shipment | No invoice, no credit note (order simply voided) |
| Cancelled after shipment, before delivery (RTO) | Invoice generated, credit note issued on RTO receipt confirmation |
| Returned after delivery | Invoice generated, credit note issued on return QC pass |

## 7. B2B Invoice Handling
- If buyer provides GSTIN at checkout, invoice is flagged B2B; input tax credit (ITC) implications differ, and such invoices must be reported in **GSTR-1 Table 4B** by the seller, vs. Table 7 (B2C small) for retail buyers.
- The reconciliation agent should treat B2B vs. B2C orders as separate matching cohorts if cross-referencing against any GST return data.

## 8. Common Exception Patterns (for agent design)
- Refund processed (per Doc 02) but no corresponding credit note found within expected window → flag as "credit note pending," not "unresolved," given the longer GST-legal window in Section 4.
- Invoice number gap in sequence → verify against cancelled-pre-shipment orders (Section 1) before flagging as a data-integrity issue.
- Credit note amount ≠ refund amount paid to customer → check for non-refundable shipping/COD fee deductions (Doc 02, Section 3) which reduce the customer refund but not necessarily the GST-taxable credit note value proportionally.
