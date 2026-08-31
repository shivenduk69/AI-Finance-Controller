import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to python path if run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_connection, init_db, is_postgres_configured, is_mysql_configured

load_dotenv()

def run_pipeline(reset=True):
    """Parses local CSV files, precomputes values, and uploads them to Postgres/MySQL/SQLite."""
    print("=== Initializing automated data pipeline ===")
    
    # 1. Initialize database tables if they don't exist
    init_db()
    
    # 2. Get connection
    conn = get_connection()
    cursor = conn.cursor()
    
    # Paths to source CSV files
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Load transactions_processed.csv (combined Flipkart & Amazon data)
    rp_path = os.path.join(base_dir, "data", "transactions_processed.csv")
    # Fallback to original Razorpay synthetic data if processed CSV is missing
    if not os.path.exists(rp_path):
        rp_path = os.path.join(base_dir, "data", "razorpay_synthetic_buildathon_data.csv")
        
    orders_path = os.path.join(base_dir, "data", "internal_orders.csv")
    bank_path = os.path.join(base_dir, "data", "bank_statement.csv")
    
    if not (os.path.exists(rp_path) and os.path.exists(orders_path) and os.path.exists(bank_path)):
        print("ERROR: One or more source CSV files are missing in data/ directory!")
        conn.close()
        return False
        
    try:
        # Load CSVs
        df_rp = pd.read_csv(rp_path)
        df_orders = pd.read_csv(orders_path)
        df_bank = pd.read_csv(bank_path)
        
        is_pg = is_postgres_configured()
        is_my = is_mysql_configured()
        
        # 3. Clear tables if resetting
        if reset:
            print("Cleaning existing database tables...")
            cursor.execute("DROP TABLE IF EXISTS transactions")
            cursor.execute("DROP TABLE IF EXISTS internal_orders")
            cursor.execute("DROP TABLE IF EXISTS bank_statements")
            # Don't drop users/merchants/stores as they are seeded in init_db
            conn.commit()
            
            # Recreate tables to apply any schema updates
            init_db()
            
        # 4. Upload Transactions (Gateway Data)
        print("Uploading transactions data...")
        df_rp['timestamp_dt'] = pd.to_datetime(df_rp['timestamp'], format="%d-%m-%Y %H:%M", errors='coerce')
        
        txs_uploaded = 0
        
        for idx, row in df_rp.iterrows():
            # Precompute expected settlement date (T+2 for payments, T+0 for payouts/refunds)
            dt = row['timestamp_dt']
            if pd.isna(dt):
                expected_settlement_date = ""
            elif row['type'] == 'PAYMENT':
                expected_settlement_date = (dt + timedelta(days=2)).strftime("%d-%m-%Y")
            else:
                expected_settlement_date = dt.strftime("%d-%m-%Y")
                
            # Handle NaN values to write NULL to database
            order_id = row['order_id'] if pd.notna(row['order_id']) else None
            method = row['method'] if pd.notna(row['method']) else None
            status = row['status'] if pd.notna(row['status']) else None
            
            # Default merchant_id and store_id if not present in CSV
            m_id = row['merchant_id'] if 'merchant_id' in row and pd.notna(row['merchant_id']) else "flipkart"
            s_id = row['store_id'] if 'store_id' in row and pd.notna(row['store_id']) else "fk_delhi"
            
            if is_pg:
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
            elif is_my:
                query = """
                INSERT INTO transactions (
                    transaction_id, order_id, type, status, method, 
                    amount_inr, fee_inr, tax_inr, settled_amount_inr, 
                    expected_settlement_date, timestamp, exception_flag,
                    merchant_id, store_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    order_id=VALUES(order_id), type=VALUES(type), status=VALUES(status), method=VALUES(method),
                    amount_inr=VALUES(amount_inr), fee_inr=VALUES(fee_inr), tax_inr=VALUES(tax_inr), settled_amount_inr=VALUES(settled_amount_inr),
                    expected_settlement_date=VALUES(expected_settlement_date), timestamp=VALUES(timestamp), exception_flag=VALUES(exception_flag),
                    merchant_id=VALUES(merchant_id), store_id=VALUES(store_id)
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
            txs_uploaded += 1
            
        # 5. Upload Internal Orders
        print("Uploading internal orders data...")
        orders_uploaded = 0
        for idx, row in df_orders.iterrows():
            customer_email = row['customer_email'] if pd.notna(row['customer_email']) else None
            status = row['status'] if pd.notna(row['status']) else None
            
            m_id = row['merchant_id'] if 'merchant_id' in row and pd.notna(row['merchant_id']) else "flipkart"
            s_id = row['store_id'] if 'store_id' in row and pd.notna(row['store_id']) else "fk_delhi"
            
            if is_pg:
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
            elif is_my:
                query = """
                INSERT INTO internal_orders (order_id, amount_inr, status, created_at, customer_email, merchant_id, store_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    amount_inr=VALUES(amount_inr), status=VALUES(status), created_at=VALUES(created_at), 
                    customer_email=VALUES(customer_email), merchant_id=VALUES(merchant_id), store_id=VALUES(store_id)
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
            orders_uploaded += 1
            
        # 6. Upload Bank Statement
        print("Uploading bank statement records...")
        bank_uploaded = 0
        for idx, row in df_bank.iterrows():
            bank_ref = row['bank_reference'] if pd.notna(row['bank_reference']) else None
            
            m_id = row['merchant_id'] if 'merchant_id' in row and pd.notna(row['merchant_id']) else "flipkart"
            s_id = row['store_id'] if 'store_id' in row and pd.notna(row['store_id']) else "fk_delhi"
            status = row['status'] if 'status' in row and pd.notna(row['status']) else "RECONCILED"
            
            if is_pg:
                query = """
                INSERT INTO bank_statements (date, amount_inr, bank_reference, merchant_id, store_id, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (date, merchant_id, store_id) DO UPDATE SET 
                    amount_inr=EXCLUDED.amount_inr, bank_reference=EXCLUDED.bank_reference, status=EXCLUDED.status
                """
                cursor.execute(query, (
                    row['date'], float(row['amount_inr']), bank_ref, m_id, s_id, status
                ))
            elif is_my:
                query = """
                INSERT INTO bank_statements (date, amount_inr, bank_reference, merchant_id, store_id, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    amount_inr=VALUES(amount_inr), bank_reference=VALUES(bank_reference), status=VALUES(status)
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
            bank_uploaded += 1
            
        conn.commit()
        print("SUCCESS: Data Pipeline Completed successfully!")
        print(f"Stats: Transactions: {txs_uploaded}, Orders: {orders_uploaded}, Bank Records: {bank_uploaded}")
        return True
        
    except Exception as e:
        print(f"ERROR: Error occurred during pipeline execution: {str(e)}")
        conn.rollback()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    run_pipeline(reset=True)
