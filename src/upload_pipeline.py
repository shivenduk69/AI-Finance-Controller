import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add src to python path if run directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_connection, init_db, is_mysql_configured

load_dotenv()

def run_pipeline(reset=True):
    """Parses local CSV files, precomputes values, and uploads them to SQLite/MySQL."""
    print("=== Initializing automated data pipeline ===")
    
    # 1. Initialize database tables if they don't exist
    init_db()
    
    # 2. Get connection
    conn = get_connection()
    cursor = conn.cursor()
    
    # Paths to source CSV files
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
        
        # 3. Clear tables if resetting
        if reset:
            print("Cleaning existing database tables...")
            cursor.execute("DROP TABLE IF EXISTS transactions")
            cursor.execute("DROP TABLE IF EXISTS internal_orders")
            cursor.execute("DROP TABLE IF EXISTS bank_statements")
            cursor.execute("DROP TABLE IF EXISTS support_tickets")
            conn.commit()
            
            # Recreate tables to apply any schema updates
            init_db()
            
        # 4. Upload Transactions (Razorpay Data)
        print("Uploading transactions data...")
        df_rp['timestamp_dt'] = pd.to_datetime(df_rp['timestamp'], format="%d-%m-%Y %H:%M", errors='coerce')
        
        txs_uploaded = 0
        is_mysql = is_mysql_configured()
        
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
            
            if is_mysql:
                query = """
                INSERT INTO transactions (
                    transaction_id, order_id, type, status, method, 
                    amount_inr, fee_inr, tax_inr, settled_amount_inr, 
                    expected_settlement_date, timestamp, exception_flag
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE order_id=%s, type=%s, status=%s, method=%s, 
                                        amount_inr=%s, fee_inr=%s, tax_inr=%s, settled_amount_inr=%s, 
                                        expected_settlement_date=%s, timestamp=%s, exception_flag=%s
                """
                cursor.execute(query, (
                    row['transaction_id'], order_id, row['type'], status, method,
                    float(row['amount_inr']), float(row['fee_inr']), float(row['tax_inr']), float(row['settled_amount_inr']),
                    expected_settlement_date, row['timestamp'], row['exception_flag'],
                    order_id, row['type'], status, method,
                    float(row['amount_inr']), float(row['fee_inr']), float(row['tax_inr']), float(row['settled_amount_inr']),
                    expected_settlement_date, row['timestamp'], row['exception_flag']
                ))
            else:
                query = """
                INSERT OR REPLACE INTO transactions (
                    transaction_id, order_id, type, status, method, 
                    amount_inr, fee_inr, tax_inr, settled_amount_inr, 
                    expected_settlement_date, timestamp, exception_flag
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    row['transaction_id'], order_id, row['type'], status, method,
                    float(row['amount_inr']), float(row['fee_inr']), float(row['tax_inr']), float(row['settled_amount_inr']),
                    expected_settlement_date, row['timestamp'], row['exception_flag']
                ))
            txs_uploaded += 1
            
        # 5. Upload Internal Orders
        print("Uploading internal orders data...")
        orders_uploaded = 0
        for idx, row in df_orders.iterrows():
            customer_email = row['customer_email'] if pd.notna(row['customer_email']) else None
            status = row['status'] if pd.notna(row['status']) else None
            
            if is_mysql:
                query = """
                INSERT INTO internal_orders (order_id, amount_inr, status, created_at, customer_email)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE amount_inr=%s, status=%s, created_at=%s, customer_email=%s
                """
                cursor.execute(query, (
                    row['order_id'], float(row['amount_inr']), status, row['created_at'], customer_email,
                    float(row['amount_inr']), status, row['created_at'], customer_email
                ))
            else:
                query = """
                INSERT OR REPLACE INTO internal_orders (order_id, amount_inr, status, created_at, customer_email)
                VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(query, (
                    row['order_id'], float(row['amount_inr']), status, row['created_at'], customer_email
                ))
            orders_uploaded += 1
            
        # 6. Upload Bank Statement
        print("Uploading bank statement records...")
        bank_uploaded = 0
        for idx, row in df_bank.iterrows():
            bank_ref = row['bank_reference'] if pd.notna(row['bank_reference']) else None
            
            if is_mysql:
                query = """
                INSERT INTO bank_statements (date, amount_inr, bank_reference)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE amount_inr=%s, bank_reference=%s
                """
                cursor.execute(query, (
                    row['date'], float(row['amount_inr']), bank_ref,
                    float(row['amount_inr']), bank_ref
                ))
            else:
                query = """
                INSERT OR REPLACE INTO bank_statements (date, amount_inr, bank_reference)
                VALUES (?, ?, ?)
                """
                cursor.execute(query, (
                    row['date'], float(row['amount_inr']), bank_ref
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
