import os
import json
import sqlite3
import pandas as pd
import psycopg2
from app.core.config import settings

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SQLITE_FALLBACK_PATH = os.path.join(BASE_DIR, "data", "finance_controller.db")

def get_connection():
    """Connects to PostgreSQL as finance_ai_user, with SQLite fallback if PG is unreachable."""
    try:
        conn = psycopg2.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            connect_timeout=3
        )
        return conn, "postgres"
    except Exception as e:
        if os.path.exists(SQLITE_FALLBACK_PATH):
            return sqlite3.connect(SQLITE_FALLBACK_PATH), "sqlite"
        raise ConnectionError(f"Could not connect to PostgreSQL ({e}) and SQLite fallback not found.")

def load_financial_data(merchant_id=None, store_id=None):
    """Loads financial datasets from database, scoped by tenant."""
    conn, engine_type = get_connection()
    placeholder = "%s" if engine_type == "postgres" else "?"
    
    tx_q = "SELECT * FROM transactions"
    order_q = "SELECT * FROM internal_orders"
    bank_q = "SELECT * FROM bank_statements"
    params = []
    
    if merchant_id and store_id:
        tx_q += f" WHERE merchant_id = {placeholder} AND store_id = {placeholder}"
        order_q += f" WHERE merchant_id = {placeholder} AND store_id = {placeholder}"
        bank_q += f" WHERE merchant_id = {placeholder} AND store_id = {placeholder}"
        params = [merchant_id, store_id]
    elif merchant_id:
        tx_q += f" WHERE merchant_id = {placeholder}"
        order_q += f" WHERE merchant_id = {placeholder}"
        bank_q += f" WHERE merchant_id = {placeholder}"
        params = [merchant_id]
        
    try:
        if params:
            df_rp = pd.read_sql_query(tx_q, conn, params=params)
            df_orders = pd.read_sql_query(order_q, conn, params=params)
            df_bank = pd.read_sql_query(bank_q, conn, params=params)
        else:
            df_rp = pd.read_sql_query(tx_q, conn)
            df_orders = pd.read_sql_query(order_q, conn)
            df_bank = pd.read_sql_query(bank_q, conn)
    except Exception as e:
        print(f"Error loading financial records from {engine_type}: {e}")
        df_rp = pd.DataFrame(columns=[
            'transaction_id', 'order_id', 'type', 'status', 'method',
            'amount_inr', 'fee_inr', 'tax_inr', 'settled_amount_inr',
            'expected_settlement_date', 'timestamp', 'exception_flag',
            'merchant_id', 'store_id'
        ])
        df_orders = pd.DataFrame(columns=[
            'order_id', 'amount_inr', 'status', 'created_at',
            'customer_email', 'merchant_id', 'store_id'
        ])
        df_bank = pd.DataFrame(columns=[
            'date', 'amount_inr', 'bank_reference', 'merchant_id', 'store_id', 'status'
        ])
    finally:
        conn.close()
        
    return df_rp, df_orders, df_bank

def save_document_chunks(file_name: str, chunks: list):
    """Saves document text chunks and embeddings into the database, clearing previous entries."""
    conn, engine_type = get_connection()
    cursor = conn.cursor()
    placeholder = "%s" if engine_type == "postgres" else "?"
    
    try:
        if engine_type == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT,
                    chunk_index INTEGER,
                    text_content TEXT,
                    embedding TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
        cursor.execute(f"DELETE FROM document_chunks WHERE file_name = {placeholder}", (file_name,))
        
        insert_sql = (
            f"INSERT INTO document_chunks (file_name, chunk_index, text_content, embedding) "
            f"VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})"
        )
        
        for chunk in chunks:
            raw_emb = chunk.get('embedding')
            if raw_emb and len(raw_emb) > 0:
                if engine_type == "postgres":
                    emb_val = "[" + ",".join(str(float(x)) for x in raw_emb) + "]"
                else:
                    emb_val = json.dumps(raw_emb)
            else:
                emb_val = None
                
            cursor.execute(insert_sql, (
                file_name,
                int(chunk.get('chunk_index', 0)),
                str(chunk.get('text_content', '')),
                emb_val
            ))
            
        conn.commit()
    finally:
        conn.close()

def get_document_chunks():
    """Loads all document chunks and embeddings from the database."""
    conn, engine_type = get_connection()
    cursor = conn.cursor()
    chunks = []
    
    try:
        if engine_type == "postgres":
            cursor.execute("SELECT file_name, chunk_index, text_content, embedding::text FROM document_chunks ORDER BY id ASC")
        else:
            cursor.execute("SELECT file_name, chunk_index, text_content, embedding FROM document_chunks ORDER BY id ASC")
            
        for row in cursor.fetchall():
            raw_emb = row[3]
            emb = None
            if raw_emb:
                try:
                    emb = json.loads(raw_emb)
                except Exception:
                    emb = None
            chunks.append({
                'file_name': row[0],
                'chunk_index': row[1],
                'text_content': row[2],
                'embedding': emb
            })
    except Exception as e:
        print(f"Error querying document_chunks from {engine_type}: {e}")
    finally:
        conn.close()
        
    return chunks
