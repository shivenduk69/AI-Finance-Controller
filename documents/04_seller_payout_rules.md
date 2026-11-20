# Seller Payout Rules — Flipkart Marketplace (Demo)
> **Note:** Synthetic demo document for a portfolio project, modeled on typical marketplace seller-payout mechanics. Not a reproduction of any real Flipkart document.

**Seller:** Demo Seller Pvt. Ltd. | **Payout Bank Account:** ****4471 | **Effective:** 01-Apr-2026

---

## 1. Payout Cycle
- Standard sellers: **weekly payout**, batched every Monday for all orders whose payment settled with Flipkart in the prior Mon–Sun window and whose return window has closed.
- Preferred/Plus sellers: **payout every 3 business days**.
- A single payout batch = **gross order value − marketplace fees (Doc 03) − TDS (Section 3) − holds (Section 4)**.

## 2. Payout Eligibility — Return Window Hold
- Funds for an order are **not released to the seller** until the applicable return window has lapsed:
  - Standard categories: 7-day return window from delivery.
  - Mobiles/Electronics: 7 days.
  - No-return categories (perishables, innerwear): released immediately post-delivery confirmation.
- This means payout date is **delivery_date + return_window + next payout batch date**, not order date — a key lag the reconciliation agent must model to avoid flagging legitimately-pending amounts as "missing."

## 3. TDS Deduction (Section 194-O, Income Tax Act)
- Flipkart deducts **1% TDS** on the gross sale amount (excluding GST) for every seller, deposited under the seller's PAN.
- TDS certificate (Form 16A) issued quarterly; seller can reconcile deducted TDS against Form 26AS.
- TDS is deducted **at the time of payout credit**, not at order/settlement time — another timing offset from Doc 01/03 events.

## 4. Payout Holds
| Hold Reason | Duration | Resolution |
|---|---|---|
| New seller (first 30 days) | 15-day extended hold on all payouts | Auto-released after tenure threshold |
| Quality complaint rate >2% | Category-level hold | Released after QC audit clears |
| Open customer dispute/chargeback | Order-level hold until dispute resolved | Released or forfeited per dispute outcome |
| Bank account under verification | All payouts | Released once penny-drop verification succeeds |
| Negative balance (excess refunds > sales in period) | Carried forward, deducted from next payout | Auto-adjusted |

## 5. Minimum Payout Threshold
- Payouts below **₹500 net** in a cycle are carried forward and combined with the next cycle's payout (not held indefinitely — max carry-forward is 3 cycles before manual payout is triggered).

## 6. Negative Balance Handling
- If refunds/returns processed in a cycle exceed new sales, the seller's payout balance goes negative. This negative balance is **carried forward and adjusted against future payouts**, not invoiced separately — a common source of a payout batch showing a lower-than-expected net despite normal sales volume.

## 7. Payout Report Fields
Each payout batch report includes: `payout_id`, `payout_date`, `order_ids[]`, `gross_amount`, `total_commission`, `total_fees`, `tds_deducted`, `hold_adjustments`, `net_amount`, `utr`

## 8. Common Exception Patterns (for agent design)
- Order appears in sales report but not in any payout batch yet → check against return-window hold (Section 2) before flagging as missing.
- Payout UTR amount doesn't match sum of listed `order_ids` → check for negative balance carry-forward (Section 6) or TDS rounding.
- Order shows "delivered" but payout never arrives → check Section 4 hold reasons before escalating.
