import os
import pandas as pd
from datetime import datetime, timedelta

def main():
    # Resolve project root dynamically relative to this file's location
    src_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(src_dir)
    data_dir = os.path.join(base_dir, "data")
    
    razorpay_path = os.path.join(data_dir, "razorpay_synthetic_buildathon_data.csv")
    if not os.path.exists(razorpay_path):
        print(f"Error: Razorpay data not found at {razorpay_path}")
        return

    # Load Razorpay dataset
    df_rp = pd.read_csv(razorpay_path)
    
    # ----------------------------------------------------
    # GENERATING INTERNAL ORDERS
    # ----------------------------------------------------
    print("Generating internal orders...")
    orders = []
    
    for idx, row in df_rp.iterrows():
        tx_type = row['type']
        tx_id = row['transaction_id']
        order_id = row['order_id']
        status = row['status']
        amount = row['amount_inr']
        timestamp_str = row['timestamp']
        
        # We only generate internal orders for payments
        if tx_type != 'PAYMENT':
            continue
            
        # Skip generating internal orders for rows that have missing order_id in Razorpay 
        if pd.isna(order_id) or str(order_id).strip() == "" or order_id == "NaN":
            continue
            
        # Parse timestamp to calculate order creation (5 minutes prior to payment)
        try:
            dt = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M")
            order_dt = dt - timedelta(minutes=5)
            order_time_str = order_dt.strftime("%d-%m-%Y %H:%M")
        except:
            order_time_str = timestamp_str
            
        # Map statuses
        order_status = 'completed' if status in ['captured', 'disputed'] else 'failed'
        order_amount = amount
        
        # Inject Discrepancy 1: Amount Mismatch
        if order_id == 'order_70291817':
            order_amount = 4340.00
            print(f"  Injected: Amount mismatch on {order_id} (Internal: {order_amount}, Razorpay: {amount})")
            
        # Inject Discrepancy 2: Status Mismatch
        if order_id == 'order_38898923':
            order_status = 'pending'
            print(f"  Injected: Status mismatch on {order_id} (Internal: {order_status}, Razorpay: {status})")
            
        orders.append({
            'order_id': order_id,
            'amount_inr': order_amount,
            'created_at': order_time_str,
            'status': order_status,
            'customer_email': f"customer_{idx}@example.com"
        })
        
    # Inject Discrepancy 3: Internal Order with NO Payment
    orphan_order_id = 'order_99999999'
    orders.append({
        'order_id': orphan_order_id,
        'amount_inr': 1500.00,
        'created_at': '12-08-2026 14:00',
        'status': 'completed',
        'customer_email': 'orphan_cust@example.com'
    })
    print(f"  Injected: Internal order with no payment: {orphan_order_id}")
    
    df_orders = pd.DataFrame(orders)
    orders_path = os.path.join(data_dir, "internal_orders.csv")
    df_orders.to_csv(orders_path, index=False)
    print(f"Saved {len(df_orders)} internal orders to {orders_path}")
    
    # ----------------------------------------------------
    # GENERATING BANK STATEMENT
    # ----------------------------------------------------
    print("Generating bank statement settlements...")
    settlements = {}
    
    for idx, row in df_rp.iterrows():
        tx_id = row['transaction_id']
        tx_type = row['type']
        status = row['status']
        timestamp_str = row['timestamp']
        settled_amount = row['settled_amount_inr']
        
        try:
            dt = datetime.strptime(timestamp_str, "%d-%m-%Y %H:%M")
        except:
            print(f"Skipping row {idx} due to invalid timestamp: {timestamp_str}")
            continue
            
        # Compute settlement date (Payments T+2, Payouts & Refunds T+0)
        if tx_type == 'PAYMENT':
            settle_date = dt + timedelta(days=2)
        else:
            settle_date = dt
            
        settle_date_str = settle_date.strftime("%d-%m-%Y")
        
        if settle_date_str not in settlements:
            settlements[settle_date_str] = 0.0
            
        settlements[settle_date_str] += settled_amount

    # Convert to list of records
    bank_records = []
    sorted_dates = sorted(settlements.keys(), key=lambda x: datetime.strptime(x, "%d-%m-%Y"))
    
    for idx, date_str in enumerate(sorted_dates):
        net_settled = round(settlements[date_str], 2)
        
        if abs(net_settled) < 0.01:
            continue
            
        # Inject Discrepancy 4: Settlement Omission
        if date_str == '18-08-2026':
            print(f"  Injected: Omitted bank statement entry for date {date_str} (Amount: {net_settled})")
            continue
            
        # Inject Discrepancy 5: Settlement Amount Mismatch
        if date_str == '10-08-2026':
            net_settled_altered = net_settled - 100.00
            print(f"  Injected: Bank settlement amount discrepancy on {date_str} (Gateway: {net_settled}, Bank: {net_settled_altered})")
            net_settled = net_settled_altered
            
        bank_records.append({
            'date': date_str,
            'description': f"Razorpay Settlement BATCH-{idx:04d}",
            'amount_inr': net_settled,
            'bank_reference': f"REF{2026080000 + idx}"
        })
        
    df_bank = pd.DataFrame(bank_records)
    bank_path = os.path.join(data_dir, "bank_statement.csv")
    df_bank.to_csv(bank_path, index=False)
    print(f"Saved {len(df_bank)} bank statement rows to {bank_path}")
    print("Mock generation complete.")

if __name__ == '__main__':
    main()
