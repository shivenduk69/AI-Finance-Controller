# Razorpay Settlement Policy — Synthetic Demo Document
> **Note:** This is a synthetic reference document created for a portfolio/demo AI Finance Controller project. It is modeled on publicly known payment-gateway settlement mechanics but does not reproduce any real Razorpay internal document. All figures are illustrative.

**Merchant:** Flipkart (Demo) | **Merchant ID (demo):** FKRT-DEMO-0001 | **Effective:** 01-Apr-2026

---

## 1. Settlement Cycle
| Merchant Tier | Standard Settlement TAT | Instant Settlement Available |
|---|---|---|
| Standard | T+2 working days | No |
| Preferred (high-volume) | T+1 working day | Yes (0.4% fee, capped ₹250/txn) |
| Enterprise (Flipkart-tier) | T+1 working day, batched daily at 11:00 IST | Yes (0.25% fee) |

- "T" = date of successful payment capture, not order date.
- Settlements are **batched by capture date**, not by order date — a payment captured at 23:55 IST may settle in the next day's batch depending on the cutoff (cutoff: 22:00 IST).
- Settlements do not occur on bank holidays or weekends; a Friday capture settles the following Monday/Tuesday.

## 2. Settlement Components (per batch)
Each settlement UTR corresponds to a **net batch amount**, calculated as:

```
Net Settlement = Gross Captured Amount
                 − Razorpay Transaction Fee (see Sec. 3)
                 − GST on Fee (18%)
                 − Refunds processed in this batch
                 − Adjustments (chargebacks, TDS, rolling reserve)
```

Because settlements are **netted, not 1:1 with orders**, a single UTR can represent 40–600 individual order captures minus refunds issued in the same window. This is the primary source of reconciliation mismatches between the payment gateway ledger and the order management system.

## 3. Transaction Fees
| Payment Mode | Fee (of transaction value) |
|---|---|
| UPI | 0% (RuPay/UPI exempt per RBI zero-MDR mandate) |
| Debit Card | 0.90% |
| Credit Card | 2.00% |
| Net Banking | 1.90% |
| Wallets | 1.95% |
| EMI / Cardless EMI | 2.30% |

GST @18% is applied on the fee amount, not on the transaction value.

## 4. Rolling Reserve
- For categories flagged "high dispute risk" (Electronics >₹50,000, Travel), Razorpay withholds a **5% rolling reserve** from each settlement.
- Reserve is released after **30 days** if no chargeback is raised, added back in a subsequent settlement batch as a separate line item — another common reconciliation break.

## 5. Failed / Delayed Settlements
- If a settlement fails (bank account validation error, IFSC mismatch), funds are held and retried in the **next 2 settlement cycles** before manual intervention is triggered.
- Failed settlement UTRs appear in the ledger with status `settlement.failed` and must not be treated as revenue until reprocessed.

## 6. Chargebacks & Disputes
- Dispute window: **120 days** from transaction date (card network rule).
- On chargeback, the disputed amount is **debited from the next settlement batch**, not from the original transaction's batch — creating a timing mismatch between order date and financial impact date.
- Merchant has **7 working days** to submit compliance documents before auto-loss.

## 7. Reconciliation Reference Fields
Every settlement record includes these fields — expected to be present in a clean payment ledger export:
`payment_id`, `order_id`, `utr`, `settlement_id`, `captured_at`, `settled_at`, `amount`, `fee`, `tax`, `settlement_status`

## 8. Common Exception Patterns (for agent design)
- Orphan payment: `payment_id` exists in gateway export, no matching `order_id` in OMS (cancelled-post-capture, or manual test order).
- Split settlement: one order's refund spans two different settlement batches.
- Currency/rounding drift: paise-level rounding differences between gateway fee calc and merchant's own fee calc.
- Reserve release mismatch: reserve released amount doesn't match original withheld amount due to partial refunds in between.
