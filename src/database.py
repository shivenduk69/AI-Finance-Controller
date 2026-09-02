import os
import json
import sqlite3
import pandas as pd
import hashlib
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Database path for SQLite
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQLITE_PATH = os.path.join(BASE_DIR, "data", "finance_controller.db")

def get_postgres_uri():
    """Checks if PostgreSQL is configured in environment variables."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("DB_HOST")
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    database = os.getenv("DB_NAME")
    port = os.getenv("DB_PORT", "5432")
    if host and user and database:
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return None

def is_postgres_configured():
    return get_postgres_uri() is not None

def is_mysql_configured():
    """Checks if MySQL credentials are fully configured in environment variables."""
    return all(os.getenv(var) for var in ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"])

def get_connection():
    """Returns a connection object for PostgreSQL, MySQL, or SQLite."""
    postgres_uri = get_postgres_uri()
    if postgres_uri:
        import psycopg2
        return psycopg2.connect(postgres_uri)
    elif is_mysql_configured():
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

def hash_password(password, salt=None):
    """Hashes a password with SHA-256 and a random salt."""
    if not salt:
        salt = uuid.uuid4().hex
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{pwd_hash}"

def verify_password(stored_password, password):
    """Verifies a password against its stored hash."""
    if not stored_password:
        return False
    if ":" not in stored_password:
        # Support plain text fallback
        return stored_password == password
    salt, pwd_hash = stored_password.split(":")
    return pwd_hash == hashlib.sha256((password + salt).encode()).hexdigest()

def init_db():
    """Creates database tables if they do not exist and seeds initial data."""
    conn = get_connection()
    cursor = conn.cursor()
    
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    
    # helper mapping for autoincrement PK
    pk_auto = "SERIAL PRIMARY KEY" if is_pg else ("INT AUTO_INCREMENT PRIMARY KEY" if is_my else "INTEGER PRIMARY KEY AUTOINCREMENT")
    text_type = "TEXT" if not is_my else "VARCHAR(255)"
    long_text = "TEXT"
    dec_type = "DECIMAL(15, 4)" if (is_pg or is_my) else "REAL"
    ts_default = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP" if (is_pg or is_my) else "DATETIME DEFAULT CURRENT_TIMESTAMP"
    
    # 1. Merchants Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS merchants (
        merchant_id VARCHAR(100) PRIMARY KEY,
        name VARCHAR(255) UNIQUE,
        status VARCHAR(50),
        created_at {ts_default}
    )
    """)
    
    # 2. Stores Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS stores (
        store_id VARCHAR(100) PRIMARY KEY,
        merchant_id VARCHAR(100),
        name VARCHAR(255),
        location VARCHAR(255),
        status VARCHAR(50),
        created_at {ts_default}
    )
    """)
    
    # 3. Users Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS users (
        user_id VARCHAR(100) PRIMARY KEY,
        email VARCHAR(255) UNIQUE,
        password_hash VARCHAR(255),
        role VARCHAR(50),
        merchant_id VARCHAR(100),
        store_id VARCHAR(100),
        created_at {ts_default}
    )
    """)
    
    # 4. Transactions Table (Gateway records)
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id VARCHAR(100) PRIMARY KEY,
        order_id VARCHAR(100),
        type VARCHAR(50),
        status VARCHAR(50),
        method VARCHAR(50),
        amount_inr {dec_type},
        fee_inr {dec_type},
        tax_inr {dec_type},
        settled_amount_inr {dec_type},
        expected_settlement_date VARCHAR(50),
        timestamp VARCHAR(50),
        exception_flag VARCHAR(50),
        merchant_id VARCHAR(100),
        store_id VARCHAR(100)
    )
    """)
    
    # 5. Internal Orders Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS internal_orders (
        order_id VARCHAR(100) PRIMARY KEY,
        amount_inr {dec_type},
        status VARCHAR(50),
        created_at VARCHAR(50),
        customer_email VARCHAR(255),
        merchant_id VARCHAR(100),
        store_id VARCHAR(100)
    )
    """)
    
    # 6. Bank Statements Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS bank_statements (
        date VARCHAR(50),
        amount_inr {dec_type},
        bank_reference VARCHAR(100),
        merchant_id VARCHAR(100),
        store_id VARCHAR(100),
        status VARCHAR(50),
        PRIMARY KEY (date, merchant_id, store_id)
    )
    """)
    
    # 7. Document Chunks Table (RAG Chunks)
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS document_chunks (
        id {pk_auto},
        file_name VARCHAR(255),
        chunk_index INT,
        text_content {long_text},
        embedding {long_text}
    )
    """)
    
    # 8. Support Tickets Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS support_tickets (
        ticket_id {pk_auto},
        transaction_id VARCHAR(100),
        merchant_name VARCHAR(100),
        subject VARCHAR(255),
        message {long_text},
        status VARCHAR(50) DEFAULT 'OPEN',
        resolution_comments {long_text},
        timestamp {ts_default},
        merchant_id VARCHAR(100),
        store_id VARCHAR(100),
        user_id VARCHAR(100),
        category VARCHAR(100),
        priority VARCHAR(50)
    )
    """)
    
    # Migrate support_tickets table if columns are missing from legacy DB
    try:
        cursor.execute("SELECT * FROM support_tickets LIMIT 1")
        col_names = [desc[0].lower() for desc in cursor.description]
        missing_cols = {
            'merchant_id': 'VARCHAR(100)',
            'store_id': 'VARCHAR(100)',
            'user_id': 'VARCHAR(100)',
            'category': 'VARCHAR(100)',
            'priority': 'VARCHAR(50)'
        }
        for col, col_type in missing_cols.items():
            if col not in col_names:
                cursor.execute(f"ALTER TABLE support_tickets ADD COLUMN {col} {col_type}")
    except Exception as e:
        print(f"Migration error for support_tickets: {e}")
    
    # 9. Persistent AI Conversations Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS ai_conversations (
        conversation_id VARCHAR(100) PRIMARY KEY,
        user_id VARCHAR(100),
        merchant_id VARCHAR(100),
        store_id VARCHAR(100),
        title VARCHAR(255),
        created_at {ts_default}
    )
    """)
    
    # 10. Persistent AI Conversation Messages Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS ai_messages (
        message_id {pk_auto},
        conversation_id VARCHAR(100),
        role VARCHAR(50),
        content {long_text},
        sources {long_text},
        timestamp {ts_default}
    )
    """)
    
    # 11. Notifications Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS notifications (
        notification_id {pk_auto},
        user_id VARCHAR(100),
        merchant_id VARCHAR(100),
        store_id VARCHAR(100),
        role VARCHAR(50),
        title VARCHAR(255),
        message {long_text},
        is_read INT DEFAULT 0,
        created_at {ts_default}
    )
    """)
    
    # 12. Audit Logs Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id {pk_auto},
        user_id VARCHAR(100),
        action VARCHAR(255),
        details {long_text},
        timestamp {ts_default}
    )
    """)
    
    # 13. System Configuration Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS configuration (
        config_key VARCHAR(100) PRIMARY KEY,
        config_value {long_text}
    )
    """)
    
    # 14. Persistent User Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_sessions (
        session_token VARCHAR(100) PRIMARY KEY,
        user_id VARCHAR(100),
        expires_at INT
    )
    """)
    
    # 15. Exception Resolutions & Audit Archive Table
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS exception_resolutions (
        resolution_id {pk_auto},
        transaction_id VARCHAR(100),
        order_id VARCHAR(100),
        merchant_id VARCHAR(100),
        store_id VARCHAR(100),
        amount_inr {dec_type},
        issue_description {long_text},
        resolution_note {long_text},
        resolved_by_role VARCHAR(50),
        resolved_by_user VARCHAR(100),
        status VARCHAR(50) DEFAULT 'RESOLVED',
        created_at {ts_default}
    )
    """)
    
    # Create performance indexes on frequently queried columns
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_merchant_store ON transactions (merchant_id, store_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_order ON transactions (order_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tx_status ON transactions (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_merchant_store ON internal_orders (merchant_id, store_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON internal_orders (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bank_date ON bank_statements (date, merchant_id, store_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets (status, merchant_id, store_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifs_role ON notifications (role, merchant_id, store_id, is_read)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exc_res_status ON exception_resolutions (status, merchant_id, store_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_doc_chunks_file ON document_chunks (file_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_msgs_conv ON ai_messages (conversation_id)")
    except Exception as e:
        print(f"Index creation notice: {e}")
        
    conn.commit()
    
    # --- SEEDING PREDEFINED DATA ---
    # We check if seeded merchants exist, if not we populate them.
    cursor.execute("SELECT COUNT(*) FROM merchants")
    if cursor.fetchone()[0] == 0:
        print("Seeding database merchants, stores, and users...")
        
        # Seed Merchants
        merchants_seed = [
            ("flipkart", "Flipkart", "ACTIVE"),
            ("amazon", "Amazon", "ACTIVE")
        ]
        for m_id, m_name, m_status in merchants_seed:
            cursor.execute("INSERT INTO merchants (merchant_id, name, status) VALUES (%s, %s, %s)" if (is_pg or is_my) else "INSERT INTO merchants (merchant_id, name, status) VALUES (?, ?, ?)", (m_id, m_name, m_status))
            
        # Seed Stores
        stores_seed = [
            # Flipkart stores
            ("fk_delhi", "flipkart", "Delhi Store", "Delhi, IN", "ACTIVE"),
            ("fk_mumbai", "flipkart", "Mumbai Store", "Mumbai, IN", "ACTIVE"),
            ("fk_bangalore", "flipkart", "Bangalore Store", "Bangalore, IN", "ACTIVE"),
            ("fk_kolkata", "flipkart", "Kolkata Store", "Kolkata, IN", "ACTIVE"),
            # Amazon stores
            ("az_delhi", "amazon", "Delhi Store", "Delhi, IN", "ACTIVE"),
            ("az_mumbai", "amazon", "Mumbai Store", "Mumbai, IN", "ACTIVE"),
            ("az_bangalore", "amazon", "Bangalore Store", "Bangalore, IN", "ACTIVE"),
            ("az_hyderabad", "amazon", "Hyderabad Store", "Hyderabad, IN", "ACTIVE"),
        ]
        for s_id, m_id, s_name, loc, s_status in stores_seed:
            cursor.execute("INSERT INTO stores (store_id, merchant_id, name, location, status) VALUES (%s, %s, %s, %s, %s)" if (is_pg or is_my) else "INSERT INTO stores (store_id, merchant_id, name, location, status) VALUES (?, ?, ?, ?, ?)", (s_id, m_id, s_name, loc, s_status))
            
        # Seed Users
        users_seed = [
            # Admin User
            ("admin", "admin@razorpay-demo.com", hash_password("admin123"), "ADMIN", None, None),
            # Flipkart Store Users
            ("fk_user_delhi", "flipkart.delhi@merchant-demo.com", hash_password("flipkart123"), "MERCHANT", "flipkart", "fk_delhi"),
            ("fk_user_mumbai", "flipkart.mumbai@merchant-demo.com", hash_password("flipkart123"), "MERCHANT", "flipkart", "fk_mumbai"),
            ("fk_user_bangalore", "flipkart.bangalore@merchant-demo.com", hash_password("flipkart123"), "MERCHANT", "flipkart", "fk_bangalore"),
            # Amazon Store Users
            ("az_user_delhi", "amazon.delhi@merchant-demo.com", hash_password("amazon123"), "MERCHANT", "amazon", "az_delhi"),
            ("az_user_mumbai", "amazon.mumbai@merchant-demo.com", hash_password("amazon123"), "MERCHANT", "amazon", "az_mumbai"),
            ("az_user_bangalore", "amazon.bangalore@merchant-demo.com", hash_password("amazon123"), "MERCHANT", "amazon", "az_bangalore"),
        ]
        for u_id, email, pw_hash, role, m_id, s_id in users_seed:
            cursor.execute("INSERT INTO users (user_id, email, password_hash, role, merchant_id, store_id) VALUES (%s, %s, %s, %s, %s, %s)" if (is_pg or is_my) else "INSERT INTO users (user_id, email, password_hash, role, merchant_id, store_id) VALUES (?, ?, ?, ?, ?, ?)", (u_id, email, pw_hash, role, m_id, s_id))
            
        # Seed initial config
        cursor.execute("INSERT INTO configuration (config_key, config_value) VALUES (%s, %s)" if (is_pg or is_my) else "INSERT INTO configuration (config_key, config_value) VALUES (?, ?)", ("sys_gemini_api_key", os.environ.get("GEMINI_API_KEY", "")))
        
        conn.commit()
        
    # Seed Notifications if empty
    cursor.execute("SELECT COUNT(*) FROM notifications")
    if cursor.fetchone()[0] == 0:
        notifs_seed = [
            ("admin", None, None, "ADMIN", "Daily Settlement Batches Cleared", "Nodal settlement batches for Flipkart and Amazon reconciled successfully with zero clearing delay."),
            ("admin", "flipkart", "fk_delhi", "ADMIN", "Fee Rate Discrepancy Flagged", "Detected 2 fee rate mismatches on Flipkart Delhi store transactions requiring operations review."),
            ("admin", "amazon", "az_mumbai", "ADMIN", "Section 194-O TDS Threshold Approaching", "Amazon gross platform collections crossed 85% of monthly compliance threshold."),
            ("admin", None, None, "ADMIN", "Automated 3-Way Reconciliation Run", "24,850 gateway, order, and bank records reconciled with 98.4% auto-match rate.")
        ]
        for u_id, m_id, s_id, r, title, msg in notifs_seed:
            cursor.execute("INSERT INTO notifications (user_id, merchant_id, store_id, role, title, message) VALUES (%s, %s, %s, %s, %s, %s)" if (is_pg or is_my) else "INSERT INTO notifications (user_id, merchant_id, store_id, role, title, message) VALUES (?, ?, ?, ?, ?, ?)", (u_id, m_id, s_id, r, title, msg))
        conn.commit()

    # Seed Support Tickets if empty
    cursor.execute("SELECT COUNT(*) FROM support_tickets WHERE status IN ('OPEN', 'PENDING')")
    if cursor.fetchone()[0] == 0:
        tickets_seed = [
            ("flipkart", "fk_delhi", "pay_95822412", "Gateway fee charged at 3% instead of contracted 2%", "We noticed fee discrepancy on order_24942603 where 3% MDR was charged. Please adjust credit.", "OPEN", "High", "Gateway Exception Review"),
            ("amazon", "az_mumbai", "pay_42780411", "Delayed bank settlement for August 10 batch", "Bank settlement amount was credited as ₹9,952.26 instead of expected ₹10,202.26. Please verify nodal transfer.", "OPEN", "Medium", "Settlement Inquiry"),
            ("flipkart", "fk_mumbai", "pay_89254563", "Missing credit advice for payout batch #892", "Bank credit reference advice missing for Mumbai store batch on Aug 18.", "OPEN", "Low", "Payout Status")
        ]
        for m_id, s_id, tx_id, subj, msg, stat, prio, cat in tickets_seed:
            cursor.execute("INSERT INTO support_tickets (merchant_id, store_id, transaction_id, subject, message, status, priority, category) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)" if (is_pg or is_my) else "INSERT INTO support_tickets (merchant_id, store_id, transaction_id, subject, message, status, priority, category) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (m_id, s_id, tx_id, subj, msg, stat, prio, cat))
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

def load_financial_data(merchant_id=None, store_id=None):
    """Loads financial data from SQL tables, isolated by merchant/store if requested."""
    conn = get_connection()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    
    tx_q = "SELECT * FROM transactions"
    order_q = "SELECT * FROM internal_orders"
    bank_q = "SELECT * FROM bank_statements"
    params = []
    
    # Build filtered queries for isolation
    if merchant_id and store_id:
        placeholder = "%s" if (is_pg or is_my) else "?"
        tx_q += f" WHERE merchant_id = {placeholder} AND store_id = {placeholder}"
        order_q += f" WHERE merchant_id = {placeholder} AND store_id = {placeholder}"
        bank_q += f" WHERE merchant_id = {placeholder} AND store_id = {placeholder}"
        params = [merchant_id, store_id]
    elif merchant_id:
        placeholder = "%s" if (is_pg or is_my) else "?"
        tx_q += f" WHERE merchant_id = {placeholder}"
        order_q += f" WHERE merchant_id = {placeholder}"
        bank_q += f" WHERE merchant_id = {placeholder}"
        params = [merchant_id]
        
    try:
        if params:
            # pd.read_sql_query supports params argument
            df_rp = pd.read_sql_query(tx_q, conn, params=params)
            df_orders = pd.read_sql_query(order_q, conn, params=params)
            df_bank = pd.read_sql_query(bank_q, conn, params=params)
        else:
            df_rp = pd.read_sql_query(tx_q, conn)
            df_orders = pd.read_sql_query(order_q, conn)
            df_bank = pd.read_sql_query(bank_q, conn)
    except Exception as e:
        print(f"Database read error: {e}")
        # Fallback to empty DataFrames if database is not initialized yet
        df_rp = pd.DataFrame(columns=['transaction_id', 'order_id', 'type', 'status', 'method', 'amount_inr', 'fee_inr', 'tax_inr', 'settled_amount_inr', 'expected_settlement_date', 'timestamp', 'exception_flag', 'merchant_id', 'store_id'])
        df_orders = pd.DataFrame(columns=['order_id', 'amount_inr', 'status', 'created_at', 'customer_email', 'merchant_id', 'store_id'])
        df_bank = pd.DataFrame(columns=['date', 'amount_inr', 'bank_reference', 'merchant_id', 'store_id', 'status'])
    finally:
        conn.close()
        
    return df_rp, df_orders, df_bank

# --- User Authentication Management ---

def authenticate_user(email, password):
    """Verifies credentials and returns user dict on success, None otherwise."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    cursor.execute(f"SELECT user_id, email, password_hash, role, merchant_id, store_id FROM users WHERE email = {placeholder}", (email,))
    row = cursor.fetchone()
    conn.close()
    
    if row and verify_password(row[2], password):
        return {
            'user_id': row[0],
            'email': row[1],
            'role': row[3],
            'merchant_id': row[4],
            'store_id': row[5]
        }
    return None

def update_user_password(user_id, new_password):
    """Updates password for a user ID."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    new_hash = hash_password(new_password)
    cursor.execute(f"UPDATE users SET password_hash = {placeholder} WHERE user_id = {placeholder}", (new_hash, user_id))
    conn.commit()
    conn.close()
    return True

def reset_user_password(email, new_password):
    """Resets the password for a user by email address."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    new_hash = hash_password(new_password)
    cursor.execute(f"UPDATE users SET password_hash = {placeholder} WHERE email = {placeholder}", (new_hash, email))
    conn.commit()
    conn.close()
    return True

def get_store_details(store_id):
    """Retrieves store details."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    cursor.execute(f"SELECT store_id, merchant_id, name, location, status FROM stores WHERE store_id = {placeholder}", (store_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'store_id': row[0], 'merchant_id': row[1], 'name': row[2], 'location': row[3], 'status': row[4]}
    return None

def get_merchant_stores(merchant_id):
    """Retrieves all stores for a merchant."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    cursor.execute(f"SELECT store_id, name, location, status FROM stores WHERE merchant_id = {placeholder} ORDER BY name", (merchant_id,))
    stores = [{'store_id': r[0], 'name': r[1], 'location': r[2], 'status': r[3]} for r in cursor.fetchall()]
    conn.close()
    return stores

def get_merchants_list():
    """Retrieves all merchants."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT merchant_id, name, status FROM merchants ORDER BY name")
    merchants = [{'merchant_id': r[0], 'name': r[1], 'status': r[2]} for r in cursor.fetchall()]
    conn.close()
    return merchants

def get_merchants():
    """Alias for get_merchants_list."""
    return get_merchants_list()

def get_stores(merchant_id):
    """Alias for get_merchant_stores."""
    return get_merchant_stores(merchant_id)

def create_store(store_id, merchant_id, name, location):
    """Creates a new store."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholders = "%s, %s, %s, %s, 'ACTIVE'" if (is_pg or is_my) else "?, ?, ?, ?, 'ACTIVE'"
    
    cursor.execute(f"INSERT INTO stores (store_id, merchant_id, name, location, status) VALUES ({placeholders})", (store_id, merchant_id, name, location))
    conn.commit()
    conn.close()

def create_merchant_user(user_id, email, password, role, merchant_id, store_id):
    """Creates a new merchant user."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholders = "%s, %s, %s, %s, %s, %s" if (is_pg or is_my) else "?, ?, ?, ?, ?, ?"
    
    pwd_hash = hash_password(password)
    cursor.execute(f"INSERT INTO users (user_id, email, password_hash, role, merchant_id, store_id) VALUES ({placeholders})", (user_id, email, pwd_hash, role, merchant_id, store_id))
    conn.commit()
    conn.close()

# --- Config Table Management ---

def save_config(key, value):
    """Saves system configurations (e.g. Gemini key)."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    
    try:
        if is_pg:
            cursor.execute("""
            INSERT INTO configuration (config_key, config_value) VALUES (%s, %s)
            ON CONFLICT (config_key) DO UPDATE SET config_value = EXCLUDED.config_value
            """, (key, value))
        elif is_my:
            cursor.execute("""
            INSERT INTO configuration (config_key, config_value) VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE config_value = VALUES(config_value)
            """, (key, value))
        else:
            cursor.execute("""
            INSERT OR REPLACE INTO configuration (config_key, config_value) VALUES (?, ?)
            """, (key, value))
        conn.commit()
    except Exception as e:
        print(f"Error saving config: {e}")
    finally:
        conn.close()

def set_config(key, value):
    """Alias for save_config."""
    return save_config(key, value)

def get_config(key, default=""):
    """Gets system configurations."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    val = default
    try:
        cursor.execute(f"SELECT config_value FROM configuration WHERE config_key = {placeholder}", (key,))
        row = cursor.fetchone()
        if row:
            val = row[0]
    except Exception:
        pass
    finally:
        conn.close()
    return val

# --- Persistent Chat History Functions ---

def create_conversation(user_id, merchant_id, store_id, title):
    """Creates a new AI conversation session and returns the conversation_id."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    
    conv_id = f"conv_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
    placeholders = "%s, %s, %s, %s, %s" if (is_pg or is_my) else "?, ?, ?, ?, ?"
    
    cursor.execute(f"""
        INSERT INTO ai_conversations (conversation_id, user_id, merchant_id, store_id, title) 
        VALUES ({placeholders})
    """, (conv_id, user_id, merchant_id, store_id, title))
    conn.commit()
    conn.close()
    return conv_id

def update_conversation_title_with_first_query(conversation_id, query_text):
    """Appends first user query preview to the conversation title if it only contains the default title."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    try:
        # Check if conversation exists and get current title
        cursor.execute(f"SELECT title FROM ai_conversations WHERE conversation_id = {placeholder}", (conversation_id,))
        row = cursor.fetchone()
        if row:
            current_title = row[0]
            # Only append if we haven't already appended a preview
            if " - " not in current_title:
                preview = query_text.strip()
                if len(preview) > 40:
                    preview = preview[:40] + "..."
                new_title = f"{current_title} - {preview}"
                cursor.execute(f"""
                    UPDATE ai_conversations SET title = {placeholder}
                    WHERE conversation_id = {placeholder}
                """, (new_title, conversation_id))
                conn.commit()
    except Exception as e:
        print(f"Error updating conversation title: {e}")
    finally:
        conn.close()

def save_conversation_message(conversation_id, role, content, sources=None):
    """Saves a conversation turn message."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholders = "%s, %s, %s, %s" if (is_pg or is_my) else "?, ?, ?, ?"
    
    sources_json = json.dumps(sources) if sources else "[]"
    cursor.execute(f"""
        INSERT INTO ai_messages (conversation_id, role, content, sources) 
        VALUES ({placeholders})
    """, (conversation_id, role, content, sources_json))
    conn.commit()
    conn.close()

def get_conversations(user_id, merchant_id=None, store_id=None):
    """Retrieves all conversation history threads for a user/store."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    try:
        if merchant_id and store_id:
            cursor.execute(f"""
                SELECT conversation_id, title, created_at FROM ai_conversations 
                WHERE merchant_id = {placeholder} AND store_id = {placeholder}
                ORDER BY created_at DESC
            """, (merchant_id, store_id))
        else:
            cursor.execute(f"""
                SELECT conversation_id, title, created_at FROM ai_conversations 
                WHERE user_id = {placeholder} OR role = 'ADMIN'
                ORDER BY created_at DESC
            """, (user_id,))
            
        sessions = [{'session_id': r[0], 'title': r[1], 'start_time': r[2]} for r in cursor.fetchall()]
        return sessions
    except Exception:
        return []
    finally:
        conn.close()

def get_conversation_messages(conversation_id):
    """Retrieves all messages in a conversation."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    try:
        cursor.execute(f"""
            SELECT role, content, sources, timestamp FROM ai_messages 
            WHERE conversation_id = {placeholder} 
            ORDER BY message_id ASC
        """, (conversation_id,))
        messages = []
        for r in cursor.fetchall():
            messages.append({
                'role': r[0],
                'content': r[1],
                'sources': json.loads(r[2]) if r[2] else [],
                'timestamp': r[3]
            })
        return messages
    except Exception as e:
        print(f"Error loading conversation messages: {e}")
        return []
    finally:
        conn.close()

def delete_conversation(conversation_id):
    """Deletes a conversation session and all its messages."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    try:
        cursor.execute(f"DELETE FROM ai_messages WHERE conversation_id = {placeholder}", (conversation_id,))
        cursor.execute(f"DELETE FROM ai_conversations WHERE conversation_id = {placeholder}", (conversation_id,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting conversation: {e}")
    finally:
        conn.close()

# --- Legacy Backup compatibility aliases (just redirect to conversation logic) ---

def save_chat_message(session_id, role, content):
    # Backward compatibility helper
    # We check if a conversation session exists for session_id, if not we create one
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    cursor.execute(f"SELECT COUNT(*) FROM ai_conversations WHERE conversation_id = {placeholder}", (session_id,))
    exists = cursor.fetchone()[0] > 0
    conn.close()
    
    if not exists:
        create_conversation("legacy", None, None, f"Legacy Session {session_id[:8]}")
    save_conversation_message(session_id, role, content)

def get_chat_sessions():
    return [{'session_id': c['session_id'], 'start_time': c['start_time'], 'first_message': c['title']} for c in get_conversations("legacy")]

def get_chat_history(session_id):
    return get_conversation_messages(session_id)

# --- RAG Chunks Storage Functions ---

def save_document_chunks(file_name, chunks):
    """Saves document text chunks and embeddings into the database, clearing previous entries."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    # 1. Clear old chunks for this file
    cursor.execute(f"DELETE FROM document_chunks WHERE file_name = {placeholder}", (file_name,))
        
    # 2. Insert new chunks
    placeholders = "%s, %s, %s, %s" if (is_pg or is_my) else "?, ?, ?, ?"
    for chunk in chunks:
        embedding_json = json.dumps(chunk['embedding'])
        cursor.execute(
            f"INSERT INTO document_chunks (file_name, chunk_index, text_content, embedding) VALUES ({placeholders})",
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

def get_indexed_documents():
    """Returns unique indexed filenames, chunk counts, and indexing metadata."""
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
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    try:
        cursor.execute(f"DELETE FROM document_chunks WHERE file_name = {placeholder}", (file_name,))
        conn.commit()
    except Exception as e:
        print(f"Database Delete Chunks Error: {str(e)}")
    finally:
        conn.close()

# --- Support Tickets / Contact Us Functions ---

def get_merchant_name(merchant_id):
    """Retrieves name of a merchant by merchant_id."""
    if not merchant_id:
        return "Unknown Merchant"
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    try:
        cursor.execute(f"SELECT name FROM merchants WHERE merchant_id = {placeholder}", (merchant_id,))
        row = cursor.fetchone()
        if row:
            return row[0]
    except Exception:
        pass
    finally:
        conn.close()
    return merchant_id.capitalize()

def raise_support_ticket(transaction_id, subject, message, merchant_id=None, store_id=None, user_id=None, category=None, priority=None, merchant_name=None):
    """Inserts a new support ticket in the database and returns the generated ticket_id."""
    if not merchant_name and merchant_id:
        merchant_name = get_merchant_name(merchant_id)
    if not merchant_name:
        merchant_name = "Unknown Merchant"
        
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    
    placeholders = "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s" if (is_pg or is_my) else "?, ?, ?, ?, ?, ?, ?, ?, ?, ?"
    
    ticket_id = None
    try:
        if is_pg:
            cursor.execute(f"""
                INSERT INTO support_tickets (
                    transaction_id, merchant_name, subject, message, status, 
                    merchant_id, store_id, user_id, category, priority
                ) VALUES ({placeholders}) RETURNING ticket_id
            """, (transaction_id, merchant_name, subject, message, 'OPEN', merchant_id, store_id, user_id, category, priority))
            ticket_id = cursor.fetchone()[0]
        else:
            cursor.execute(f"""
                INSERT INTO support_tickets (
                    transaction_id, merchant_name, subject, message, status, 
                    merchant_id, store_id, user_id, category, priority
                ) VALUES ({placeholders})
            """, (transaction_id, merchant_name, subject, message, 'OPEN', merchant_id, store_id, user_id, category, priority))
            ticket_id = cursor.lastrowid
        conn.commit()
    except Exception as e:
        print(f"Error raising support ticket: {e}")
    finally:
        conn.close()
    return ticket_id

def get_support_tickets(merchant_name=None, merchant_id=None, store_id=None):
    """Retrieves support tickets. Isolated by merchant/store if specified."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    try:
        if merchant_id and store_id:
            cursor.execute(f"""
                SELECT ticket_id, transaction_id, merchant_name, subject, message, status, 
                       resolution_comments, timestamp, category, priority, store_id, merchant_id 
                FROM support_tickets 
                WHERE merchant_id = {placeholder} AND store_id = {placeholder} 
                ORDER BY timestamp DESC
            """, (merchant_id, store_id))
        elif merchant_id:
            cursor.execute(f"""
                SELECT ticket_id, transaction_id, merchant_name, subject, message, status, 
                       resolution_comments, timestamp, category, priority, store_id, merchant_id 
                FROM support_tickets 
                WHERE merchant_id = {placeholder} 
                ORDER BY timestamp DESC
            """, (merchant_id,))
        elif merchant_name:
            cursor.execute(f"""
                SELECT ticket_id, transaction_id, merchant_name, subject, message, status, 
                       resolution_comments, timestamp, category, priority, store_id, merchant_id 
                FROM support_tickets 
                WHERE merchant_name = {placeholder} 
                ORDER BY timestamp DESC
            """, (merchant_name,))
        else:
            cursor.execute("""
                SELECT ticket_id, transaction_id, merchant_name, subject, message, status, 
                       resolution_comments, timestamp, category, priority, store_id, merchant_id 
                FROM support_tickets 
                ORDER BY timestamp DESC
            """)
            
        tickets = []
        for row in cursor.fetchall():
            tickets.append({
                'ticket_id': row[0],
                'transaction_id': row[1],
                'merchant_name': row[2],
                'subject': row[3],
                'message': row[4],
                'status': row[5],
                'reply': row[6], # Maps to reply for app.py compat (truthy check)
                'timestamp': row[7],
                'category': row[8] or "General",
                'priority': row[9] or "Medium",
                'store_id': row[10],
                'merchant_id': row[11] or ""
            })
        return tickets
    except Exception as e:
        print(f"Error getting tickets: {e}")
        return []
    finally:
        conn.close()

def resolve_support_ticket(ticket_id, resolution_comments):
    """Updates ticket status to RESOLVED and saves resolution comments."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    cursor.execute(f"UPDATE support_tickets SET status = 'RESOLVED', resolution_comments = {placeholder} WHERE ticket_id = {placeholder}", (resolution_comments, ticket_id))
        
    conn.commit()
    conn.close()

def delete_support_ticket(ticket_id):
    """Permanently deletes a specific support ticket by its ID."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    cursor.execute(f"DELETE FROM support_tickets WHERE ticket_id = {placeholder}", (ticket_id,))
    conn.commit()
    conn.close()

def clear_resolved_support_tickets():
    """Permanently deletes all resolved support tickets."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM support_tickets WHERE status = 'RESOLVED'")
    conn.commit()
    conn.close()

def get_global_metrics():
    """Calculates global platform metrics across all merchants and stores."""
    from src.reconciliation import run_3way_reconciliation
    metrics, _, _, _, _ = run_3way_reconciliation(None, None)
    return {
        'total_volume': float(metrics['gross_collections_inr']),
        'needs_review_count': int(metrics['needs_review_count'])
    }

# --- Persistent Notifications ---

def create_notification(user_id, merchant_id, store_id, role, title, message):
    """Creates a badged notification in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholders = "%s, %s, %s, %s, %s, %s" if (is_pg or is_my) else "?, ?, ?, ?, ?, ?"
    
    cursor.execute(f"""
        INSERT INTO notifications (user_id, merchant_id, store_id, role, title, message) 
        VALUES ({placeholders})
    """, (user_id, merchant_id, store_id, role, title, message))
    conn.commit()
    conn.close()

def get_notifications(user_id=None, merchant_id=None, store_id=None, role=None):
    """Retrieves unread notifications."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    try:
        query = "SELECT notification_id, title, message, is_read, created_at, merchant_id, store_id, role FROM notifications WHERE is_read = 0"
        params = []
        
        if merchant_id and store_id:
            query += f" AND (((merchant_id = {placeholder} OR merchant_id IS NULL) AND (store_id = {placeholder} OR store_id IS NULL OR store_id = '')) OR role = 'ALL' OR (user_id = {placeholder}))"
            params = [merchant_id, store_id, user_id]
        elif merchant_id:
            query += f" AND (merchant_id = {placeholder} OR role = 'ALL' OR role = 'MERCHANT')"
            params = [merchant_id]
        elif role == 'ADMIN':
            query += f" AND (role = 'ADMIN' OR role = 'ALL')"
        elif role == 'MERCHANT':
            query += f" AND (role = 'MERCHANT' OR role = 'ALL')"
        elif user_id:
            query += f" AND (user_id = {placeholder} OR role = 'ALL')"
            params = [user_id]
            
        query += " ORDER BY created_at DESC, notification_id DESC"
        
        if params:
            cursor.execute(query, tuple(params))
        else:
            cursor.execute(query)
            
        notifs = []
        for r in cursor.fetchall():
            notifs.append({
                'notification_id': r[0],
                'title': r[1],
                'message': r[2],
                'is_read': r[3],
                'created_at': r[4],
                'merchant_id': r[5],
                'store_id': r[6],
                'role': r[7]
            })
        return notifs
    except Exception as e:
        print(f"Error getting notifications: {e}")
        return []
    finally:
        conn.close()

def mark_notification_as_read(notif_id):
    """Marks a notification as read."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    cursor.execute(f"UPDATE notifications SET is_read = 1 WHERE notification_id = {placeholder}", (notif_id,))
    conn.commit()
    conn.close()

def record_exception_resolution(transaction_id, order_id="", merchant_id="", store_id="", amount_inr=0.0, issue_description="", resolution_note="", resolved_by_role="ADMIN", resolved_by_user="admin", status="RESOLVED"):
    """Records an exception resolution in the persistent database, notifies the relevant parties, and logs an audit trail."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholders = "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s" if (is_pg or is_my) else "?, ?, ?, ?, ?, ?, ?, ?, ?, ?"
    
    try:
        cursor.execute(f"""
            INSERT INTO exception_resolutions 
            (transaction_id, order_id, merchant_id, store_id, amount_inr, issue_description, resolution_note, resolved_by_role, resolved_by_user, status)
            VALUES ({placeholders})
        """, (transaction_id, order_id, merchant_id, store_id, float(amount_inr or 0.0), str(issue_description), str(resolution_note), resolved_by_role, resolved_by_user, status))
        conn.commit()
    except Exception as e:
        print(f"Error inserting exception resolution: {e}")
    finally:
        conn.close()

    # Automatic cross-role synchronized notifications
    if resolved_by_role == 'ADMIN' and status == 'RESOLVED':
        # Admin resolved -> Notify the corresponding store
        create_notification(
            user_id=None,
            merchant_id=merchant_id if merchant_id else None,
            store_id=store_id if store_id else None,
            role='MERCHANT',
            title=f"Exception Resolved for {transaction_id}",
            message=f"Admin has resolved discrepancy on Transaction {transaction_id} (Order: {order_id}). Resolution Note: '{resolution_note}'."
        )
        log_action(resolved_by_user, "Admin Exception Resolution", f"Admin resolved {transaction_id} (Store: {store_id or 'Global'}). Note: {resolution_note}")
    elif resolved_by_role == 'MERCHANT':
        # Merchant resolved on store side -> Notify Admin to review and verify manually
        create_notification(
            user_id=None,
            merchant_id=merchant_id,
            store_id=store_id,
            role='ADMIN',
            title=f"Merchant Resolution Submitted: {transaction_id}",
            message=f"Store {(store_id or '').upper()} ({(merchant_id or '').upper()}) submitted resolution for Transaction {transaction_id} (Order: {order_id}). Store Note: '{resolution_note}'. Please review and verify in Exception Command Center."
        )
        log_action(resolved_by_user, "Merchant Resolution Submitted", f"Store {store_id} submitted resolution for {transaction_id}. Note: {resolution_note}")

    # Synchronize with Streamlit session state if available
    try:
        import streamlit as st
        if status == 'RESOLVED':
            if "resolved_exceptions" not in st.session_state:
                st.session_state.resolved_exceptions = []
            if transaction_id not in st.session_state.resolved_exceptions:
                st.session_state.resolved_exceptions.append(transaction_id)
            if "resolution_notes" not in st.session_state:
                st.session_state.resolution_notes = {}
            st.session_state.resolution_notes[transaction_id] = resolution_note
    except Exception:
        pass

def approve_merchant_resolution(resolution_id, transaction_id, admin_note="Approved by Razorpay Admin.", admin_user="admin"):
    """Approves a merchant-submitted resolution request from the Admin side and notifies the merchant store."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    merchant_id = None
    store_id = None
    order_id = ""
    original_note = ""
    
    try:
        cursor.execute(f"SELECT merchant_id, store_id, order_id, resolution_note FROM exception_resolutions WHERE resolution_id = {placeholder}", (resolution_id,))
        row = cursor.fetchone()
        if row:
            merchant_id, store_id, order_id, original_note = row[0], row[1], row[2], row[3]
            
        combined_note = f"{original_note} | Verified & Approved by Admin: {admin_note}" if admin_note else original_note
        
        cursor.execute(f"UPDATE exception_resolutions SET status = 'RESOLVED', resolution_note = {placeholder}, resolved_by_role = 'ADMIN', resolved_by_user = {placeholder} WHERE resolution_id = {placeholder}", (combined_note, admin_user, resolution_id))
        conn.commit()
    except Exception as e:
        print(f"Error approving merchant resolution: {e}")
        combined_note = admin_note
    finally:
        conn.close()
        
    # Notify merchant store of final admin confirmation
    create_notification(
        user_id=None,
        merchant_id=merchant_id,
        store_id=store_id,
        role='MERCHANT',
        title=f"Resolution Verified & Approved: {transaction_id}",
        message=f"Razorpay Admin verified and approved the resolution for Transaction {transaction_id} (Order: {order_id}). Audit Note: '{admin_note}'."
    )
    log_action(admin_user, "Admin Approved Resolution", f"Approved merchant resolution for {transaction_id} (Store: {store_id}). Note: {admin_note}")

    try:
        import streamlit as st
        if "resolved_exceptions" not in st.session_state:
            st.session_state.resolved_exceptions = []
        if transaction_id not in st.session_state.resolved_exceptions:
            st.session_state.resolved_exceptions.append(transaction_id)
        if "resolution_notes" not in st.session_state:
            st.session_state.resolution_notes = {}
        st.session_state.resolution_notes[transaction_id] = combined_note
    except Exception:
        pass

def get_exception_resolutions(merchant_id=None, store_id=None, status=None):
    """Retrieves resolution history and pending requests from the persistent database."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    query = "SELECT resolution_id, transaction_id, order_id, merchant_id, store_id, amount_inr, issue_description, resolution_note, resolved_by_role, resolved_by_user, status, created_at FROM exception_resolutions WHERE 1=1"
    params = []
    
    if merchant_id and str(merchant_id).lower() != "all":
        query += f" AND merchant_id = {placeholder}"
        params.append(merchant_id)
    if store_id and str(store_id).lower() != "all":
        query += f" AND store_id = {placeholder}"
        params.append(store_id)
    if status and str(status).lower() != "all":
        query += f" AND status = {placeholder}"
        params.append(status)
        
    query += " ORDER BY created_at DESC, resolution_id DESC"
    
    try:
        if params:
            cursor.execute(query, tuple(params))
        else:
            cursor.execute(query)
            
        rows = []
        for r in cursor.fetchall():
            rows.append({
                'resolution_id': r[0],
                'transaction_id': r[1],
                'order_id': r[2],
                'merchant_id': r[3],
                'store_id': r[4],
                'amount_inr': float(r[5] or 0.0),
                'issue_description': r[6],
                'resolution_note': r[7],
                'resolved_by_role': r[8],
                'resolved_by_user': r[9],
                'status': r[10],
                'created_at': r[11]
            })
        return rows
    except Exception as e:
        print(f"Error fetching exception resolutions: {e}")
        return []
    finally:
        conn.close()

def resolve_transaction_exception(transaction_id, note, order_id="", merchant_id="", store_id="", amount_inr=0.0, issue_description="", resolved_by_role="ADMIN", resolved_by_user="admin"):
    """Applies a manual correction to a transaction exception and persists it."""
    record_exception_resolution(
        transaction_id=transaction_id,
        order_id=order_id,
        merchant_id=merchant_id,
        store_id=store_id,
        amount_inr=amount_inr,
        issue_description=issue_description,
        resolution_note=note,
        resolved_by_role=resolved_by_role,
        resolved_by_user=resolved_by_user,
        status="RESOLVED"
    )

# --- Persistent Audit Log Functions ---

def log_action(user_id, action, details):
    """Records an activity log."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholders = "%s, %s, %s" if (is_pg or is_my) else "?, ?, ?"
    
    try:
        cursor.execute(f"INSERT INTO audit_logs (user_id, action, details) VALUES ({placeholders})", (user_id, action, details))
        conn.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
    finally:
        conn.close()

def get_audit_logs():
    """Retrieves all activity audit logs."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT log_id, user_id, action, details, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 200")
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'log_id': row[0],
                'user_id': row[1],
                'action': row[2],
                'details': row[3],
                'timestamp': row[4]
            })
        return logs
    except Exception as e:
        print(f"Error reading audit logs: {e}")
        return []
    finally:
        conn.close()

def create_user_session(user_id):
    """Creates a persistent session token in the database valid for 14 days."""
    import secrets
    import time
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholders = "%s, %s, %s" if (is_pg or is_my) else "?, ?, ?"
    
    token = secrets.token_hex(24)
    # 14 days in seconds
    expires_at = int(time.time() + 14 * 24 * 60 * 60)
    
    try:
        cursor.execute(f"INSERT INTO user_sessions (session_token, user_id, expires_at) VALUES ({placeholders})", (token, user_id, expires_at))
        conn.commit()
    except Exception as e:
        print(f"Error creating user session: {e}")
    finally:
        conn.close()
    return token

def get_user_by_session(token):
    """Retrieves user details if session token is valid and not expired."""
    import time
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    
    current_time = int(time.time())
    try:
        cursor.execute(f"""
            SELECT u.user_id, u.email, u.role, u.merchant_id, u.store_id 
            FROM user_sessions s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.session_token = {placeholder} AND s.expires_at > {placeholder}
        """, (token, current_time))
        row = cursor.fetchone()
        if row:
            return {
                'user_id': row[0],
                'email': row[1],
                'role': row[2],
                'merchant_id': row[3],
                'store_id': row[4]
            }
    except Exception as e:
        print(f"Error validating session: {e}")
    finally:
        conn.close()
    return None

def delete_user_session(token):
    """Deletes a session token from database."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    try:
        cursor.execute(f"DELETE FROM user_sessions WHERE session_token = {placeholder}", (token,))
        conn.commit()
    except Exception as e:
        print(f"Error deleting session: {e}")
    finally:
        conn.close()

def log_action(user_id, action, details=""):
    """Inserts an action into audit_logs table."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholders = "%s, %s, %s" if (is_pg or is_my) else "?, ?, ?"
    try:
        cursor.execute(f"INSERT INTO audit_logs (user_id, action, details) VALUES ({placeholders})", (user_id, action, str(details)))
        conn.commit()
    except Exception as e:
        print(f"Error logging action: {e}")
    finally:
        conn.close()

def get_action_logs(limit=50):
    """Retrieves the most recent audit logs."""
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    try:
        cursor.execute(f"SELECT log_id, user_id, action, details, timestamp FROM audit_logs ORDER BY log_id DESC LIMIT {placeholder}", (limit,))
        rows = cursor.fetchall()
        logs = []
        for r in rows:
            logs.append({
                'log_id': r[0],
                'user_id': r[1],
                'action': r[2],
                'details': r[3],
                'timestamp': str(r[4])
            })
        return logs
    except Exception as e:
        print(f"Error getting action logs: {e}")
        return []
    finally:
        conn.close()

def get_users():
    """Retrieves all registered platform users."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id, email, role, merchant_id, store_id FROM users")
        users = []
        for r in cursor.fetchall():
            users.append({
                'user_id': r[0],
                'email': r[1],
                'role': r[2],
                'merchant_id': r[3],
                'store_id': r[4]
            })
        return users
    except Exception as e:
        print(f"Error getting users: {e}")
        return []
    finally:
        conn.close()

def reset_user_password(email, new_password):
    # Resets user password by email
    conn = get_connection()
    cursor = conn.cursor()
    is_pg = is_postgres_configured()
    is_my = is_mysql_configured()
    placeholder = "%s" if (is_pg or is_my) else "?"
    pw_hash = hash_password(new_password)
    try:
        cursor.execute(f"UPDATE users SET password_hash = {placeholder} WHERE email = {placeholder}", (pw_hash, email))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error resetting password: {e}")
        return False
    finally:
        conn.close()

