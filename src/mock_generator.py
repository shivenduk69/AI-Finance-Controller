import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def main():
    # Resolve project root dynamically relative to this file's location
    src_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(src_dir)
    data_dir = os.path.join(base_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    # ----------------------------------------------------
    # LOAD/PROCESS FLIPKART GATEWAY DATA
    # ----------------------------------------------------
    original_rp_path = os.path.join(data_dir, "razorpay_synthetic_buildathon_data.csv")
    if not os.path.exists(original_rp_path):
        print(f"Error: Original Flipkart gateway data not found at {original_rp_path}")
        return
        
    df_fk_gateway = pd.read_csv(original_rp_path)
    
    # Map Flipkart stores: Delhi, Mumbai, Bangalore, Kolkata
    fk_stores = ["fk_delhi", "fk_mumbai", "fk_bangalore", "fk_kolkata"]
    df_fk_gateway["merchant_id"] = "flipkart"
    # Assign stores deterministically based on transaction ID digits
    df_fk_gateway["store_id"] = df_fk_gateway["transaction_id"].apply(
        lambda x: fk_stores[int(''.join(filter(str.isdigit, x))) % len(fk_stores)]
    )
    
    # ----------------------------------------------------
    # GENERATE AMAZON GATEWAY DATA
    # ----------------------------------------------------
    print("Generating Amazon gateway data...")
    amz_stores = ["az_delhi", "az_mumbai", "az_bangalore", "az_hyderabad"]
    amz_txs = []
    
    # Generate ~60 Amazon transactions mirroring the Flipkart schema
    np.random.seed(42)  # for reproducible dummy data
    
    # Dates from Aug 01 to Aug 21, 2026
    start_date = datetime(2026, 8, 1, 0, 0)
    
    for i in range(60):
        tx_id = f"pay_amz_{10000000 + i}"
        order_id = f"order_amz_{20000000 + i}"
        
        # Determine transaction type (45 payments, 8 refunds, 7 payouts)
        if i < 45:
            tx_type = "PAYMENT"
        elif i < 53:
            tx_type = "REFUND"
        else:
            tx_type = "PAYOUT"
            
        # Determine store_id
        store_id = amz_stores[i % len(amz_stores)]
        
        # Timestamps spread over August 2026
        dt = start_date + timedelta(days=(i % 21), hours=(i * 7) % 24, minutes=(i * 13) % 60)
        timestamp_str = dt.strftime("%d-%m-%Y %H:%M")
        
        # Base amounts
        amount = round(float(np.random.uniform(500, 5000)), 2)
        
        # Calculate fees and tax
        if tx_type == "PAYMENT":
            status = "captured"
            method = ["upi", "card", "netbanking", "wallet"][i % 4]
            # Default rate is 2% fee, 18% GST on fee
            fee = round(amount * 0.02, 2)
            tax = round(fee * 0.18, 2)
            settled = round(amount - fee - tax, 2)
            exc = "NO"
            
            # Inject exception 1: Fee Mismatch (charged 3% instead of 2%)
            if i == 5:
                fee = round(amount * 0.03, 2)
                tax = round(fee * 0.18, 2)
                settled = round(amount - (amount * 0.02) - (amount * 0.02 * 0.18), 2)  # Settled on 2% rules
                exc = "YES"
                print(f"  Amazon: Injected Fee Mismatch on {tx_id}")
                
            # Inject exception 2: Missing Order ID (Orphan gateway payment)
            elif i == 12:
                order_id = ""
                exc = "YES"
                print(f"  Amazon: Injected Missing Order ID on {tx_id}")
                
            # Inject exception 3: Disputed Payment
            elif i == 20:
                status = "disputed"
                exc = "YES"
                print(f"  Amazon: Injected Disputed transaction on {tx_id}")
                
            # Inject exception 4: Failed transaction (should not reconcile to completed orders)
            elif i == 25:
                status = "failed"
                settled = 0.0
                
        elif tx_type == "REFUND":
            status = "processed"
            method = "card"
            fee = 0.0
            tax = 0.0
            settled = -amount
            exc = "NO"
            
        else:  # PAYOUT
            status = "processed"
            method = "netbanking"
            fee = 5.0
            tax = 0.90
            settled = -(amount + fee + tax)
            exc = "NO"
            
        amz_txs.append({
            'transaction_id': tx_id,
            'order_id': order_id,
            'timestamp': timestamp_str,
            'type': tx_type,
            'amount_inr': amount,
            'fee_inr': fee,
            'tax_inr': tax,
            'settled_amount_inr': settled,
            'status': status,
            'method': method,
            'exception_flag': exc,
            'merchant_id': 'amazon',
            'store_id': store_id
        })
        
    df_amz_gateway = pd.DataFrame(amz_txs)
    
    # Combined Gateway data
    df_combined_gateway = pd.concat([df_fk_gateway, df_amz_gateway], ignore_index=True)
    df_combined_gateway.to_csv(os.path.join(data_dir, "transactions_processed.csv"), index=False)
    print(f"Saved {len(df_combined_gateway)} combined transactions to transactions_processed.csv")
    
    # ----------------------------------------------------
    # GENERATING INTERNAL ORDERS
    # ----------------------------------------------------
    print("Generating internal orders...")
    orders = []
    
    # 1. Generate orders for Flipkart
    for idx, row in df_fk_gateway.iterrows():
        if row['type'] != 'PAYMENT':
            continue
        order_id = row['order_id']
        if pd.isna(order_id) or str(order_id).strip() == "" or order_id == "NaN":
            continue
            
        # Parse timestamp to calculate order creation
        try:
            dt = datetime.strptime(row['timestamp'], "%d-%m-%Y %H:%M")
            order_dt = dt - timedelta(minutes=5)
            order_time_str = order_dt.strftime("%d-%m-%Y %H:%M")
        except:
            order_time_str = row['timestamp']
            
        order_status = 'completed' if row['status'] in ['captured', 'disputed'] else 'failed'
        order_amount = row['amount_inr']
        
        # Inject Flipkart exceptions (keep legacy mismatches)
        if order_id == 'order_70291817':
            order_amount = 4340.00
        if order_id == 'order_38898923':
            order_status = 'pending'
            
        orders.append({
            'order_id': order_id,
            'amount_inr': order_amount,
            'created_at': order_time_str,
            'status': order_status,
            'customer_email': f"fk_customer_{idx}@example.com",
            'merchant_id': 'flipkart',
            'store_id': row['store_id']
        })
        
    # Inject Flipkart legacy orphan internal order
    orders.append({
        'order_id': 'order_99999999',
        'amount_inr': 1500.00,
        'created_at': '12-08-2026 14:00',
        'status': 'completed',
        'customer_email': 'orphan_cust@example.com',
        'merchant_id': 'flipkart',
        'store_id': 'fk_delhi'
    })
    
    # 2. Generate orders for Amazon
    for idx, row in df_amz_gateway.iterrows():
        if row['type'] != 'PAYMENT':
            continue
        order_id = row['order_id']
        if pd.isna(order_id) or str(order_id).strip() == "" or order_id == "NaN":
            continue
            
        try:
            dt = datetime.strptime(row['timestamp'], "%d-%m-%Y %H:%M")
            order_dt = dt - timedelta(minutes=5)
            order_time_str = order_dt.strftime("%d-%m-%Y %H:%M")
        except:
            order_time_str = row['timestamp']
            
        order_status = 'completed' if row['status'] in ['captured', 'disputed'] else 'failed'
        order_amount = row['amount_inr']
        
        # Inject Amazon exceptions:
        # 1. Amount mismatch on order_amz_20000010 (captures ₹200 more on gateway)
        if order_id == 'order_amz_20000010':
            order_amount = round(row['amount_inr'] - 200.00, 2)
            print(f"  Amazon: Injected Amount Mismatch on order {order_id}")
            
        # 2. Status mismatch on order_amz_20000018 (Internal order pending, gateway captured)
        if order_id == 'order_amz_20000018':
            order_status = 'pending'
            print(f"  Amazon: Injected Status Mismatch on order {order_id}")
            
        orders.append({
            'order_id': order_id,
            'amount_inr': order_amount,
            'created_at': order_time_str,
            'status': order_status,
            'customer_email': f"amz_customer_{idx}@example.com",
            'merchant_id': 'amazon',
            'store_id': row['store_id']
        })
        
    # Inject Amazon orphan order (Completed internally, no payment capture)
    orders.append({
        'order_id': 'order_amz_99999999',
        'amount_inr': 2400.00,
        'created_at': '15-08-2026 10:00',
        'status': 'completed',
        'customer_email': 'amz_orphan@example.com',
        'merchant_id': 'amazon',
        'store_id': 'az_delhi'
    })
    
    df_orders = pd.DataFrame(orders)
    orders_path = os.path.join(data_dir, "internal_orders.csv")
    df_orders.to_csv(orders_path, index=False)
    print(f"Saved {len(df_orders)} internal orders to {orders_path}")
    
    # ----------------------------------------------------
    # GENERATING BANK STATEMENTS
    # ----------------------------------------------------
    print("Generating bank statements...")
    bank_records = []
    
    # Aggregator for settlements
    # We aggregate settlements daily per merchant and store!
    settlement_agg = {}
    
    for df_gateway, merchant_name in [(df_fk_gateway, 'flipkart'), (df_amz_gateway, 'amazon')]:
        for idx, row in df_gateway.iterrows():
            tx_type = row['type']
            settled_amount = row['settled_amount_inr']
            store_id = row['store_id']
            
            try:
                dt = datetime.strptime(row['timestamp'], "%d-%m-%Y %H:%M")
            except:
                continue
                
            # Expected settlement date: Payments T+2, payouts/refunds T+0
            if tx_type == "PAYMENT":
                settle_date = dt + timedelta(days=2)
            else:
                settle_date = dt
                
            settle_date_str = settle_date.strftime("%d-%m-%Y")
            
            key = (settle_date_str, merchant_name, store_id)
            if key not in settlement_agg:
                settlement_agg[key] = 0.0
            settlement_agg[key] += settled_amount

    # Convert aggregated values into bank statement list
    sorted_keys = sorted(settlement_agg.keys(), key=lambda x: datetime.strptime(x[0], "%d-%m-%Y"))
    
    # We maintain index counters per store to generate realistic batch descriptions
    batch_indices = {}
    
    for date_str, m_id, s_id in sorted_keys:
        net_settled = round(settlement_agg[(date_str, m_id, s_id)], 2)
        if abs(net_settled) < 0.01:
            continue
            
        store_key = f"{m_id}_{s_id}"
        batch_indices[store_key] = batch_indices.get(store_key, 0) + 1
        b_idx = batch_indices[store_key]
        
        status = "RECONCILED"
        
        # Inject bank statement discrepancies:
        # Flipkart:
        # 1. Settlement omission (August 18, 2026) merchant-wide
        if m_id == 'flipkart' and date_str == '18-08-2026':
            print(f"  Flipkart {s_id}: Injected omitted settlement credit for {date_str} (INR {net_settled})")
            continue
            
        # 2. Settlement mismatch (August 10, 2026) on Delhi Store (-INR 100)
        if m_id == 'flipkart' and s_id == 'fk_delhi' and date_str == '10-08-2026':
            print(f"  Flipkart Delhi: Injected bank mismatch on {date_str} (Diff -INR 100)")
            net_settled = round(net_settled - 100.00, 2)
            status = "SETTLEMENT_AMOUNT_MISMATCH"
            
        # Amazon:
        # 1. Settlement omission (August 18, 2026) merchant-wide
        if m_id == 'amazon' and date_str == '18-08-2026':
            print(f"  Amazon {s_id}: Injected omitted settlement credit for {date_str} (INR {net_settled})")
            continue
            
        # 2. Settlement mismatch (August 10, 2026) on Delhi Store (-INR 150)
        if m_id == 'amazon' and s_id == 'az_delhi' and date_str == '10-08-2026':
            print(f"  Amazon Delhi: Injected bank mismatch on {date_str} (Diff -INR 150)")
            net_settled = round(net_settled - 150.00, 2)
            status = "SETTLEMENT_AMOUNT_MISMATCH"
            
        bank_records.append({
            'date': date_str,
            'description': f"Razorpay Settlement {m_id.upper()}-{s_id.upper()}-B{b_idx:03d}",
            'amount_inr': net_settled,
            'bank_reference': f"REF{m_id[:2].upper()}{s_id[-2:].upper()}{20260800 + b_idx}",
            'merchant_id': m_id,
            'store_id': s_id,
            'status': status
        })
        
    df_bank = pd.DataFrame(bank_records)
    bank_path = os.path.join(data_dir, "bank_statement.csv")
    df_bank.to_csv(bank_path, index=False)
    print(f"Saved {len(df_bank)} bank statement records to {bank_path}")

if __name__ == "__main__":
    main()
