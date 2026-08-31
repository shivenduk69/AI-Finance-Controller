# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our reconciliation engine
from src.reconciliation import run_3way_reconciliation
from src.forecaster import get_cash_forecast
from src.tax_matcher import run_tax_audit

# Import SQL database and RAG engine modules
from src.database import (
    save_chat_message, get_chat_sessions, get_chat_history, init_db,
    raise_support_ticket, get_support_tickets, resolve_support_ticket
)
from src.rag_engine import retrieve_relevant_context, build_document_index

def get_august_25_example_data(merchant_id="flipkart", store_id="fk_delhi"):
    """Returns the exact numbers/exceptions for the user's August 25 example."""
    summary = {
        'total_payments_processed': 80,
        'total_transactions': 96, # 80 payments, 8 refunds, 8 payouts
        'auto_resolved_count': 64,
        'needs_review_count': 16,
        'auto_match_accuracy_pct': 96.9, # Match rate metric specified in user prompt
        'gross_collections_inr': 124000.00,
        'refunds_inr': 8500.00,
        'fees_gst_inr': 2918.00,
        'settled_to_bank_inr': 89232.00,
        'expected_next_2_days_inr': 23350.00,
        'unreconciled_review_inr': 0.0
    }
    
    # Generate 80 payment transactions
    txs = []
    
    # Let's add the 16 exceptions:
    # 1. 4 Fee Mismatches
    for i in range(4):
        txs.append({
            'transaction_id': f"pay_exc_fee_{i:02d}",
            'order_id': f"order_fee_{i:02d}",
            'type': 'PAYMENT',
            'status': 'captured',
            'method': 'wallet' if i % 2 == 0 else 'card',
            'amount_inr': 4000.00 + i * 500,
            'fee_inr': 150.00 + i * 15, # 3% instead of 2%
            'tax_inr': 18.00 + i * 2, # Tax calculated on 2% fee but recorded fee is 3%
            'settled_amount_inr': (4000.00 + i * 500) - (80.00 + i * 10) - (14.4 + i * 1.8), # Settled on 2% rules
            'expected_settlement_date': '25-08-2026',
            'calculated_exceptions': ['FEE_MISMATCH (Expected 2%, Charged 3%)', 'SETTLED_AMOUNT_MISMATCH (Settled on 2% rules but recorded 3% fee)'],
            'resolution_status': 'NEEDS_REVIEW',
            'confidence_score': 0.10,
            'orig_exception': 'YES'
        })
        
    # 2. 3 Missing Order IDs (Gateway orphans)
    for i in range(3):
        txs.append({
            'transaction_id': f"pay_exc_miss_{i:02d}",
            'order_id': "",
            'type': 'PAYMENT',
            'status': 'captured',
            'method': 'card',
            'amount_inr': 2500.00 + i * 200,
            'fee_inr': 50.00 + i * 4,
            'tax_inr': 9.00 + i * 0.72,
            'settled_amount_inr': (2500.00 + i * 200) - (50.00 + i * 4) - (9.00 + i * 0.72),
            'expected_settlement_date': '25-08-2026',
            'calculated_exceptions': ['MISSING_ORDER_ID'],
            'resolution_status': 'NEEDS_REVIEW',
            'confidence_score': 0.00,
            'orig_exception': 'YES'
        })
        
    # 3. 2 Disputed Payments
    for i in range(2):
        txs.append({
            'transaction_id': f"pay_exc_disp_{i:02d}",
            'order_id': f"order_disp_{i:02d}",
            'type': 'PAYMENT',
            'status': 'disputed',
            'method': 'card',
            'amount_inr': 5000.00 + i * 1000,
            'fee_inr': 100.00 + i * 20,
            'tax_inr': 18.00 + i * 3.6,
            'settled_amount_inr': (5000.00 + i * 1000) - (100.00 + i * 20) - (18.00 + i * 3.6),
            'expected_settlement_date': '25-08-2026',
            'calculated_exceptions': ['DISPUTED_TRANSACTION'],
            'resolution_status': 'NEEDS_REVIEW',
            'confidence_score': 0.00,
            'orig_exception': 'YES'
        })
        
    # 4. 3 Bank Statement Omissions (Bank statement lacks settlement batch)
    for i in range(3):
        txs.append({
            'transaction_id': f"pay_exc_bankom_{i:02d}",
            'order_id': f"order_bankom_{i:02d}",
            'type': 'PAYMENT',
            'status': 'captured',
            'method': 'upi',
            'amount_inr': 3000.00 + i * 100,
            'fee_inr': 60.00 + i * 2,
            'tax_inr': 10.80 + i * 0.36,
            'settled_amount_inr': (3000.00 + i * 100) - (60.00 + i * 2) - (10.80 + i * 0.36),
            'expected_settlement_date': '25-08-2026',
            'calculated_exceptions': ['BANK_CREDIT_MISSING (Expected bank settlement not recorded on statement)'],
            'resolution_status': 'NEEDS_REVIEW',
            'confidence_score': 0.10,
            'orig_exception': 'YES'
        })
        
    # 5. 3 Bank Settlement Mismatches
    for i in range(3):
        txs.append({
            'transaction_id': f"pay_exc_bankms_{i:02d}",
            'order_id': f"order_bankms_{i:02d}",
            'type': 'PAYMENT',
            'status': 'captured',
            'method': 'upi',
            'amount_inr': 1200.00 + i * 100,
            'fee_inr': 24.00 + i * 2,
            'tax_inr': 4.32 + i * 0.36,
            'settled_amount_inr': (1200.00 + i * 100) - (24.00 + i * 2) - (4.32 + i * 0.36),
            'expected_settlement_date': '25-08-2026',
            'calculated_exceptions': ['BANK_SETTLEMENT_MISMATCH (Actual bank credited amount differs from expectations)'],
            'resolution_status': 'NEEDS_REVIEW',
            'confidence_score': 0.20,
            'orig_exception': 'YES'
        })
        
    # 6. 1 Amount Mismatch
    txs.append({
        'transaction_id': "pay_exc_amt_01",
        'order_id': "order_amt_01",
        'type': 'PAYMENT',
        'status': 'captured',
        'method': 'card',
        'amount_inr': 8750.00,
        'fee_inr': 175.00,
        'tax_inr': 31.50,
        'settled_amount_inr': 8543.50,
        'expected_settlement_date': '25-08-2026',
        'calculated_exceptions': ['INTERNAL_AMOUNT_MISMATCH (Internal: INR8,500.00, Gateway Captured: INR8,750.00)'],
        'resolution_status': 'NEEDS_REVIEW',
        'confidence_score': 0.30,
        'orig_exception': 'YES'
    })
    
    # Populate the rest 64 as auto-resolved
    for i in range(64):
        txs.append({
            'transaction_id': f"pay_resolved_{i:02d}",
            'order_id': f"order_ok_{i:02d}",
            'type': 'PAYMENT',
            'status': 'captured',
            'method': 'upi' if i % 2 == 0 else 'card',
            'amount_inr': 1000.00 + (i * 20),
            'fee_inr': 20.00 + (i * 0.4),
            'tax_inr': 3.60 + (i * 0.07),
            'settled_amount_inr': (1000.00 + (i * 20)) - (20.00 + (i * 0.4)) - (3.60 + (i * 0.07)),
            'expected_settlement_date': '25-08-2026',
            'calculated_exceptions': [],
            'resolution_status': 'AUTO_RESOLVED',
            'confidence_score': 1.0,
            'orig_exception': 'NO'
        })
        
    df_txs = pd.DataFrame(txs)
    
    # Mock unmatched internal orders (gateway payment not found)
    df_unmatched = pd.DataFrame([{
        'order_id': "order_unmatched_99",
        'amount_inr': 3200.00,
        'created_at': '25-08-2026 12:00',
        'status': 'completed',
        'customer_email': 'buyer@example.com',
        'calculated_exceptions': ['GATEWAY_PAYMENT_NOT_FOUND'],
        'resolution_status': 'NEEDS_REVIEW',
        'confidence_score': 0.0
    }])
    
    # Mock bank settlements
    bank_records = [
        {'date': '25-08-2026', 'expected_amount_inr': 89232.00, 'amount_inr': 89232.00, 'difference': 0.0, 'bank_reference': 'REF2026082501', 'status': 'RECONCILED'},
        {'date': '24-08-2026', 'expected_amount_inr': 21450.00, 'amount_inr': 21450.00, 'difference': 0.0, 'bank_reference': 'REF2026082401', 'status': 'RECONCILED'},
        # A mismatch settlement
        {'date': '23-08-2026', 'expected_amount_inr': 15200.00, 'amount_inr': 15000.00, 'difference': -200.0, 'bank_reference': 'REF2026082301', 'status': 'SETTLEMENT_AMOUNT_MISMATCH'},
        # An omitted settlement batch
        {'date': '22-08-2026', 'expected_amount_inr': 5350.00, 'amount_inr': 0.0, 'difference': -5350.0, 'bank_reference': '', 'status': 'MISSING_BANK_CREDIT'}
    ]
    df_bank = pd.DataFrame(bank_records)
    bank_excs = [
        "Settlement amount mismatch on 23-08-2026. Expected: INR15,200.00, Bank Credited: INR15,000.00 (Diff: INR-200.00)",
        "Settlement on 22-08-2026 of INR5,350.00 did not hit the bank (Omitted deposit)."
    ]
    
    # Inject multi-tenant scoping
    df_txs['merchant_id'] = merchant_id
    df_txs['store_id'] = store_id
    df_unmatched['merchant_id'] = merchant_id
    df_unmatched['store_id'] = store_id
    df_bank['merchant_id'] = merchant_id
    df_bank['store_id'] = store_id
    
    return summary, df_txs, df_unmatched, df_bank, bank_excs

# Initialize SQL database
init_db()

# Load internal orders lookup for the Audit Deep-Dive Tab
base_dir = os.path.dirname(os.path.abspath(__file__))
orders_csv_path = os.path.join(base_dir, "data", "internal_orders.csv")
if os.path.exists(orders_csv_path):
    df_orders = pd.read_csv(orders_csv_path)
else:
    df_orders = pd.DataFrame(columns=['order_id', 'amount_inr', 'status', 'created_at', 'customer_email'])

# ----------------------------------------------------
# INITIALIZE STATE VARIABLES
# ----------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "dashboard"
if "admin_page" not in st.session_state:
    st.session_state.admin_page = "Admin Overview"
if "audit_tx" not in st.session_state:
    st.session_state.audit_tx = None
if "explain_tx" not in st.session_state:
    st.session_state.explain_tx = None
if "resolved_exceptions" not in st.session_state:
    st.session_state.resolved_exceptions = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{int(datetime.now().timestamp())}"
if "chat_query" not in st.session_state:
    st.session_state.chat_query = None
if "prompt_default" not in st.session_state:
    st.session_state.prompt_default = ""
if "current_indexed_batch" not in st.session_state:
    st.session_state.current_indexed_batch = ""

# Admin panel system rules config state
if "sys_gateway_fee" not in st.session_state:
    st.session_state.sys_gateway_fee = 2.0
if "sys_gst_rate" not in st.session_state:
    st.session_state.sys_gst_rate = 18.0
if "sys_payout_fee" not in st.session_state:
    st.session_state.sys_payout_fee = 5.0
if "sys_settlement_delay" not in st.session_state:
    st.session_state.sys_settlement_delay = "T+2 Days"
if "sys_gemini_model" not in st.session_state:
    st.session_state.sys_gemini_model = "gemini-3.6-flash"
if "sys_confidence_threshold" not in st.session_state:
    st.session_state.sys_confidence_threshold = 80
if "sys_gemini_api_key" not in st.session_state:
    from src.database import get_config
    st.session_state.sys_gemini_api_key = get_config("sys_gemini_api_key", os.environ.get("GEMINI_API_KEY", ""))
# Force override or initialize sys_system_prompt_template to ensure no sources are displayed in responses
st.session_state.sys_system_prompt_template = """You are the AI Finance Controller assistant.
Your goal is to answer the user's question using both transaction evidence and the provided financial documents/context.

{evidence_prompt}

DOCUMENTATION CONTEXT (Policy rules and Tax specifications retrieved from files):
{retrieved_context}

{history_context}

Rules:
1. Prefer information from the retrieved documents.
2. Do not invent financial facts.
3. If the documents do not contain the answer, clearly say that the information was not found in the available documents.
4. Distinguish between documented facts and your own reasoning.
5. For financial calculations, show the relevant calculation.
6. Do not display, mention, or list the sources, filenames, or document chunks used to support your answer."""

# TDS config
if "sys_tds_config" not in st.session_state:
    st.session_state.sys_tds_config = {
        'PAYMENT': {
            'Individual': {'applicable': True, 'rate': 0.01},
            'Company': {'applicable': True, 'rate': 0.02},
            'Non-Resident': {'applicable': False, 'rate': 0.00}
        },
        'PAYOUT': {
            'Individual': {'applicable': False, 'rate': 0.00},
            'Company': {'applicable': False, 'rate': 0.00},
            'Non-Resident': {'applicable': False, 'rate': 0.00}
        },
        'REFUND': {
            'Individual': {'applicable': False, 'rate': 0.00},
            'Company': {'applicable': False, 'rate': 0.00},
            'Non-Resident': {'applicable': False, 'rate': 0.00}
        }
    }

# Read potential URL query parameters for direct page linking (e.g. from table action buttons)
query_params = st.query_params
if "page" in query_params:
    st.session_state.page = query_params["page"]
if "audit_tx" in query_params:
    st.session_state.audit_tx = query_params["audit_tx"]
if "explain_tx" in query_params:
    st.session_state.explain_tx = query_params["explain_tx"]
if "admin_page" in query_params:
    st.session_state.admin_page = query_params["admin_page"]

# Set page config
st.set_page_config(
    page_title="AI Finance Controller - Dashboard",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Try to restore session from cookie
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    cookies = st.context.cookies
    token = cookies.get("session_token")
    if token:
        from src.database import get_user_by_session
        user = get_user_by_session(token)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = user
            st.session_state.page = "dashboard" if user['role'] == 'MERCHANT' else "admin"
            st.session_state.messages = []

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.logged_in:
    # Render Login Page
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap');
        
        .login-wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 80vh;
            font-family: 'Inter', sans-serif;
            background-color: #F7F9FC;
        }
        .login-card {
            width: 100%;
            max-width: 440px;
            padding: 40px;
            background: #FFFFFF;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.04);
            border: 1px solid #E2E8F0;
            text-align: center;
        }
        .login-logo {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 24px;
        }
        .login-title {
            font-family: 'Outfit', sans-serif;
            font-size: 1.75rem;
            font-weight: 800;
            color: #172B4D;
            margin-bottom: 6px;
            letter-spacing: -0.5px;
        }
        .login-subtitle {
            font-size: 0.95rem;
            color: #6B7C93;
            margin-bottom: 32px;
        }
        .info-box {
            background-color: #F0F4FA;
            border-left: 4px solid #3b82f6;
            color: #1e3a8a;
            padding: 12px;
            border-radius: 4px;
            margin-top: 15px;
            font-size: 0.85rem;
            text-align: left;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    
    # Logo and Titles
    st.markdown('''
    <div class="login-logo">
        <div style="width: 42px; height: 42px; border-radius: 10px; background-color: #0F4C75; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 22px; font-family: \'Outfit\', sans-serif;">
            R
        </div>
        <div style="display: flex; flex-direction: column; font-family: \'Outfit\', sans-serif; text-align: left;">
            <span style="color: #172B4D; font-weight: 800; font-size: 1.35rem; line-height: 1.1; letter-spacing: -0.3px;">Razorpay</span>
            <span style="color: #6B7C93; font-weight: 600; font-size: 0.8rem; letter-spacing: 0.5px;">FINANCE PLATFORM</span>
        </div>
    </div>
    <div class="login-title">Sign In</div>
    <div class="login-subtitle">Access your merchant or admin control dashboard</div>
    ''', unsafe_allow_html=True)
    
    # Inputs
    email = st.text_input("Corporate Email Address", placeholder="flipkart.delhi@merchant-demo.com", key="login_email")
    password = st.text_input("Password", type="password", placeholder="••••••••", key="login_pass")
    
    st.markdown('<div style="font-family: \'Inter\', sans-serif; text-align: left; margin-bottom: 20px; font-size: 0.8rem; color: #6B7C93;">Predefined credentials for demo in README.</div>', unsafe_allow_html=True)
    
    col_sub_btn, col_sub_forgot = st.columns([1.3, 1])
    with col_sub_btn:
        login_clicked = st.button("Secure Login 🔒", use_container_width=True, key="login_submit_btn")
    with col_sub_forgot:
        forgot_clicked = st.button("Forgot Password?", use_container_width=True, key="login_forgot_btn")
        
    if login_clicked:
        if email.strip() and password.strip():
            from src.database import authenticate_user, log_action
            user = authenticate_user(email.strip(), password.strip())
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.session_state.page = "dashboard" if user['role'] == 'MERCHANT' else "admin"
                st.session_state.messages = []  # Clear chat
                log_action(user['user_id'], "User Login", f"Successful login. Role: {user['role']}, Merchant: {user['merchant_id']}, Store: {user['store_id']}")
                st.toast(f"Logged in successfully as {email}!", icon="\u2705")
                from src.database import create_user_session
                session_token = create_user_session(user['user_id'])
                import streamlit.components.v1 as components
                components.html(f"""
                <script>
                    const expires = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toUTCString();
                    window.parent.document.cookie = "session_token={session_token}; path=/; expires=" + expires + "; SameSite=Lax";
                    window.parent.location.reload();
                </script>
                """, height=0, width=0)
                st.stop()
            else:
                st.error("Authentication failed. Invalid email or password.")
        else:
            st.warning("Please enter your email and password.")
            
    if forgot_clicked:
        st.markdown('''
        <div class="info-box">
            <strong>🔒 Enterprise Recovery Protocol:</strong> Self-service reset is disabled. Please raise a password recovery ticket or contact your Razorpay Administrator.
        </div>
        ''', unsafe_allow_html=True)
        
    st.markdown('</div></div>', unsafe_allow_html=True)
    st.stop()

# ----------------------------------------------------
# CSS DESIGN SYSTEM INJECTION
# ----------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    :root {
        --primary: #0F4C75;
        --navy: #172B4D;
        --bg: #F7F9FC;
        --card: #FFFFFF;
        --text-sec: #6B7C93;
        --success: #10B981;
        --warning: #F59E0B;
        --error: #EF4444;
        --border: #E2E8F0;
    }
    
    /* Global Overrides */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
        background-color: var(--bg) !important;
        color: var(--navy) !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        color: var(--navy) !important;
        font-weight: 700 !important;
    }
    
    /* Hide default Streamlit elements */
    header, [data-testid="stHeader"] {
        display: none !important;
    }
    
    footer {
        visibility: hidden;
    }
    
    /* Layout block size optimization */
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 1.5rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 2.5rem !important;
        padding-right: 2.5rem !important;
    }
    
    /* Sidebar Overhaul */
    [data-testid="stSidebar"] {
        background-color: #161f30 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        width: 260px !important;
    }
    
    [data-testid="stSidebarUserContent"] {
        padding-top: 1.5rem !important;
        padding-left: 0px !important;
        padding-right: 0px !important;
    }
    
    /* Hide Streamlit default collapse sidebar button */
    [data-testid="stSidebarCollapseButton"] {
        display: none !important;
    }
    
    /* Custom Sidebar Logo styling */
    .sidebar-logo {
        padding: 0 24px 15px 24px;
        margin-bottom: 5px;
    }
    
    /* Sidebar Section Headers */
    .sidebar-section-header {
        color: #6B7C93 !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        letter-spacing: 1px !important;
        margin-top: 16px !important;
        margin-bottom: 4px !important;
        padding-left: 24px !important;
        text-transform: uppercase !important;
    }
    
    /* Sidebar Nav Buttons Styling */
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] {
        gap: 0px !important;
    }
    
    section[data-testid="stSidebar"] div[data-testid="element-container"] {
        margin: 0px !important;
        padding: 0px !important;
    }
    
    .sidebar-btn-wrapper {
        margin-bottom: 0px !important;
        position: relative !important;
        width: 100% !important;
    }
    
    /* Target all buttons inside the sidebar to override default Streamlit white cards */
    section[data-testid="stSidebar"] div.stButton > button,
    section[data-testid="stSidebar"] button[data-testid="baseButton-secondary"],
    section[data-testid="stSidebar"] button {
        background-color: transparent !important;
        color: #9AA9BD !important;
        border: none !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 11px 24px !important;
        border-radius: 0px !important;
        font-size: 14.5px !important;
        font-weight: 500 !important;
        width: 100% !important;
        border-left: 3px solid transparent !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: center !important;
        height: 44px !important;
        margin: 0px !important;
    }
    
    section[data-testid="stSidebar"] div.stButton > button:hover,
    section[data-testid="stSidebar"] button:hover {
        background-color: rgba(255, 255, 255, 0.03) !important;
        color: #FFFFFF !important;
    }
    
    section[data-testid="stSidebar"] div.element-container:has(.sidebar-btn-active) + div.element-container button,
    section[data-testid="stSidebar"] div[data-testid="element-container"]:has(.sidebar-btn-active) + div[data-testid="element-container"] button,
    section[data-testid="stSidebar"] .sidebar-btn-active div.stButton > button,
    section[data-testid="stSidebar"] .sidebar-btn-active button {
        background-color: #212c40 !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-left: 3px solid #3B82F6 !important;
    }
    
    /* Admin active sidebar button state */
    section[data-testid="stSidebar"] div.element-container:has(.sidebar-btn-active-admin) + div.element-container button,
    section[data-testid="stSidebar"] div[data-testid="element-container"]:has(.sidebar-btn-active-admin) + div[data-testid="element-container"] button,
    section[data-testid="stSidebar"] .sidebar-btn-active-admin div.stButton > button,
    section[data-testid="stSidebar"] .sidebar-btn-active-admin button {
        background-color: #0B66E4 !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        border-left: none !important;
    }
    
    /* Color the first character (the Unicode symbol icon) blue when active */
    section[data-testid="stSidebar"] .sidebar-btn-active div.stButton > button::first-letter,
    section[data-testid="stSidebar"] .sidebar-btn-active button::first-letter {
        color: #3B82F6 !important;
    }
    
    /* Ensure all text inside the buttons inherits active/hover colors */
    section[data-testid="stSidebar"] button *,
    section[data-testid="stSidebar"] button p,
    section[data-testid="stSidebar"] button span {
        color: inherit !important;
        font-size: 14.5px !important;
        font-weight: inherit !important;
    }
    
    /* Remove default Streamlit button focus outline */
    section[data-testid="stSidebar"] button:focus,
    section[data-testid="stSidebar"] button:active,
    section[data-testid="stSidebar"] button:focus-visible {
        outline: none !important;
        box-shadow: none !important;
        border-color: transparent !important;
    }
    
    /* Sidebar badge container positioning */
    .sidebar-btn-wrapper {
        position: relative !important;
        width: 100% !important;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
    }
    
    /* Lightning bolt circle indicator on Settlements */
    .sidebar-btn-badge-lightning {
        position: absolute !important;
        right: 24px !important;
        top: 22px !important;
        transform: translateY(-50%) !important;
        background-color: #0070F3 !important;
        color: white !important;
        width: 16px !important;
        height: 16px !important;
        border-radius: 50% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 9px !important;
        z-index: 10 !important;
        pointer-events: none !important;
        font-weight: bold !important;
    }
    
    /* Sidebar badges for Support & Notifications */
    .sidebar-badge {
        position: absolute !important;
        right: 20px !important;
        top: 22px !important;
        transform: translateY(-50%) !important;
        padding: 2px 7px !important;
        border-radius: 10px !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        pointer-events: none !important;
        z-index: 10 !important;
    }
    .sidebar-badge.badge-red {
        background-color: #EF4444 !important;
        color: #FFFFFF !important;
    }
    .sidebar-badge.badge-blue {
        background-color: #3B82F6 !important;
        color: #FFFFFF !important;
    }
    
    /* Admin Custom Sidebar Navigation */
    .admin-sidebar-section {
        color: #6B7C93;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.8px;
        margin-top: 14px;
        margin-bottom: 4px;
        padding-left: 14px;
        text-transform: uppercase;
        font-family: 'Inter', sans-serif;
    }
    .admin-nav-item {
        display: flex;
        align-items: center;
        padding: 7px 12px;
        margin: 2px 10px;
        border-radius: 6px;
        color: #9AA9BD;
        text-decoration: none;
        font-size: 13.5px;
        font-weight: 500;
        transition: all 0.15s ease;
        cursor: pointer;
        height: 36px;
        box-sizing: border-box;
    }
    .admin-nav-item:hover {
        background-color: rgba(255, 255, 255, 0.05);
        color: #FFFFFF;
        text-decoration: none;
    }
    .admin-nav-item.active {
        background-color: #0B66E4;
        color: #FFFFFF;
        font-weight: 600;
    }
    .admin-nav-icon {
        font-size: 13px;
        margin-right: 10px;
        width: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .admin-nav-text {
        flex-grow: 1;
    }
    .admin-nav-badge {
        padding: 1px 6px;
        border-radius: 10px;
        font-size: 10.5px;
        font-weight: 700;
        line-height: 1.2;
        margin-left: auto;
    }
    .admin-nav-badge.badge-red {
        background-color: #EF4444;
        color: #FFFFFF;
    }
    .admin-nav-badge.badge-blue {
        background-color: #3B82F6;
        color: #FFFFFF;
    }
    
    /* Streamlit Border Container Overrides for Admin Analytics Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02) !important;
        padding: 14px 16px !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        background-color: transparent !important;
    }
    
    /* Admin Fintech KPI Cards */
    .admin-kpi-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 14px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 110px;
        height: 100%;
        box-sizing: border-box;
    }
    .admin-kpi-top {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .admin-kpi-icon {
        width: 28px;
        height: 28px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        flex-shrink: 0;
    }
    .admin-kpi-label {
        font-size: 10px;
        font-weight: 700;
        color: #6B7C93;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .admin-kpi-value {
        font-size: 20px;
        font-weight: 800;
        color: #172B4D;
        font-family: 'Outfit', sans-serif;
        line-height: 1.1;
        margin: 4px 0 2px 0;
    }
    .admin-kpi-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 10.5px;
        color: #6B7C93;
        border-top: 1px solid #F8FAFC;
        padding-top: 4px;
    }
    .admin-kpi-trend {
        font-size: 10px;
        font-weight: 600;
        white-space: nowrap;
    }
    .admin-kpi-trend.trend-green {
        color: #10B981;
    }
    .admin-kpi-trend.trend-red {
        color: #EF4444;
    }
    
    /* Admin Standard Dashboard Cards */
    .admin-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        margin-bottom: 14px;
        box-sizing: border-box;
        overflow-x: auto;
        width: 100%;
    }
    .admin-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .admin-card-title {
        font-size: 14px;
        font-weight: 700;
        color: #172B4D;
        font-family: 'Outfit', sans-serif;
        margin: 0;
    }
    .admin-card-action {
        font-size: 11.5px;
        font-weight: 600;
        color: #2563EB;
        text-decoration: none;
        cursor: pointer;
    }
    .admin-card-action:hover {
        text-decoration: underline;
    }
    
    /* Admin Fintech Tables */
    .admin-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Inter', sans-serif;
        font-size: 11px;
    }
    .admin-table th {
        text-align: left;
        font-size: 9.5px;
        font-weight: 700;
        color: #6B7C93;
        text-transform: uppercase;
        letter-spacing: 0.3px;
        padding: 6px 6px;
        border-bottom: 1px solid #E2E8F0;
        background-color: transparent;
        white-space: nowrap;
    }
    .admin-table td {
        padding: 7px 6px;
        border-bottom: 1px solid #F8FAFC;
        color: #172B4D;
        vertical-align: middle;
        white-space: nowrap;
        font-size: 11px;
    }
    .admin-table tr:last-child td {
        border-bottom: none;
    }
    .admin-table tr:hover td {
        background-color: #F8FAFC;
    }
    
    /* Admin Badge Helpers */
    .admin-badge {
        display: inline-block;
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        text-align: center;
        white-space: nowrap;
    }
    .admin-badge-success {
        background-color: #ECFDF5;
        color: #10B981;
    }
    .admin-badge-warning {
        background-color: #FEF3C7;
        color: #D97706;
    }
    .admin-badge-danger {
        background-color: #FEE2E2;
        color: #EF4444;
    }
    .admin-badge-info {
        background-color: #EFF6FF;
        color: #3B82F6;
    }
    .admin-badge-neutral {
        background-color: #F1F5F9;
        color: #64748B;
    }
    
    .header-search-container {
        background-color: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 6px 12px;
        display: flex;
        align-items: center;
        height: 38px;
        margin-bottom: 12px;
    }
    
    .header-icons-wrapper {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 16px;
        height: 38px;
    }
    
    .header-icon {
        font-size: 1.2rem;
        color: var(--text-sec);
        cursor: pointer;
        transition: color 0.2s, transform 0.2s;
    }
    .header-icon:hover {
        color: var(--primary);
        transform: scale(1.1);
    }
    
    .header-avatar {
        background-color: var(--primary);
        color: #FFFFFF;
        font-weight: 700;
        font-size: 0.8rem;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: transform 0.2s;
        cursor: pointer;
    }
    .header-avatar:hover {
        transform: scale(1.1);
        background-color: #083D63;
    }
    
    .header-divider {
        border-bottom: 1px solid var(--border);
        margin-bottom: 20px;
        margin-top: 4px;
    }
    
    /* Cards Layout styling */
    .kpi-card {
        background-color: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        transition: all 0.2s ease;
        min-height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    .kpi-card:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.06);
    }
    
    .kpi-card.primary-kpi {
        background-color: var(--primary);
        border-color: var(--primary);
        color: #FFFFFF !important;
    }
    
    .kpi-title {
        font-size: 10.5px;
        font-weight: 700;
        color: var(--text-sec);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-bottom: 4px;
    }
    
    .kpi-value {
        font-size: 24px;
        font-weight: 700;
        color: var(--navy);
        font-family: 'Outfit', sans-serif;
        line-height: 1.1;
    }
    
    .kpi-desc {
        font-size: 11px;
        font-weight: 500;
        color: var(--text-sec);
        margin-top: 4px;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    /* White page subpanels */
    .card-panel {
        background-color: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
    }
    
    /* Progress styling */
    .custom-progress-container {
        width: 100%;
        background-color: #E2E8F0;
        border-radius: 4px;
        height: 6px;
        margin-top: 8px;
        margin-bottom: 12px;
        overflow: hidden;
    }
    .custom-progress-bar {
        background-color: var(--primary);
        height: 100%;
        border-radius: 4px;
    }
    
    /* Health Checklist */
    .health-checklist {
        margin-top: 14px;
    }
    .checklist-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        color: var(--navy);
        margin-bottom: 8px;
        font-weight: 500;
    }
    .checklist-item .badge-icon {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 9px;
        font-weight: 700;
    }
    .checklist-item.success .badge-icon {
        background-color: rgba(16, 185, 129, 0.1);
        color: var(--success);
    }
    .checklist-item.warning .badge-icon {
        background-color: rgba(245, 158, 11, 0.1);
        color: var(--warning);
    }
    .checklist-item.error .badge-icon {
        background-color: rgba(239, 68, 68, 0.1);
        color: var(--error);
    }
    
    /* Financial Flow Diagram */
    .flow-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 16px 20px;
        margin-top: 8px;
        margin-bottom: 20px;
        overflow-x: auto;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .flow-step {
        text-align: center;
        flex: 1;
        min-width: 120px;
    }
    .flow-step .step-label {
        font-size: 10.5px;
        font-weight: 700;
        color: var(--text-sec);
        text-transform: uppercase;
        margin-bottom: 4px;
        letter-spacing: 0.5px;
    }
    .flow-step .step-value {
        font-size: 14.5px;
        font-weight: 700;
        color: var(--navy);
        font-family: 'Outfit', sans-serif;
    }
    .flow-arrow {
        font-size: 16px;
        color: #CBD5E1;
        font-weight: 700;
        padding: 0 8px;
    }
    
    /* AI Insights Dashboard block */
    .ai-insights-card {
        background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%);
        border: 1px solid #BFDBFE;
        border-radius: 6px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    .ai-insights-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
    }
    .ai-spark-icon {
        color: var(--primary);
        font-size: 16px;
        font-weight: 700;
    }
    .ai-insights-header h3 {
        margin: 0 !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        color: var(--primary) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .ai-issue-summary {
        margin-top: 10px;
        border-left: 2px solid #3B82F6;
        padding-left: 12px;
    }
    .issue-item {
        font-size: 12.5px;
        margin-bottom: 4px;
        color: var(--navy);
    }
    .text-error {
        color: var(--error);
        font-weight: 600;
    }
    
    /* Premium Table Styling */
    .custom-table-container {
        background-color: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 6px;
        overflow-x: auto;
        margin-top: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
    }
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
        font-family: 'Inter', sans-serif;
        font-size: 13px;
    }
    .custom-table th {
        background-color: #F8FAFC;
        color: var(--text-sec);
        font-weight: 700;
        padding: 10px 14px;
        border-bottom: 1px solid var(--border);
        text-transform: uppercase;
        font-size: 10.5px;
        letter-spacing: 0.5px;
    }
    .custom-table td {
        padding: 10px 14px;
        border-bottom: 1px solid #F1F5F9;
        color: var(--navy);
        font-weight: 500;
        vertical-align: middle;
    }
    .custom-table tr:last-child td {
        border-bottom: none;
    }
    .custom-table tr:hover {
        background-color: #F8FAFC;
    }
    
    /* Status Badge styling */
    .status-pill {
        display: inline-flex;
        align-items: center;
        padding: 3px 8px;
        border-radius: 9999px;
        font-size: 10.5px;
        font-weight: 600;
        text-transform: capitalize;
    }
    .status-pill.reconciled, .status-pill.auto-resolved, .status-pill.verified, .status-pill.ok {
        background-color: rgba(16, 185, 129, 0.1);
        color: var(--success);
        border: 1px solid rgba(16, 185, 129, 0.2);
    }
    .status-pill.needs_review, .status-pill.discrepancy, .status-pill.pending, .status-pill.under_review {
        background-color: rgba(245, 158, 11, 0.1);
        color: var(--warning);
        border: 1px solid rgba(245, 158, 11, 0.2);
    }
    .status-pill.unmatched, .status-pill.failed, .status-pill.missing_bank_credit, .status-pill.high, .status-pill.tds_under_deduction, .status-pill.tds_over_deduction {
        background-color: rgba(239, 68, 68, 0.1);
        color: var(--error);
        border: 1px solid rgba(239, 68, 68, 0.2);
    }
    .status-pill.low {
        background-color: rgba(59, 130, 246, 0.1);
        color: #3B82F6;
        border: 1px solid rgba(59, 130, 246, 0.2);
    }
    .status-pill.medium {
        background-color: rgba(245, 158, 11, 0.1);
        color: var(--warning);
        border: 1px solid rgba(245, 158, 11, 0.2);
    }
    
    .action-link {
        color: var(--primary);
        font-weight: 600;
        text-decoration: none;
        cursor: pointer;
    }
    .action-link:hover {
        text-decoration: underline;
    }
    
    /* 3-way Audit Flow Layout styles */
    .audit-flow-container {
        background-color: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 20px;
        margin-top: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .audit-flow-nodes {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    .audit-flow-node {
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 12px 16px;
        background-color: #F8FAFC;
    }
    .audit-flow-node.active-node {
        border-left: 4px solid var(--primary);
    }
    .audit-flow-node.error-node {
        border-left: 4px solid var(--error);
        background-color: #FFF8F8;
    }
    .audit-flow-arrow {
        text-align: center;
        color: #94A3B8;
        font-size: 16px;
        margin: -6px 0;
    }
    .node-header {
        font-weight: 700;
        font-size: 11px;
        color: var(--text-sec);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .node-details {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 8px;
        font-size: 12.5px;
    }
    .detail-item strong {
        color: var(--text-sec);
        font-weight: 500;
        font-size: 10px;
        text-transform: uppercase;
    }
    .detail-item div {
        color: var(--navy);
        font-weight: 600;
    }
    
    /* AI Explanation Modal/Panel */
    .ai-explanation-panel {
        background-color: #F8FAFC;
        border: 1px solid var(--border);
        border-left: 4px solid var(--primary);
        border-radius: 6px;
        padding: 16px 20px;
        margin-top: 15px;
    }
    .ai-explanation-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    }
    .ai-explanation-header h4 {
        margin: 0 !important;
        color: var(--primary) !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 15px !important;
        font-weight: 700 !important;
    }
    .ai-explanation-checklist {
        list-style: none;
        padding: 0;
        margin: 0 0 10px 0;
    }
    .ai-explanation-checklist li {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12.5px;
        color: var(--navy);
        margin-bottom: 4px;
        font-weight: 500;
    }
    
    /* Admin subtabs horizontal radio styling */
    div[data-testid="stHorizontalBlock"] div.stRadio > div {
        background-color: #FFFFFF;
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 6px 12px;
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
    }
    div[data-testid="stHorizontalBlock"] div.stRadio > label {
        display: none !important;
    }
    
    /* Chat Popover styled floating button in bottom right */
    div[data-testid="stPopover"] {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 99999;
    }
    
    div[data-testid="stPopover"] button {
        width: 54px !important;
        height: 54px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, var(--primary) 0%, #083D63 100%) !important;
        box-shadow: 0 4px 15px rgba(15, 76, 117, 0.4) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
        transition: transform 0.2s ease !important;
    }
    
    div[data-testid="stPopover"] button:hover {
        transform: scale(1.08) !important;
    }
    
    div[data-testid="stPopover"] button p {
        display: none !important;
    }
    
    div[data-testid="stPopover"] button div[data-testid="stMarkdownContainer"] {
        display: none !important;
    }
    
    div[data-testid="stPopover"] button::after {
        content: "✦" !important;
        font-size: 24px !important;
        color: white !important;
        line-height: 1;
        font-weight: bold;
    }
    
    div[data-testid="stPopoverWindow"] {
        width: 400px !important;
        max-height: 480px !important;
        border-radius: 8px !important;
        box-shadow: 0 10px 30px rgba(11, 28, 51, 0.2) !important;
        border: 1px solid var(--border) !important;
        background-color: #FFFFFF !important;
        padding: 12px !important;
    }
    
    .chat-header-spark {
        background: linear-gradient(135deg, #0b1c33 0%, var(--primary) 100%);
        padding: 10px;
        border-radius: 6px;
        color: white;
        margin-bottom: 10px;
        text-align: center;
    }
    .chat-header-spark h3 {
        color: white !important;
        margin: 0 !important;
        font-size: 0.95rem !important;
    }
    .chat-header-spark p {
        color: rgba(255,255,255,0.65) !important;
        margin: 2px 0 0 0 !important;
        font-size: 0.7rem !important;
    }
    
    /* Native streamlit metrics and elements styling fixes */
    [data-testid="stMetricValue"] {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 700 !important;
        color: var(--navy) !important;
    }
    
    [data-testid="stNotification"] {
        border-radius: 6px !important;
        border: 1px solid var(--border) !important;
    }
    
    /* Focus and active input element borders override (replace Streamlit's red/coral theme color) */
    div[data-baseweb="input"] {
        border: 1px solid var(--border) !important;
    }
    div[data-baseweb="input"]:focus-within, 
    div[data-baseweb="input"]:hover {
        border-color: #000000 !important;
        box-shadow: 0 0 0 1px #000000 !important;
    }
    div[data-baseweb="textarea"] {
        border: 1px solid var(--border) !important;
    }
    div[data-baseweb="textarea"]:focus-within, 
    div[data-baseweb="textarea"]:hover {
        border-color: #000000 !important;
        box-shadow: 0 0 0 1px #000000 !important;
    }
    div[data-testid="stChatInput"] textarea:focus {
        border-color: #000000 !important;
        box-shadow: 0 0 0 1px #000000 !important;
    }
    
    /* Selectbox active borders override (replace Streamlit's red/coral theme color) */
    div[data-baseweb="select"] {
        border: 1px solid var(--border) !important;
        border-radius: 4px !important;
    }
    div[data-baseweb="select"]:focus-within, 
    div[data-baseweb="select"]:hover {
        border-color: #000000 !important;
        box-shadow: 0 0 0 1px #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

def clean_html(html_str):
    """Strips all leading and trailing whitespace and removes newlines to guarantee no Markdown code block triggers."""
    return "".join([line.strip() for line in html_str.splitlines() if line.strip()])

def get_mismatch_color_tuple(exceptions, status="NEEDS_REVIEW"):
    """
    Returns (bg_color, text_color, border_color, badge_label, severity_name)
    Categories:
    - RED (Critical): Amount mismatch, Bank credit missing, Missing order/gateway payment, Disputes.
    - YELLOW / AMBER (Rates & Pricing): Fee mismatch, Tax/GST mismatch, Bank settlement amount diff.
    - ORANGE (Status & Lifecycle): Status mismatch, Settled amount diff.
    - GREEN (Auto-Resolved): Auto resolved or no active exceptions.
    """
    if status == "AUTO_RESOLVED" or not exceptions or (isinstance(exceptions, list) and len(exceptions) == 0):
        return ("#ECFDF5", "#10B981", "#A7F3D0", "AUTO_RESOLVED", "RESOLVED")
        
    exc_str = " ".join([str(e) for e in exceptions]).upper() if isinstance(exceptions, list) else str(exceptions).upper()
    
    # 1. RED - Critical / High Severity
    if any(k in exc_str for k in ['AMOUNT_MISMATCH', 'BANK_CREDIT_MISSING', 'MISSING_ORDER', 'NOT_FOUND', 'DISPUTE', 'CHARGEBACK']):
        return ("#FEE2E2", "#EF4444", "#FECACA", "NEEDS_REVIEW (Critical)", "HIGH")
    # 2. YELLOW / AMBER - Pricing, Fee & Tax
    elif any(k in exc_str for k in ['FEE_MISMATCH', 'TAX_MISMATCH', 'GST_MISMATCH', 'BANK_SETTLEMENT_MISMATCH']):
        return ("#FEF3C7", "#D97706", "#FDE68A", "NEEDS_REVIEW (Fee/Tax)", "MEDIUM")
    # 3. ORANGE - Status & Timing differences
    elif any(k in exc_str for k in ['STATUS_MISMATCH', 'SETTLED_AMOUNT_MISMATCH']):
        return ("#FFEDD5", "#EA580C", "#FED7AA", "NEEDS_REVIEW (Status)", "LOW")
    else:
        return ("#FEE2E2", "#EF4444", "#FECACA", "NEEDS_REVIEW", "HIGH")

def get_mismatch_badge_html(exceptions, status="NEEDS_REVIEW"):
    bg, color, border, label, _ = get_mismatch_color_tuple(exceptions, status)
    return f'<span style="background-color: {bg}; color: {color}; border: 1px solid {border}; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 700; white-space: nowrap; display: inline-block;">{label}</span>'

def get_exception_pills_html(exceptions):
    if not exceptions or (isinstance(exceptions, list) and len(exceptions) == 0):
        return '<span style="color: #94A3B8; font-size: 11px;">None</span>'
        
    exc_list = exceptions if isinstance(exceptions, list) else [exceptions]
    pills = []
    for exc_item in exc_list:
        e_str = str(exc_item).upper()
        if any(k in e_str for k in ['AMOUNT_MISMATCH', 'BANK_CREDIT_MISSING', 'MISSING_ORDER', 'NOT_FOUND', 'DISPUTE', 'CHARGEBACK']):
            bg, color, border = '#FEE2E2', '#EF4444', '#FECACA'
            clean = "Amount Mismatch" if "AMOUNT" in e_str else ("Missing Bank Credit" if "BANK_CREDIT" in e_str else ("Missing Order" if "MISSING_ORDER" in e_str or "NOT_FOUND" in e_str else "Dispute"))
        elif any(k in e_str for k in ['FEE_MISMATCH', 'TAX_MISMATCH', 'GST_MISMATCH', 'BANK_SETTLEMENT_MISMATCH']):
            bg, color, border = '#FEF3C7', '#D97706', '#FDE68A'
            clean = "Fee Mismatch" if "FEE" in e_str else ("Tax Mismatch" if "TAX" in e_str or "GST" in e_str else "Settlement Diff")
        elif any(k in e_str for k in ['STATUS_MISMATCH', 'SETTLED_AMOUNT_MISMATCH']):
            bg, color, border = '#FFEDD5', '#EA580C', '#FED7AA'
            clean = "Status Mismatch" if "STATUS" in e_str else "Settled Amt Diff"
        else:
            bg, color, border = '#F1F5F9', '#64748B', '#E2E8F0'
            clean = str(exc_item).split('(')[0].replace('_', ' ').strip().title()
            
        pills.append(f'<span style="background-color: {bg}; color: {color}; border: 1px solid {border}; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; white-space: nowrap; margin-right: 4px; display: inline-block; margin-bottom: 2px;">{clean}</span>')
    return "".join(pills)

def generate_ai_response(user_query, conversation_id=None, merchant_id=None):
    # Retrieve matching segments from .md and .pdf policy files
    api_key = st.session_state.sys_gemini_api_key
    
    # 1. semantic search / RAG retrieval
    retrieved_chunks = []
    if api_key:
        try:
            from src.rag_engine import retrieve_relevant_context_with_sources
            retrieved_chunks = retrieve_relevant_context_with_sources(user_query, api_key, top_n=3, merchant_id=merchant_id)
        except Exception as e:
            print(f"RAG retrieval error: {str(e)}")
            
    # Format retrieved context for prompt
    if retrieved_chunks:
        retrieved_context = "\n\n".join([f"Source: {c['file_name']} (Chunk {c['chunk_index']}):\n{c['text_content']}" for c in retrieved_chunks])
    else:
        retrieved_context = "No document context found."

    # Construct conversation history
    history_context = ""
    if len(st.session_state.messages) > 1:
        history_context = "\nCONVERSATION HISTORY (Previous turns in this thread):\n"
        for msg in st.session_state.messages[:-1]:
            role_label = "USER" if msg['role'] == 'user' else "ASSISTANT"
            # Strip sources block from previous turns so context prompt stays clean
            content_clean = msg['content'].split("---")[0].strip()
            history_context += f"- {role_label}: {content_clean}\n"

    # Core database context prompt (daily close metrics)
    evidence_prompt = f"""
    DAILY CLOSE DATA SUMMARY:
    - Total Payments Processed: {metrics.get('total_payments_processed', 0)}
    - Auto-match Accuracy: {metrics.get('auto_match_accuracy_pct', 0.0)}%
    - Gross Customer Collections: INR {metrics.get('gross_collections_inr', 0.0):,.2f}
    - Refunds Processed: INR {metrics.get('refunds_inr', 0.0):,.2f}
    - Gateway Fees + GST: INR {metrics.get('fees_gst_inr', 0.0):,.2f}
    - Settled to Bank: INR {metrics.get('settled_to_bank_inr', 0.0):,.2f}
    - Expected pending settlement: INR {metrics.get('expected_next_2_days_inr', 0.0):,.2f}
    - Needs Review (Exceptions) count: {metrics.get('needs_review_count', 0)}
    """

    # Grounding System Instructions using the editable template
    full_system_context = st.session_state.sys_system_prompt_template.format(
        evidence_prompt=evidence_prompt,
        retrieved_context=retrieved_context,
        history_context=history_context
    )

    # Generate LLM response
    answer = ""
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(st.session_state.sys_gemini_model)
            full_prompt = f"{full_system_context}\n\nUser Question: {user_query}\n\nAnswer:"
            response = model.generate_content(full_prompt)
            answer = response.text
        except Exception as e:
            answer = f"Gemini connection unavailable.\n\nPlease verify your API configuration.\n\n[Open AI Configuration](?page=settings)"
    else:
        # Fallback to local heuristic engine
        from src.heuristic_engine import local_heuristic_engine
        answer = local_heuristic_engine(user_query, metrics=metrics, df_tx=df_tx, df_unmatched=df_unmatched, bank_excs=bank_excs)

    # 3. Format RAG Metadata & Sources section at the bottom of the answer
    # Check if Gemini was unavailable
    if "Gemini connection unavailable" in answer:
        pass
    elif "No relevant information found" in answer or "information was not found in the available documents" in answer:
        # Grounded failure message
        answer = """No relevant information found

I could not find sufficient information in the available knowledge base to answer this question.

[View Knowledge Base](?page=settings)"""
    elif retrieved_chunks:
        # Deduplicate sources by filename
        unique_docs = {}
        for c in retrieved_chunks:
            fn = c['file_name']
            if fn not in unique_docs:
                unique_docs[fn] = []
            unique_docs[fn].append(c['chunk_index'])
            
        sources_md = "\n\n---\n✦ **RAG-powered response**\n"
        sources_md += f"*{len(retrieved_chunks)} relevant chunks retrieved*\n\n"
        sources_md += "**Sources used:**\n"
        for i, (doc, chunks) in enumerate(unique_docs.items(), 1):
            chunks_str = ", ".join([f"Page {chk+1}" if doc.endswith('.pdf') else f"Chunk {chk}" for chk in chunks])
            sources_md += f"{i}. {doc}\n   {chunks_str}\n"
            
        sources_md += "\n<details>\n<summary><b>[ View Sources ]</b></summary>\n\n"
        for c in retrieved_chunks:
            # Strip filename prefix for cleaner preview
            chunk_display = c['text_content'].replace(f"[{c['file_name']}] ", "")
            sources_md += f"**{c['file_name']} (Chunk {c['chunk_index']}):**\n"
            sources_md += f"> {chunk_display}\n\n"
        sources_md += "</details>"
        
        # Do not append RAG sources metadata to the final response
        # answer += sources_md

    st.session_state.messages.append({"role": "assistant", "content": answer})
    if conversation_id:
        from src.database import save_conversation_message
        save_conversation_message(conversation_id, "assistant", answer)
    else:
        save_chat_message(st.session_state.session_id, "assistant", answer)

def export_data_for_rag(df_tx, df_orders, df_bank, merchant_id="flipkart", store_id="fk_delhi"):
    """Generates structured Markdown files for active database records and indexes them into the RAG vector store."""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        docs_dir = os.path.join(base_dir, "documents")
        os.makedirs(docs_dir, exist_ok=True)
        
        # 1. Export Internal Orders Data
        orders_path = os.path.join(docs_dir, f"07_internal_orders_data_{merchant_id}_{store_id}.md")
        orders_md = "# Internal Orders Database Records\n\n"
        orders_md += "| Order ID | Amount (INR) | Status | Created At | Customer Email |\n"
        orders_md += "|---|---|---|---|---|\n"
        for _, row in df_orders.iterrows():
            created_at_val = row['created_at'] if 'created_at' in df_orders.columns else 'N/A'
            orders_md += f"| {row['order_id']} | {row['amount_inr']:.2f} | {row['status']} | {created_at_val} | {row['customer_email']} |\n"
            
        with open(orders_path, "w", encoding="utf-8") as f:
            f.write(orders_md)
            
        # 2. Export Razorpay Transactions Data
        txs_path = os.path.join(docs_dir, f"08_razorpay_transactions_data_{merchant_id}_{store_id}.md")
        txs_md = "# Razorpay Gateway Transactions Database Records\n\n"
        txs_md += "| Transaction ID | Order ID | Type | Status | Method | Amount (INR) | Fee (INR) | GST (INR) | Settled (INR) | Expected Settlement Date | Timestamp | Resolution Status |\n"
        txs_md += "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        for _, row in df_tx.iterrows():
            timestamp_val = row['timestamp'] if 'timestamp' in df_tx.columns else row.get('expected_settlement_date', 'N/A')
            txs_md += f"| {row['transaction_id']} | {row['order_id']} | {row['type']} | {row['status']} | {row['method']} | {row['amount_inr']:.2f} | {row['fee_inr']:.2f} | {row['tax_inr']:.2f} | {row['settled_amount_inr']:.2f} | {row['expected_settlement_date']} | {timestamp_val} | {row['resolution_status']} |\n"
            
        with open(txs_path, "w", encoding="utf-8") as f:
            f.write(txs_md)
            
        # 3. Export Bank Statements Data
        bank_path = os.path.join(docs_dir, f"09_bank_statements_data_{merchant_id}_{store_id}.md")
        bank_md = "# Bank Statements Database Records\n\n"
        bank_md += "| Value Date | Expected Amount (INR) | Actual Amount (INR) | Difference (INR) | Bank Reference | Status |\n"
        bank_md += "|---|---|---|---|---|---|\n"
        for _, row in df_bank.iterrows():
            expected_val = row.get('expected_amount_inr', row['amount_inr'])
            difference_val = row.get('difference', 0.0)
            bank_md += f"| {row['date']} | {expected_val:.2f} | {row['amount_inr']:.2f} | {difference_val:.2f} | {row['bank_reference']} | {row['status']} |\n"
            
        with open(bank_path, "w", encoding="utf-8") as f:
            f.write(bank_md)
            
        # Re-index newly generated Markdown files (only deleting and indexing the changed ones)
        from src.database import delete_document_chunks
        delete_document_chunks(f"07_internal_orders_data_{merchant_id}_{store_id}.md")
        delete_document_chunks(f"08_razorpay_transactions_data_{merchant_id}_{store_id}.md")
        delete_document_chunks(f"09_bank_statements_data_{merchant_id}_{store_id}.md")
        
        from src.rag_engine import build_document_index
        build_document_index(st.session_state.sys_gemini_api_key, force_reindex=False)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error exporting data for RAG: {str(e)}")

# ----------------------------------------------------
# CUSTOM SIDEBAR NAVIGATION RENDERER
# ----------------------------------------------------
def render_sidebar_item(label, page_name, icon="", badge=""):
    is_active = st.session_state.page == page_name
    is_admin = st.session_state.user and st.session_state.user.get('role') == 'ADMIN'
    if is_active:
        active_class = "sidebar-btn-active-admin" if is_admin else "sidebar-btn-active"
    else:
        active_class = "sidebar-btn-inactive"
        
    badge_html = badge if badge else ""
    st.sidebar.markdown(f'<div class="sidebar-btn-wrapper {active_class}">{badge_html}</div>', unsafe_allow_html=True)
    if st.sidebar.button(f"{icon}  {label}", key=f"btn_nav_{page_name}", use_container_width=True):
        st.session_state.page = page_name
        st.session_state.audit_tx = None
        st.session_state.explain_tx = None
        st.query_params.clear()
        st.query_params.page = page_name
        st.rerun()

# Render Sidebar Title & Subtitle
# Base64 encode logo.png for sidebar rendering
import base64
base_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(base_dir, "logo.png")
logo_base64 = ""
if os.path.exists(logo_path):
    with open(logo_path, "rb") as logo_file:
        logo_base64 = base64.b64encode(logo_file.read()).decode("utf-8")

# Render Sidebar Title & Subtitle using the brand logo
st.sidebar.markdown(clean_html(f"""
<div class="sidebar-logo">
    <div style="display: flex; align-items: center; gap: 12px;">
        <img src="data:image/png;base64,{logo_base64}" style="width: 42px; height: 42px; border-radius: 8px; object-fit: cover;">
        <div style="display: flex; flex-direction: column; font-family: 'Outfit', sans-serif;">
            <span style="color: #FFFFFF; font-weight: 800; font-size: 1.15rem; line-height: 1.15; letter-spacing: -0.3px;">AI Finance</span>
            <span style="color: #9AA9BD; font-weight: 600; font-size: 0.85rem; letter-spacing: 0.5px;">Controller</span>
        </div>
    </div>
</div>
<div style="border-bottom: 1px solid rgba(255, 255, 255, 0.05); width: 84%; margin: 8px auto 14px auto;"></div>
"""), unsafe_allow_html=True)

# Render Sidebar Menu groupings and items based on role
user = st.session_state.user
if user and user.get('role') == 'ADMIN':
    st.sidebar.markdown('<div class="sidebar-section-header">ADMIN CONSOLE</div>', unsafe_allow_html=True)
    render_sidebar_item("Dashboard", "admin", "▣")
    render_sidebar_item("Merchants", "admin_merchants", "♙")
    render_sidebar_item("Stores", "admin_stores", "⌂")
    render_sidebar_item("Transactions", "admin_transactions", "⇄")
    render_sidebar_item("Reconciliation", "admin_reconciliation", "⇄")
    render_sidebar_item("Exceptions", "admin_exceptions", "⇄")
    render_sidebar_item("Settlements", "admin_settlements", "▣")
    render_sidebar_item("Payouts", "admin_payouts", "⇄")
    
    st.sidebar.markdown('<div class="sidebar-section-header">SUPPORT</div>', unsafe_allow_html=True)
    # Dynamic open tickets count
    open_tickets_count = 5
    try:
        from src.database import get_support_tickets
        all_tks = get_support_tickets()
        open_tks = [t for t in all_tks if t.get('status') in ['OPEN', 'PENDING']]
        if open_tks:
            open_tickets_count = len(open_tks)
    except Exception:
        pass
    render_sidebar_item("Support Tickets", "admin_tickets", "⚙", badge=f'<div class="sidebar-badge badge-red">{open_tickets_count}</div>')
    render_sidebar_item("Notifications", "admin_notifications", "♧", badge='<div class="sidebar-badge badge-blue">12</div>')
    
    st.sidebar.markdown('<div class="sidebar-section-header">INTELLIGENCE</div>', unsafe_allow_html=True)
    render_sidebar_item("AI & RAG Center", "admin_ai", "✦")
    render_sidebar_item("Knowledge Base", "admin_kb", "▤")
    
    st.sidebar.markdown('<div class="sidebar-section-header">ADMINISTRATION</div>', unsafe_allow_html=True)
    render_sidebar_item("Users & Access", "admin_users", "♙")
    render_sidebar_item("Audit Logs", "admin_audit", "▤")
    render_sidebar_item("Settings", "admin_settings", "⚙")
else:
    st.sidebar.markdown('<div class="sidebar-section-header">OVERVIEW</div>', unsafe_allow_html=True)
    render_sidebar_item("Dashboard", "dashboard", "\u25A3")
    
    st.sidebar.markdown('<div class="sidebar-section-header">RECONCILIATION</div>', unsafe_allow_html=True)
    render_sidebar_item("Transactions", "transactions", "\u21C4")
    render_sidebar_item("Exceptions", "exceptions", "\u26A0")
    render_sidebar_item("Settlements", "settlements", "\u2713", badge='<div class="sidebar-btn-badge-lightning">⚡</div>')
    
    st.sidebar.markdown('<div class="sidebar-section-header">FINANCE</div>', unsafe_allow_html=True)
    render_sidebar_item("Payouts", "payouts", "\u20B9")
    render_sidebar_item("Bank", "bank", "\u25A3")
    render_sidebar_item("Tax & TDS", "tax", "\u25A4")
    
    st.sidebar.markdown('<div class="sidebar-section-header">INSIGHTS</div>', unsafe_allow_html=True)
    render_sidebar_item("AI Insights", "insights", "\u2726")
    render_sidebar_item("Cash Forecast", "forecast", "\u2197")
    render_sidebar_item("Raise Ticket", "tickets", "\U0001F39F")
    
    st.sidebar.markdown('<div style="border-bottom: 1px solid rgba(255, 255, 255, 0.05); width: 84%; margin: 12px auto 14px auto;"></div>', unsafe_allow_html=True)
    render_sidebar_item("Settings", "settings", "\u2699")

# Profile info area at the bottom
if user:
    role_label = "Razorpay Admin" if user.get('role') == 'ADMIN' else f"{(user.get('merchant_id') or '').upper()} - {(user.get('store_id') or '').split('_')[-1].upper()}"
    initials = "RA" if user.get('role') == 'ADMIN' else f"{(user.get('merchant_id') or 'M')[:1].upper()}{(user.get('store_id') or 'S').split('_')[-1][:1].upper()}"
    user_email = user.get('email', '')

    st.sidebar.markdown(f"""
    <div style="padding: 12px 24px; border-top: 1px solid rgba(255,255,255,0.05); margin-top: 10px; display: flex; align-items: center; gap: 10px;">
        <div style="width: 32px; height: 32px; border-radius: 50%; background-color: #0F4C75; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 13px; font-family: 'Outfit', sans-serif;">
            {initials}
        </div>
        <div style="display: flex; flex-direction: column; font-family: 'Inter', sans-serif;">
            <span style="color: white; font-weight: 600; font-size: 13px; line-height: 1.2;">{role_label}</span>
            <span style="color: #9AA9BD; font-size: 11px;">{user_email}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.sidebar.button("🚪 Log Out", key="logout_sidebar_btn", use_container_width=True):
        from src.database import log_action, delete_user_session
        log_action(user.get('user_id', ''), "User Logout", "Logged out successfully.")
        token = st.context.cookies.get("session_token")
        if token:
            delete_user_session(token)
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.page = "dashboard"
        import streamlit.components.v1 as components
        components.html("""
        <script>
            window.parent.document.cookie = "session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;";
            window.parent.location.reload();
        </script>
        """, height=0, width=0)
        st.stop()

# ----------------------------------------------------
# TOP HEADER BAR IMPLEMENTATION
# ----------------------------------------------------
if "active_batch" not in st.session_state:
    st.session_state.active_batch = "Razorpay Synthetic Batch (60 records)"

if st.session_state.page == "dashboard":
    col_header_left, col_header_right = st.columns([2.2, 1.8])
    with col_header_left:
        st.markdown(clean_html(f"""
        <form action="" method="get" target="_self" style="width: 100%; margin: 0; padding: 0;">
            <input type="hidden" name="page" value="{st.session_state.page}">
            <div class="header-search-container">
                <span style="font-size: 1rem; margin-right: 8px; color: #6B7C93;">🔍</span>
                <input type="text" name="search" placeholder="Search transaction IDs, orders, or settlement credits..." style="border: none; outline: none; width: 100%; font-size: 0.85rem; font-weight: 500; color: #172B4D; font-family: 'Inter', sans-serif; background: transparent;">
            </div>
        </form>
        """), unsafe_allow_html=True)

    with col_header_right:
        col_sub_icons, col_sub_sel = st.columns([1, 2])
        with col_sub_icons:
            st.markdown(clean_html("""
            <div class="header-icons-wrapper">
                <a href="?notify=true" target="_self" class="header-icon" title="Notifications" style="text-decoration: none;">🔔</a>
                <a href="?page=settings" target="_self" class="header-icon" title="Help Centre" style="text-decoration: none;">❓</a>
                <a href="?page=settings" target="_self" class="header-avatar" title="Shivendu K (Admin)" style="text-decoration: none; color: white;">FK</a>
            </div>
            """), unsafe_allow_html=True)
        with col_sub_sel:
            # Dynamic interactive batch selector
            dataset_option = st.selectbox(
                "Reconciliation Batch Selection",
                ["Razorpay Synthetic Batch (60 records)", "Example August 25 Daily Close (80 records)"],
                label_visibility="collapsed",
                key="header_batch_selector"
            )
            st.session_state.active_batch = dataset_option

    st.markdown('<div class="header-divider"></div>', unsafe_allow_html=True)
else:
    dataset_option = st.session_state.active_batch

# ----------------------------------------------------
# CORE ENGINE DATA RETRIEVAL
# ----------------------------------------------------
# Resolve multi-tenant filter scoping
if "admin_filter_merchant" not in st.session_state:
    st.session_state.admin_filter_merchant = None
if "admin_filter_store" not in st.session_state:
    st.session_state.admin_filter_store = None

user = st.session_state.user
if user and user['role'] == 'MERCHANT':
    current_merchant_id = user['merchant_id']
    current_store_id = user['store_id']
else:
    current_merchant_id = st.session_state.admin_filter_merchant
    current_store_id = st.session_state.admin_filter_store

# Execute the relevant batch retrieval
if dataset_option == "Razorpay Synthetic Batch (60 records)":
    metrics, df_tx, df_unmatched, df_bank, bank_excs = run_3way_reconciliation(current_merchant_id, current_store_id)
else:
    # AUGUST 25 DATASET MOCK ENDPOINT (Adapt to current store)
    metrics, df_tx, df_unmatched, df_bank, bank_excs = get_august_25_example_data(current_merchant_id or "flipkart", current_store_id or "fk_delhi")

# Filter internal orders global dataframe to scope it to tenant store
if current_merchant_id and current_store_id:
    df_orders_scoped = df_orders[(df_orders['merchant_id'] == current_merchant_id) & (df_orders['store_id'] == current_store_id)].copy()
elif current_merchant_id:
    df_orders_scoped = df_orders[df_orders['merchant_id'] == current_merchant_id].copy()
else:
    df_orders_scoped = df_orders.copy()

# Trigger dynamic dataset RAG export only when the active batch selection changes
if st.session_state.current_indexed_batch != dataset_option:
    st.session_state.current_indexed_batch = dataset_option
    try:
        export_data_for_rag(df_tx, df_orders_scoped, df_bank, current_merchant_id or "flipkart", current_store_id or "fk_delhi")
    except Exception as e:
        st.error(f"Failed to export data for RAG: {e}")

# Handle search and notify queries
query_params = st.query_params
if "notify" in query_params:
    st.toast("🔔 Notifications: Today's closing batch contains 16 unresolved gateway exceptions.", icon="⚠️")
    st.query_params.clear()
    if "page" in st.session_state:
        st.query_params.page = st.session_state.page
if "search" in query_params:
    q = query_params["search"].strip()
    if q:
        matches = df_tx[df_tx['transaction_id'].str.contains(q, case=False, na=False) | df_tx['order_id'].str.contains(q, case=False, na=False)]
        if not matches.empty:
            st.session_state.page = "transactions"
            st.session_state.audit_tx = matches.iloc[0]['transaction_id']
            st.query_params.clear()
            st.query_params.page = "transactions"
            st.query_params.audit_tx = matches.iloc[0]['transaction_id']
            st.rerun()

# Apply local exception resolutions dynamically
if len(st.session_state.resolved_exceptions) > 0:
    if "resolution_notes" not in st.session_state:
        st.session_state.resolution_notes = {}
    for res_id in st.session_state.resolved_exceptions:
        # Reconcile df_tx
        idx_list = df_tx[df_tx['transaction_id'] == res_id].index
        if not idx_list.empty:
            df_tx.loc[idx_list, 'resolution_status'] = 'AUTO_RESOLVED'
            for idx in idx_list:
                df_tx.at[idx, 'calculated_exceptions'] = []
            df_tx.loc[idx_list, 'confidence_score'] = 1.0
            note_val = st.session_state.resolution_notes.get(res_id, "Manually corrected by Administrator.")
            df_tx.loc[idx_list, 'resolution_note'] = note_val
            
        # Reconcile df_unmatched
        idx_list_un = df_unmatched[df_unmatched['order_id'] == res_id].index
        if not idx_list_un.empty:
            df_unmatched.loc[idx_list_un, 'resolution_status'] = 'AUTO_RESOLVED'
            for idx in idx_list_un:
                df_unmatched.at[idx, 'calculated_exceptions'] = []
            df_unmatched.loc[idx_list_un, 'confidence_score'] = 1.0
            
    # Recalculate metrics based on resolutions
    needs_review_tx = df_tx[df_tx['resolution_status'] == 'NEEDS_REVIEW']
    needs_review_un = df_unmatched[df_unmatched['resolution_status'] == 'NEEDS_REVIEW']
    total_active_exceptions = len(needs_review_tx) + len(needs_review_un)
    
    metrics['needs_review_count'] = total_active_exceptions
    metrics['auto_resolved_count'] = len(df_tx) - len(needs_review_tx) + (len(df_unmatched) - len(needs_review_un))
    total_elements = len(df_tx) + len(df_unmatched)
    metrics['auto_match_accuracy_pct'] = round((metrics['auto_resolved_count'] / total_elements) * 100, 1)

# Run forecasting and tax compliance checkers
forecast_df = get_cash_forecast(df_tx, df_bank, days=7)
tax_summary, tax_df = run_tax_audit(df_tx, tds_config=st.session_state.sys_tds_config)

# ----------------------------------------------------
# PAGE 1: MERCHANT DASHBOARD
# ----------------------------------------------------
if st.session_state.page == "dashboard":
    st.markdown("<h2 style='margin-bottom: 2px;'>Hello, Welcome to Finance Controller</h2>", unsafe_allow_html=True)
    
    # Subtitle with metadata & Refresh Action
    col_sub_meta, col_sub_act = st.columns([3, 1])
    with col_sub_meta:
        st.markdown(f"""
        <div style="font-size: 0.95rem; color: #6B7C93; margin-bottom: 20px;">
            Active Batch: <strong style="color: #172B4D;">{dataset_option.split('(')[0].strip()}</strong> 
            • <strong style="color: #1F2A37;">{metrics['total_transactions']} transactions</strong> 
            • Last synced: 2 min ago
        </div>
        """, unsafe_allow_html=True)
    with col_sub_act:
        if st.button("🔄 Refresh Data Feed", key="dashboard_refresh_btn", use_container_width=True):
            st.rerun()
            
    # KPI Grid (5 Columns)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Transactions</div>
            <div class="kpi-value">{metrics['total_payments_processed']}</div>
            <div class="kpi-desc"><span style="color: var(--primary);">●</span> Batch volume</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        # Reconciled is the primary rate card (Razorpay blue background card)
        acc_val = metrics['auto_match_accuracy_pct']
        st.markdown(f"""
        <div class="kpi-card primary-kpi">
            <div class="kpi-title" style="color: rgba(255,255,255,0.75);">Reconciled</div>
            <div class="kpi-value" style="color: #FFFFFF;">{metrics['auto_resolved_count']}</div>
            <div class="kpi-desc" style="color: rgba(255,255,255,0.85);">{acc_val}% solved rate</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Exceptions</div>
            <div class="kpi-value" style="color: var(--error);">{metrics['needs_review_count']}</div>
            <div class="kpi-desc"><span style="color: var(--error);">⚠</span> Needs review</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Settled to Bank</div>
            <div class="kpi-value">₹{metrics['settled_to_bank_inr']:,.2f}</div>
            <div class="kpi-desc"><span style="color: var(--success);">✓</span> Verified Credit</div>
        </div>
        """, unsafe_allow_html=True)
    with k5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Expected Settlement</div>
            <div class="kpi-value">₹{metrics['expected_next_2_days_inr']:,.2f}</div>
            <div class="kpi-desc"><span style="color: var(--warning);">⏳</span> T+2 Pending</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Reconciliation Health layout
    col_hl, col_hr = st.columns([1.1, 0.9])
    
    with col_hl:
        st.markdown("### RECONCILIATION HEALTH")
        st.markdown(f"""
        <div class="card-panel" style="min-height: 260px;">
            <div style="font-size: 1.6rem; font-weight: 700; color: var(--navy); font-family: 'Outfit', sans-serif;">{acc_val}%</div>
            <div style="font-size: 0.85rem; color: var(--text-sec); font-weight: 600; margin-bottom: 12px;">
                {metrics['auto_resolved_count']} of {metrics['total_transactions']} transactions reconciled
            </div>
            <div class="custom-progress-container">
                <div class="custom-progress-bar" style="width: {acc_val}%;"></div>
            </div>
            <div class="health-checklist">
                <div class="checklist-item success">
                    <span class="badge-icon">✓</span>
                    <span>Gateway matched ({metrics['total_payments_processed']}/{metrics['total_payments_processed']} payment records verified)</span>
                </div>
                <div class="checklist-item success">
                    <span class="badge-icon">✓</span>
                    <span>Bank statement verified (settlement entries match statement deposits)</span>
                </div>
                <div class="checklist-item warning">
                    <span class="badge-icon">⚠</span>
                    <span>{metrics['needs_review_count']} transactions require manual investigation</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_hr:
        st.markdown("### RECONCILIATION TREND")
        # Reconciliation health Plotly Stacked Bar Chart
        fig = go.Figure()
        # Grouped bar data
        fig.add_trace(go.Bar(
            x=['Aug 20', 'Aug 21', 'Aug 22', 'Aug 23', 'Aug 24', 'Aug 25'],
            y=[15, 12, 10, 5, 1, 0],
            name='Reconciled',
            marker_color='#0F4C75'
        ))
        fig.add_trace(go.Bar(
            x=['Aug 20', 'Aug 21', 'Aug 22', 'Aug 23', 'Aug 24', 'Aug 25'],
            y=[0, 1, 2, 5, 8, 2],
            name='Exceptions',
            marker_color='#F59E0B'
        ))
        fig.update_layout(
            barmode='stack',
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor='#F1F5F9')
        )
        st.plotly_chart(fig, use_container_width=True)

    # Financial flow overview
    st.markdown("### FINANCIAL FLOW OVERVIEW")
    st.markdown(clean_html("""
    <div class="flow-container">
        <div class="flow-step">
            <div class="step-label">Customer Collections</div>
            <div class="step-value">₹72,392.00</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
            <div class="step-label">Refunds</div>
            <div class="step-value">-₹8,500.00</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
            <div class="step-label">Gateway Fees & GST</div>
            <div class="step-value">-₹2,341.00</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
            <div class="step-label">Net Collections</div>
            <div class="step-value">₹61,551.00</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
            <div class="step-label">Expected Settlement</div>
            <div class="step-value">₹61,551.00</div>
        </div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">
            <div class="step-label" style="color: var(--success);">Bank Settlement</div>
            <div class="step-value" style="color: var(--success); font-weight: 800;">₹61,551.00</div>
        </div>
    </div>
    """), unsafe_allow_html=True)
    
    # AI insights card
    st.markdown("### AI INSIGHTS")
    st.markdown(f"""
    <div class="ai-insights-card">
        <div class="ai-insights-header">
            <span class="ai-spark-icon">✦</span>
            <h3>AI Finance Insights</h3>
        </div>
        <div class="ai-insights-content">
            <p style="font-size: 13.5px; font-weight: 500; margin: 0 0 10px 0;">Today's batch reconciliation is <strong>{acc_val}% complete</strong>. The system has flagged <strong>{metrics['needs_review_count']} transactions</strong> requiring audit verification.</p>
            <div class="ai-issue-summary">
                <div class="issue-item"><strong>Primary Driver:</strong> Settlement discrepancies hit Aug 22 batches.</div>
                <div class="issue-item"><strong>Potential Impact:</strong> <span class="text-error">₹8,420.00</span> in bank credits requires explanation.</div>
                <div class="issue-item"><strong>Recommended Action:</strong> Run a bank credit audit and check Razorpay payouts.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_act_left, col_act_right = st.columns([1, 3])
    with col_act_left:
        if st.button("Review Exceptions Queue", key="ai_redirect_exceptions_btn", use_container_width=True):
            st.session_state.page = "exceptions"
            st.rerun()
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Daily Close Workflow Section
    st.markdown("### DAILY CLOSE WORKFLOW")
    exceptions_unresolved = metrics['needs_review_count']
    if exceptions_unresolved > 0:
        st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid var(--border); border-left: 4px solid var(--warning); padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <h4 style="color: var(--warning); margin: 0 0 8px 0; font-size: 15px;">DAILY CLOSE STATUS: PENDING ACTIONS</h4>
            <div class="health-checklist" style="margin-top: 10px; margin-bottom: 15px;">
                <div class="checklist-item success"><span class="badge-icon">✓</span> Gateway reconciliation complete (60/60 matched)</div>
                <div class="checklist-item success"><span class="badge-icon">✓</span> Bank settlement deposits verified</div>
                <div class="checklist-item success"><span class="badge-icon">✓</span> Gateway processing fees validated</div>
                <div class="checklist-item error"><span class="badge-icon">⚠</span> {exceptions_unresolved} exceptions require manual attention</div>
                <div class="checklist-item success"><span class="badge-icon">✓</span> Tax compliance & TDS checks completed</div>
            </div>
            <p style="margin: 0 0 15px 0; font-size: 13.5px; font-weight: 500; color: var(--navy);">
                <strong>{exceptions_unresolved} unresolved exceptions</strong> are preventing batch closure. You must audit and resolve these exceptions before closing today's daily ledger.
            </p>
        </div>
        """, unsafe_allow_html=True)
        col_c1, col_csp = st.columns([1.2, 4.8])
        with col_c1:
            if st.button("Review Exceptions Queue", key="close_review_exceptions_btn", use_container_width=True):
                st.session_state.page = "exceptions"
                st.rerun()
    else:
        st.markdown(f"""
        <div style="background-color: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-left: 4px solid var(--success); padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
            <h4 style="color: var(--success); margin: 0 0 8px 0; font-size: 15px;">✓ DAILY CLOSE READY</h4>
            <div class="health-checklist" style="margin-top: 10px; margin-bottom: 15px;">
                <div class="checklist-item success"><span class="badge-icon">✓</span> Gateway reconciliation complete (all payments matched)</div>
                <div class="checklist-item success"><span class="badge-icon">✓</span> Bank settlement deposits verified</div>
                <div class="checklist-item success"><span class="badge-icon">✓</span> Gateway processing fees validated</div>
                <div class="checklist-item success"><span class="badge-icon">✓</span> All exceptions successfully resolved</div>
                <div class="checklist-item success"><span class="badge-icon">✓</span> Tax compliance & GST audits passed</div>
            </div>
            <p style="margin: 0 0 15px 0; font-size: 13.5px; font-weight: 500; color: var(--navy);">
                All accounts are fully reconciled. Today's ledger batch is balanced and prepared for official closing.
            </p>
        </div>
        """, unsafe_allow_html=True)
        col_c1, col_c2, col_csp = st.columns([1.2, 1, 3.8])
        with col_c1:
            if st.button("Generate Close Report", key="close_gen_report_btn", use_container_width=True):
                st.success("Daily Close Summary Report generated and saved to exports.")
        with col_c2:
            if st.button("Close Ledger Batch", key="close_batch_btn", use_container_width=True):
                st.balloons()
                st.success("Batch successfully closed and archived in general ledger.")

# ----------------------------------------------------
# PAGE 2: TRANSACTIONS LEDGER & AUDIT
# ----------------------------------------------------
elif st.session_state.page == "transactions":
    
    # CHECK IF SINGLE TRANSACTION AUDIT VIEW IS ACTIVE
    if st.session_state.audit_tx:
        st.markdown(f"<h2>Transaction Audit: `{st.session_state.audit_tx}`</h2>", unsafe_allow_html=True)
        
        # Row layout for back controls
        col_back, col_explain = st.columns([1, 3])
        with col_back:
            if st.button("← Back to Ledger", key="back_to_ledger_btn", use_container_width=True):
                st.session_state.audit_tx = None
                st.session_state.explain_tx = None
                st.query_params.clear()
                st.query_params.page = "transactions"
                st.rerun()
                
        # Load transaction details
        tx_row_matches = df_tx[df_tx['transaction_id'] == st.session_state.audit_tx]
        if tx_row_matches.empty:
            st.error("Transaction not found in active batch.")
        else:
            tx_row = tx_row_matches.iloc[0]
            o_id = tx_row['order_id']
            
            # Draw Audit Nodes
            st.markdown("### THREE-WAY AUDIT VERIFICATION")
            
            # Node 1: Internal Order
            ord_amt = "₹0.00"
            ord_status = "Not Found"
            ord_class = "error-node"
            
            if o_id:
                ord_match = df_orders_scoped[df_orders_scoped['order_id'] == o_id]
                # Mock details if example batch is used and order matches exception patterns
                if dataset_option != "Razorpay Synthetic Batch (60 records)":
                    if "fee" in o_id or "disp" in o_id or "bank" in o_id:
                        ord_match = pd.DataFrame([{'order_id': o_id, 'amount_inr': tx_row['amount_inr'], 'status': 'completed'}])
                    elif "amt" in o_id:
                        ord_match = pd.DataFrame([{'order_id': o_id, 'amount_inr': 8500.00, 'status': 'completed'}])
                    else:
                        ord_match = pd.DataFrame([{'order_id': o_id, 'amount_inr': tx_row['amount_inr'], 'status': 'completed'}])
                        
                if not ord_match.empty:
                    o_row = ord_match.iloc[0]
                    ord_amt = f"₹{o_row['amount_inr']:,.2f}"
                    ord_status = o_row['status'].upper()
                    ord_class = "active-node"
            
            # Node 2: Gateway Details
            gate_class = "active-node"
            if len(tx_row['calculated_exceptions']) > 0 and any('FEE' in str(e) or 'TAX' in str(e) for e in tx_row['calculated_exceptions']):
                gate_class = "error-node"
                
            # Node 3: Bank Credit details
            bank_amt = "₹0.00"
            bank_ref = "No Reference"
            bank_status = "Omitted"
            bank_class = "error-node"
            s_date = tx_row['expected_settlement_date']
            
            if s_date:
                bank_row = df_bank[df_bank['date'] == s_date]
                if not bank_row.empty:
                    b_row = bank_row.iloc[0]
                    if b_row['status'] == 'RECONCILED':
                        bank_amt = f"₹{tx_row['settled_amount_inr']:,.2f}"
                        bank_ref = b_row['bank_reference']
                        bank_status = "VERIFIED CREDIT"
                        bank_class = "active-node"
                    elif b_row['status'] == 'SETTLEMENT_AMOUNT_MISMATCH':
                        bank_amt = f"₹{b_row['amount_inr']:,.2f}"
                        bank_ref = b_row['bank_reference']
                        bank_status = "SETTLEMENT MISMATCH"
                        bank_class = "error-node"
            
            # Render Audit Flow Nodes as HTML
            st.markdown(clean_html(f"""
            <div class="audit-flow-container">
                <div class="audit-flow-nodes">
                    <!-- Node 1: Internal Orders -->
                    <div class="audit-flow-node {ord_class}">
                        <div class="node-header">01 Internal Order Ledger</div>
                        <div class="node-details">
                            <div class="detail-item"><strong>Order ID</strong><div>{o_id or 'Missing'}</div></div>
                            <div class="detail-item"><strong>Ledger Amount</strong><div>{ord_amt}</div></div>
                            <div class="detail-item"><strong>Sync Status</strong><div>{ord_status}</div></div>
                        </div>
                    </div>
                    
                    <div class="audit-flow-arrow">↓</div>
                    
                    <!-- Node 2: Gateway (Razorpay) -->
                    <div class="audit-flow-node {gate_class}">
                        <div class="node-header">02 Razorpay Gateway Capture</div>
                        <div class="node-details">
                            <div class="detail-item"><strong>Transaction ID</strong><div>{tx_row['transaction_id']}</div></div>
                            <div class="detail-item"><strong>Captured Amount</strong><div>₹{tx_row['amount_inr']:,.2f}</div></div>
                            <div class="detail-item"><strong>Fees & GST</strong><div>₹{tx_row['fee_inr']:,.2f} + ₹{tx_row['tax_inr']:,.2f}</div></div>
                            <div class="detail-item"><strong>Settlement Net</strong><div>₹{tx_row['settled_amount_inr']:,.2f}</div></div>
                            <div class="detail-item"><strong>Expected Settlement</strong><div>{tx_row['expected_settlement_date']}</div></div>
                            <div class="detail-item"><strong>Payment Type</strong><div>{tx_row['type']} ({tx_row['method']})</div></div>
                        </div>
                    </div>
                    
                    <div class="audit-flow-arrow">↓</div>
                    
                    <!-- Node 3: Bank Statement -->
                    <div class="audit-flow-node {bank_class}">
                        <div class="node-header">03 Bank Statement Credit</div>
                        <div class="node-details">
                            <div class="detail-item"><strong>Credit Date</strong><div>{s_date or 'No date'}</div></div>
                            <div class="detail-item"><strong>Bank Net Credit</strong><div>{bank_amt}</div></div>
                            <div class="detail-item"><strong>Bank Reference</strong><div>{bank_ref}</div></div>
                            <div class="detail-item"><strong>Credit Status</strong><div>{bank_status}</div></div>
                        </div>
                    </div>
                </div>
            </div>
            """), unsafe_allow_html=True)
            
            # Reconcile verdict card
            st.markdown("### AUDIT VERDICT")
            if len(tx_row['calculated_exceptions']) == 0:
                st.markdown("""
                <div style="background-color: rgba(16, 185, 129, 0.08); border-left: 4px solid var(--success); padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                    <h5 style="color: var(--success); margin: 0 0 4px 0;">✓ AUTO-RESOLVED</h5>
                    <p style="margin: 0; font-size: 13px; font-weight: 500;">Confidence: 100%. All reconciliation audit checks passed successfully.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                ex_clean = [str(ex).replace('₹', 'Rs.') for ex in tx_row['calculated_exceptions']]
                st.markdown(f"""
                <div style="background-color: rgba(239, 68, 68, 0.08); border-left: 4px solid var(--error); padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                    <h5 style="color: var(--error); margin: 0 0 4px 0;">⚠ NEEDS REVIEW</h5>
                    <p style="margin: 0; font-size: 13px; font-weight: 600;">Discrepancies isolated: {ex_clean}</p>
                    <p style="margin: 6px 0 0 0; font-size: 12px; color: var(--text-sec);">AI Recommendation: Inspect order mappings and charge parameters to identify charge discrepancies.</p>
                </div>
                """, unsafe_allow_html=True)
                
            # Explain Decision button
            col_dec_btn, col_dec_spc = st.columns([1, 2.5])
            with col_dec_btn:
                if st.button("✦ Explain Decision with AI", key="explain_decision_btn", use_container_width=True):
                    st.session_state.explain_tx = st.session_state.audit_tx
                    st.rerun()
            
            # Show AI explanation panel if active
            if st.session_state.explain_tx == st.session_state.audit_tx:
                st.markdown("### AI EXPLANATION")
                if len(tx_row['calculated_exceptions']) == 0:
                    st.markdown("""
                    <div class="ai-explanation-panel">
                        <div class="ai-explanation-header">
                            <span class="ai-spark-icon">✦</span>
                            <h4>AI RECONCILIATION EXPLANATION</h4>
                        </div>
                        <ul class="ai-explanation-checklist">
                            <li><span style="color: var(--success); font-weight: bold;">✓</span> Order ID matched</li>
                            <li><span style="color: var(--success); font-weight: bold;">✓</span> Gateway transaction matched</li>
                            <li><span style="color: var(--success); font-weight: bold;">✓</span> Amount matched</li>
                            <li><span style="color: var(--success); font-weight: bold;">✓</span> Fee validated</li>
                            <li><span style="color: var(--success); font-weight: bold;">✓</span> GST validated</li>
                            <li><span style="color: var(--success); font-weight: bold;">✓</span> Bank settlement matched</li>
                        </ul>
                        <div style="font-size: 12.5px; font-weight: 500;">
                            <strong>Confidence: 100%</strong><br>
                            Conclusion: No discrepancies detected. All parameters verify against merchant guidelines.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Failed explanation
                    st.markdown(f"""
                    <div class="ai-explanation-panel" style="border-left-color: var(--error);">
                        <div class="ai-explanation-header">
                            <span class="ai-spark-icon" style="color: var(--error);">✦</span>
                            <h4 style="color: var(--error);">AI RECONCILIATION EXPLANATION</h4>
                        </div>
                        <div style="font-size: 13px; font-weight: 500; line-height: 1.5;">
                            <strong>Anomalies Detected:</strong><br>
                            - Exceptions flagged: <span style="color: var(--error);">{ex_clean}</span><br><br>
                            <strong>Analysis Conclusion:</strong><br>
                            The mathematical verification checks failed. The gateway processing charges did not match the default rate rules ({st.session_state.sys_gateway_fee}% standard, {st.session_state.sys_gst_rate}% GST on fees).
                            Specifically, the recorded gateway fee of ₹{tx_row['fee_inr']:.2f} differs from the expected amount, causing settlement net differences.<br><br>
                            <strong>Recommended action:</strong> Adjust settlement rules in settings or contact support to resolve discrepancy.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

    else:
        # REGULAR TRANSACTIONS LEDGER TABLE VIEW
        st.markdown("<h2>Payment Gateway Transactions</h2>", unsafe_allow_html=True)
        
        # Filters Row
        fl_s, fl_t, fl_m, fl_search = st.columns([1, 1, 1, 1.5])
        
        with fl_s:
            status_filter = st.selectbox(
                "Resolution Status",
                ["All Statuses", "Auto-Resolved", "Needs Review (Exceptions)"]
            )
        with fl_t:
            type_filter = st.selectbox(
                "Transaction Type",
                ["All Types", "PAYMENT", "REFUND", "PAYOUT"]
            )
        with fl_m:
            method_filter = st.selectbox(
                "Payment Method",
                ["All Methods", "upi", "card", "netbanking", "wallet"]
            )
        with fl_search:
            search_query = st.text_input(
                "Search transaction/order ID",
                placeholder="Search pay_xxx or order_xxx..."
            )
            
        # Apply filters to df_tx
        display_df = df_tx.copy()
        
        if status_filter == "Auto-Resolved":
            display_df = display_df[display_df['resolution_status'] == 'AUTO_RESOLVED']
        elif status_filter == "Needs Review (Exceptions)":
            display_df = display_df[display_df['resolution_status'] == 'NEEDS_REVIEW']
            
        if type_filter != "All Types":
            display_df = display_df[display_df['type'] == type_filter]
            
        if method_filter != "All Methods":
            display_df = display_df[display_df['method'] == method_filter]
            
        if search_query.strip():
            q = search_query.strip().lower()
            display_df = display_df[
                display_df['transaction_id'].str.lower().str.contains(q) |
                display_df['order_id'].str.lower().str.contains(q)
            ]
            
        # Table render controls (Export and stats)
        col_export, col_counts = st.columns([1, 3])
        with col_export:
            # Mock Export Button with dynamic download link
            csv_data = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Export Ledger to CSV",
                data=csv_data,
                file_name="reconciliation_gateway_ledger.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_counts:
            st.markdown(f"""
            <div style="text-align: right; font-size: 0.85rem; color: var(--text-sec); font-weight: 600; padding-top: 8px;">
                Showing {len(display_df)} transactions matching filters
            </div>
            """, unsafe_allow_html=True)
            
        # Draw custom premium HTML Table
        html_rows = ""
        for idx, row in display_df.iterrows():
            status_pill_class = row['resolution_status'].lower()
            status_label = "Reconciled" if row['resolution_status'] == 'AUTO_RESOLVED' else "Needs Review"
            
            # Action audit deep link
            tx_id = row['transaction_id']
            action_btn = f'<a href="?page=transactions&audit_tx={tx_id}" target="_self" class="action-link">Audit</a>'
            
            html_rows += f"""
            <tr>
                <td><code>{tx_id}</code></td>
                <td><code>{row['order_id'] or 'NaN'}</code></td>
                <td><strong>{row['type']}</strong></td>
                <td>₹{row['amount_inr']:,.2f}</td>
                <td>₹{row['fee_inr']:,.2f}</td>
                <td>₹{row['tax_inr']:,.2f}</td>
                <td>₹{row['settled_amount_inr']:,.2f}</td>
                <td><span class="status-pill {status_pill_class}">{status_label}</span></td>
                <td>{row['confidence_score']*100:.0f}%</td>
                <td>{action_btn}</td>
            </tr>
            """
            
        if not html_rows:
            html_rows = "<tr><td colspan='10' style='text-align: center; color: var(--text-sec);'>No transactions found matching filters.</td></tr>"
            
        st.markdown(clean_html(f"""<div class="custom-table-container">
            <table class="custom-table">
                <thead>
                    <tr>
                        <th>Transaction ID</th>
                        <th>Order ID</th>
                        <th>Type</th>
                        <th>Amount</th>
                        <th>Fee</th>
                        <th>GST</th>
                        <th>Settlement Net</th>
                        <th>Status</th>
                        <th>Confidence</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {html_rows}
                </tbody>
            </table>
        </div>"""), unsafe_allow_html=True)

# ----------------------------------------------------
# PAGE 3: EXCEPTIONS QUEUE
# ----------------------------------------------------
elif st.session_state.page == "exceptions":
    st.markdown("<h2>Exceptions Investigation Queue</h2>", unsafe_allow_html=True)
    
    # Active Exceptions count
    exc_txs = df_tx[df_tx['resolution_status'] == 'NEEDS_REVIEW']
    exc_unmatched = df_unmatched[df_unmatched['resolution_status'] == 'NEEDS_REVIEW']
    total_active_count = len(exc_txs) + len(exc_unmatched)
    
    st.markdown(f"""
    <div style="font-size: 1rem; color: var(--text-sec); margin-bottom: 20px;">
        There are <strong style="color: var(--error);">{total_active_count} unresolved exceptions</strong> requiring review.
    </div>
    """, unsafe_allow_html=True)
    
    # Filters
    col_ef1, col_ef2, col_ef_search = st.columns([1, 1, 2])
    with col_ef1:
        severity_filter = st.selectbox(
            "Exceptions Severity",
            ["All Severities", "HIGH", "MEDIUM", "LOW"]
        )
    with col_ef2:
        exc_type_filter = st.selectbox(
            "Anomalies Classification",
            ["All Exceptions", "Fee Mismatch", "Missing Order Link", "Bank Credit Missing", "Dispute Transaction"]
        )
    with col_ef_search:
        exc_search = st.text_input(
            "Search exception reference ID",
            placeholder="Search transaction or order ID..."
        )
        
    # Iterate and draw exception cards
    exceptions_list = []
    
    # Add df_tx exceptions
    for idx, row in exc_txs.iterrows():
        # Determine Severity based on confidence
        if row['confidence_score'] == 0:
            severity = "HIGH"
        elif row['confidence_score'] <= 0.2:
            severity = "MEDIUM"
        else:
            severity = "LOW"
            
        ex_str = ", ".join([str(e).replace('₹', 'Rs.') for e in row['calculated_exceptions']])
        
        exceptions_list.append({
            'id': row['transaction_id'],
            'ref_id': row['order_id'],
            'type': 'Gateway Transaction',
            'amount': row['amount_inr'],
            'severity': severity,
            'issue': ex_str,
            'rec': "Audit Gateway charges and verify mappings.",
            'raw_row': row
        })
        
    # Add unmatched orders
    for idx, row in exc_unmatched.iterrows():
        exceptions_list.append({
            'id': row['order_id'],
            'ref_id': 'Missing link',
            'type': 'Internal Order Orphan',
            'amount': row['amount_inr'],
            'severity': 'HIGH',
            'issue': "GATEWAY_PAYMENT_NOT_FOUND (Completed internally but no payment capture)",
            'rec': "Contact merchant billing support or check database logs.",
            'raw_row': row
        })
        
    # Filter exceptions_list
    filtered_excs = []
    for item in exceptions_list:
        if severity_filter != "All Severities" and item['severity'] != severity_filter:
            continue
            
        if exc_type_filter != "All Exceptions":
            if exc_type_filter == "Fee Mismatch" and "FEE" not in item['issue']:
                continue
            if exc_type_filter == "Missing Order Link" and "ORDER" not in item['issue'] and "GATEWAY" not in item['issue']:
                continue
            if exc_type_filter == "Bank Credit Missing" and "BANK" not in item['issue']:
                continue
            if exc_type_filter == "Dispute Transaction" and "DISPUTE" not in item['issue']:
                continue
                
        if exc_search.strip():
            sq = exc_search.strip().lower()
            if sq not in item['id'].lower() and sq not in str(item['ref_id']).lower():
                continue
                
        filtered_excs.append(item)
        
    # Draw exception rows
    if not filtered_excs:
        st.info("No exceptions found matching filters.")
    else:
        for ex in filtered_excs:
            sev_class = ex['severity'].lower()
            
            st.markdown(f"""
            <div style="background-color: #FFFFFF; border: 1px solid var(--border); border-left: 4px solid {'var(--error)' if ex['severity']=='HIGH' else ('var(--warning)' if ex['severity']=='MEDIUM' else '#3B82F6')}; padding: 16px; border-radius: 6px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.02);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div>
                        <span class="status-pill {sev_class}" style="margin-right: 8px;">{ex['severity']}</span>
                        <strong style="font-size: 13.5px; color: var(--navy);">{ex['type']}: <code>{ex['id']}</code></strong>
                    </div>
                    <strong style="color: var(--navy); font-size: 14.5px;">₹{ex['amount']:,.2f}</strong>
                </div>
                <div style="font-size: 13px; color: var(--navy); margin-bottom: 8px; font-weight: 500;">
                    <strong>Discrepancy Details:</strong> <code>{ex['issue']}</code>
                </div>
                <div style="font-size: 12px; color: var(--text-sec); margin-bottom: 12px;">
                    <strong>AI Recommended Action:</strong> {ex['rec']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action row buttons
            col_b1, col_b2, col_b3, col_bsp = st.columns([1, 1.2, 1, 3.5])
            with col_b1:
                # View details redirect
                if st.button("View Details", key=f"exc_view_{ex['id']}", use_container_width=True):
                    st.query_params.clear()
                    if ex['type'] == 'Gateway Transaction':
                        st.session_state.page = "transactions"
                        st.session_state.audit_tx = ex['id']
                        st.query_params.page = "transactions"
                        st.query_params.audit_tx = ex['id']
                    else:
                        st.session_state.page = "admin"
                        st.session_state.admin_page = "Data Sources"
                        st.query_params.page = "admin"
                        st.query_params.admin_page = "Data Sources"
                    st.rerun()
            with col_b2:
                if st.button("Explain with AI", key=f"exc_explain_{ex['id']}", use_container_width=True):
                    # Set audit ID and trigger explanation
                    st.session_state.page = "transactions"
                    st.session_state.audit_tx = ex['id']
                    st.session_state.explain_tx = ex['id']
                    st.query_params.clear()
                    st.query_params.page = "transactions"
                    st.query_params.audit_tx = ex['id']
                    st.query_params.explain_tx = ex['id']
                    st.rerun()
            with col_b3:
                # Resolve exception locally!
                if st.button("Resolve", key=f"exc_resolve_{ex['id']}", use_container_width=True):
                    st.session_state.resolved_exceptions.append(ex['id'])
                    st.success(f"Discrepancy resolved for {ex['id']}.")
                    st.rerun()

# ----------------------------------------------------
# PAGE 4: SETTLEMENTS LEDGER
# ----------------------------------------------------
elif st.session_state.page == "settlements":
    st.markdown("<h2>Merchant Settlements Dashboard</h2>", unsafe_allow_html=True)
    
    # Expected vs settled metrics
    col_st1, col_st2, col_st3 = st.columns(3)
    with col_st1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Expected Settlement Volume</div>
            <div class="kpi-value">₹72,392.00</div>
            <div class="kpi-desc">Total expected credit ledger</div>
        </div>
        """, unsafe_allow_html=True)
    with col_st2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Settled Amount</div>
            <div class="kpi-value" style="color: var(--success);">₹{metrics['settled_to_bank_inr']:,.2f}</div>
            <div class="kpi-desc"><span style="color: var(--success);">✓</span> Confirmed deposits</div>
        </div>
        """, unsafe_allow_html=True)
    with col_st3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Pending Settlement</div>
            <div class="kpi-value" style="color: var(--warning);">₹{metrics['expected_next_2_days_inr']:,.2f}</div>
            <div class="kpi-desc">T+2 Settlement delay queue</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### DAILY SETTLEMENT LEDGER")
    
    # Format and draw settlements table
    settle_rows = ""
    for idx, row in df_bank.iterrows():
        status_label = row['status'].replace('_', ' ')
        status_pill_class = row['status'].lower()
        
        settle_rows += f"""
        <tr>
            <td><strong>{row['date']}</strong></td>
            <td>₹{row['expected_amount_inr']:,.2f}</td>
            <td>₹{row['amount_inr']:,.2f}</td>
            <td><code>{row['bank_reference'] or 'Omitted'}</code></td>
            <td><span class="status-pill {status_pill_class}">{status_label}</span></td>
        </tr>
        """
        
    st.markdown(clean_html(f"""<div class="custom-table-container">
        <table class="custom-table">
            <thead>
                <tr>
                    <th>Settlement Date</th>
                    <th>Expected Amount</th>
                    <th>Bank Credit Amount</th>
                    <th>Bank Reference ID</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {settle_rows}
            </tbody>
        </table>
    </div>"""), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("ℹ️ T+2 Settlements Window: Standard collection credits hit bank statement 2 days after transaction dates. Refunds and Payouts resolve instantly (T+0).")

# ----------------------------------------------------
# PAGE 5: PAYOUTS DETAILS
# ----------------------------------------------------
elif st.session_state.page == "payouts":
    st.markdown("<h2>Payouts & Vendor Disbursements</h2>", unsafe_allow_html=True)
    
    # Separate payouts summary numbers
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-title">Gross Payouts</div>
            <div class="kpi-value">₹50,000.00</div>
            <div class="kpi-desc">Disbursed collections</div>
        </div>
        """, unsafe_allow_html=True)
    with col_p2:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-title">Processing Fee & GST</div>
            <div class="kpi-value">₹5.90</div>
            <div class="kpi-desc">Flat Rs. 5 fee + 18% GST</div>
        </div>
        """, unsafe_allow_html=True)
    with col_p3:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-title">Net Settlement Deducted</div>
            <div class="kpi-value">₹49,495.00</div>
            <div class="kpi-desc">Treasury charge deduction</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Crucial compliance notice
    st.markdown("""
    <div style="background-color: rgba(59, 130, 246, 0.08); border-left: 4px solid #3B82F6; padding: 15px; border-radius: 6px; margin-bottom: 24px;">
        <h5 style="color: #3B82F6; margin: 0 0 4px 0;">🏛️ Payout Compliance Guideline</h5>
        <p style="margin: 0; font-size: 13px; font-weight: 500;">
            Customer collections are <strong>not</strong> subject to transaction-level TDS deductions. TDS rules only apply to vendor payouts and merchant settlements as defined in your corporate policy. Adjust these rates in <strong>Admin Panel → TDS Policy</strong>.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### DISBURSEMENT RECORD")
    
    # Filter payouts list
    payouts_df = df_tx[df_tx['type'] == 'PAYOUT']
    
    p_rows = ""
    for idx, row in payouts_df.iterrows():
        p_rows += f"""
        <tr>
            <td><code>{row['transaction_id']}</code></td>
            <td>₹{row['amount_inr']:,.2f}</td>
            <td>₹{row['fee_inr']:,.2f}</td>
            <td>₹{row['tax_inr']:,.2f}</td>
            <td>₹{abs(row['settled_amount_inr']):,.2f}</td>
            <td><span class="status-pill ok">Processed</span></td>
        </tr>
        """
        
    if not p_rows:
        p_rows = "<tr><td colspan='6' style='text-align: center; color: var(--text-sec);'>No processed payouts in current batch.</td></tr>"
        
    st.markdown(clean_html(f"""<div class="custom-table-container">
        <table class="custom-table">
            <thead>
                <tr>
                    <th>Payout Reference ID</th>
                    <th>Gross Amount</th>
                    <th>Gateway Fee</th>
                    <th>GST (18%)</th>
                    <th>Net Treasury Deduction</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {p_rows}
            </tbody>
        </table>
    </div>"""), unsafe_allow_html=True)

# ----------------------------------------------------
# PAGE 6: BANK RECONCILIATION
# ----------------------------------------------------
elif st.session_state.page == "bank":
    st.markdown("<h2>Bank Statement Reconciliation</h2>", unsafe_allow_html=True)
    
    # Bank metrics
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Current Bank Statement Balance</div>
            <div class="kpi-value">₹{metrics['settled_to_bank_inr']:,.2f}</div>
            <div class="kpi-desc">Verified actual bank reserves</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Expected Settlement Net</div>
            <div class="kpi-value">₹{metrics['settled_to_bank_inr']:,.2f}</div>
            <div class="kpi-desc">Calculated expected deposits</div>
        </div>
        """, unsafe_allow_html=True)
    with col_b3:
        st.markdown("""
        <div class="kpi-card">
            <div class="kpi-title">Treasury Difference</div>
            <div class="kpi-value" style="color: var(--success);">₹0.00</div>
            <div class="kpi-desc"><span class="status-pill reconciled">Fully Reconciled</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("### BANK STATEMENT ENTRIES")
    
    # Generate clean statement entries with Credits and Debits separated
    statement_rows = ""
    
    # Render statement records based on bank data
    for idx, row in df_bank.iterrows():
        val = row['amount_inr']
        
        # Debits or Payouts are negative, Credits are positive
        if val > 0:
            credit_str = f"₹{val:,.2f}"
            debit_str = "-"
        else:
            credit_str = "-"
            debit_str = f"₹{abs(val):,.2f}"
            
        desc = f"Gateway Settlement Credit {row['bank_reference']}" if row['bank_reference'] else "Unidentified Bank Deposit"
        
        statement_rows += f"""
        <tr>
            <td>{row['date']}</td>
            <td>{desc}</td>
            <td style="color: var(--success); font-weight: 600;">{credit_str}</td>
            <td style="color: var(--error); font-weight: 600;">{debit_str}</td>
            <td><code>{row['bank_reference'] or 'NaN'}</code></td>
        </tr>
        """
        
    st.markdown(clean_html(f"""<div class="custom-table-container">
        <table class="custom-table">
            <thead>
                <tr>
                    <th>Value Date</th>
                    <th>Description</th>
                    <th>Credit (Deposits)</th>
                    <th>Debit (Withdrawals)</th>
                    <th>Bank Reference ID</th>
                </tr>
            </thead>
            <tbody>
                {statement_rows}
            </tbody>
        </table>
    </div>"""), unsafe_allow_html=True)

# ----------------------------------------------------
# PAGE 7: TAX & TDS COMPLIANCE
# ----------------------------------------------------
elif st.session_state.page == "tax":
    st.markdown("<h2>Tax Auditing & Compliance</h2>", unsafe_allow_html=True)
    
    # Tax metrics
    tx1, tx2, tx3, tx4 = st.columns(4)
    with tx1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">TOTAL GATEWAY GST AUDITED</div>
            <div class="kpi-value">₹{tax_summary['total_gst_collected_inr']:,.2f}</div>
            <div class="kpi-desc">Audited gateway GST collected</div>
        </div>
        """, unsafe_allow_html=True)
    with tx2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">TOTAL 194-O TDS AUDITED</div>
            <div class="kpi-value">₹{tax_summary['total_tds_deducted_inr']:,.2f}</div>
            <div class="kpi-desc">Audited 1% e-commerce TDS</div>
        </div>
        """, unsafe_allow_html=True)
    with tx3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">COMPLIANCE RATE</div>
            <div class="kpi-value">{tax_summary['tax_compliance_pct']}%</div>
            <div class="kpi-desc">Tax compliance match rate</div>
        </div>
        """, unsafe_allow_html=True)
    with tx4:
        anom_val = tax_summary['total_tax_discrepancies']
        status_pill_html = '<span class="status-pill ok">Fully Compliant</span>' if anom_val == 0 else '<span class="status-pill needs_review">Requires Review</span>'
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">ANOMALIES FLAGGED</div>
            <div class="kpi-value">{anom_val}</div>
            <div class="kpi-desc">{status_pill_html}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tax ledger with filters
    st.markdown("### TAX LEDGER")
    tax_filter = st.selectbox(
        "Filter tax entries",
        ["All Tax Entries", "GST Discrepancies Only", "TDS Under-deduction Only"]
    )
    
    filtered_tax = tax_df.copy()
    if tax_filter == "GST Discrepancies Only":
        filtered_tax = filtered_tax[filtered_tax['tax_status'].isin(['GST_MISMATCH', 'MULTIPLE_TAX_ISSUES'])]
    elif tax_filter == "TDS Under-deduction Only":
        filtered_tax = filtered_tax[filtered_tax['tax_status'] == 'TDS_UNDER_DEDUCTION']
        
    t_rows = ""
    for idx, row in filtered_tax.iterrows():
        status_class = row['tax_status'].lower()
        t_rows += f"""
        <tr>
            <td><code>{row['transaction_id']}</code></td>
            <td>{row['type']}</td>
            <td>₹{row['amount_inr']:,.2f}</td>
            <td>₹{row['fee_inr']:,.2f}</td>
            <td>₹{row['actual_gst']:,.2f} / ₹{row['expected_gst']:,.2f}</td>
            <td>₹{row['actual_tds']:,.2f} / ₹{row['expected_tds']:,.2f}</td>
            <td><span class="status-pill {status_class}">{row['tax_status']}</span></td>
        </tr>
        """
        
    if not t_rows:
        t_rows = "<tr><td colspan='7' style='text-align: center; color: var(--text-sec);'>No tax audit entries.</td></tr>"
        
    st.markdown(clean_html(f"""<div class="custom-table-container">
        <table class="custom-table">
            <thead>
                <tr>
                    <th>Transaction ID</th>
                    <th>Type</th>
                    <th>Amount</th>
                    <th>Gateway Fee</th>
                    <th>GST (Actual / Expected)</th>
                    <th>TDS (Actual / Expected)</th>
                    <th>Compliance Status</th>
                </tr>
            </thead>
            <tbody>
                {t_rows}
            </tbody>
        </table>
    </div>"""), unsafe_allow_html=True)

# ----------------------------------------------------
# PAGE 8: AI INSIGHTS & GENERATIVE AUDITOR
# ----------------------------------------------------
elif st.session_state.page == "insights":
    st.markdown("<h2>✦ AI Finance Assistant</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>RAG-enabled Generative Finance Auditor & Compliance assistant.</p>", unsafe_allow_html=True)
    
    user = st.session_state.user
    from src.database import get_conversations, get_conversation_messages, create_conversation, save_conversation_message, delete_conversation, update_conversation_title_with_first_query
    
    # Initialize conversation thread state on first load
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
        
    if st.session_state.conversation_id is None:
        convs = get_conversations(user['user_id'], user['merchant_id'], user['store_id'])
        if convs:
            st.session_state.conversation_id = convs[0]['session_id']
            st.session_state.messages = get_conversation_messages(st.session_state.conversation_id)
        else:
            st.session_state.messages = []
            
    # Custom interactive chatbot UI split
    col_chat, col_backup = st.columns([2.1, 0.9])
    
    with col_chat:
        st.markdown("### Generative Auditor Chat Console")
        chat_box = st.container()
        with chat_box:
            if not st.session_state.conversation_id:
                st.info("Start a new conversation thread using the panel on the right to begin!")
            else:
                if len(st.session_state.messages) == 0:
                    st.info("Ask a question about settlement policies, fee discrepancies, or daily close audits.")
                for msg in st.session_state.messages:
                    role_label = "👤 User Query" if msg['role'] == 'user' else "🤖 AI Response"
                    role_color = "rgba(15, 76, 117, 0.05)" if msg['role'] == 'user' else "#F8FAFC"
                    st.markdown(f"""
                    <div style="background-color: {role_color}; padding: 15px; border-radius: 6px; border: 1px solid var(--border); margin-bottom: 12px;">
                        <strong>{role_label}</strong>
                        <p style="margin: 6px 0 0 0; font-size: 13.5px; font-weight: 500;">{msg['content']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
        # Form input
        if st.session_state.conversation_id:
            with st.form(key="ai_page_chat_form", clear_on_submit=True):
                chat_col_inp, chat_col_btn = st.columns([5, 1.3])
                with chat_col_inp:
                    chat_user_query = st.text_input(
                        "Ask a question:", 
                        placeholder="Why did transaction pay_exc_fee_00 fail reconciliation?", 
                        label_visibility="collapsed"
                    )
                with chat_col_btn:
                    chat_submit = st.form_submit_button("Send Query", use_container_width=True)
                    
            if chat_submit and chat_user_query.strip():
                # Save user message
                st.session_state.messages.append({"role": "user", "content": chat_user_query})
                save_conversation_message(st.session_state.conversation_id, "user", chat_user_query)
                # Update conversation title with first user query preview
                update_conversation_title_with_first_query(st.session_state.conversation_id, chat_user_query)
                
                # Generate RAG grounded response
                with st.spinner("Generating..."):
                    generate_ai_response(chat_user_query, conversation_id=st.session_state.conversation_id, merchant_id=user['merchant_id'])
                st.rerun()
 
    with col_backup:
        st.markdown("### Saved Conversations")
        
        # Start new conversation button
        if st.button("➕ Start New Thread", key="insights_new_conv_btn", use_container_width=True):
            title = f"Chat: {datetime.now().strftime('%d-%b %H:%M')}"
            conv_id = create_conversation(user['user_id'], user['merchant_id'], user['store_id'], title)
            st.session_state.conversation_id = conv_id
            st.session_state.messages = []
            st.rerun()
            
        sessions = get_conversations(user['user_id'], user['merchant_id'], user['store_id'])
        if not sessions:
            st.info("No saved conversation threads found.")
        else:
            session_options = {s['session_id']: s['title'] for s in sessions}
            
            # Safe default index
            default_idx = 0
            if st.session_state.conversation_id in session_options:
                default_idx = list(session_options.keys()).index(st.session_state.conversation_id)
                
            selected_s_id = st.selectbox(
                "Select Thread",
                list(session_options.keys()),
                index=default_idx,
                format_func=lambda x: session_options[x],
                key="insights_thread_selectbox"
            )
            
            # Switch conversation thread if changed
            if selected_s_id != st.session_state.conversation_id:
                st.session_state.conversation_id = selected_s_id
                st.session_state.messages = get_conversation_messages(selected_s_id)
                st.rerun()
                
            # Export logs
            history_data = st.session_state.messages
            if history_data:
                txt_output = f"AI FINANCE CONTROLLER CONVERSATION EXPORT\n"
                txt_output += f"Session ID: {selected_s_id}\n"
                txt_output += f"Title: {session_options[selected_s_id]}\n"
                txt_output += f"==========================================\n\n"
                for msg in history_data:
                    txt_output += f"{msg['role'].upper()}:\n{msg['content']}\n\n"
                    
                st.download_button(
                    label="📥 Export Chat Log",
                    data=txt_output,
                    file_name=f"chat_history_{selected_s_id}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
            # Delete thread button
            if st.button("🗑️ Delete Thread", key="insights_delete_thread_btn", use_container_width=True):
                delete_conversation(selected_s_id)
                st.session_state.conversation_id = None
                st.toast("Conversation thread deleted.", icon="✓")
                st.rerun()


# ----------------------------------------------------
# PAGE 9: CASH FORECAST
# ----------------------------------------------------
elif st.session_state.page == "forecast":
    st.markdown("<h2>📈 Forward Treasury & Cash Flow Forecast</h2>", unsafe_allow_html=True)
    
    # 1. Determine forecast start date dynamically
    df_bank_clean = df_bank.copy()
    df_bank_clean['date_dt'] = pd.to_datetime(df_bank_clean['date'], format="%d-%m-%Y", errors='coerce')
    
    if not df_bank_clean.empty and not df_bank_clean['date_dt'].isna().all():
        latest_bank_date = df_bank_clean['date_dt'].max()
    elif not df_tx.empty:
        if 'timestamp' in df_tx.columns:
            ts = pd.to_datetime(df_tx['timestamp'], format="%d-%m-%Y %H:%M", errors='coerce')
            latest_bank_date = ts.max()
        else:
            latest_bank_date = datetime.now()
    else:
        latest_bank_date = datetime.now()
        
    forecast_start_date = latest_bank_date + timedelta(days=1)
    
    # Render selectors inside columns
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date_val = st.date_input("Start Date", value=forecast_start_date.date(), min_value=forecast_start_date.date(), key="forecast_start_date_picker")
    with col_d2:
        end_date_val = st.date_input("End Date", value=(forecast_start_date + timedelta(days=6)).date(), min_value=start_date_val, key="forecast_end_date_picker")
        
    # Calculate days needed and run dynamic forecast
    days_needed = (end_date_val - forecast_start_date.date()).days + 1
    # Generate forecast up to at least the days requested
    dynamic_forecast_df = get_cash_forecast(df_tx, df_bank, days=max(7, days_needed))
    dynamic_forecast_df['date_dt'] = pd.to_datetime(dynamic_forecast_df['date'], format="%d-%m-%Y")
    
    # Filter to chosen date range
    filtered_df = dynamic_forecast_df[
        (dynamic_forecast_df['date_dt'].dt.date >= start_date_val) & 
        (dynamic_forecast_df['date_dt'].dt.date <= end_date_val)
    ]
    
    if filtered_df.empty:
        st.warning("No data available for the selected date range.")
    else:
        # Sum collections and outflows in the filtered period
        total_inflow = filtered_df['gross_collections'].sum()
        total_outflow = (filtered_df['refunds'] + filtered_df['payouts'] + filtered_df['fees_gst']).sum()
        net_flow_sum = filtered_df['net_inflow'].sum()
        ending_reserves = filtered_df.iloc[-1]['cumulative_cash']
        
        # Forecasting metrics
        cf1, cf2, cf3 = st.columns(3)
        with cf1:
            st.metric("Projected Ending Reserves", f"₹{ending_reserves:,.2f}")
        with cf2:
            st.metric("Total Projected Net Cash Flow", f"₹{net_flow_sum:,.2f}")
        with cf3:
            st.metric("Total Projected Inflows", f"₹{total_inflow:,.2f}")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Forecast chart
        st.markdown(f"### FORWARD TREASURY TREND ({start_date_val.strftime('%d %b %Y')} to {end_date_val.strftime('%d %b %Y')})")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=filtered_df['date'],
            y=filtered_df['net_inflow'],
            name='Net Daily Cash flow',
            marker_color='#0F4C75'
        ))
        fig.add_trace(go.Scatter(
            x=filtered_df['date'],
            y=filtered_df['cumulative_cash'],
            name='Cumulative Reserves',
            line=dict(color='#EF4444', width=3)
        ))
        fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------
# PAGE 10: REPORTS
# ----------------------------------------------------
elif st.session_state.page == "reports":
    st.markdown("<h2>Reports Centre</h2>", unsafe_allow_html=True)
    
    reports_list = [
        {"title": "Daily Reconciliation Summary Report", "desc": "Aggregated 3-way reconciliation audit checklist and verdict overview."},
        {"title": "Gateway Settlement Variance Report", "desc": "Details on fee discrepancies and missed credits by Razorpay."},
        {"title": "Tax Compliance & TDS Audit Report", "desc": "Auditing e-commerce TDS deductions under Sec 194-O."},
        {"title": "Forward Treasury Forecast Report", "desc": "7-day forward liquidity predictions and committed bank inflows."},
        {"title": "Exceptions & Fraud Audit Ledger", "desc": "History of disputed transactions, missing order IDs and resolutions."},
        {"title": "Bank Feed Reconciliation Report", "desc": "Detailed matching logs of gateway batches vs bank credit reference IDs."}
    ]
    
    for idx, rep in enumerate(reports_list):
        st.markdown(f"""
        <div style="background-color: #FFFFFF; border: 1px solid var(--border); padding: 16px; border-radius: 6px; margin-bottom: 12px;">
            <strong style="font-size: 14px; color: var(--navy);">{rep['title']}</strong>
            <p style="margin: 4px 0 12px 0; font-size: 12.5px; color: var(--text-sec);">{rep['desc']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        col_gen, col_csv, col_pdf, col_sp = st.columns([1.2, 1, 1, 4])
        with col_gen:
            if st.button("Generate Report", key=f"gen_{idx}"):
                st.success("Report successfully generated inside treasury exports.")

# ----------------------------------------------------
# PAGE 11: SETTINGS & HELPDESK
# ----------------------------------------------------
elif st.session_state.page == "settings":
    st.markdown("<h2>⚙ Corporate Profile Settings</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Manage corporate credentials, profile address, and default settlement preferences.</p>", unsafe_allow_html=True)
    
    user = st.session_state.user
    from src.database import reset_user_password, log_action
    
    col_prof, col_pwd = st.columns(2)
    
    with col_prof:
        st.markdown("### Profile Settings")
        st.text_input("Merchant Entity ID", value=user['merchant_id'].upper(), disabled=True)
        st.text_input("Store Location ID", value=user['store_id'].upper(), disabled=True)
        st.text_input("Corporate Billing Address", value="Electronic City, Bengaluru, Karnataka - 560100" if user['merchant_id'] == 'flipkart' else "Outer Ring Road, Bengaluru, Karnataka - 560103")
        st.selectbox("Default Settlement Mode", ["T+2 Standard", "Instant Payouts"])
        
    with col_pwd:
        st.markdown("### Change Password")
        with st.form(key="merchant_pwd_change_form", clear_on_submit=True):
            old_p = st.text_input("Current Password", type="password")
            new_p = st.text_input("New Password", type="password")
            confirm_p = st.text_input("Confirm New Password", type="password")
            pwd_submit = st.form_submit_button("Update Password")
            
        if pwd_submit:
            from src.database import authenticate_user
            if authenticate_user(user['email'], old_p):
                if new_p.strip() == confirm_p.strip():
                    if len(new_p.strip()) >= 6:
                        reset_user_password(user['email'], new_p.strip())
                        log_action(user['user_id'], "Password Change", "Changed corporate password.")
                        st.success("✓ Password updated successfully.")
                    else:
                        st.error("New password must be at least 6 characters.")
                else:
                    st.error("New password and confirmation do not match.")
            else:
                st.error("Current password incorrect.")

# ----------------------------------------------------
# PAGE 11B: SUPPORT TICKETS & RESOLUTIONS (MERCHANT)
# ----------------------------------------------------
elif st.session_state.page == "tickets":
    st.markdown("<h2>🎟 Support Tickets & Resolutions Helpdesk</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Raise support queries, request exception reviews, or trace bank credit settlement issues.</p>", unsafe_allow_html=True)
    
    user = st.session_state.user
    from src.database import raise_support_ticket, get_support_tickets, log_action
    
    t_tab1, t_tab2 = st.tabs(["Raise New Ticket", "Ticket History & Resolutions"])
    
    with t_tab1:
        st.markdown("### Open a Support Ticket")
        with st.form(key="merchant_raise_ticket_form", clear_on_submit=True):
            needs_review_tx = df_tx[df_tx['resolution_status'] == 'NEEDS_REVIEW']['transaction_id'].tolist()
            tx_opts = ["General Support Query"] + needs_review_tx
            
            sel_tx = st.selectbox("Related Transaction ID", tx_opts)
            subj = st.text_input("Subject / Title")
            category = st.selectbox("Issue Category", ["Gateway Exception Review", "Missing Bank Credit", "Fee Discrepancy", "Payout Issue", "Other"])
            priority = st.selectbox("Priority Level", ["Low", "Medium", "High", "Critical"])
            msg_body = st.text_area("Provide a detailed description of the discrepancy")
            
            sub_ticket = st.form_submit_button("Submit Ticket to Razorpay Operations")
            
        if sub_ticket:
            if subj.strip() and msg_body.strip():
                ticket_id = raise_support_ticket(
                    merchant_id=user['merchant_id'],
                    store_id=user['store_id'],
                    user_id=user['user_id'],
                    transaction_id=sel_tx if sel_tx != "General Support Query" else "",
                    subject=subj.strip(),
                    message=msg_body.strip(),
                    category=category,
                    priority=priority
                )
                log_action(user['user_id'], "Raise Ticket", f"Ticket #{ticket_id} opened. Subject: {subj.strip()}")
                st.success(f"[OK] Ticket #{ticket_id} submitted successfully to Razorpay Operations.")
                st.toast(f"Ticket #{ticket_id} submitted!", icon="✅")
                st.rerun()
            else:
                st.error("Please provide both a subject and description.")
                
    with t_tab2:
        st.markdown("### Ticket Logs")
        tickets = get_support_tickets(merchant_id=user['merchant_id'], store_id=user['store_id'])
        if not tickets:
            st.info("No helpdesk queries raised for this store.")
        else:
            for tk in tickets:
                color_tk = "var(--success)" if tk['status'] == 'RESOLVED' else "var(--warning)"
                t_store = tk['store_id'].split('_')[-1].upper()
                t_tx = tk['transaction_id'] if tk['transaction_id'] else 'None'
                st.markdown(f"""
                <div style="background-color: #FFFFFF; border: 1px solid var(--border); border-left: 4px solid {color_tk}; padding: 16px; border-radius: 6px; margin-bottom: 12px; font-family: 'Inter', sans-serif;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                        <strong style="color: var(--navy); font-size: 14.5px;">#{tk['ticket_id']} - {tk['subject']}</strong>
                        <span style="color: {color_tk}; font-weight: 700; font-size: 11px; padding: 2px 8px; border-radius: 20px; background-color:#F1F5F9;">{tk['status']}</span>
                    </div>
                    <span style="font-size: 11.5px; color: var(--text-sec);">
                        Store: {t_store} | Related Tx: {t_tx} | Created: {tk['timestamp']}
                    </span>
                    <p style="margin: 8px 0; font-size: 13px; background: #F8FAFC; padding: 10px; border-radius: 4px; border: 1px solid var(--border);">{tk['message']}</p>
                """, unsafe_allow_html=True)
                
                if tk['reply']:
                    st.markdown(f"""
                    <div style="margin-left: 20px; padding: 10px 14px; background-color: #F0FDF4; border-left: 3px solid #10B981; border-radius: 4px; font-size: 12.5px;">
                        <span style="font-weight: 600; color: #15803D;">&#8627; Razorpay Operations Reply:</span>
                        <p style="margin: 4px 0 0 0; color: #1E3A1E;">{tk['reply']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------------------
# ADMIN PAGE 1: OVERVIEW / DASHBOARD (REDESIGNED)
# ----------------------------------------------------
elif st.session_state.page == "admin":
    # 1. TOP HEADER
    col_h_left, col_h_right = st.columns([1.8, 1.2])
    with col_h_left:
        st.markdown("""
        <div style="margin-bottom: 18px;">
            <h1 style="margin: 0; font-size: 24px; font-weight: 700; color: #172B4D; font-family: 'Outfit', sans-serif; letter-spacing: -0.3px;">
                Welcome back, Razorpay Admin 👋
            </h1>
            <p style="margin: 3px 0 0 0; font-size: 13.5px; color: #6B7C93; font-family: 'Inter', sans-serif;">
                Here's what's happening across your platform today.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_h_right:
        col_dr, col_rf, col_exp = st.columns([2.0, 0.6, 1.6])
        with col_dr:
            # Custom styled date display
            st.markdown("""
            <div style="display: flex; align-items: center; justify-content: space-between; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px 12px; font-size: 12px; font-weight: 500; color: #172B4D; box-shadow: 0 1px 2px rgba(0,0,0,0.02); height: 38px;">
                <span>📅 May 22 – May 28, 2025</span>
                <span style="font-size: 10px; color: #6B7C93;">▼</span>
            </div>
            """, unsafe_allow_html=True)
        with col_rf:
            if st.button("↻", key="admin_refresh_btn", help="Refresh Dashboard", use_container_width=True):
                st.rerun()
        with col_exp:
            # Export report button - triggers CSV download of platform transactions
            report_csv = df_tx.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Report",
                data=report_csv,
                file_name=f"razorpay_admin_platform_report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="admin_export_report_btn",
                use_container_width=True
            )
            
    # 2. SIX KPI CARDS IN 1 ROW
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    
    # 2. SIX KPI CARDS IN 1 ROW
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    
    with k1:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); height: 110px; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 22px; height: 22px; border-radius: 5px; background-color: #F3E8FF; color: #9333EA; display: flex; align-items: center; justify-content: center; font-size: 11px; flex-shrink: 0;">👥</div>
                <div style="font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; letter-spacing: 0.2px;">TOTAL MERCHANTS</div>
            </div>
            <div style="font-size: 20px; font-weight: 800; color: #172B4D; font-family: 'Outfit', sans-serif; line-height: 1.1; margin: 2px 0;">2</div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #6B7C93; border-top: 1px solid #F8FAFC; padding-top: 4px;">
                <span style="white-space: nowrap;">Active platform</span>
                <span style="color: #10B981; font-weight: 600; white-space: nowrap;">↗ 0%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with k2:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); height: 110px; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 22px; height: 22px; border-radius: 5px; background-color: #EFF6FF; color: #3B82F6; display: flex; align-items: center; justify-content: center; font-size: 11px; flex-shrink: 0;">🏬</div>
                <div style="font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; letter-spacing: 0.2px;">ACTIVE STORES</div>
            </div>
            <div style="font-size: 20px; font-weight: 800; color: #172B4D; font-family: 'Outfit', sans-serif; line-height: 1.1; margin: 2px 0;">10</div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #6B7C93; border-top: 1px solid #F8FAFC; padding-top: 4px;">
                <span style="white-space: nowrap;">Operational</span>
                <span style="color: #10B981; font-weight: 600; white-space: nowrap;">↗ 11.1%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with k3:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); height: 110px; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 22px; height: 22px; border-radius: 5px; background-color: #ECFDF5; color: #10B981; display: flex; align-items: center; justify-content: center; font-size: 11px; flex-shrink: 0;">💳</div>
                <div style="font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; letter-spacing: 0.2px;">TOTAL TRANSACTIONS</div>
            </div>
            <div style="font-size: 20px; font-weight: 800; color: #172B4D; font-family: 'Outfit', sans-serif; line-height: 1.1; margin: 2px 0;">24,850</div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #6B7C93; border-top: 1px solid #F8FAFC; padding-top: 4px;">
                <span style="white-space: nowrap;">This week</span>
                <span style="color: #10B981; font-weight: 600; white-space: nowrap;">↗ 8.4%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with k4:
        vol_fmt = f"₹{metrics['gross_collections_inr']:,.2f}" if 'gross_collections_inr' in metrics else "₹196,373.71"
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); height: 110px; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 22px; height: 22px; border-radius: 5px; background-color: #FEF3C7; color: #D97706; display: flex; align-items: center; justify-content: center; font-size: 11px; flex-shrink: 0;">🪙</div>
                <div style="font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; letter-spacing: 0.2px;">PROCESSING VOLUME</div>
            </div>
            <div style="font-size: 18px; font-weight: 800; color: #172B4D; font-family: 'Outfit', sans-serif; line-height: 1.1; margin: 2px 0;">{vol_fmt}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #6B7C93; border-top: 1px solid #F8FAFC; padding-top: 4px;">
                <span style="white-space: nowrap;">This week</span>
                <span style="color: #10B981; font-weight: 600; white-space: nowrap;">↗ 12.6%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with k5:
        exc_fmt = str(metrics.get('needs_review_count', 38))
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); height: 110px; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 22px; height: 22px; border-radius: 5px; background-color: #FEE2E2; color: #EF4444; display: flex; align-items: center; justify-content: center; font-size: 11px; flex-shrink: 0;">⚠️</div>
                <div style="font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; letter-spacing: 0.2px;">UNRESOLVED EXCEPTIONS</div>
            </div>
            <div style="font-size: 20px; font-weight: 800; color: #172B4D; font-family: 'Outfit', sans-serif; line-height: 1.1; margin: 2px 0;">{exc_fmt}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #6B7C93; border-top: 1px solid #F8FAFC; padding-top: 4px;">
                <span style="white-space: nowrap;">Requires review</span>
                <span style="color: #EF4444; font-weight: 600; white-space: nowrap;">↗ 5.6%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with k6:
        st.markdown(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 12px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); height: 110px; display: flex; flex-direction: column; justify-content: space-between; box-sizing: border-box;">
            <div style="display: flex; align-items: center; gap: 6px;">
                <div style="width: 22px; height: 22px; border-radius: 5px; background-color: #FDF2F8; color: #EC4899; display: flex; align-items: center; justify-content: center; font-size: 11px; flex-shrink: 0;">🎫</div>
                <div style="font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; letter-spacing: 0.2px;">OPEN TICKETS</div>
            </div>
            <div style="font-size: 20px; font-weight: 800; color: #172B4D; font-family: 'Outfit', sans-serif; line-height: 1.1; margin: 2px 0;">{open_tickets_count}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: #6B7C93; border-top: 1px solid #F8FAFC; padding-top: 4px;">
                <span style="white-space: nowrap;">Support queue</span>
                <span style="color: #EF4444; font-weight: 600; white-space: nowrap;">↗ 5.6%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    # 3. MAIN ANALYTICS ROW (3 COLUMNS)
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    col_a1, col_a2, col_a3 = st.columns([1.6, 1.2, 1.2])
    
    # Column 1: Transaction Volume Trend
    with col_a1:
        with st.container(border=True):
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
                <h3 style="font-size: 13.5px; font-weight: 700; color: #172B4D; font-family: 'Outfit', sans-serif; margin: 0;">Transaction Volume Trend</h3>
                <div style="font-size: 10.5px; color: #6B7C93; background: #F8FAFC; border: 1px solid #E2E8F0; padding: 2px 6px; border-radius: 4px; font-weight: 500;">
                    7 Days ▼
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            import plotly.graph_objects as go
            fig_trend = go.Figure()
            
            dates_x = ['May 22', 'May 23', 'May 24', 'May 25', 'May 26', 'May 27', 'May 28']
            this_week_y = [2300, 3950, 4200, 4800, 6100, 7100, 5800]
            last_week_y = [1800, 2400, 2750, 3400, 4300, 5600, 4900]
            
            fig_trend.add_trace(go.Scatter(
                x=dates_x,
                y=this_week_y,
                mode='lines+markers',
                name='This Week',
                line=dict(color='#2563EB', width=2.2),
                marker=dict(size=6, color='#2563EB', line=dict(color='#FFFFFF', width=1.5)),
                hovertemplate='<b>This Week</b>: %{y:,}<extra></extra>'
            ))
            
            fig_trend.add_trace(go.Scatter(
                x=dates_x,
                y=last_week_y,
                mode='lines+markers',
                name='Last Week',
                line=dict(color='#94A3B8', width=1.8, dash='dot'),
                marker=dict(size=5, symbol='diamond', color='#94A3B8'),
                hovertemplate='<b>Last Week</b>: %{y:,}<extra></extra>'
            ))
            
            fig_trend.update_layout(
                height=195,
                margin=dict(l=5, r=5, t=15, b=10),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=1.02,
                    xanchor='left',
                    x=0,
                    font=dict(size=10, color='#6B7C93', family='Inter'),
                    itemclick=False,
                    itemdoubleclick=False
                ),
                xaxis=dict(
                    showgrid=False,
                    zeroline=False,
                    tickfont=dict(size=9.5, color='#6B7C93', family='Inter'),
                    linecolor='#E2E8F0'
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='#F1F5F9',
                    zeroline=False,
                    range=[0, 8500],
                    tickvals=[0, 2000, 4000, 6000, 8000],
                    ticktext=['0', '2K', '4K', '6K', '8K'],
                    tickfont=dict(size=9.5, color='#6B7C93', family='Inter')
                ),
                hovermode='x unified'
            )
            st.plotly_chart(fig_trend, use_container_width=True, config={'displayModeBar': False})
        
    # Column 2: Reconciliation Health Donut Chart
    with col_a2:
        with st.container(border=True):
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="font-size: 13.5px; font-weight: 700; color: #172B4D; font-family: 'Outfit', sans-serif; margin: 0;">Reconciliation Health</h3>
            </div>
            """, unsafe_allow_html=True)
            
            fig_donut = go.Figure(data=[go.Pie(
                labels=['Matched', 'Mismatched', 'Pending', 'Failed'],
                values=[19842, 2845, 1723, 440],
                hole=0.68,
                marker=dict(colors=['#10B981', '#F97316', '#FBBF24', '#EF4444']),
                textinfo='none',
                hoverinfo='label+value+percent',
                sort=False
            )])
            
            fig_donut.update_layout(
                height=130,
                margin=dict(l=0, r=0, t=5, b=5),
                showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                annotations=[
                    dict(
                        text='<span style="font-size:15px; font-weight:800; color:#172B4D; font-family:Outfit;">24,850</span><br><span style="font-size:10px; color:#6B7C93; font-family:Inter;">Total</span>',
                        x=0.5, y=0.5,
                        font_size=13,
                        showarrow=False
                    )
                ]
            )
            st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("""
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 10px; font-family: 'Inter', sans-serif; border-top: 1px solid #F8FAFC; padding-top: 4px;">
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="width: 6px; height: 6px; border-radius: 50%; background: #10B981; display: inline-block;"></span>
                    <span style="color: #6B7C93;">Matched</span>
                    <strong style="color: #172B4D; margin-left: auto;">19.8K (79.8%)</strong>
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="width: 6px; height: 6px; border-radius: 50%; background: #F97316; display: inline-block;"></span>
                    <span style="color: #6B7C93;">Mismatch</span>
                    <strong style="color: #172B4D; margin-left: auto;">2.8K (11.4%)</strong>
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="width: 6px; height: 6px; border-radius: 50%; background: #FBBF24; display: inline-block;"></span>
                    <span style="color: #6B7C93;">Pending</span>
                    <strong style="color: #172B4D; margin-left: auto;">1.7K (6.9%)</strong>
                </div>
                <div style="display: flex; align-items: center; gap: 4px;">
                    <span style="width: 6px; height: 6px; border-radius: 50%; background: #EF4444; display: inline-block;"></span>
                    <span style="color: #6B7C93;">Failed</span>
                    <strong style="color: #172B4D; margin-left: auto;">440 (1.8%)</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
    # Column 3: Top Exception Categories
    with col_a3:
        with st.container(border=True):
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h3 style="font-size: 13.5px; font-weight: 700; color: #172B4D; font-family: 'Outfit', sans-serif; margin: 0;">Top Exception Categories</h3>
                <a href="?page=admin_exceptions" target="_self" style="font-size: 11px; font-weight: 600; color: #2563EB; text-decoration: none;">View All</a>
            </div>
            <div style="display: flex; flex-direction: column; justify-content: space-around; height: 185px;">
                <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px;">
                    <div style="display: flex; align-items: center; gap: 6px; width: 115px; flex-shrink: 0;">
                        <span style="color: #EF4444; font-size: 8px;">●</span>
                        <span style="color: #172B4D; font-weight: 500;">Amount Mismatch</span>
                    </div>
                    <div style="flex-grow: 1; margin: 0 8px; background: #F1F5F9; height: 5px; border-radius: 3px; overflow: hidden;">
                        <div style="width: 47.4%; height: 100%; background: #EF4444; border-radius: 3px;"></div>
                    </div>
                    <div style="width: 45px; text-align: right; flex-shrink: 0; font-size: 10.5px;">
                        <strong style="color: #172B4D;">18</strong>
                        <span style="color: #6B7C93; font-size: 9.5px; margin-left: 2px;">47.4%</span>
                    </div>
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px;">
                    <div style="display: flex; align-items: center; gap: 6px; width: 115px; flex-shrink: 0;">
                        <span style="color: #F97316; font-size: 8px;">●</span>
                        <span style="color: #172B4D; font-weight: 500;">Status Mismatch</span>
                    </div>
                    <div style="flex-grow: 1; margin: 0 8px; background: #F1F5F9; height: 5px; border-radius: 3px; overflow: hidden;">
                        <div style="width: 21.1%; height: 100%; background: #F97316; border-radius: 3px;"></div>
                    </div>
                    <div style="width: 45px; text-align: right; flex-shrink: 0; font-size: 10.5px;">
                        <strong style="color: #172B4D;">8</strong>
                        <span style="color: #6B7C93; font-size: 9.5px; margin-left: 2px;">21.1%</span>
                    </div>
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px;">
                    <div style="display: flex; align-items: center; gap: 6px; width: 115px; flex-shrink: 0;">
                        <span style="color: #F59E0B; font-size: 8px;">●</span>
                        <span style="color: #172B4D; font-weight: 500;">Missing Bank Credit</span>
                    </div>
                    <div style="flex-grow: 1; margin: 0 8px; background: #F1F5F9; height: 5px; border-radius: 3px; overflow: hidden;">
                        <div style="width: 15.8%; height: 100%; background: #F59E0B; border-radius: 3px;"></div>
                    </div>
                    <div style="width: 45px; text-align: right; flex-shrink: 0; font-size: 10.5px;">
                        <strong style="color: #172B4D;">6</strong>
                        <span style="color: #6B7C93; font-size: 9.5px; margin-left: 2px;">15.8%</span>
                    </div>
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px;">
                    <div style="display: flex; align-items: center; gap: 6px; width: 115px; flex-shrink: 0;">
                        <span style="color: #3B82F6; font-size: 8px;">●</span>
                        <span style="color: #172B4D; font-weight: 500;">Missing Order</span>
                    </div>
                    <div style="flex-grow: 1; margin: 0 8px; background: #F1F5F9; height: 5px; border-radius: 3px; overflow: hidden;">
                        <div style="width: 10.5%; height: 100%; background: #3B82F6; border-radius: 3px;"></div>
                    </div>
                    <div style="width: 45px; text-align: right; flex-shrink: 0; font-size: 10.5px;">
                        <strong style="color: #172B4D;">4</strong>
                        <span style="color: #6B7C93; font-size: 9.5px; margin-left: 2px;">10.5%</span>
                    </div>
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px;">
                    <div style="display: flex; align-items: center; gap: 6px; width: 115px; flex-shrink: 0;">
                        <span style="color: #6366F1; font-size: 8px;">●</span>
                        <span style="color: #172B4D; font-weight: 500;">Tax Mismatch</span>
                    </div>
                    <div style="flex-grow: 1; margin: 0 8px; background: #F1F5F9; height: 5px; border-radius: 3px; overflow: hidden;">
                        <div style="width: 2.6%; height: 100%; background: #6366F1; border-radius: 3px;"></div>
                    </div>
                    <div style="width: 45px; text-align: right; flex-shrink: 0; font-size: 10.5px;">
                        <strong style="color: #172B4D;">1</strong>
                        <span style="color: #6B7C93; font-size: 9.5px; margin-left: 2px;">2.6%</span>
                    </div>
                </div>
                <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px;">
                    <div style="display: flex; align-items: center; gap: 6px; width: 115px; flex-shrink: 0;">
                        <span style="color: #8B5CF6; font-size: 8px;">●</span>
                        <span style="color: #172B4D; font-weight: 500;">Settlement Mismatch</span>
                    </div>
                    <div style="flex-grow: 1; margin: 0 8px; background: #F1F5F9; height: 5px; border-radius: 3px; overflow: hidden;">
                        <div style="width: 2.6%; height: 100%; background: #8B5CF6; border-radius: 3px;"></div>
                    </div>
                    <div style="width: 45px; text-align: right; flex-shrink: 0; font-size: 10.5px;">
                        <strong style="color: #172B4D;">1</strong>
                        <span style="color: #6B7C93; font-size: 9.5px; margin-left: 2px;">2.6%</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    # 4. SECONDARY DATA ROW (3 COLUMNS)
    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
    col_t1, col_t2, col_t3 = st.columns([1.0, 1.25, 1.25])
    
    # 1. Merchant Performance Table
    with col_t1:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); height: 220px; box-sizing: border-box; overflow-x: auto; width: 100%;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="font-size: 13.5px; font-weight: 700; color: #172B4D; font-family: 'Outfit', sans-serif; margin: 0;">Merchant Performance</h3>
                <a href="?page=admin_merchants" target="_self" style="font-size: 11px; font-weight: 600; color: #2563EB; text-decoration: none;">View All</a>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; font-size: 11px;">
                <thead>
                    <tr>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Merchant</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Stores</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Volume (₹)</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Match Rate</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Exceptions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 7px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <div style="width: 18px; height: 18px; border-radius: 3px; background: #FFD814; display: flex; align-items: center; justify-content: center; font-size: 10px;">🛍️</div>
                                <strong>Flipkart</strong>
                            </div>
                        </td>
                        <td style="padding: 7px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">4</td>
                        <td style="padding: 7px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">₹112,842.45</td>
                        <td style="padding: 7px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="background: #ECFDF5; color: #10B981; padding: 1px 5px; border-radius: 3px; font-weight: 700; font-size: 10px;">98.2%</span></td>
                        <td style="padding: 7px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="color: #EF4444; font-weight: 700;">23</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 7px 4px; border-bottom: none; white-space: nowrap;">
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <div style="width: 18px; height: 18px; border-radius: 3px; background: #131921; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #FF9900; font-family: Outfit; font-weight: 800;">a</div>
                                <strong>Amazon</strong>
                            </div>
                        </td>
                        <td style="padding: 7px 4px; border-bottom: none; white-space: nowrap;">6</td>
                        <td style="padding: 7px 4px; border-bottom: none; white-space: nowrap;">₹83,531.26</td>
                        <td style="padding: 7px 4px; border-bottom: none; white-space: nowrap;"><span style="background: #ECFDF5; color: #10B981; padding: 1px 5px; border-radius: 3px; font-weight: 700; font-size: 10px;">97.1%</span></td>
                        <td style="padding: 7px 4px; border-bottom: none; white-space: nowrap;"><span style="color: #EF4444; font-weight: 700;">15</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
    # 2. Recent High Priority Exceptions Table
    with col_t2:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); height: 220px; box-sizing: border-box; overflow-x: auto; width: 100%;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="font-size: 13.5px; font-weight: 700; color: #172B4D; font-family: 'Outfit', sans-serif; margin: 0;">Recent High Priority Exceptions</h3>
                <a href="?page=admin_exceptions" target="_self" style="font-size: 11px; font-weight: 600; color: #2563EB; text-decoration: none;">View All</a>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; font-size: 11px;">
                <thead>
                    <tr>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">ID</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Merchant</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Store</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Type</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Amount</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Age</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><strong style="color: #2563EB;">EXC-10245</strong></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Flipkart</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Delhi</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="background-color: #FEE2E2; color: #EF4444; border: 1px solid #FECACA; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600;">Amount Mismatch</span></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">₹24,850.00</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="color: #EF4444; font-weight: 700;">2h</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><strong style="color: #2563EB;">EXC-10244</strong></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Amazon</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Mumbai</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="background-color: #FFEDD5; color: #EA580C; border: 1px solid #FED7AA; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600;">Status Mismatch</span></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">₹18,420.50</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="color: #F59E0B; font-weight: 700;">3h</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><strong style="color: #2563EB;">EXC-10243</strong></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Flipkart</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Bangalore</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="background-color: #FEE2E2; color: #EF4444; border: 1px solid #FECACA; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600;">Missing Bank Credit</span></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">₹12,330.75</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="color: #6B7C93; font-weight: 500;">5h</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;"><strong style="color: #2563EB;">EXC-10242</strong></td>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;">Amazon</td>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;">Delhi</td>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;"><span style="background-color: #FEF3C7; color: #D97706; border: 1px solid #FDE68A; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600;">Settlement Mismatch</span></td>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;">₹8,965.10</td>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;"><span style="color: #6B7C93; font-weight: 500;">6h</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
    # 3. Recent Support Tickets Table
    with col_t3:
        st.markdown("""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02); height: 220px; box-sizing: border-box; overflow-x: auto; width: 100%;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="font-size: 13.5px; font-weight: 700; color: #172B4D; font-family: 'Outfit', sans-serif; margin: 0;">Recent Support Tickets</h3>
                <a href="?page=admin_tickets" target="_self" style="font-size: 11px; font-weight: 600; color: #2563EB; text-decoration: none;">View All</a>
            </div>
            <table style="width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; font-size: 11px;">
                <thead>
                    <tr>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Ticket ID</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Merchant</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Subject</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Priority</th>
                        <th style="padding: 5px 4px; font-size: 9.5px; font-weight: 700; color: #6B7C93; text-transform: uppercase; border-bottom: 1px solid #E2E8F0; text-align: left; white-space: nowrap;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><strong style="color: #2563EB;">TKT-5005</strong></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Flipkart</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Settlement mismatch</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="background: #FEE2E2; color: #EF4444; padding: 1px 5px; border-radius: 3px; font-size: 9.5px; font-weight: 600;">High</span></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="background: #EFF6FF; color: #3B82F6; padding: 1px 5px; border-radius: 3px; font-size: 9.5px; font-weight: 600;">Open</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><strong style="color: #2563EB;">TKT-5004</strong></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Amazon</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Payment not reflected</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="background: #FEF3C7; color: #D97706; padding: 1px 5px; border-radius: 3px; font-size: 9.5px; font-weight: 600;">Medium</span></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="background: #EFF6FF; color: #3B82F6; padding: 1px 5px; border-radius: 3px; font-size: 9.5px; font-weight: 600;">In Progress</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><strong style="color: #2563EB;">TKT-5003</strong></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Flipkart</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;">Bank reconciliation</td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="background: #FEE2E2; color: #EF4444; padding: 1px 5px; border-radius: 3px; font-size: 9.5px; font-weight: 600;">High</span></td>
                        <td style="padding: 6px 4px; border-bottom: 1px solid #F8FAFC; white-space: nowrap;"><span style="background: #EFF6FF; color: #3B82F6; padding: 1px 5px; border-radius: 3px; font-size: 9.5px; font-weight: 600;">Open</span></td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;"><strong style="color: #2563EB;">TKT-5002</strong></td>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;">Amazon</td>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;">TDS query</td>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;"><span style="background: #F1F5F9; color: #64748B; padding: 1px 5px; border-radius: 3px; font-size: 9.5px; font-weight: 600;">Low</span></td>
                        <td style="padding: 6px 4px; border-bottom: none; white-space: nowrap;"><span style="background: #ECFDF5; color: #10B981; padding: 1px 5px; border-radius: 3px; font-size: 9.5px; font-weight: 600;">Resolved</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
    # 5. BOTTOM PLATFORM ALERT
    st.markdown("""
    <div style="background-color: #FEF2F2; border: 1px solid #FEE2E2; border-radius: 8px; padding: 14px 20px; display: flex; justify-content: space-between; align-items: center; margin-top: 14px; margin-bottom: 20px;">
        <div style="display: flex; align-items: center; gap: 14px;">
            <div style="width: 32px; height: 32px; border-radius: 6px; background-color: #FEE2E2; display: flex; align-items: center; justify-content: center; color: #EF4444; font-size: 16px;">
                ⚠️
            </div>
            <div>
                <div style="font-weight: 700; font-size: 13.5px; color: #991B1B; font-family: 'Outfit', sans-serif;">
                    Platform Alert
                </div>
                <div style="font-size: 12.5px; color: #7F1D1D; margin-top: 1px; font-family: 'Inter', sans-serif;">
                    Unusual spike in amount mismatches detected in Flipkart stores. Please review exceptions.
                </div>
            </div>
        </div>
        <div>
            <a href="?page=admin_exceptions" target="_self" style="background-color: #FFFFFF; border: 1px solid #FCA5A5; color: #991B1B; padding: 7px 16px; border-radius: 6px; font-size: 12.5px; font-weight: 600; text-decoration: none; display: inline-block;">
                View Exceptions
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ----------------------------------------------------
# ADMIN PAGE 2: PLATFORM EXCEPTIONS LEDGER
# ----------------------------------------------------
elif st.session_state.page == "admin_exceptions":
    st.markdown("<h2>⚠ Global Exception Command Center</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Monitor, debug, and resolve matching exceptions across all merchants and stores.</p>", unsafe_allow_html=True)
    
    from src.database import get_merchants, get_stores, resolve_transaction_exception
    merchants = get_merchants()
    
    col_m_sel, col_s_sel = st.columns(2)
    with col_m_sel:
        m_opts = ["All Merchants"] + [m['merchant_id'] for m in merchants]
        m_sel = st.selectbox("Filter Merchant Entity", m_opts)
        if m_sel == "All Merchants":
            st.session_state.admin_filter_merchant = None
            st.session_state.admin_filter_store = None
        else:
            st.session_state.admin_filter_merchant = m_sel
            
    with col_s_sel:
        if st.session_state.admin_filter_merchant:
            stores = get_stores(st.session_state.admin_filter_merchant)
            s_opts = ["All Stores"] + [s['store_id'] for s in stores]
            s_sel = st.selectbox("Filter Store Location", s_opts)
            if s_sel == "All Stores":
                st.session_state.admin_filter_store = None
            else:
                st.session_state.admin_filter_store = s_sel
        else:
            st.selectbox("Filter Store Location", ["All Stores"], disabled=True)
            st.session_state.admin_filter_store = None
            
    st.markdown("### Platform Exception Ledger")
    
    excs_tx = df_tx[df_tx['calculated_exceptions'].apply(lambda x: len(x) > 0 if isinstance(x, list) else False)]
    
    if excs_tx.empty:
        st.info("No active exceptions detected in the selected filter.")
    else:
        for idx, row in excs_tx.iterrows():
            bg_c, text_c, border_c, status_lbl, severity = get_mismatch_color_tuple(row['calculated_exceptions'], row['resolution_status'])
            m_id_upper = row['merchant_id'].upper()
            s_loc_upper = row['store_id'].split('_')[-1].upper()
            amt_formatted = f"{row['amount_inr']:.2f}"
            method_val = row['method']
            
            pills_html = get_exception_pills_html(row['calculated_exceptions'])
            ex_card_html = (
                f'<div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-left: 5px solid {text_c}; padding: 16px; border-radius: 6px; margin-bottom: 12px; font-family: \'Inter\', sans-serif; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">'
                '    <div style="display:flex; justify-content:space-between; align-items:center;">'
                f'        <strong style="color:#172B4D; font-size:13.5px;">Transaction Ref: <code>{row["transaction_id"]}</code> (Order Ref: <code>{row["order_id"]}</code>)</strong>'
                f'        <span style="font-weight:700; font-size:11px; padding:2px 8px; border-radius:4px; color:{text_c}; background-color:{bg_c}; border:1px solid {border_c};">{status_lbl}</span>'
                '    </div>'
                '    <div style="font-size:12px; color:#6B7C93; margin-top:4px;">'
                f'        Merchant: <strong>{m_id_upper}</strong> | Store: <strong>{s_loc_upper}</strong> | Amount: <strong style="color:#172B4D;">INR {amt_formatted}</strong> | Method: {method_val}'
                '    </div>'
                '    <div style="font-size:13px; margin: 8px 0;">'
                f'        {pills_html}'
                '    </div>'
            )
            st.markdown(ex_card_html, unsafe_allow_html=True)
            
            if row['resolution_status'] == 'NEEDS_REVIEW':
                with st.expander(f"Resolve Exception for {row['transaction_id']}"):
                    note = st.text_input("Audit Resolution Note", key=f"note_{row['transaction_id']}")
                    if st.button("Apply Manual Correction", key=f"btn_res_{row['transaction_id']}"):
                        if note.strip():
                            resolve_transaction_exception(row['transaction_id'], note.strip())
                            st.success(f"Transaction {row['transaction_id']} resolved successfully.")
                            st.rerun()
                        else:
                            st.error("Please add resolution notes for audit tracking.")
            else:
                st.markdown(
                    '<div style="margin-top: 8px; padding: 8px 12px; background-color: #F0FDF4; border-left: 3px solid #10B981; border-radius: 4px; font-size: 12.5px; color:#1E3A1E;">\n'
                    f'    <strong>Corrected Resolution:</strong> {row.get("resolution_note", "Auto-resolved during engine check")}\n'
                    '</div>',
                    unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------------------
# ADMIN PAGE 3: TICKET RESOLVER
# ----------------------------------------------------
elif st.session_state.page == "admin_tickets":
    st.markdown("<h2>🎟 Support Tickets Resolution Center</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Review and reply to helpdesk queries submitted by merchant users.</p>", unsafe_allow_html=True)
    
    from src.database import get_support_tickets, resolve_support_ticket
    tickets = get_support_tickets()
    
    if not tickets:
        st.info("No helpdesk queries raised on the platform.")
    else:
        for tk in tickets:
            color_tk = "var(--success)" if tk['status'] == 'RESOLVED' else "var(--warning)"
            t_merchant = (tk['merchant_id'] or "general").upper()
            t_store = tk['store_id'].split('_')[-1].upper()
            t_tx = tk['transaction_id'] if tk['transaction_id'] else 'None'
            ticket_info_html = (
                f'<div style="background-color: #FFFFFF; border: 1px solid var(--border); border-left: 4px solid {color_tk}; padding: 16px; border-radius: 6px; margin-bottom: 12px; font-family: \'Inter\', sans-serif;">\n'
                '    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">\n'
                f'        <strong style="color: var(--navy); font-size: 14.5px;">Ticket #{tk["ticket_id"]}: {tk["subject"]}</strong>\n'
                f'        <span style="color: {color_tk}; font-weight: 700; font-size: 11px; padding: 2px 8px; border-radius: 20px; background-color:#F1F5F9;">{tk["status"]}</span>\n'
                '    </div>\n'
                '    <span style="font-size: 11.5px; color: var(--text-sec);">\n'
                f'        Merchant: {t_merchant} | Store: {t_store} | Related Tx: {t_tx} | Created: {tk["timestamp"]}\n'
                '    </span>\n'
                f'    <p style="margin: 8px 0; font-size: 13px; background: #F8FAFC; padding: 10px; border-radius: 4px; border: 1px solid var(--border);">{tk["message"]}</p>'
            )
            st.markdown(ticket_info_html, unsafe_allow_html=True)
            
            if tk['status'] in ['OPEN', 'PENDING']:
                with st.expander("Reply and Resolve Ticket"):
                    reply_text = st.text_area("Operations Response Msg", key=f"reply_{tk['ticket_id']}")
                    if st.button("Submit Response & Mark Resolved", key=f"btn_reply_{tk['ticket_id']}"):
                        if reply_text.strip():
                            resolve_support_ticket(tk['ticket_id'], reply_text.strip())
                            st.toast(f"Ticket #{tk['ticket_id']} resolved!", icon="\u2705")
                            st.rerun()
                        else:
                            st.error("Please enter a response body.")
            else:
                st.markdown(
                    '<div style="margin-top: 8px; padding: 10px 14px; background-color: #F0FDF4; border-left: 3px solid #10B981; border-radius: 4px; font-size: 12.5px; color:#1E3A1E;">\n'
                    f'    <strong>Resolved Response:</strong> {tk["reply"]}\n'
                    '</div>',
                    unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)

# ----------------------------------------------------
# ADMIN PAGE 4: CENTRAL AI & RAG CONTROL CENTER
# ----------------------------------------------------
elif st.session_state.page == "admin_ai":
    st.markdown("<h2>✦ Central Intelligence & RAG Operations Center</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Centralized AI configurations and RAG Knowledge Hub. Merchants consume these settings in read-only form.</p>", unsafe_allow_html=True)
    
    from src.database import get_indexed_documents, set_config
    indexed_docs = get_indexed_documents()
    total_docs = len(indexed_docs)
    
    has_key = bool(st.session_state.sys_gemini_api_key)
    rag_connected = has_key and total_docs > 0
    status_color = "#10B981" if rag_connected else "#EF4444"
    status_text = "Connected" if rag_connected else "Not Connected"
    
    col_cfg_l, col_cfg_r = st.columns(2)
    with col_cfg_l:
        masked_key = ""
        if has_key:
            raw_key = st.session_state.sys_gemini_api_key
            masked_key = "•" * 12 + raw_key[-4:] if len(raw_key) >= 4 else "••••••••••••••••"
            
        new_key_input = st.text_input(
            "Gemini API Key",
            type="password",
            value="",
            placeholder="Enter new Gemini API key to update...",
            help=f"Active Key: {masked_key}" if has_key else "No active key configured."
        )
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            test_conn = st.button("Test Connection", use_container_width=True)
        with col_t2:
            save_cfg = st.button("Save Configuration", use_container_width=True)
            
    with col_cfg_r:
        selected_model_val = st.selectbox(
            "Gemini Model",
            ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
            index=["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"].index(st.session_state.sys_gemini_model) if st.session_state.sys_gemini_model in ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"] else 0
        )
        
        rag_status_html = (
            '<div style="background-color: #F8FAFC; border: 1px solid var(--border); padding: 12px; border-radius: 6px; margin-top: 10px;">\n'
            '    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">\n'
            f'        <span style="color: {status_color}; font-size: 1.15rem;">&#9679;</span>\n'
            f'        <strong style="font-size: 13.5px; color: var(--navy);">RAG Status: {status_text}</strong>\n'
            '    </div>\n'
            '    <div style="font-size: 12.5px; color: var(--text-sec);">\n'
            f'        <strong>Document Index:</strong> {total_docs} documents indexed\n'
            '    </div>\n'
            '</div>'
        )
        st.markdown(rag_status_html, unsafe_allow_html=True)

    if test_conn:
        test_key = new_key_input.strip() or st.session_state.sys_gemini_api_key
        if not test_key:
            st.error("No API key available to test.")
        else:
            with st.spinner("Testing connection..."):
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=test_key)
                    test_model = genai.GenerativeModel(selected_model_val)
                    resp = test_model.generate_content("Ping test. Respond with 'OK'.")
                    if resp.text:
                        st.success("Connection Successful!")
                except Exception as e:
                    st.error(f"Connection Failed: {str(e)}")
                      
    if save_cfg:
        if new_key_input.strip():
            st.session_state.sys_gemini_api_key = new_key_input.strip()
            set_config("sys_gemini_api_key", new_key_input.strip())
        st.session_state.sys_gemini_model = selected_model_val
        set_config("sys_gemini_model", selected_model_val)
        st.success("Central intelligence configurations saved successfully.")
        st.rerun()
        
    st.markdown("---")
    st.markdown("### Document Hub & RAG Uploads")
    
    m_c1, m_c2, m_c3 = st.columns(3)
    with m_c1:
        st.metric("Documents", total_docs)
    with m_c2:
        st.metric("Indexed", total_docs)
    with m_c3:
        st.metric("Failed", 0)
        
    uploaded_file = st.file_uploader("Upload Document (PDF or Markdown)", type=["pdf", "md"])
    if uploaded_file is not None:
        if st.button("Upload & Index Document"):
            with st.spinner("Processing document embeddings..."):
                try:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    docs_dir = os.path.join(base_dir, "documents")
                    os.makedirs(docs_dir, exist_ok=True)
                    dest_path = os.path.join(docs_dir, uploaded_file.name)
                    
                    with open(dest_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                        
                    from src.rag_engine import build_document_index
                    active_key = st.session_state.sys_gemini_api_key
                    if build_document_index(active_key, force_reindex=True):
                        st.success(f"[OK] Indexed {uploaded_file.name} successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to generate document index embeddings.")
                except Exception as ex:
                    st.error(f"Upload Error: {str(ex)}")

    st.markdown("#### Document Index Status Table")
    if not indexed_docs:
        st.info("No documents currently indexed.")
    else:
        for idx, doc in enumerate(indexed_docs):
            d_name = doc['file_name']
            d_type = "PDF" if d_name.endswith('.pdf') else "MD"
            d_chunks = doc['chunks']
            
            c_tbl1, c_tbl2, c_tbl3, c_tbl4, c_tbl5 = st.columns([3, 1, 1, 2, 2])
            with c_tbl1:
                st.markdown(f"📄 **{d_name}**")
            with c_tbl2:
                st.markdown(f"`{d_type}`")
            with c_tbl3:
                st.markdown(f"{d_chunks} chunks")
            with c_tbl4:
                st.markdown("<span style='color: #10B981; font-weight: 600;'>&#10003; Indexed</span>", unsafe_allow_html=True)
            with c_tbl5:
                col_btn_v, col_btn_d = st.columns(2)
                with col_btn_v:
                    if st.button("View", key=f"btn_view_{idx}_{d_name}"):
                        st.session_state[f"view_toggle_{d_name}"] = not st.session_state.get(f"view_toggle_{d_name}", False)
                with col_btn_d:
                    if st.button("Delete", key=f"btn_del_{idx}_{d_name}"):
                        from src.database import delete_document_chunks
                        delete_document_chunks(d_name)
                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        local_file = os.path.join(base_dir, "documents", d_name)
                        if os.path.exists(local_file):
                            os.remove(local_file)
                        st.success(f"Deleted index references for {d_name}.")
                        st.rerun()
                        
            if st.session_state.get(f"view_toggle_{d_name}", False):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                local_file = os.path.join(base_dir, "documents", d_name)
                if os.path.exists(local_file):
                    with open(local_file, "r", encoding="utf-8", errors="ignore") as f_prev:
                        st.text_area(f"Preview: {d_name}", f_prev.read()[:2000], height=200, key=f"txt_area_{idx}_{d_name}")

    st.markdown("---")
    st.markdown("### Test RAG Pipeline")
    
    test_prompt = st.text_input(
        "Test Question", 
        value="How is TDS calculated according to the uploaded policy?",
        key="config_rag_test_prompt"
    )
    
    if st.button("Test RAG", key="btn_run_test_rag"):
        if not st.session_state.sys_gemini_api_key:
            st.error("RAG testing requires a valid Gemini API key to run semantic embeddings.")
        else:
            with st.spinner("Executing retrieval queries..."):
                try:
                    from src.rag_engine import retrieve_relevant_context_with_sources
                    results = retrieve_relevant_context_with_sources(test_prompt, st.session_state.sys_gemini_api_key, top_n=3)
                    
                    if not results:
                        st.warning("No matching context blocks returned from database index.")
                    else:
                        st.markdown(f"**Retrieved Documents:** {len(results)}")
                        top_src = results[0]
                        st.markdown(f"**Top matching source:** `{top_src['file_name']}`")
                        
                        similarity_pct = int(top_src.get('score', 0.5) * 100)
                        st.markdown(f"**Similarity / relevance:** `{similarity_pct}%`")
                        
                        context_str = "\n\n".join([r['text_content'] for r in results])
                        prompt_str = (
                            "You are the AI Finance Controller assistant.\n"
                            "Answer the user's question using the provided financial documents/context.\n\n"
                            f"Retrieved Context:\n{context_str}\n\n"
                            f"User Question:\n{test_prompt}\n"
                        )
                        
                        import google.generativeai as genai
                        genai.configure(api_key=st.session_state.sys_gemini_api_key)
                        test_model = genai.GenerativeModel(selected_model_val)
                        resp = test_model.generate_content(prompt_str)
                        st.markdown("**Generated Answer:**")
                        st.info(resp.text)
                except Exception as e:
                    st.error(f"RAG Test Error: {str(e)}")

# ----------------------------------------------------
# ADMIN PAGE 5: USERS & ROLES
# ----------------------------------------------------
elif st.session_state.page == "admin_users":
    st.markdown("<h2>♙ Users & Access Management</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Manage corporate logins, reset credentials, and audit tenant stores access.</p>", unsafe_allow_html=True)
    
    from src.database import get_users, reset_user_password
    users_list = get_users()
    
    st.markdown("### Seeded Accounts Ledger")
    df_usr = pd.DataFrame(users_list)
    st.dataframe(df_usr[['user_id', 'email', 'role', 'merchant_id', 'store_id']], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("### Force Credentials Recovery")
    with st.form(key="admin_reset_pwd_form", clear_on_submit=True):
        user_emails = [u['email'] for u in users_list if u['role'] == 'MERCHANT']
        sel_email = st.selectbox("Select Merchant User Email", user_emails)
        new_pass = st.text_input("Temporary Recovered Password", type="password")
        submit_reset = st.form_submit_button("Reset Password & Force Sync")
        
    if submit_reset:
        if sel_email and new_pass.strip():
            reset_user_password(sel_email, new_pass.strip())
            st.success(f"[OK] Credentials for {sel_email} updated successfully.")
            st.toast(f"Password reset for {sel_email}!", icon="\u2705")
        else:
            st.error("Please select a user and provide a new password.")

# ----------------------------------------------------
# ADMIN PAGE 6: AUDIT TRAIL LOGS
# ----------------------------------------------------
elif st.session_state.page == "admin_audit":
    st.markdown("<h2>▤ Platform Audit Trail Logs</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Verifiable chronological database of all operations, manual adjustments, and user login activity.</p>", unsafe_allow_html=True)
    
    from src.database import get_action_logs
    action_logs = get_action_logs()
    
    if not action_logs:
        st.info("No audit logs recorded in the system yet.")
    else:
        df_logs = pd.DataFrame(action_logs)
        st.dataframe(df_logs[['log_id', 'timestamp', 'user_email', 'action', 'details']], use_container_width=True, hide_index=True)

# ----------------------------------------------------
# ADMIN PAGE 7: PLATFORM SETTINGS & RULES
# ----------------------------------------------------
elif st.session_state.page == "admin_settings":
    st.markdown("<h2>⚙ platform settings & compliance parameters</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Adjust matching parameters, fee structures, and Section 194-O TDS compliance configurations.</p>", unsafe_allow_html=True)
    
    st.markdown("### Standard Reconciliation Parameters")
    st.session_state.sys_gateway_fee = st.number_input("Standard Gateway fee rate (%)", min_value=0.0, max_value=10.0, value=st.session_state.sys_gateway_fee, step=0.1)
    st.session_state.sys_gst_rate = st.number_input("GST rate on gateway charges (%)", min_value=0.0, max_value=30.0, value=st.session_state.sys_gst_rate, step=1.0)
    st.session_state.sys_payout_fee = st.number_input("Standard payout Flat rate (INR)", min_value=0.0, max_value=100.0, value=st.session_state.sys_payout_fee, step=1.0)
    st.session_state.sys_settlement_delay = st.selectbox("Expected settlement Delay", ["T+2 Days", "T+1 Day", "T+0 Days"], index=0)
    
    st.markdown("### Section 194-O TDS Policy Adjustments")
    with st.expander("Update Withholding Settings"):
        st.markdown("**Resident Individual Rate settings**")
        app_ind = st.checkbox("Resident Individual Withholding", value=st.session_state.sys_tds_config['PAYMENT']['Individual']['applicable'])
        rate_ind = st.number_input("Individual Withholding TDS (%)", min_value=0.0, max_value=10.0, value=st.session_state.sys_tds_config['PAYMENT']['Individual']['rate']*100, step=0.1)/100
        
        st.markdown("**Corporate Rate settings**")
        app_corp = st.checkbox("Corporate Withholding", value=st.session_state.sys_tds_config['PAYMENT']['Company']['applicable'])
        rate_corp = st.number_input("Corporate Withholding TDS (%)", min_value=0.0, max_value=10.0, value=st.session_state.sys_tds_config['PAYMENT']['Company']['rate']*100, step=0.1)/100
        
        st.session_state.sys_tds_config['PAYMENT']['Individual']['applicable'] = app_ind
        st.session_state.sys_tds_config['PAYMENT']['Individual']['rate'] = rate_ind
        st.session_state.sys_tds_config['PAYMENT']['Company']['applicable'] = app_corp
        st.session_state.sys_tds_config['PAYMENT']['Company']['rate'] = rate_corp
        
    if st.button("Save Settings", key="btn_save_admin_settings"):
        st.success("[OK] Platform settings and Section 194-O rules updated successfully.")
        st.toast("Settings saved!", icon="✅")
        st.rerun()

# ----------------------------------------------------
# ADMIN SUBPAGE: MERCHANTS PORTFOLIO
# ----------------------------------------------------
elif st.session_state.page == "admin_merchants":
    st.markdown("<h2>♙ Global Merchant Portfolio Directory</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Platform overview of all registered enterprise merchant entities and store networks.</p>", unsafe_allow_html=True)
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown("""
        <div class="admin-card">
            <div class="admin-card-header">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 32px; height: 32px; border-radius: 6px; background: #FFD814; display: flex; align-items: center; justify-content: center; font-size: 16px;">🛍️</div>
                    <div>
                        <h3 class="admin-card-title">Flipkart Internet Private Limited</h3>
                        <span style="font-size: 11.5px; color: #6B7C93;">MID: MID-FK-99201 | Status: <span class="admin-badge admin-badge-success">ACTIVE</span></span>
                    </div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 12px 0;">
                <div style="background: #F8FAFC; padding: 10px; border-radius: 6px; border: 1px solid #E2E8F0;">
                    <div style="font-size: 11px; color: #6B7C93; font-weight: 700;">OPERATIONAL STORES</div>
                    <div style="font-size: 18px; font-weight: 800; color: #172B4D; font-family: Outfit;">4 Stores</div>
                </div>
                <div style="background: #F8FAFC; padding: 10px; border-radius: 6px; border: 1px solid #E2E8F0;">
                    <div style="font-size: 11px; color: #6B7C93; font-weight: 700;">GROSS VOLUME</div>
                    <div style="font-size: 18px; font-weight: 800; color: #172B4D; font-family: Outfit;">₹112,842.45</div>
                </div>
                <div style="background: #F8FAFC; padding: 10px; border-radius: 6px; border: 1px solid #E2E8F0;">
                    <div style="font-size: 11px; color: #6B7C93; font-weight: 700;">RECONCILIATION</div>
                    <div style="font-size: 18px; font-weight: 800; color: #10B981; font-family: Outfit;">98.2%</div>
                </div>
            </div>
            <div style="font-size: 12px; color: #6B7C93;">
                <strong>Stores:</strong> Delhi NCR (`fk_delhi`), Mumbai West (`fk_mumbai`), Bangalore Central (`fk_bangalore`), Hyderabad Hub (`fk_hyderabad`)
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_m2:
        st.markdown("""
        <div class="admin-card">
            <div class="admin-card-header">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 32px; height: 32px; border-radius: 6px; background: #131921; display: flex; align-items: center; justify-content: center; font-size: 16px; color: #FF9900; font-family: Outfit; font-weight: 800;">a</div>
                    <div>
                        <h3 class="admin-card-title">Amazon Seller Services India Pvt Ltd</h3>
                        <span style="font-size: 11.5px; color: #6B7C93;">MID: MID-AZ-88310 | Status: <span class="admin-badge admin-badge-success">ACTIVE</span></span>
                    </div>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 12px 0;">
                <div style="background: #F8FAFC; padding: 10px; border-radius: 6px; border: 1px solid #E2E8F0;">
                    <div style="font-size: 11px; color: #6B7C93; font-weight: 700;">OPERATIONAL STORES</div>
                    <div style="font-size: 18px; font-weight: 800; color: #172B4D; font-family: Outfit;">6 Stores</div>
                </div>
                <div style="background: #F8FAFC; padding: 10px; border-radius: 6px; border: 1px solid #E2E8F0;">
                    <div style="font-size: 11px; color: #6B7C93; font-weight: 700;">GROSS VOLUME</div>
                    <div style="font-size: 18px; font-weight: 800; color: #172B4D; font-family: Outfit;">₹83,531.26</div>
                </div>
                <div style="background: #F8FAFC; padding: 10px; border-radius: 6px; border: 1px solid #E2E8F0;">
                    <div style="font-size: 11px; color: #6B7C93; font-weight: 700;">RECONCILIATION</div>
                    <div style="font-size: 18px; font-weight: 800; color: #10B981; font-family: Outfit;">97.1%</div>
                </div>
            </div>
            <div style="font-size: 12px; color: #6B7C93;">
                <strong>Stores:</strong> Mumbai South (`az_mumbai`), Delhi Central (`az_delhi`), Bangalore Hub (`az_bangalore`), Pune Metro (`az_pune`), Chennai (`az_chennai`), Kolkata (`az_kolkata`)
            </div>
        </div>
        """, unsafe_allow_html=True)

# ----------------------------------------------------
# ADMIN SUBPAGE: STORES REGISTRY
# ----------------------------------------------------
elif st.session_state.page == "admin_stores":
    st.markdown("<h2>⌂ Platform Multi-Tenant Stores Registry</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Manage and monitor active store locations and settlement configurations across tenants.</p>", unsafe_allow_html=True)
    
    stores_data = [
        {"Store ID": "fk_delhi", "Merchant": "Flipkart", "City": "Delhi NCR", "Settlement Delay": "T+2 Days", "Status": "OPERATIONAL", "Exceptions": 18},
        {"Store ID": "fk_mumbai", "Merchant": "Flipkart", "City": "Mumbai West", "Settlement Delay": "T+2 Days", "Status": "OPERATIONAL", "Exceptions": 3},
        {"Store ID": "fk_bangalore", "Merchant": "Flipkart", "City": "Bangalore Central", "Settlement Delay": "T+2 Days", "Status": "OPERATIONAL", "Exceptions": 1},
        {"Store ID": "fk_hyderabad", "Merchant": "Flipkart", "City": "Hyderabad Hub", "Settlement Delay": "T+2 Days", "Status": "OPERATIONAL", "Exceptions": 1},
        {"Store ID": "az_mumbai", "Merchant": "Amazon", "City": "Mumbai South", "Settlement Delay": "T+2 Days", "Status": "OPERATIONAL", "Exceptions": 8},
        {"Store ID": "az_delhi", "Merchant": "Amazon", "City": "Delhi Central", "Settlement Delay": "T+2 Days", "Status": "OPERATIONAL", "Exceptions": 4},
        {"Store ID": "az_bangalore", "Merchant": "Amazon", "City": "Bangalore Hub", "Settlement Delay": "T+2 Days", "Status": "OPERATIONAL", "Exceptions": 1},
        {"Store ID": "az_pune", "Merchant": "Amazon", "City": "Pune Metro", "Settlement Delay": "T+2 Days", "Status": "OPERATIONAL", "Exceptions": 1},
        {"Store ID": "az_chennai", "Merchant": "Amazon", "City": "Chennai", "Settlement Delay": "T+2 Days", "Status": "OPERATIONAL", "Exceptions": 1},
        {"Store ID": "az_kolkata", "Merchant": "Amazon", "City": "Kolkata", "Settlement Delay": "T+2 Days", "Status": "OPERATIONAL", "Exceptions": 0},
    ]
    st.dataframe(pd.DataFrame(stores_data), use_container_width=True, hide_index=True)

# ----------------------------------------------------
# ADMIN SUBPAGE: GLOBAL TRANSACTIONS EXPLORER
# ----------------------------------------------------
elif st.session_state.page == "admin_transactions":
    st.markdown("<h2>⇄ Global Transactions Explorer</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Platform-wide transactions ledger with color-coded mismatch classification (Red: Critical/Amount, Yellow: Fee/Tax, Orange: Status, Green: Auto-Resolved).</p>", unsafe_allow_html=True)
    
    # Interactive Filters
    fl_m, fl_stat, fl_type, fl_search = st.columns([1, 1.3, 1, 1.7])
    with fl_m:
        m_filter = st.selectbox("Merchant", ["All Merchants", "Flipkart", "Amazon"], key="adm_tx_m_filter")
    with fl_stat:
        status_filter = st.selectbox(
            "Mismatch Type & Status",
            [
                "All Transactions",
                "All Needs Review",
                "🔴 Critical (Amount / Bank Credit)",
                "🟡 Fee & Tax Mismatches",
                "🟠 Status Mismatches",
                "🟢 Auto-Resolved"
            ],
            key="adm_tx_stat_filter"
        )
    with fl_type:
        type_filter = st.selectbox("Type", ["All Types", "PAYMENT", "REFUND", "PAYOUT"], key="adm_tx_type_filter")
    with fl_search:
        search_query = st.text_input("Search ID", placeholder="Search pay_xxx or order_xxx...", key="adm_tx_search")
        
    display_df = df_tx.copy()
    
    if m_filter != "All Merchants":
        display_df = display_df[display_df['merchant_id'].str.lower() == m_filter.lower()]
        
    if status_filter == "🟢 Auto-Resolved":
        display_df = display_df[display_df['resolution_status'] == 'AUTO_RESOLVED']
    elif status_filter == "All Needs Review":
        display_df = display_df[display_df['resolution_status'] == 'NEEDS_REVIEW']
    elif status_filter == "🔴 Critical (Amount / Bank Credit)":
        display_df = display_df[
            (display_df['resolution_status'] == 'NEEDS_REVIEW') & 
            display_df['calculated_exceptions'].apply(lambda x: any(k in str(x).upper() for k in ['AMOUNT_MISMATCH', 'BANK_CREDIT_MISSING', 'MISSING_ORDER', 'NOT_FOUND', 'DISPUTE']))
        ]
    elif status_filter == "🟡 Fee & Tax Mismatches":
        display_df = display_df[
            (display_df['resolution_status'] == 'NEEDS_REVIEW') & 
            display_df['calculated_exceptions'].apply(lambda x: any(k in str(x).upper() for k in ['FEE_MISMATCH', 'TAX_MISMATCH', 'GST_MISMATCH', 'BANK_SETTLEMENT_MISMATCH']))
        ]
    elif status_filter == "🟠 Status Mismatches":
        display_df = display_df[
            (display_df['resolution_status'] == 'NEEDS_REVIEW') & 
            display_df['calculated_exceptions'].apply(lambda x: any(k in str(x).upper() for k in ['STATUS_MISMATCH', 'SETTLED_AMOUNT_MISMATCH']))
        ]
        
    if type_filter != "All Types":
        display_df = display_df[display_df['type'] == type_filter]
        
    if search_query.strip():
        q = search_query.strip().lower()
        display_df = display_df[
            display_df['transaction_id'].str.lower().str.contains(q) |
            display_df['order_id'].str.lower().str.contains(q)
        ]
        
    # Mismatch counts metric cards
    col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
    with col_c1:
        st.markdown(clean_html(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px 12px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #6B7C93;">SHOWING</div>
            <div style="font-size: 16px; font-weight: 800; color: #172B4D;">{len(display_df)}</div>
        </div>
        """), unsafe_allow_html=True)
    with col_c2:
        crit_c = len(display_df[(display_df['resolution_status'] == 'NEEDS_REVIEW') & display_df['calculated_exceptions'].apply(lambda x: any(k in str(x).upper() for k in ['AMOUNT', 'CREDIT', 'ORDER', 'NOT_FOUND']))])
        st.markdown(clean_html(f"""
        <div style="background: #FFF5F5; border: 1px solid #FED7D7; border-radius: 6px; padding: 8px 12px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #EF4444;">🔴 CRITICAL MISMATCH</div>
            <div style="font-size: 16px; font-weight: 800; color: #EF4444;">{crit_c}</div>
        </div>
        """), unsafe_allow_html=True)
    with col_c3:
        fee_c = len(display_df[(display_df['resolution_status'] == 'NEEDS_REVIEW') & display_df['calculated_exceptions'].apply(lambda x: any(k in str(x).upper() for k in ['FEE', 'TAX', 'GST', 'SETTLEMENT']))])
        st.markdown(clean_html(f"""
        <div style="background: #FEFCE8; border: 1px solid #FEF08A; border-radius: 6px; padding: 8px 12px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #D97706;">🟡 FEE/TAX MISMATCH</div>
            <div style="font-size: 16px; font-weight: 800; color: #D97706;">{fee_c}</div>
        </div>
        """), unsafe_allow_html=True)
    with col_c4:
        stat_c = len(display_df[(display_df['resolution_status'] == 'NEEDS_REVIEW') & display_df['calculated_exceptions'].apply(lambda x: any(k in str(x).upper() for k in ['STATUS']))])
        st.markdown(clean_html(f"""
        <div style="background: #FFF7ED; border: 1px solid #FFEDD5; border-radius: 6px; padding: 8px 12px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #EA580C;">🟠 STATUS MISMATCH</div>
            <div style="font-size: 16px; font-weight: 800; color: #EA580C;">{stat_c}</div>
        </div>
        """), unsafe_allow_html=True)
    with col_c5:
        auto_c = len(display_df[display_df['resolution_status'] == 'AUTO_RESOLVED'])
        st.markdown(clean_html(f"""
        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 8px 12px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #10B981;">🟢 AUTO RESOLVED</div>
            <div style="font-size: 16px; font-weight: 800; color: #10B981;">{auto_c}</div>
        </div>
        """), unsafe_allow_html=True)
        
    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
    
    # Custom HTML Table
    html_rows = ""
    for idx, row in display_df.iterrows():
        tx_id = row['transaction_id']
        ord_id = row['order_id'] or '—'
        m_id = str(row['merchant_id']).upper()
        s_id = str(row['store_id']).split('_')[-1].upper()
        amt = f"₹{row['amount_inr']:,.2f}"
        fee = f"₹{row['fee_inr']:,.2f}"
        tax = f"₹{row['tax_inr']:,.2f}"
        net = f"₹{row['settled_amount_inr']:,.2f}"
        
        status_badge = get_mismatch_badge_html(row['calculated_exceptions'], row['resolution_status'])
        exc_pills = get_exception_pills_html(row['calculated_exceptions'])
        
        html_rows += f"""<tr>
<td><code>{tx_id}</code></td>
<td><code>{ord_id}</code></td>
<td><span style="font-weight: 600; color: #172B4D;">{m_id}</span> <span style="font-size: 10px; color: #6B7C93;">({s_id})</span></td>
<td><strong>{row['type']}</strong></td>
<td><strong style="color: #172B4D;">{amt}</strong></td>
<td style="color: #6B7C93;">{fee}</td>
<td style="color: #6B7C93;">{tax}</td>
<td style="font-weight: 600; color: #172B4D;">{net}</td>
<td>{status_badge}</td>
<td>{exc_pills}</td>
</tr>"""
        
    if not html_rows:
        html_rows = "<tr><td colspan='10' style='text-align: center; color: #6B7C93; padding: 20px;'>No transactions found matching the selected filters.</td></tr>"
        
    st.markdown(clean_html(f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; overflow-x: auto; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
        <table class="admin-table" style="width: 100%; border-collapse: collapse; font-size: 11px;">
            <thead>
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Transaction ID</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Order ID</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Merchant / Store</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Type</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Gross Amount</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Fee</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Tax</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Settled Net</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Resolution Status</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Calculated Exceptions</th>
                </tr>
            </thead>
            <tbody>
                {html_rows}
            </tbody>
        </table>
    </div>
    """), unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    st.download_button(
        "📥 Export Filtered Ledger (CSV)",
        data=display_df.to_csv(index=False),
        file_name="global_transactions_ledger.csv",
        mime="text/csv"
    )

# ----------------------------------------------------
# ADMIN SUBPAGE: RECONCILIATION COMMAND CENTER
# ----------------------------------------------------
elif st.session_state.page == "admin_reconciliation":
    st.markdown("<h2>⇄ Platform 3-Way Reconciliation Ledger</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Global matching engine status across Razorpay Gateway, OMS Orders, and Bank Settlement Feeds with colored mismatch resolution badges.</p>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Payments", f"{len(df_tx):,}")
    with c2:
        st.metric("Auto Resolved", f"{metrics.get('auto_resolved_count', 84):,}")
    with c3:
        st.metric("Review Required", f"{metrics.get('needs_review_count', 38):,}")
    with c4:
        st.metric("Auto Match Accuracy", f"{metrics.get('auto_match_accuracy_pct', 68.9)}%")
        
    html_rec_rows = ""
    for idx, row in df_tx.iterrows():
        tx_id = row['transaction_id']
        m_id = str(row['merchant_id']).upper()
        s_id = str(row['store_id']).split('_')[-1].upper()
        amt = f"₹{row['amount_inr']:,.2f}"
        status_badge = get_mismatch_badge_html(row['calculated_exceptions'], row['resolution_status'])
        exc_pills = get_exception_pills_html(row['calculated_exceptions'])
        
        html_rec_rows += f"""<tr>
<td><code>{tx_id}</code></td>
<td><strong>{m_id}</strong> <span style="font-size: 10px; color: #6B7C93;">({s_id})</span></td>
<td><strong style="color: #172B4D;">{amt}</strong></td>
<td>{status_badge}</td>
<td>{exc_pills}</td>
</tr>"""
        
    st.markdown(clean_html(f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; overflow-x: auto; margin-top: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
        <table class="admin-table" style="width: 100%; border-collapse: collapse; font-size: 11px;">
            <thead>
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Transaction ID</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Merchant / Store</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Amount</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Resolution Status</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Calculated Exceptions</th>
                </tr>
            </thead>
            <tbody>
                {html_rec_rows}
            </tbody>
        </table>
    </div>
    """), unsafe_allow_html=True)

# ----------------------------------------------------
# ADMIN SUBPAGE: SETTLEMENTS & CLEARING
# ----------------------------------------------------
elif st.session_state.page == "admin_settlements":
    st.markdown("<h2>▣ Platform Settlements & Clearing Batches</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Nodal clearing ledger, expected vs actual bank settlement transfers, and UTR reference mappings.</p>", unsafe_allow_html=True)
    
    # Filters
    fl_m, fl_stat, fl_search = st.columns([1, 1.2, 1.8])
    with fl_m:
        m_filter = st.selectbox("Merchant", ["All Merchants", "Flipkart", "Amazon"], key="adm_settle_m_filter")
    with fl_stat:
        status_filter = st.selectbox("Batch Status", ["All Batches", "Matched Deposits", "Variances / Mismatches"], key="adm_settle_stat_filter")
    with fl_search:
        search_query = st.text_input("Search Reference", placeholder="Search UTR / Bank Reference or Date...", key="adm_settle_search")
        
    display_bank = df_bank.copy()
    if m_filter != "All Merchants" and 'merchant_id' in display_bank.columns:
        display_bank = display_bank[display_bank['merchant_id'].str.lower() == m_filter.lower()]
        
    if status_filter == "Matched Deposits":
        if 'difference' in display_bank.columns:
            display_bank = display_bank[display_bank['difference'].abs() < 0.01]
        elif 'expected_amount_inr' in display_bank.columns:
            display_bank = display_bank[(display_bank['expected_amount_inr'] - display_bank['amount_inr']).abs() < 0.01]
    elif status_filter == "Variances / Mismatches":
        if 'difference' in display_bank.columns:
            display_bank = display_bank[display_bank['difference'].abs() >= 0.01]
        elif 'expected_amount_inr' in display_bank.columns:
            display_bank = display_bank[(display_bank['expected_amount_inr'] - display_bank['amount_inr']).abs() >= 0.01]
            
    if search_query.strip():
        q = search_query.strip().lower()
        display_bank = display_bank[
            display_bank['bank_reference'].astype(str).str.lower().str.contains(q) |
            display_bank['date'].astype(str).str.lower().str.contains(q)
        ]
        
    # Stats Cards Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(clean_html(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #6B7C93;">TOTAL CLEARING BATCHES</div>
            <div style="font-size: 17px; font-weight: 800; color: #172B4D;">{len(display_bank)}</div>
        </div>
        """), unsafe_allow_html=True)
    with c2:
        exp_sum = display_bank['expected_amount_inr'].sum() if 'expected_amount_inr' in display_bank.columns else 0
        st.markdown(clean_html(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #6B7C93;">EXPECTED NET TRANSFER</div>
            <div style="font-size: 17px; font-weight: 800; color: #2563EB;">₹{exp_sum:,.2f}</div>
        </div>
        """), unsafe_allow_html=True)
    with c3:
        act_sum = display_bank['amount_inr'].sum() if 'amount_inr' in display_bank.columns else 0
        st.markdown(clean_html(f"""
        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 10px 14px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #10B981;">CONFIRMED CLEARED</div>
            <div style="font-size: 17px; font-weight: 800; color: #10B981;">₹{act_sum:,.2f}</div>
        </div>
        """), unsafe_allow_html=True)
    with c4:
        diff_total = (display_bank['expected_amount_inr'] - display_bank['amount_inr']).sum() if 'expected_amount_inr' in display_bank.columns else 0
        diff_color = "#EF4444" if abs(diff_total) > 0.01 else "#10B981"
        diff_bg = "#FFF5F5" if abs(diff_total) > 0.01 else "#F0FDF4"
        diff_border = "#FED7D7" if abs(diff_total) > 0.01 else "#BBF7D0"
        st.markdown(clean_html(f"""
        <div style="background: {diff_bg}; border: 1px solid {diff_border}; border-radius: 6px; padding: 10px 14px;">
            <div style="font-size: 9.5px; font-weight: 700; color: {diff_color};">TOTAL VARIANCE / DELTA</div>
            <div style="font-size: 17px; font-weight: 800; color: {diff_color};">₹{diff_total:,.2f}</div>
        </div>
        """), unsafe_allow_html=True)
        
    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
    
    # Custom HTML Table
    html_settle_rows = ""
    for idx, row in display_bank.iterrows():
        dt = row.get('date', '—')
        m_id = str(row.get('merchant_id', 'flipkart')).upper()
        s_id = str(row.get('store_id', 'main')).split('_')[-1].upper()
        exp_amt = row.get('expected_amount_inr', row.get('amount_inr', 0.0))
        act_amt = row.get('amount_inr', 0.0)
        diff = exp_amt - act_amt
        
        bank_ref = str(row.get('bank_reference', '—'))
        if ";" in bank_ref:
            refs = [r.strip() for r in bank_ref.split(";") if r.strip()]
            ref_display = f"<code>{refs[0]}</code> + {len(refs)-1} more"
        else:
            ref_display = f"<code>{bank_ref}</code>"
            
        if abs(diff) < 0.01:
            status_pill = '<span style="background-color: #ECFDF5; color: #10B981; border: 1px solid #A7F3D0; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 700;">✓ CLEARED</span>'
            diff_pill = '<span style="color: #10B981; font-weight: 600;">₹0.00</span>'
        else:
            status_pill = '<span style="background-color: #FEE2E2; color: #EF4444; border: 1px solid #FECACA; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 700;">⚠️ MISMATCH</span>'
            diff_pill = f'<span style="color: #EF4444; font-weight: 700;">₹{diff:,.2f}</span>'
            
        amt_color = "#172B4D" if act_amt >= 0 else "#EF4444"
        
        html_settle_rows += f"""<tr>
<td><strong>{dt}</strong></td>
<td><span style="font-weight: 600; color: #172B4D;">{m_id}</span> <span style="font-size: 10px; color: #6B7C93;">({s_id})</span></td>
<td style="color: #6B7C93; font-weight: 600;">₹{exp_amt:,.2f}</td>
<td style="color: {amt_color}; font-weight: 700;">₹{act_amt:,.2f}</td>
<td>{diff_pill}</td>
<td>{status_pill}</td>
<td style="color: #475569; font-size: 10.5px;">{ref_display}</td>
</tr>"""
        
    if not html_settle_rows:
        html_settle_rows = "<tr><td colspan='7' style='text-align: center; color: #6B7C93; padding: 20px;'>No settlement records found matching filters.</td></tr>"
        
    st.markdown(clean_html(f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; overflow-x: auto; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
        <table class="admin-table" style="width: 100%; border-collapse: collapse; font-size: 11px;">
            <thead>
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Clearing Date</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Merchant / Store</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Expected Transfer</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Actual Cleared Amount</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Variance / Delta</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Batch Status</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Bank Reference / UTR</th>
                </tr>
            </thead>
            <tbody>
                {html_settle_rows}
            </tbody>
        </table>
    </div>
    """), unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    st.download_button(
        "📥 Export Settlements Ledger (CSV)",
        data=display_bank.to_csv(index=False),
        file_name="platform_settlements_ledger.csv",
        mime="text/csv"
    )

# ----------------------------------------------------
# ADMIN SUBPAGE: PAYOUTS & BALANCES
# ----------------------------------------------------
elif st.session_state.page == "admin_payouts":
    st.markdown("<h2>⇄ Platform Merchant Payouts & Net Balances</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Withholding TDS calculations, merchant disbursement queues, and platform net settlement transfers.</p>", unsafe_allow_html=True)
    
    payout_df = df_tx[df_tx['type'] == 'PAYMENT'].copy()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(clean_html(f"""
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px 14px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #6B7C93;">TOTAL PAYOUT VOLUME</div>
            <div style="font-size: 17px; font-weight: 800; color: #172B4D;">₹{payout_df['amount_inr'].sum():,.2f}</div>
        </div>
        """), unsafe_allow_html=True)
    with c2:
        fee_sum = payout_df['fee_inr'].sum() + payout_df['tax_inr'].sum()
        st.markdown(clean_html(f"""
        <div style="background: #FEFCE8; border: 1px solid #FEF08A; border-radius: 6px; padding: 10px 14px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #D97706;">WITHHELD FEES & GST</div>
            <div style="font-size: 17px; font-weight: 800; color: #D97706;">₹{fee_sum:,.2f}</div>
        </div>
        """), unsafe_allow_html=True)
    with c3:
        net_sum = payout_df['settled_amount_inr'].sum()
        st.markdown(clean_html(f"""
        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 6px; padding: 10px 14px;">
            <div style="font-size: 9.5px; font-weight: 700; color: #10B981;">NET MERCHANT DISBURSEMENT</div>
            <div style="font-size: 17px; font-weight: 800; color: #10B981;">₹{net_sum:,.2f}</div>
        </div>
        """), unsafe_allow_html=True)
        
    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
    
    html_payout_rows = ""
    for idx, row in payout_df.iterrows():
        tx_id = row['transaction_id']
        m_id = str(row['merchant_id']).upper()
        s_id = str(row['store_id']).split('_')[-1].upper()
        gross = f"₹{row['amount_inr']:,.2f}"
        fee = f"₹{row['fee_inr']:,.2f}"
        tax = f"₹{row['tax_inr']:,.2f}"
        net = f"₹{row['settled_amount_inr']:,.2f}"
        date_exp = row.get('expected_settlement_date', 'T+2 Days')
        
        html_payout_rows += f"""<tr>
<td><code>{tx_id}</code></td>
<td><strong>{m_id}</strong> <span style="font-size: 10px; color: #6B7C93;">({s_id})</span></td>
<td style="font-weight: 700; color: #172B4D;">{gross}</td>
<td style="color: #6B7C93;">{fee}</td>
<td style="color: #6B7C93;">{tax}</td>
<td style="font-weight: 700; color: #10B981;">{net}</td>
<td><span style="background-color: #EFF6FF; color: #3B82F6; border: 1px solid #BFDBFE; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; font-weight: 600;">{date_exp}</span></td>
</tr>"""
        
    st.markdown(clean_html(f"""
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px; overflow-x: auto; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
        <table class="admin-table" style="width: 100%; border-collapse: collapse; font-size: 11px;">
            <thead>
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Transaction ID</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Merchant / Store</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Gross Collected</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Fee (2%)</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">GST (18%)</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Net Payable</th>
                    <th style="padding: 8px 6px; color: #6B7C93; font-weight: 700; font-size: 9.5px; text-transform: uppercase;">Disbursement Target</th>
                </tr>
            </thead>
            <tbody>
                {html_payout_rows}
            </tbody>
        </table>
    </div>
    """), unsafe_allow_html=True)

# ----------------------------------------------------
# ADMIN SUBPAGE: NOTIFICATIONS HUB
# ----------------------------------------------------
elif st.session_state.page == "admin_notifications":
    st.markdown("<h2>♧ Platform Security & Compliance Notifications</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Active platform alerts, webhook triggers, and compliance reminders.</p>", unsafe_allow_html=True)
    
    from src.database import get_notifications
    notifs = get_notifications(role='ADMIN')
    if notifs:
        for n in notifs:
            st.markdown(f"""
            <div class="admin-card" style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>{n.get('title', 'System Notification')}</strong>
                    <span style="font-size: 11.5px; color: #6B7C93;">{n.get('created_at', '')}</span>
                </div>
                <p style="margin: 6px 0 0 0; font-size: 13px; color: #172B4D;">{n.get('message', '')}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No unread admin security alerts.")

# ----------------------------------------------------
# ADMIN SUBPAGE: KNOWLEDGE BASE & VECTOR REPOSITORY
# ----------------------------------------------------
elif st.session_state.page == "admin_kb":
    st.markdown("<h2>▤ RAG Knowledge Base Document Repository</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-sec); font-size: 14px;'>Indexed fintech documents, Section 194-O guidelines, and vector chunks.</p>", unsafe_allow_html=True)
    
    from src.database import get_indexed_documents
    docs = get_indexed_documents()
    if docs:
        st.dataframe(pd.DataFrame(docs), use_container_width=True, hide_index=True)
    else:
        st.info("No documents indexed yet in vector database.")

# ----------------------------------------------------
# FLOATING AI ASSISTANT SPARKS OVERLAY (META AI STYLE)
# ----------------------------------------------------
st.markdown('<div class="floating-popover-container">', unsafe_allow_html=True)
with st.popover("💬 Ask AI Assistant", use_container_width=False):
    st.markdown('<div class="chat-header-spark"><h3>🤖 AI Finance Assistant</h3><p>Reconciliation Auditor (Gemini 3.5 Flash)</p></div>', unsafe_allow_html=True)
    
    chat_popup_cont = st.container()
    with chat_popup_cont:
        if len(st.session_state.messages) == 0:
            st.write("Hello! I am your AI Finance Assistant. Ask me anything about the Daily Close metrics, tax compliance rules, or upload policies.")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
    with st.form(key="popover_floating_chat_form", clear_on_submit=True):
        col_pop_inp, col_pop_btn = st.columns([4, 1.2])
        with col_pop_inp:
            popup_chat_input = st.text_input(
                "Ask a question:", 
                value=st.session_state.prompt_default,
                placeholder="Ask about settlement policies, taxes, or database status...", 
                label_visibility="collapsed"
            )
        with col_pop_btn:
            popup_submit_chat = st.form_submit_button("Send")
            
    if st.session_state.chat_query:
        popup_chat_input = st.session_state.chat_query
        popup_submit_chat = True
        st.session_state.chat_query = None
 
    if popup_submit_chat and popup_chat_input.strip():
        st.session_state.prompt_default = ""
        st.session_state.messages.append({"role": "user", "content": popup_chat_input})
        save_chat_message(st.session_state.session_id, "user", popup_chat_input)
        
        with chat_popup_cont:
            with st.chat_message("user"):
                st.markdown(popup_chat_input)
                
        with chat_popup_cont:
            with st.chat_message("assistant"):
                with st.spinner("Generating..."):
                    u_merchant_id = st.session_state.user['merchant_id'] if st.session_state.user['role'] == 'MERCHANT' else None
                    generate_ai_response(popup_chat_input, merchant_id=u_merchant_id)
                    st.markdown(st.session_state.messages[-1]["content"])
                    
        st.rerun()
 
    if st.button("🗑️ Restart Chat Session", key="restart_chat_popover_btn", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = f"session_{int(datetime.now().timestamp())}"
        st.rerun()


st.markdown('</div>', unsafe_allow_html=True)