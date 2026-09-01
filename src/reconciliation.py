import os
import pandas as pd
from datetime import datetime, timedelta

def run_3way_reconciliation(merchant_id=None, store_id=None, gateway_fee_rate=0.02, gst_rate=0.18, payout_fee=5.0, settlement_delay_days=2):
    from src.database import load_financial_data, is_db_empty
    from src.upload_pipeline import run_pipeline
    
    # If the database is empty, auto-populate it using the ingestion pipeline
    if is_db_empty():
        run_pipeline(reset=True)
        
    # Load from SQLite / MySQL database
    df_rp, df_orders, df_bank = load_financial_data(merchant_id, store_id)
    
    # Preprocess date formats
    df_orders['created_at_dt'] = pd.to_datetime(df_orders['created_at'], format="%d-%m-%Y %H:%M", errors='coerce')
    df_rp['timestamp_dt'] = pd.to_datetime(df_rp['timestamp'], format="%d-%m-%Y %H:%M", errors='coerce')
    df_bank['date_dt'] = pd.to_datetime(df_bank['date'], format="%d-%m-%Y", errors='coerce')
    
    # We will compute the expected bank settlement date for each gateway transaction
    # Payments settle T+settlement_delay_days
    # Payouts & Refunds settle T+0 (same day)
    settlement_dates = []
    for idx, row in df_rp.iterrows():
        dt = row['timestamp_dt']
        if pd.isna(dt):
            settlement_dates.append(None)
            continue
        if row['type'] == 'PAYMENT':
            settlement_dates.append(dt + timedelta(days=int(settlement_delay_days)))
        else:
            settlement_dates.append(dt)
    df_rp['expected_settlement_dt'] = settlement_dates
    df_rp['expected_settlement_date_str'] = df_rp['expected_settlement_dt'].apply(
        lambda x: x.strftime("%d-%m-%Y") if not pd.isna(x) else ""
    )
    
    # Aggregate expected settlements by date
    expected_daily_settlement = df_rp.groupby('expected_settlement_date_str')['settled_amount_inr'].sum().reset_index()
    expected_daily_settlement.columns = ['date', 'expected_amount_inr']
    
    # Aggregate bank statement by date to handle multi-store records in a single merchant/admin view
    if not df_bank.empty:
        agg_dict = {
            'amount_inr': 'sum',
            'bank_reference': lambda x: '; '.join(filter(None, x.astype(str))) if len(x) > 0 else '',
            'date_dt': 'first'
        }
        if 'merchant_id' in df_bank.columns:
            agg_dict['merchant_id'] = 'first'
        if 'store_id' in df_bank.columns:
            agg_dict['store_id'] = 'first'
        if 'status' in df_bank.columns:
            agg_dict['status'] = lambda x: 'SETTLEMENT_AMOUNT_MISMATCH' if 'SETTLEMENT_AMOUNT_MISMATCH' in x.values else ('MISSING_BANK_CREDIT' if 'MISSING_BANK_CREDIT' in x.values else 'RECONCILED')
            
        df_bank_grouped = df_bank.groupby('date').agg(agg_dict).reset_index()
    else:
        df_bank_grouped = df_bank

    # Merge with actual bank statement
    df_bank_reconciled = pd.merge(
        expected_daily_settlement, 
        df_bank_grouped, 
        on='date', 
        how='outer'
    )
    df_bank_reconciled['expected_amount_inr'] = df_bank_reconciled['expected_amount_inr'].fillna(0.0)
    df_bank_reconciled['amount_inr'] = df_bank_reconciled['amount_inr'].fillna(0.0)
    df_bank_reconciled['difference'] = df_bank_reconciled['amount_inr'] - df_bank_reconciled['expected_amount_inr']
    
    # Classify bank settlement statuses
    bank_status = []
    bank_exceptions = []
    for idx, row in df_bank_reconciled.iterrows():
        diff = row['difference']
        date_str = row['date']
        
        # Check if actual bank record is missing
        if pd.isna(row['bank_reference']) or row['amount_inr'] == 0:
            if abs(row['expected_amount_inr']) > 0.05:
                bank_status.append("MISSING_BANK_CREDIT")
                bank_exceptions.append(f"Settlement on {date_str} of ₹{row['expected_amount_inr']:,.2f} did not hit the bank.")
            else:
                bank_status.append("RECONCILED")
        elif abs(diff) > 0.05:
            bank_status.append("SETTLEMENT_AMOUNT_MISMATCH")
            bank_exceptions.append(f"Settlement amount mismatch on {date_str}. Expected: ₹{row['expected_amount_inr']:,.2f}, Bank Credited: ₹{row['amount_inr']:,.2f} (Diff: ₹{diff:,.2f})")
        else:
            bank_status.append("RECONCILED")
            
    df_bank_reconciled['status'] = bank_status
    
    # Create dict lookup for bank settlement statuses
    bank_status_lookup = dict(zip(df_bank_reconciled['date'], df_bank_reconciled['status']))
    bank_diff_lookup = dict(zip(df_bank_reconciled['date'], df_bank_reconciled['difference']))
    
    # Duplicate transaction IDs check
    duplicate_txs = df_rp[df_rp.duplicated(subset=['transaction_id'], keep=False)]['transaction_id'].tolist()
    
    # ----------------------------------------------------
    # RECONCILING EACH GATEWAY RECORD
    # ----------------------------------------------------
    reconciled_records = []
    matched_order_ids = set()
    
    for idx, row in df_rp.iterrows():
        tx_id = row['transaction_id']
        order_id = row['order_id']
        tx_type = row['type']
        status = row['status']
        method = row['method']
        amount = row['amount_inr']
        rec_fee = row['fee_inr']
        rec_tax = row['tax_inr']
        rec_settled = row['settled_amount_inr']
        settle_date_str = row['expected_settlement_date_str']
        orig_exception = row['exception_flag']
        
        exceptions = []
        confidence = 100
        
        # Rule 1: Duplicate transaction ID
        if tx_id in duplicate_txs:
            exceptions.append("DUPLICATE_TRANSACTION_ID")
            confidence = min(confidence, 0)
            
        # Rule 2: Missing Order ID (Gateway orphan)
        if pd.isna(order_id) or str(order_id).strip() == "" or order_id == "NaN":
            exceptions.append("MISSING_ORDER_ID")
            confidence = min(confidence, 0)
            
        # Rule 3: Disputed status
        if status == 'disputed':
            exceptions.append("DISPUTED_TRANSACTION")
            confidence = min(confidence, 0)
            
        # Rule 4: Fee & Tax Calculations (Dynamic benchmark comparison)
        if tx_type == 'PAYMENT':
            if status == 'failed':
                expected_fee = round(amount * gateway_fee_rate, 2)
                expected_tax = round(expected_fee * gst_rate, 2)
            else:
                if method == 'netbanking' and abs(rec_fee) < 0.01:
                    expected_fee = 0.0
                    expected_tax = 0.0
                else:
                    expected_fee = round(amount * gateway_fee_rate, 2)
                    expected_tax = round(expected_fee * gst_rate, 2)
            
            # Tolerances
            if abs(rec_fee - expected_fee) > 0.05:
                exceptions.append(f"FEE_MISMATCH (Expected: ₹{expected_fee:.2f}, Recorded: ₹{rec_fee:.2f})")
                confidence = min(confidence, 30)
            if abs(rec_tax - expected_tax) > 0.05:
                exceptions.append(f"TAX_MISMATCH (Expected GST: ₹{expected_tax:.2f}, Recorded: ₹{rec_tax:.2f})")
                confidence = min(confidence, 30)
                
        elif tx_type == 'PAYOUT':
            expected_fee = float(payout_fee)
            expected_tax = round(expected_fee * gst_rate, 2)
            if abs(rec_fee - expected_fee) > 0.01:
                exceptions.append(f"PAYOUT_FEE_MISMATCH (Expected: ₹{expected_fee:.2f}, Recorded: ₹{rec_fee:.2f})")
                confidence = min(confidence, 30)
            if abs(rec_tax - expected_tax) > 0.01:
                exceptions.append(f"PAYOUT_TAX_MISMATCH (Expected: ₹{expected_tax:.2f}, Recorded: ₹{rec_tax:.2f})")
                confidence = min(confidence, 30)
                
        elif tx_type == 'REFUND':
            expected_fee = round(amount * gateway_fee_rate, 2)
            expected_tax = round(expected_fee * gst_rate, 2)
            if abs(rec_fee - expected_fee) > 0.05:
                exceptions.append(f"REFUND_FEE_MISMATCH (Expected: ₹{expected_fee:.2f}, Recorded: ₹{rec_fee:.2f})")
                confidence = min(confidence, 30)
            if abs(rec_tax - expected_tax) > 0.05:
                exceptions.append(f"REFUND_TAX_MISMATCH (Expected: ₹{expected_tax:.2f}, Recorded: ₹{rec_tax:.2f})")
                confidence = min(confidence, 30)
                
        # Rule 5: Math of Settled Amount
        if tx_type == 'PAYMENT':
            expected_settled = round(amount - rec_fee - rec_tax, 2)
            if abs(rec_settled - expected_settled) > 0.05:
                exceptions.append(f"SETTLED_AMOUNT_MISMATCH (Expected: ₹{expected_settled:.2f}, Recorded: ₹{rec_settled:.2f})")
                confidence = min(confidence, 10)
        elif tx_type == 'PAYOUT':
            expected_settled = round(-(amount + rec_fee + rec_tax), 2)
            if abs(rec_settled - expected_settled) > 0.05:
                exceptions.append(f"PAYOUT_SETTLED_AMOUNT_MISMATCH (Expected: ₹{expected_settled:.2f}, Recorded: ₹{rec_settled:.2f})")
                confidence = min(confidence, 10)
        elif tx_type == 'REFUND':
            expected_settled = round(-amount, 2)
            if abs(rec_settled - expected_settled) > 0.05:
                exceptions.append(f"REFUND_SETTLED_AMOUNT_MISMATCH (Expected: ₹{expected_settled:.2f}, Recorded: ₹{rec_settled:.2f})")
                confidence = min(confidence, 10)

        # Rule 6: Internal Order Lookup (for payments only)
        order_amount_match = True
        order_status_match = True
        
        if tx_type == 'PAYMENT' and "MISSING_ORDER_ID" not in exceptions:
            # Lookup order
            matched_orders = df_orders[df_orders['order_id'] == order_id]
            if len(matched_orders) == 0:
                exceptions.append("INTERNAL_ORDER_NOT_FOUND")
                confidence = min(confidence, 0)
            else:
                matched_order_ids.add(order_id)
                ord_row = matched_orders.iloc[0]
                
                # Check amount
                if abs(ord_row['amount_inr'] - amount) > 0.05:
                    exceptions.append(f"INTERNAL_AMOUNT_MISMATCH (Internal: ₹{ord_row['amount_inr']:,.2f}, Gateway: ₹{amount:,.2f})")
                    confidence = min(confidence, 30)
                    order_amount_match = False
                    
                # Check status compatibility
                expected_ord_status = 'completed' if status in ['captured', 'disputed'] else 'failed'
                if ord_row['status'] != expected_ord_status:
                    exceptions.append(f"INTERNAL_STATUS_MISMATCH (Internal: '{ord_row['status']}', Gateway expected: '{expected_ord_status}')")
                    confidence = min(confidence, 40)
                    order_status_match = False

        # Rule 7: Bank Statement Match
        if settle_date_str in bank_status_lookup:
            b_status = bank_status_lookup[settle_date_str]
            if b_status == "MISSING_BANK_CREDIT":
                exceptions.append(f"BANK_CREDIT_MISSING (Settlement batch for {settle_date_str} omitted from bank statement)")
                confidence = min(confidence, 10)
            elif b_status == "SETTLEMENT_AMOUNT_MISMATCH":
                b_diff = bank_diff_lookup[settle_date_str]
                exceptions.append(f"BANK_SETTLEMENT_MISMATCH (Bank statement is off by ₹{b_diff:,.2f} on {settle_date_str})")
                confidence = min(confidence, 20)

        # Confidence categorization
        if len(exceptions) == 0:
            res_status = "AUTO_RESOLVED"
            conf_score = 1.0
        else:
            res_status = "NEEDS_REVIEW"
            conf_score = confidence / 100.0
            
        reconciled_records.append({
            'transaction_id': tx_id,
            'order_id': order_id if not pd.isna(order_id) else "",
            'type': tx_type,
            'status': status,
            'method': method,
            'amount_inr': amount,
            'fee_inr': rec_fee,
            'tax_inr': rec_tax,
            'settled_amount_inr': rec_settled,
            'expected_settlement_date': settle_date_str,
            'calculated_exceptions': exceptions,
            'resolution_status': res_status,
            'confidence_score': conf_score,
            'orig_exception': orig_exception,
            'merchant_id': row.get('merchant_id', ''),
            'store_id': row.get('store_id', '')
        })
        
    df_reconciled_txs = pd.DataFrame(reconciled_records)
    if df_reconciled_txs.empty:
        df_reconciled_txs = pd.DataFrame(columns=[
            'transaction_id', 'order_id', 'type', 'status', 'method', 
            'amount_inr', 'fee_inr', 'tax_inr', 'settled_amount_inr', 
            'expected_settlement_date', 'calculated_exceptions', 
            'resolution_status', 'confidence_score', 'orig_exception',
            'merchant_id', 'store_id'
        ])
    
    # ----------------------------------------------------
    # FIND UNMATCHED INTERNAL ORDERS (Orphans)
    # ----------------------------------------------------
    # Completed internal orders that are not in the gateway report
    df_completed_orders = df_orders[df_orders['status'] == 'completed']
    unmatched_orders = []
    
    for idx, row in df_completed_orders.iterrows():
        o_id = row['order_id']
        if o_id not in matched_order_ids:
            unmatched_orders.append({
                'order_id': o_id,
                'amount_inr': row['amount_inr'],
                'created_at': row['created_at'],
                'status': row['status'],
                'customer_email': row['customer_email'],
                'calculated_exceptions': ["GATEWAY_PAYMENT_NOT_FOUND"],
                'resolution_status': "NEEDS_REVIEW",
                'confidence_score': 0.0,
                'merchant_id': row.get('merchant_id', ''),
                'store_id': row.get('store_id', '')
            })
    df_unmatched_orders = pd.DataFrame(unmatched_orders)
    if df_unmatched_orders.empty:
        df_unmatched_orders = pd.DataFrame(columns=[
            'order_id', 'amount_inr', 'created_at', 'status', 
            'customer_email', 'calculated_exceptions', 
            'resolution_status', 'confidence_score',
            'merchant_id', 'store_id'
        ])
    
    # ----------------------------------------------------
    # CALCULATE METRICS
    # ----------------------------------------------------
    total_tx_count = len(df_rp)
    
    # Gross collections: Captured payments
    captured_payments = df_rp[(df_rp['type'] == 'PAYMENT') & (df_rp['status'] == 'captured')]
    gross_collections = captured_payments['amount_inr'].sum()
    
    # Refunds: Refunded transactions
    refunds_df = df_rp[df_rp['type'] == 'REFUND']
    total_refunds = refunds_df['amount_inr'].sum()
    
    # Fees + GST: Sum of fee_inr + tax_inr across all transactions
    total_fees_gst = df_rp['fee_inr'].sum() + df_rp['tax_inr'].sum()
    
    # Settled to Bank: Sum of amount_inr in bank statement
    settled_to_bank = df_bank['amount_inr'].sum()
    
    # Expected in next 2 days: Payments processed on latest 2 days: 20-08-2026 and 21-08-2026 (captured)
    latest_bank_date = df_bank_reconciled[df_bank_reconciled['amount_inr'] > 0]['date_dt'].max()
    pending_settlements = df_rp[df_rp['expected_settlement_dt'] > latest_bank_date]
    expected_next_2_days = pending_settlements[pending_settlements['type'] == 'PAYMENT']['settled_amount_inr'].sum()
    
    # Exceptions lists
    needs_review_txs = df_reconciled_txs[df_reconciled_txs['resolution_status'] == 'NEEDS_REVIEW']
    auto_resolved_count = total_tx_count - len(needs_review_txs) + len(df_unmatched_orders[df_unmatched_orders['resolution_status'] == 'AUTO_RESOLVED'])
    needs_review_total = len(needs_review_txs) + len(df_unmatched_orders)
    
    auto_match_accuracy = (auto_resolved_count / (total_tx_count + len(df_unmatched_orders))) * 100
    
    summary_metrics = {
        'total_payments_processed': len(df_rp[df_rp['type'] == 'PAYMENT']),
        'total_transactions': total_tx_count,
        'auto_resolved_count': auto_resolved_count,
        'needs_review_count': needs_review_total,
        'auto_match_accuracy_pct': round(auto_match_accuracy, 1),
        'gross_collections_inr': round(gross_collections, 2),
        'refunds_inr': round(total_refunds, 2),
        'fees_gst_inr': round(total_fees_gst, 2),
        'settled_to_bank_inr': round(settled_to_bank, 2),
        'expected_next_2_days_inr': round(expected_next_2_days, 2),
        'unreconciled_review_inr': 0.0
    }
    
    return summary_metrics, df_reconciled_txs, df_unmatched_orders, df_bank_reconciled, bank_exceptions

if __name__ == '__main__':
    metrics, df_tx, df_unmatched, df_bank, bank_excs = run_3way_reconciliation()
    print("=== Reconciliation Summary Metrics ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print(f"\nTotal Exceptions: {len(df_tx[df_tx['resolution_status']=='NEEDS_REVIEW']) + len(df_unmatched)}")
    print("\nDetailed Exceptions:")
    for idx, row in df_tx[df_tx['resolution_status']=='NEEDS_REVIEW'].iterrows():
        exc_str = str(row['calculated_exceptions']).replace('₹', 'INR')
        print(f"  TX_ID={row['transaction_id']} (Order: {row['order_id']}) -> {exc_str}")
    for idx, row in df_unmatched.iterrows():
        exc_str = str(row['calculated_exceptions']).replace('₹', 'INR')
        print(f"  ORDER_ID={row['order_id']} (Internal Completed) -> {exc_str}")
    for exc in bank_excs:
        print(f"  BANK_EXC: {exc.replace('₹', 'INR')}")
