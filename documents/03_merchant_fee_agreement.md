# Merchant Fee Agreement — Flipkart Marketplace (Demo Seller Agreement)
> **Note:** Synthetic demo document for a portfolio project. Modeled on typical Indian marketplace commission structures; not a reproduction of any real Flipkart seller agreement.

**Seller:** Demo Seller Pvt. Ltd. | **Seller ID:** FSN-SLR-88213 | **Agreement Type:** Standard Marketplace | **Effective:** 01-Apr-2026

---

## 1. Commission Structure (by category)
| Category | Commission % of order value | Fixed Fee per order |
|---|---|---|
| Mobiles | 5.0% | ₹15 |
| Electronics (non-mobile) | 7.5% | ₹20 |
| Fashion & Apparel | 14.0% | ₹10 |
| Home & Kitchen | 10.0% | ₹12 |
| Beauty & Personal Care | 11.5% | ₹10 |
| Books | 8.0% | ₹5 |
| Large Appliances | 6.0% | ₹25 |

Commission is calculated on **item price after seller discount, before customer coupon/Flipkart-funded discount** — i.e., on the "seller share" of the selling price, not the MRP or final customer-paid price.

## 2. Additional Fees
| Fee Type | Rate | Notes |
|---|---|---|
| Collection Fee (COD orders) | 2.0% of order value, min ₹10 | Charged only on COD orders |
| Payment Gateway Fee (prepaid) | Per Razorpay Settlement Policy (Doc 01) | Pass-through, not a Flipkart fee |
| Shipping Fee | Weight-slab based (₹28–₹210) | Charged to seller; waived for orders >₹499 in select categories |
| Reverse Shipping Fee | 100% of forward shipping fee | Charged when return reason is customer-fault (not defective) |
| Storage Fee (FBF/warehousing) | ₹0.50/unit/day after 30 free days | Applies to Flipkart-fulfilled inventory only |
| Advertising Fee (if opted-in) | Variable (CPC/CPM billing) | Billed separately, not part of order-level settlement |

## 3. GST Treatment
- Commission + fixed fee + collection fee + shipping fee are all **subject to 18% GST**, charged by Flipkart to the seller as a tax invoice.
- Seller must self-account GST on the sale to the end customer separately (Flipkart is not the seller of record; it is the marketplace facilitator under Section 52 of the CGST Act — hence TCS is also applicable, see Section 5).

## 4. Fee Settlement Timing
- All fees for an order are **deducted at the time that order's payment is settled** (per Doc 01 settlement cycle), not at order placement or shipment.
- For COD orders, fees are deducted from the COD remittance batch (typically T+7 from delivery confirmation).
- Reverse shipping fees (for returns) are deducted in the **settlement batch following return QC completion**, which can be 15–20 days after the original order settlement — creating a lagged, order-spanning fee event.

## 5. Tax Collected at Source (TCS) — Section 52 CGST
- Flipkart, as marketplace operator, collects **1% TCS (0.5% CGST + 0.5% SGST, or 1% IGST for inter-state)** on the net taxable value of each sale, deposited against the seller's GSTIN.
- TCS is reflected in GSTR-8 filed by Flipkart and should reconcile against the seller's GSTR-2A/2B — a cross-document check the reconciliation agent should be able to flag as "requires GST-module cross-reference" if TCS data isn't in scope.

## 6. Payout Cycle to Seller
- Net payout (order value − all fees above) is transferred per the **Seller Payout Rules** (Doc 04) — weekly cycle, subject to minimum threshold and holds.

## 7. Fee Dispute Window
- Seller may raise a fee-discrepancy dispute within **45 days** of the settlement date. Disputes older than 45 days are not eligible for fee reversal, only forward adjustment.
