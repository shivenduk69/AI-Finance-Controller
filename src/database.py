import os
import json
import sqlite3
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Database path for SQLite
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(BASE_DIR, "data", "finance_controller.db")

def is_mysql_configured():
    """Checks if MySQL credentials are fully configured in environment variables."""
    return all(os.getenv(var) for var in ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"])

def get_connection():
    """Returns a connection object for MySQL or SQLite."""
    if is_mysql_configured():
        import mysql.connector
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST"),
            user=os.getenv("MYSQL_USER"),
            password=os.getenv("MYSQL_PASSWORD"),
            database=os.getenv("MYSQL_DATABASE")
        )
    else:
        # For SQLite, automatically create the data folder if it doesn't exist
        os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)
        return sqlite3.connect(SQLITE_PATH)

def init_db():
    """Creates tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    is_mysql = is_mysql_configured()
    
    # 1. Transactions Table
    # SQLite uses INTEGER PRIMARY KEY AUTOINCREMENT, MySQL uses INT AUTO_INCREMENT
    if is_mysql:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id VARCHAR(100) PRIMARY KEY,
            order_id VARCHAR(100),
            type VARCHAR(50),
            status VARCHAR(50),
            method VARCHAR(50),
            amount_inr DECIMAL(15, 4),
            fee_inr DECIMAL(15, 4),
            tax_inr DECIMAL(15, 4),
            settled_amount_inr DECIMAL(15, 4),
            expected_settlement_date VARCHAR(50),
            timestamp VARCHAR(50),
            exception_flag VARCHAR(50)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS internal_orders (
            order_id VARCHAR(100) PRIMARY KEY,
            amount_inr DECIMAL(15, 4),
            status VARCHAR(50),
            created_at VARCHAR(50),
            customer_email VARCHAR(255)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_statements (
            date VARCHAR(50) PRIMARY KEY,
            amount_inr DECIMAL(15, 4),
            bank_reference VARCHAR(100)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            session_id VARCHAR(100),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            role VARCHAR(50),
            content TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            file_name VARCHAR(255),
            chunk_index INT,
            text_content TEXT,
            embedding TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            ticket_id INT AUTO_INCREMENT PRIMARY KEY,
            transaction_id VARCHAR(100),
            merchant_name VARCHAR(100),
            subject VARCHAR(255),
            message TEXT,
            status VARCHAR(50) DEFAULT 'OPEN',
            resolution_comments TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
    else:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            order_id TEXT,
            type TEXT,
            status TEXT,
            method TEXT,
            amount_inr REAL,
            fee_inr REAL,
            tax_inr REAL,
            settled_amount_inr REAL,
            expected_settlement_date TEXT,
            timestamp TEXT,
            exception_flag TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS internal_orders (
            order_id TEXT PRIMARY KEY,
            amount_inr REAL,
            status TEXT,
            created_at TEXT,
            customer_email TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank_statements (
            date TEXT PRIMARY KEY,
            amount_inr REAL,
            bank_reference TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            content TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            chunk_index INTEGER,
            text_content TEXT,
            embedding TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT,
            merchant_name TEXT,
            subject TEXT,
            message TEXT,
            status TEXT DEFAULT 'OPEN',
            resolution_comments TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
    conn.commit()
    conn.close()

def is_db_empty():
    """Checks if the data tables are empty."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM transactions")
        count = cursor.fetchone()[0]
        return count == 0
    except Exception:
        return True
    finally:
        conn.close()

def load_financial_data():
    """Loads all financial data from SQL tables into Pandas DataFrames."""
    conn = get_connection()
    
    # Check if empty or tables don't exist, handle gracefully
    try:
        df_rp = pd.read_sql_query("SELECT * FROM transactions", conn)
        df_orders = pd.read_sql_query("SELECT * FROM internal_orders", conn)
        df_bank = pd.read_sql_query("SELECT * FROM bank_statements", conn)
    except Exception:
        # Fallback to empty DataFrames if database is not initialized yet
        df_rp = pd.DataFrame(columns=['transaction_id', 'order_id', 'type', 'status', 'method', 'amount_inr', 'fee_inr', 'tax_inr', 'settled_amount_inr', 'expected_settlement_date', 'timestamp'])
        df_orders = pd.DataFrame(columns=['order_id', 'amount_inr', 'status', 'created_at', 'customer_email'])
        df_bank = pd.DataFrame(columns=['date', 'amount_inr', 'bank_reference'])
    finally:
        conn.close()
        
    return df_rp, df_orders, df_bank

# --- Chat Messages Backup Functions ---

def save_chat_message(session_id, role, content):
    """Saves a single chat message into the database for history backups."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # To handle timestamp differences in standard SQL vs SQLite
    if is_mysql_configured():
        query = "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)"
        cursor.execute(query, (session_id, role, content))
    else:
        query = "INSERT INTO chat_messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)"
        cursor.execute(query, (session_id, role, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
    conn.commit()
    conn.close()

def get_chat_sessions():
    """Returns a list of unique session IDs, sorted by their last active timestamp."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get session_id, message snippet, and timestamp of first message
        cursor.execute("""
            SELECT session_id, MIN(timestamp) as start_time, 
                   (SELECT content FROM chat_messages c2 WHERE c2.session_id = c1.session_id AND c2.role = 'user' ORDER BY timestamp ASC LIMIT 1) as first_msg
            FROM chat_messages c1
            GROUP BY session_id
            ORDER BY start_time DESC
        """)
        sessions = [{'session_id': row[0], 'start_time': row[1], 'first_message': row[2] or "Empty Chat"} for row in cursor.fetchall()]
        return sessions
    except Exception:
        return []
    finally:
        conn.close()

def get_chat_history(session_id):
    """Retrieves all chat messages for a specific session."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if is_mysql_configured():
            query = "SELECT role, content, timestamp FROM chat_messages WHERE session_id = %s ORDER BY timestamp ASC"
            cursor.execute(query, (session_id,))
        else:
            query = "SELECT role, content, timestamp FROM chat_messages WHERE session_id = ? ORDER BY timestamp ASC"
            cursor.execute(query, (session_id,))
            
        history = [{'role': row[0], 'content': row[1], 'timestamp': row[2]} for row in cursor.fetchall()]
        return history
    except Exception:
        return []
    finally:
        conn.close()

# --- RAG Chunks Storage Functions ---

def save_document_chunks(file_name, chunks):
    """Saves document text chunks and embeddings into the database, clearing previous entries for the file."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Clear old chunks for this file
    if is_mysql_configured():
        cursor.execute("DELETE FROM document_chunks WHERE file_name = %s", (file_name,))
    else:
        cursor.execute("DELETE FROM document_chunks WHERE file_name = ?", (file_name,))
        
    # 2. Insert new chunks
    for chunk in chunks:
        # Embedding vector serialized to JSON string
        embedding_json = json.dumps(chunk['embedding'])
        if is_mysql_configured():
            cursor.execute(
                "INSERT INTO document_chunks (file_name, chunk_index, text_content, embedding) VALUES (%s, %s, %s, %s)",
                (file_name, chunk['chunk_index'], chunk['text_content'], embedding_json)
            )
        else:
            cursor.execute(
                "INSERT INTO document_chunks (file_name, chunk_index, text_content, embedding) VALUES (?, ?, ?, ?)",
                (file_name, chunk['chunk_index'], chunk['text_content'], embedding_json)
            )
            
    conn.commit()
    conn.close()

def get_document_chunks():
    """Loads all document chunks and their embeddings from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT file_name, chunk_index, text_content, embedding FROM document_chunks")
        chunks = []
        for row in cursor.fetchall():
            chunks.append({
                'file_name': row[0],
                'chunk_index': row[1],
                'text_content': row[2],
                'embedding': json.loads(row[3]) if row[3] else None
            })
        return chunks
    except Exception:
        return []
    finally:
        conn.close()

# --- Support Tickets / Contact Us Functions ---

def raise_support_ticket(transaction_id, merchant_name, subject, message):
    """Inserts a new support ticket in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if is_mysql_configured():
        query = """
        INSERT INTO support_tickets (transaction_id, merchant_name, subject, message, status) 
        VALUES (%s, %s, %s, %s, 'OPEN')
        """
        cursor.execute(query, (transaction_id, merchant_name, subject, message))
    else:
        query = """
        INSERT INTO support_tickets (transaction_id, merchant_name, subject, message, status, timestamp) 
        VALUES (?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query, (transaction_id, merchant_name, subject, message, 'OPEN', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
    conn.commit()
    conn.close()

def get_support_tickets(merchant_name=None):
    """Retrieves support tickets. If merchant_name is specified, returns only theirs."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        if merchant_name:
            if is_mysql_configured():
                query = "SELECT ticket_id, transaction_id, merchant_name, subject, message, status, resolution_comments, timestamp FROM support_tickets WHERE merchant_name = %s ORDER BY timestamp DESC"
                cursor.execute(query, (merchant_name,))
            else:
                query = "SELECT ticket_id, transaction_id, merchant_name, subject, message, status, resolution_comments, timestamp FROM support_tickets WHERE merchant_name = ? ORDER BY timestamp DESC"
                cursor.execute(query, (merchant_name,))
        else:
            query = "SELECT ticket_id, transaction_id, merchant_name, subject, message, status, resolution_comments, timestamp FROM support_tickets ORDER BY timestamp DESC"
            cursor.execute(query)
            
        tickets = []
        for row in cursor.fetchall():
            tickets.append({
                'ticket_id': row[0],
                'transaction_id': row[1],
                'merchant_name': row[2],
                'subject': row[3],
                'message': row[4],
                'status': row[5],
                'resolution_comments': row[6] or "No resolution response yet.",
                'timestamp': row[7]
            })
        return tickets
    except Exception:
        return []
    finally:
        conn.close()

def resolve_support_ticket(ticket_id, resolution_comments):
    """Updates ticket status to RESOLVED and saves resolution comments."""
    conn = get_connection()
    cursor = conn.cursor()
    
    if is_mysql_configured():
        query = "UPDATE support_tickets SET status = 'RESOLVED', resolution_comments = %s WHERE ticket_id = %s"
        cursor.execute(query, (resolution_comments, ticket_id))
    else:
        query = "UPDATE support_tickets SET status = 'RESOLVED', resolution_comments = ? WHERE ticket_id = ?"
        cursor.execute(query, (resolution_comments, ticket_id))
        
    conn.commit()
    conn.close()

def get_indexed_documents():
    """Returns unique indexed filenames, chunk counts, and indexing metadata from SQLite."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT file_name, COUNT(id) FROM document_chunks GROUP BY file_name")
        docs = []
        for row in cursor.fetchall():
            docs.append({
                'file_name': row[0],
                'chunks': row[1],
                'status': '✓ Indexed',
                'uploaded': '29 Aug 2026'
            })
        return docs
    except Exception:
        return []
    finally:
        conn.close()

def delete_document_chunks(file_name):
    """Deletes all vector chunks associated with the specified filename."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if is_mysql_configured():
            cursor.execute("DELETE FROM document_chunks WHERE file_name = %s", (file_name,))
        else:
            cursor.execute("DELETE FROM document_chunks WHERE file_name = ?", (file_name,))
        conn.commit()
    except Exception as e:
        print(f"Database Delete Chunks Error: {str(e)}")
    finally:
        conn.close()
