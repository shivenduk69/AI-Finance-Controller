# AI Finance Controller - System Logic & Mathematical Formulas

This document outlines the core business logic, compliance rules, and mathematical formulas utilized by the AI Finance Controller platform for audits, GST matches, and treasury forecasts.

## 1. 3-Way Reconciliation Logic
The reconciliation engine cross-references transactions across three sources:
1. **Internal Orders Ledger**: Original merchant orders (`order_id`, `amount_inr`, `status`).
2. **Razorpay Payments Gateway**: Captured fees and taxes (`transaction_id`, `amount_inr`, `fee_inr`, `tax_inr`, `settled_amount_inr`).
3. **Bank Statement Feed**: Actual cash credited to bank accounts (`bank_reference`, `amount_inr`, `date`).

### Reconciliation Flags:
- **RECONCILIATION_MATCH**: Internal Order Amount == Razorpay Amount == Bank Statement Credit Amount.
- **INTERNAL_AMOUNT_MISMATCH**: Razorpay captured amount differs from internal order amount.
- **GATEWAY_PAYMENT_NOT_FOUND**: An internal order exists but has no matching Razorpay transaction.
- **SETTLEMENT_AMOUNT_MISMATCH**: Expected bank settlement amount != Actual bank credited amount.
- **MISSING_BANK_CREDIT**: Gateway indicates settlement has completed but no bank credit is found.

## 2. Gateway Fee & GST Calculations
Razorpay applies standard transaction fees and GST charges:
- **Standard Gateway Fee**: 2.0% of the transaction amount.
  $$\text{Expected Fee} = \text{Amount} \times 0.02$$
- **GST on Gateway Charges**: 18.0% of the gateway fee.
  $$\text{Expected GST} = \text{Expected Fee} \times 0.18$$
- **Settlement Formula**:
  $$\text{Expected Settled Amount} = \text{Amount} - (\text{Expected Fee} + \text{Expected GST})$$

## 3. TDS Compliance Rules (Section 194-O)
For e-commerce marketplace sellers, TDS Withholding is calculated under Section 194-O of the Indian Income Tax Act:
- **Applicable Threshold**: ₹5,00,000 gross transaction volume per financial year for individuals (otherwise flat withholding).
- **Resident Individual Rate**: 1.0% of gross transaction volume.
- **Corporate Company Rate**: 2.0% of gross transaction volume.
- **TDS Under-deduction Flag**: Expected TDS > Actual TDS deducted.

## 4. Cash Flow & Treasury Forecasting
The system generates a 7-day forward liquidity forecast based on daily close inputs:
- **Daily Net Treasury Inflow**:
  $$\text{Net Inflow} = \text{Collections} - (\text{Refunds} + \text{Gateway Fees} + \text{TDS})$$
- **Cumulative Reserves Forecast**:
  $$\text{Reserves}_{t} = \text{Reserves}_{t-1} + \text{Net Inflow}_{t}$$
