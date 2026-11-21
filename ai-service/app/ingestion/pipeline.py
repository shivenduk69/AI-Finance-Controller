import os
import pandas as pd
from datetime import datetime, timedelta
from app.core.database import get_connection

def find_data_dir():
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "data"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data"),
        os.path.join(os.getcwd(), "data"),
        "/app/data"
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]

def run_ingestion_pipeline(reset=False):
    """Parses local CSV files, precomputes settlement dates and values, and uploads them to PostgreSQL/SQLite."""
    conn, engine_type = get_connection()
    cursor = conn.cursor()
    
    data_dir = find_data_dir()
    rp_path = os.path.join(data_dir, "transactions_processed.csv")
    if not os.path.exists(rp_path):
        rp_path = os.path.join(data_dir, "razorpay_synthetic_buildathon_data.csv")
        
    orders_path = os.path.join(data_dir, "internal_orders.csv")
    bank_path = os.path.join(data_dir, "bank_statement.csv")
    
    if not (os.path.exists(rp_path) and os.path.exists(orders_path) and os.path.exists(bank_path)):
        conn.close()
        return {"success": False, "error": f"One or more CSV files missing in {data_dir}"}
        
    try:
        df_rp = pd.read_csv(rp_path)
        df_orders = pd.read_csv(orders_path)
        df_bank = pd.read_csv(bank_path)
        
        if reset:
            cursor.execute("TRUNCATE TABLE transactions, internal_orders, bank_statements CASCADE" if engine_type == "postgres" else "DELETE FROM transactions; DELETE FROM internal_orders; DELETE FROM bank_statements;")
            conn.commit()
            
        df_rp['timestamp_dt'] = pd.to_datetime(df_rp['timestamp'], format="%d-%m-%Y %H:%M", errors='coerce')
        
        txs_count = 0
        for idx, row in df_rp.iterrows():
            dt = row.get('timestamp_dt')
            if pd.isna(dt):
                expected_settlement_date = ""
            elif row.get('type') == 'PAYMENT':
                expected_settlement_date = (dt + timedelta(days=2)).strftime("%d-%m-%Y")
            else:
                expected_settlement_date = dt.strftime("%d-%m-%Y")
                
            order_id = row['order_id'] if pd.notna(row['order_id']) else None
            method = row['method'] if pd.notna(row['method']) else None
            status = row['status'] if pd.notna(row['status']) else None
            m_id = row['merchant_id'] if 'merchant_id' in row and pd.notna(row['merchant_id']) else "flipkart"
            s_id = row['store_id'] if 'store_id' in row and pd.notna(row['store_id']) else "fk_delhi"
            
            if engine_type == "postgres":
                query = """
                INSERT INTO transactions (
                    transaction_id, order_id, type, status, method, 
                    amount_inr, fee_inr, tax_inr, settled_amount_inr, 
                    expected_settlement_date, timestamp, exception_flag,
                    merchant_id, store_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (transaction_id) DO UPDATE SET 
                    order_id=EXCLUDED.order_id, type=EXCLUDED.type, status=EXCLUDED.status, method=EXCLUDED.method,
                    amount_inr=EXCLUDED.amount_inr, fee_inr=EXCLUDED.fee_inr, tax_inr=EXCLUDED.tax_inr, settled_amount_inr=EXCLUDED.settled_amount_inr,
                    expected_settlement_date=EXCLUDED.expected_settlement_date, timestamp=EXCLUDED.timestamp, exception_flag=EXCLUDED.exception_flag,
                    merchant_id=EXCLUDED.merchant_id, store_id=EXCLUDED.store_id
                """
                cursor.execute(query, (
                    row['transaction_id'], order_id, row['type'], status, method,
                    float(row['amount_inr']), float(row['fee_inr']), float(row['tax_inr']), float(row['settled_amount_inr']),
                    expected_settlement_date, row['timestamp'], row['exception_flag'],
                    m_id, s_id
                ))
            else:
                query = """
                INSERT OR REPLACE INTO transactions (
                    transaction_id, order_id, type, status, method, 
                    amount_inr, fee_inr, tax_inr, settled_amount_inr, 
                    expected_settlement_date, timestamp, exception_flag,
                    merchant_id, store_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    row['transaction_id'], order_id, row['type'], status, method,
                    float(row['amount_inr']), float(row['fee_inr']), float(row['tax_inr']), float(row['settled_amount_inr']),
                    expected_settlement_date, row['timestamp'], row['exception_flag'],
                    m_id, s_id
                ))
            txs_count += 1
            
        orders_count = 0
        for idx, row in df_orders.iterrows():
            customer_email = row['customer_email'] if pd.notna(row['customer_email']) else None
            status = row['status'] if pd.notna(row['status']) else None
            m_id = row['merchant_id'] if 'merchant_id' in row and pd.notna(row['merchant_id']) else "flipkart"
            s_id = row['store_id'] if 'store_id' in row and pd.notna(row['store_id']) else "fk_delhi"
            
            if engine_type == "postgres":
                query = """
                INSERT INTO internal_orders (order_id, amount_inr, status, created_at, customer_email, merchant_id, store_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (order_id) DO UPDATE SET 
                    amount_inr=EXCLUDED.amount_inr, status=EXCLUDED.status, created_at=EXCLUDED.created_at, 
                    customer_email=EXCLUDED.customer_email, merchant_id=EXCLUDED.merchant_id, store_id=EXCLUDED.store_id
                """
                cursor.execute(query, (
                    row['order_id'], float(row['amount_inr']), status, row['created_at'], customer_email, m_id, s_id
                ))
            else:
                query = """
                INSERT OR REPLACE INTO internal_orders (order_id, amount_inr, status, created_at, customer_email, merchant_id, store_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    row['order_id'], float(row['amount_inr']), status, row['created_at'], customer_email, m_id, s_id
                ))
            orders_count += 1
            
        bank_count = 0
        for idx, row in df_bank.iterrows():
            bank_ref = row['bank_reference'] if pd.notna(row['bank_reference']) else None
            m_id = row['merchant_id'] if 'merchant_id' in row and pd.notna(row['merchant_id']) else "flipkart"
            s_id = row['store_id'] if 'store_id' in row and pd.notna(row['store_id']) else "fk_delhi"
            status = row['status'] if 'status' in row and pd.notna(row['status']) else "RECONCILED"
            
            if engine_type == "postgres":
                query = """
                INSERT INTO bank_statements (date, amount_inr, bank_reference, merchant_id, store_id, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, merchant_id, store_id) DO UPDATE SET 
                    amount_inr=EXCLUDED.amount_inr, bank_reference=EXCLUDED.bank_reference, status=EXCLUDED.status
                """
                cursor.execute(query, (
                    row['date'], float(row['amount_inr']), bank_ref, m_id, s_id, status
                ))
            else:
                query = """
                INSERT OR REPLACE INTO bank_statements (date, amount_inr, bank_reference, merchant_id, store_id, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    row['date'], float(row['amount_inr']), bank_ref, m_id, s_id, status
                ))
            bank_count += 1
            
        conn.commit()
        return {
            "success": True,
            "transactions_ingested": txs_count,
            "orders_ingested": orders_count,
            "bank_records_ingested": bank_count
        }
    finally:
        conn.close()
