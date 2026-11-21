#!/usr/bin/env python3
"""
AI Finance Controller — Data Ingestion & Seeding Script (02_import_csv.py)
Reads existing CSV datasets from data/ and populates PostgreSQL tables:
- transactions (Razorpay gateway records)
- internal_orders (Merchant order ledger)
- bank_statements (Nodal settlement records)
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

# Load environment variables
infra_env = os.path.join(BASE_DIR, "infrastructure", ".env")
if os.path.exists(infra_env):
    load_dotenv(infra_env)
else:
    load_dotenv()

def get_pg_connection():
    import psycopg2
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5434"))
    db = os.getenv("POSTGRES_DB", "finance_controller")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres_secure_root_password")
    
    print(f"Connecting to PostgreSQL at {host}:{port}/{db} as {user}...")
    return psycopg2.connect(
        host=host,
        port=port,
        dbname=db,
        user=user,
        password=password
    )

def import_csv_data():
    conn = get_pg_connection()
    cursor = conn.cursor()
    
    data_dir = os.path.join(BASE_DIR, "data")
    rp_path = os.path.join(data_dir, "transactions_processed.csv")
    if not os.path.exists(rp_path):
        rp_path = os.path.join(data_dir, "razorpay_synthetic_buildathon_data.csv")
        
    orders_path = os.path.join(data_dir, "internal_orders.csv")
    bank_path = os.path.join(data_dir, "bank_statement.csv")
    
    print(f"Reading CSV datasets from: {data_dir}")
    df_rp = pd.read_csv(rp_path)
    df_orders = pd.read_csv(orders_path)
    df_bank = pd.read_csv(bank_path)
    
    # 1. Ingest Internal Orders
    print(f"Ingesting {len(df_orders)} internal orders...")
    for _, row in df_orders.iterrows():
        m_id = row['merchant_id'] if 'merchant_id' in row and pd.notna(row['merchant_id']) else "flipkart"
        s_id = row['store_id'] if 'store_id' in row and pd.notna(row['store_id']) else "fk_delhi"
        c_email = row['customer_email'] if 'customer_email' in row and pd.notna(row['customer_email']) else "customer@demo.com"
        
        cursor.execute("""
            INSERT INTO internal_orders (order_id, amount_inr, status, created_at, customer_email, merchant_id, store_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (order_id) DO UPDATE SET
                amount_inr = EXCLUDED.amount_inr,
                status = EXCLUDED.status,
                created_at = EXCLUDED.created_at,
                customer_email = EXCLUDED.customer_email,
                merchant_id = EXCLUDED.merchant_id,
                store_id = EXCLUDED.store_id;
        """, (str(row['order_id']), float(row['amount_inr']), str(row['status']), str(row['created_at']), str(c_email), str(m_id), str(s_id)))
    conn.commit()
    print("✓ Internal orders ingested successfully.")
    
    # 2. Ingest Gateway Transactions
    print(f"Ingesting {len(df_rp)} gateway transactions...")
    df_rp['timestamp_dt'] = pd.to_datetime(df_rp['timestamp'], format="%d-%m-%Y %H:%M", errors='coerce')
    
    for _, row in df_rp.iterrows():
        dt = row['timestamp_dt']
        if pd.isna(dt):
            expected_settlement_date = ""
        elif row['type'] == 'PAYMENT':
            expected_settlement_date = (dt + timedelta(days=2)).strftime("%d-%m-%Y")
        else:
            expected_settlement_date = dt.strftime("%d-%m-%Y")
            
        order_id = str(row['order_id']) if pd.notna(row['order_id']) else None
        method = str(row['method']) if pd.notna(row['method']) else "card"
        status = str(row['status']) if pd.notna(row['status']) else "captured"
        m_id = row['merchant_id'] if 'merchant_id' in row and pd.notna(row['merchant_id']) else "flipkart"
        s_id = row['store_id'] if 'store_id' in row and pd.notna(row['store_id']) else "fk_delhi"
        exc_flag = str(row['exception_flag']) if 'exception_flag' in row and pd.notna(row['exception_flag']) else "NO"
        
        cursor.execute("""
            INSERT INTO transactions (
                transaction_id, order_id, type, status, method,
                amount_inr, fee_inr, tax_inr, settled_amount_inr,
                expected_settlement_date, timestamp, exception_flag,
                merchant_id, store_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (transaction_id) DO UPDATE SET
                order_id = EXCLUDED.order_id,
                type = EXCLUDED.type,
                status = EXCLUDED.status,
                method = EXCLUDED.method,
                amount_inr = EXCLUDED.amount_inr,
                fee_inr = EXCLUDED.fee_inr,
                tax_inr = EXCLUDED.tax_inr,
                settled_amount_inr = EXCLUDED.settled_amount_inr,
                expected_settlement_date = EXCLUDED.expected_settlement_date,
                timestamp = EXCLUDED.timestamp,
                exception_flag = EXCLUDED.exception_flag,
                merchant_id = EXCLUDED.merchant_id,
                store_id = EXCLUDED.store_id;
        """, (
            str(row['transaction_id']), order_id, str(row['type']), status, method,
            float(row['amount_inr']), float(row['fee_inr']), float(row['tax_inr']), float(row['settled_amount_inr']),
            expected_settlement_date, str(row['timestamp']), exc_flag, str(m_id), str(s_id)
        ))
    conn.commit()
    print("✓ Gateway transactions ingested successfully.")
    
    # 3. Ingest Bank Statements
    print(f"Ingesting {len(df_bank)} bank statement records...")
    for _, row in df_bank.iterrows():
        m_id = row['merchant_id'] if 'merchant_id' in row and pd.notna(row['merchant_id']) else "flipkart"
        s_id = row['store_id'] if 'store_id' in row and pd.notna(row['store_id']) else "fk_delhi"
        b_ref = str(row['bank_reference']) if pd.notna(row['bank_reference']) else ""
        b_status = str(row['status']) if 'status' in row and pd.notna(row['status']) else "RECONCILED"
        
        cursor.execute("""
            INSERT INTO bank_statements (date, amount_inr, bank_reference, merchant_id, store_id, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, merchant_id, store_id) DO UPDATE SET
                amount_inr = EXCLUDED.amount_inr,
                bank_reference = EXCLUDED.bank_reference,
                status = EXCLUDED.status;
        """, (str(row['date']), float(row['amount_inr']), b_ref, str(m_id), str(s_id), b_status))
    conn.commit()
    print("✓ Bank statements ingested successfully.")
    
    cursor.close()
    conn.close()
    print("=== All CSV datasets imported into PostgreSQL successfully ===")

if __name__ == "__main__":
    import_csv_data()
