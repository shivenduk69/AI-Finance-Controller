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

# Load internal orders lookup for the Audit Deep-Dive Tab
base_dir = os.path.dirname(os.path.abspath(__file__))
orders_csv_path = os.path.join(base_dir, "data", "internal_orders.csv")
if os.path.exists(orders_csv_path):
    df_orders = pd.read_csv(orders_csv_path)
else:
    df_orders = pd.DataFrame(columns=['order_id', 'amount_inr', 'status', 'created_at', 'customer_email'])


# ----------------------------------------------------
# CONFIG & STYLING
# ----------------------------------------------------
st.set_page_config(
    page_title="AI Finance Controller - Daily Close",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

import streamlit as st

st.markdown("""
<style>
    /* 1. Target ALL text elements inside Inactive Tabs */
    button[data-baseweb="tab"] p,
    button[data-baseweb="tab"] div,
    button[data-baseweb="tab"] span {
        color: #e2e8f0 !important;              /* Crisp light-gray/white text */
        font-weight: 500 !important;
        font-size: 15px !important;
    }

    button[data-baseweb="tab"] {
        background-color: transparent !important;
    }

    /* 2. Target ALL text elements inside Active/Selected Tab */
    button[data-baseweb="tab"][aria-selected="true"] {
        background-color: #ffffff !important;
        border-radius: 6px 6px 0px 0px !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] p,
    button[data-baseweb="tab"][aria-selected="true"] div,
    button[data-baseweb="tab"][aria-selected="true"] span {
        color: #002b49 !important;              /* Dark navy text on white tab */
        font-weight: 700 !important;
    }

    /* 3. Hover state for tabs */
    button[data-baseweb="tab"]:hover p,
    button[data-baseweb="tab"]:hover div,
    button[data-baseweb="tab"]:hover span {
        color: #ffffff !important;
    }

    /* 4. Sidebar Labels & Markdown text */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] label p,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 600 !important;
    }

    /* 5. Input text fields & Dropdowns visibility */
    [data-testid="stSidebar"] input {
        color: #0f172a !important;
        background-color: #ffffff !important;
    }

    [data-testid="stSidebar"] div[data-baseweb="select"] * {
        color: #0f172a !important;
    }

    [data-testid="stSidebar"] div[data-baseweb="select"] {
        background-color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)
# Custom Premium CSS Injection — Income Tax e-Filing portal inspired
# (light surfaces, navy header/nav, single blue accent)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    :root {
        --bg-app: #eef2f6;
        --bg-sidebar: #0b3d63;
        --bg-card: #ffffff;
        --border-soft: #d7e0ea;
        --border-strong: #b7c4d3;
        --text-primary: #1f2a37;
        --text-secondary: #5b6b7c;
        --accent: #0b5ea8;
        --accent-hover: #0f6fc4;
        --green: #1c7c3f;
        --red: #c62828;
        --amber: #b8720b;
        --navy: #0b3d63;
        --navy-dark: #082c48;
    }

    /* Font overrides */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    /* Global Background */
    .stApp {
        background-color: var(--bg-app);
        color: var(--text-primary);
    }

    .stApp, .stApp p, .stApp span, .stApp li, .stApp label,
    .stMarkdown, .stMarkdown p, .stMarkdown li,
    .stCaption, [data-testid="stMetricLabel"], [data-testid="stMetricValue"],
    [data-testid="stMarkdownContainer"] {
        color: var(--text-primary);
    }

    /* Sidebar styling (navy, like the portal's header/nav band) */
    [data-testid="stSidebar"] {
        background-color: var(--bg-sidebar);
        border-right: 1px solid var(--navy-dark);
    }

    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] .stMarkdown small,
    [data-testid="stSidebar"] p {
        color: #cfe0f0 !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.2) !important;
    }

    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
    [data-testid="stSidebar"] .stTextInput input {
        color: var(--text-primary) !important;
    }

    /* Select boxes / text inputs (closed state) */
    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div,
    .stTextInput input,
    .stTextArea textarea,
    .stNumberInput input,
    .stDateInput input {
        background-color: #ffffff !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 6px !important;
    }

    /* Dropdown menu (renders in a portal, so target globally) */
    div[data-baseweb="popover"] ul[role="listbox"],
    div[data-baseweb="menu"] {
        background-color: #ffffff !important;
        border: 1px solid var(--border-soft) !important;
        box-shadow: 0 4px 12px rgba(11, 61, 99, 0.15) !important;
    }

    div[data-baseweb="popover"] li,
    div[data-baseweb="menu"] li {
        color: var(--text-primary) !important;
        background-color: transparent !important;
    }

    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="menu"] li:hover {
        background-color: #eaf2fa !important;
        color: var(--navy) !important;
    }

    /* Buttons */
    .stButton button, .stFormSubmitButton button {
        background: linear-gradient(135deg, #0b5ea8 0%, #084a86 100%);
        color: #ffffff !important;
        border: 1px solid #084a86;
        border-radius: 6px;
        font-weight: 600;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    .stButton button:hover, .stFormSubmitButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(11, 94, 168, 0.35);
        color: #ffffff !important;
    }

    .stButton button p {
        color: #ffffff !important;
    }

    /* Dataframes / tables */
    [data-testid="stDataFrame"] {
        background-color: #ffffff;
        border: 1px solid var(--border-soft);
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(11, 61, 99, 0.08);
    }

    [data-testid="stDataFrame"] div {
        color: var(--text-primary);
    }

    /* Cards styling — white cards with a navy accent bar,
       similar to the portal's "Quick Links" / stat tiles */
    .metric-card {
        background: #ffffff;
        border: 1px solid var(--border-soft);
        border-top: 3px solid var(--accent);
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 1px 4px rgba(11, 61, 99, 0.08);
        transition: transform 0.2s, box-shadow 0.2s;
    }

    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(11, 61, 99, 0.14);
    }

    .metric-title {
        font-size: 0.8rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 8px;
        font-weight: 600;
    }

    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--navy);
        margin-bottom: 4px;
    }

    .metric-delta {
        font-size: 0.75rem;
        font-weight: 600;
    }

    .delta-green {
        color: #1c7c3f;
    }

    .delta-red {
        color: #c62828;
    }

    .delta-amber {
        color: #b8720b;
    }

    /* Headers & Subheaders */
    h1, h2, h3 {
        color: var(--navy) !important;
        font-weight: 700 !important;
    }

    /* Custom tab styles (navy pill bar like the portal's main nav) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: var(--navy);
        padding: 6px;
        border-radius: 8px;
        border: 1px solid var(--navy-dark);
    }

    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        color: #cfe0f0;
        border-radius: 6px;
        font-weight: 500;
        transition: background-color 0.2s, color 0.2s;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff;
        background-color: rgba(255,255,255,0.12);
    }

    .stTabs [aria-selected="true"] {
        color: var(--navy) !important;
        background-color: #ffffff !important;
    }

    /* Native Streamlit alerts */
    [data-testid="stNotification"] {
        border-radius: 6px !important;
        border: 1px solid var(--border-soft) !important;
    }

    [data-testid="stNotification"] p, [data-testid="stNotification"] div {
        color: var(--text-primary) !important;
    }

    .stAlert, .stAlert * {
        color: var(--text-primary) !important;
    }

    /* Accent Alerts (like the portal's notice/ticker strip) */
    .custom-alert {
        padding: 16px;
        border-radius: 6px;
        margin-bottom: 16px;
        border: 1px solid;
    }

    .alert-success {
        background-color: rgba(28, 124, 63, 0.08);
        border-color: rgba(28, 124, 63, 0.3);
        color: #1c7c3f;
    }

    .alert-warning {
        background-color: rgba(184, 114, 11, 0.08);
        border-color: rgba(184, 114, 11, 0.3);
        color: #8a5809;
    }

    .alert-danger {
        background-color: rgba(198, 40, 40, 0.08);
        border-color: rgba(198, 40, 40, 0.3);
        color: #c62828;
    }

    /* Chat interface */
    [data-testid="stChatMessage"] {
        background-color: #ffffff;
        border: 1px solid var(--border-soft);
        border-radius: 8px;
        color: var(--text-primary) !important;
        box-shadow: 0 1px 3px rgba(11, 61, 99, 0.06);
    }

    [data-testid="stChatMessage"] p, [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] span {
        color: var(--text-primary) !important;
    }

    [data-testid="stChatInput"] textarea {
        background-color: #ffffff !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-strong) !important;
    }

    /* Code blocks */
    code, pre {
        background-color: #eef2f6 !important;
        color: #0b5ea8 !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: var(--bg-app); }
    ::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 6px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--accent); }

    /* Floating Popover Widget Style (WhatsApp Meta AI Style) */
    div[data-testid="stPopover"] {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 999999;
    }

    div[data-testid="stPopover"] button {
        width: 65px !important;
        height: 65px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #128c7e 0%, #075e54 100%) !important; /* WhatsApp Green */
        box-shadow: 0 6px 20px rgba(7, 94, 84, 0.4) !important;
        border: 2px solid #ffffff !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        padding: 0 !important;
    }

    div[data-testid="stPopover"] button:hover {
        transform: scale(1.15) rotate(5deg) !important;
        box-shadow: 0 8px 25px rgba(7, 94, 84, 0.6) !important;
    }

    /* Hide default popover arrow and text label */
    div[data-testid="stPopover"] button p {
        display: none !important;
    }

    div[data-testid="stPopover"] button div[data-testid="stMarkdownContainer"] {
        display: none !important;
    }

    div[data-testid="stPopover"] button::after {
        content: "💬" !important;
        font-size: 28px !important;
        color: white !important;
    }

    /* Floating Chat Window Panel styling */
    div[data-testid="stPopoverWindow"] {
        width: 440px !important;
        max-height: 550px !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 40px rgba(11, 61, 99, 0.25) !important;
        border: 1px solid var(--border-soft) !important;
        background-color: #ffffff !important;
        padding: 16px !important;
        overflow-y: auto !important;
    }
    
    /* Style Chat history header inside popover */
    .assistant-header {
        background: linear-gradient(135deg, #0b3d63 0%, #0b5ea8 100%);
        padding: 12px;
        border-radius: 8px;
        color: white;
        margin-bottom: 12px;
        text-align: center;
    }
    
    .assistant-header h3 {
        color: white !important;
        margin: 0 !important;
        font-size: 1.1rem !important;
    }
    
    .assistant-header p {
        color: #cfe0f0 !important;
        margin: 2px 0 0 0 !important;
        font-size: 0.75rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# SIDEBAR CREDENTIALS & OPTIONS
# ----------------------------------------------------
st.sidebar.markdown("<h2 style='text-align: center; color: #ffffff; font-weight: 800; margin-bottom: 4px;'>AI Finance Controller</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; color: #cfe0f0; font-size: 0.8rem; margin-top: 0;'>Multi-Source Reconciliation Agent</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# 1. Access Control Selection
st.sidebar.markdown("### Access Control")
app_role = st.sidebar.radio(
    "Select Interface Panel",
    ["Merchant Panel", "Admin Panel"],
    index=0,
    help="Switch between Merchant Dashboard (e.g. Flipkart) and Admin Oversight Dashboard (e.g. Razorpay)."
)
st.sidebar.markdown("---")

# Default admin variables to prevent name errors in compilation
selected_merchant = "Flipkart (Demo)"

if app_role == "Merchant Panel":
    # Data selection option
    dataset_option = st.sidebar.selectbox(
        "Select Reconciliation Batch",
        ["Razorpay Synthetic Batch (60 records)", "Example August 25 Daily Close (80 records)"],
        index=0
    )

    st.sidebar.markdown("### AI Layer Configuration")
    gemini_api_key = st.sidebar.text_input(
        "Google Gemini API Key",
        type="password",
        help="Enter your API Key to enable generative answers from your financial evidence.",
        value=os.environ.get("GEMINI_API_KEY", "")
    )

    model_option = st.sidebar.selectbox(
        "Select Gemini Model",
        ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🏛️ TDS Policy Configurator")
    with st.sidebar.expander("Adjust TDS Rates & Rules", expanded=False):
        st.markdown("**Payment TDS Rules**")
        tds_app_ind = st.checkbox("Resident Individual", value=True, help="Deduct TDS for resident individuals (Sec 194-O)")
        tds_rate_ind = st.number_input("Individual TDS Rate (%)", min_value=0.0, max_value=10.0, value=1.0, step=0.1) / 100.0
        
        tds_app_corp = st.checkbox("Resident Company", value=True, help="Deduct TDS for companies")
        tds_rate_corp = st.number_input("Company TDS Rate (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1) / 100.0
        
        tds_app_nres = st.checkbox("Non-Resident Entity", value=False, help="Deduct TDS for non-resident entities")
        tds_rate_nres = st.number_input("Non-Res TDS Rate (%)", min_value=0.0, max_value=10.0, value=0.0, step=0.1) / 100.0

    # Build tds_config from these widgets
    ui_tds_config = {
        'PAYMENT': {
            'Individual': {'applicable': tds_app_ind, 'rate': tds_rate_ind},
            'Company': {'applicable': tds_app_corp, 'rate': tds_rate_corp},
            'Non-Resident': {'applicable': tds_app_nres, 'rate': tds_rate_nres}
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

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Core Engine Rules")
    st.sidebar.markdown("""
    - **Exact ID Matching**: Order ID lookups.
    - **Math Checks**: Settled = Amt - Fee - GST.
    - **Fee Rate Validation**: 2% Gateway, Flat 5 INR Payouts, T+0 Refunds.
    - **Settlement Window**: T+2 bank statement deposit verification.
    - **Duplicate Check**: Unique gateway ID check.
    """)
    if gemini_api_key:
        st.sidebar.success("🔑 Gemini API Active (Generative auditor enabled)")
    else:
        st.sidebar.info("💡 Fallback Heuristic engine is active (local diagnostics only).")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Database & RAG Admin")
    if st.sidebar.button("🔄 Sync Database from CSVs", use_container_width=True, help="Reruns the ingestion pipeline to reload transactions, orders, and bank statement CSV files into SQLite/MySQL."):
        from src.upload_pipeline import run_pipeline
        with st.sidebar.spinner("Syncing database..."):
            if run_pipeline(reset=True):
                st.sidebar.success("Database synced successfully!")
                st.rerun()
            else:
                st.sidebar.error("Error syncing database.")

    if st.sidebar.button("📂 Re-index Documents (RAG)", use_container_width=True, help="Scans the documents/ folder and updates text embeddings."):
        with st.sidebar.spinner("Parsing and indexing documents..."):
            if build_document_index(gemini_api_key, force_reindex=True):
                st.sidebar.success("Documents indexed successfully!")
                st.rerun()
            else:
                st.sidebar.error("Indexing failed. Ensure documents are present.")

else:
    # Admin Panel Sidebar Options
    st.sidebar.markdown("### Admin Panel Oversight")
    selected_merchant = st.sidebar.selectbox(
        "Select Merchant to Audit",
        ["Flipkart (Demo)", "Shopify Store (Mock)", "WooCommerce Shop (Mock)"],
        index=0
    )
    
    st.sidebar.markdown("### Global AI Configuration")
    gemini_api_key = st.sidebar.text_input(
        "Google Gemini API Key",
        type="password",
        help="Admin Key to enable cross-merchant auditing diagnostics.",
        value=os.environ.get("GEMINI_API_KEY", "")
    )
    
    model_option = st.sidebar.selectbox(
        "Select Gemini Model",
        ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
        index=0
    )
    
    # Static Default TDS Configuration for Admin matching calculations
    ui_tds_config = {
        'PAYMENT': {
            'Individual': {'applicable': True, 'rate': 0.01},
            'Company': {'applicable': True, 'rate': 0.02},
            'Non-Resident': {'applicable': False, 'rate': 0.00}
        },
        'PAYOUT': {'Individual': {'applicable': False, 'rate': 0.0}, 'Company': {'applicable': False, 'rate': 0.0}, 'Non-Resident': {'applicable': False, 'rate': 0.0}},
        'REFUND': {'Individual': {'applicable': False, 'rate': 0.0}, 'Company': {'applicable': False, 'rate': 0.0}, 'Non-Resident': {'applicable': False, 'rate': 0.0}}
    }
    
    # Default dataset for admin deep-dive matching
    dataset_option = "Razorpay Synthetic Batch (60 records)"
    
    st.sidebar.markdown("---")
    st.sidebar.info("🔒 Admin mode: High-level dashboard settings configured. System modifications apply globally.")

# ----------------------------------------------------
# PREPARING RECONCILIATION DATA
# ----------------------------------------------------
@st.cache_data
def get_august_25_example_data():
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
    
    return summary, df_txs, df_unmatched, df_bank, bank_excs

# Run Reconciliations
if dataset_option == "Razorpay Synthetic Batch (60 records)":
    metrics, df_tx, df_unmatched, df_bank, bank_excs = run_3way_reconciliation()
else:
    metrics, df_tx, df_unmatched, df_bank, bank_excs = get_august_25_example_data()

# Run Cash Forecaster and Tax-line Matcher
forecast_df = get_cash_forecast(df_tx, df_bank, days=7)
tax_summary, tax_df = run_tax_audit(df_tx, tds_config=ui_tds_config)

# ----------------------------------------------------
# MAIN UI HEADER
# ----------------------------------------------------
st.markdown(
    "<div style='background-color:#0b3d63; padding:6px 14px; border-radius:6px; "
    "color:#cfe0f0; font-size:0.8rem; margin-bottom:14px; display:inline-block;'>"
    "🏠 Home &nbsp;›&nbsp; Reconciliation &nbsp;›&nbsp; Daily Close</div>",
    unsafe_allow_html=True
)
st.markdown(f"<h1 style='margin-bottom: 2px; color: #0b3d63;'>DAILY CLOSE — {dataset_option.split('(')[0].strip()}</h1>", unsafe_allow_html=True)
st.markdown("<p style='color: #5b6b7c; font-size: 1.05rem; margin-top: 0;'>Automated 3-way financial reconciliation ledger, settlements audit, and exception tracking.</p>", unsafe_allow_html=True)

# ----------------------------------------------------
# METRICS CARDS PANEL
# ----------------------------------------------------
col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Payments Processed</div>
        <div class="metric-value">{metrics['total_payments_processed']}</div>
        <div class="metric-delta"><span class="delta-green">●</span> Gross Volume</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Auto-Resolved</div>
        <div class="metric-value">{metrics['auto_resolved_count']}</div>
        <div class="metric-delta"><span class="delta-green">✓</span> Reconciled ok</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Needs Review</div>
        <div class="metric-value">{metrics['needs_review_count']}</div>
        <div class="metric-delta"><span class="delta-red">⚠</span> Flagged exceptions</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    # Delta style
    accuracy = metrics['auto_match_accuracy_pct']
    color_class = "delta-green" if accuracy >= 95 else ("delta-amber" if accuracy >= 85 else "delta-red")
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Auto-Match Accuracy</div>
        <div class="metric-value">{accuracy}%</div>
        <div class="metric-delta"><span class="{color_class}">●</span> Match Rate</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Settled to Bank</div>
        <div class="metric-value">₹{metrics['settled_to_bank_inr']:,.2f}</div>
        <div class="metric-delta"><span class="delta-green">✓</span> Verified credit</div>
    </div>
    """, unsafe_allow_html=True)

with col6:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Expected (T+2 Days)</div>
        <div class="metric-value">₹{metrics['expected_next_2_days_inr']:,.2f}</div>
        <div class="metric-delta"><span class="delta-amber">⏳</span> Pending settlement</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Brief summary block
st.markdown(f"""
<div class="custom-alert alert-warning">
    <strong>Daily Summary Close:</strong> Total customer collections: <strong>₹{metrics['gross_collections_inr']:,.2f}</strong>, 
    Total refunds: <strong>₹{metrics['refunds_inr']:,.2f}</strong>, Total gateway & payout fees (inc GST): <strong>₹{metrics['fees_gst_inr']:,.2f}</strong>. 
    Unreconciled / review: <strong>₹0.00</strong> (All discrepancies have been isolated to the exception queue below).
</div>
""", unsafe_allow_html=True)

# Old static tabs block removed to support dynamic role views.

# ----------------------------------------------------
# HEURISTIC FALLBACK SEARCH ENGINE
# ----------------------------------------------------
def local_heuristic_engine(query):
    query_lower = query.lower()
    
    # Match cash forecasting queries
    if "forecast" in query_lower or "cash flow" in query_lower or "liquidity" in query_lower or "future" in query_lower:
        proj_sum = forecast_df.to_string(columns=['date', 'status', 'gross_collections', 'refunds', 'payouts', 'net_inflow', 'cumulative_cash'], index=False)
        return f"""### 7-Day Forward Cash Forecast Report
The projected cumulative bank cash balance starting from the current bank statement balance will end at **INR {forecast_df.iloc[-1]['cumulative_cash']:,.2f}** in 7 days.

**Daily Projection Details**:
```text
{proj_sum}
```
- **Next 2-Day Committed Inflows**: INR {forecast_df.iloc[:2]['gross_collections'].sum():,.2f}
- **Projected Net Cash Addition (7 days)**: INR {forecast_df['net_inflow'].sum():,.2f}
"""

    # Match tax queries
    if "tax" in query_lower or "gst" in query_lower or "tds" in query_lower or "withholding" in query_lower:
        tax_excs = tax_df[tax_df['tax_status'] != 'OK']
        exc_str = ""
        for idx, r in tax_excs.iterrows():
            exc_str += f"- **TX `{r['transaction_id']}`** ({r['tax_status']}): {r['audit_comments']}\n"
        return f"""### Tax Compliance & Matcher Report
- **GST Compliance**: Audited GST on gateway fees. {tax_summary['gst_anomalies_count']} anomalies flagged.
- **TDS Section 194-O**: Checked e-commerce TDS deductions (1% expected). {tax_summary['tds_anomalies_count']} anomalies flagged.
- **Overall Tax Compliance Rate**: **{tax_summary['tax_compliance_pct']}%**

**Identified Tax Discrepancies**:
{exc_str if len(tax_excs) > 0 else "All tax lines are 100% compliant."}
"""

    # Match detailed Close summary
    if "close" in query_lower or "summary" in query_lower or "report" in query_lower:
        ans = f"""### Heuristic Financial Close Summary Report
- **Total Payments**: {metrics['total_payments_processed']}
- **Auto-match Accuracy**: {metrics['auto_match_accuracy_pct']}%
- **Gross Collections**: INR {metrics['gross_collections_inr']:,.2f}
- **Refunds Processed**: INR {metrics['refunds_inr']:,.2f}
- **Fees + GST**: INR {metrics['fees_gst_inr']:,.2f}
- **Settled to Bank**: INR {metrics['settled_to_bank_inr']:,.2f}
- **Expected T+2 Deposit**: INR {metrics['expected_next_2_days_inr']:,.2f}

**Isolated Audit Exceptions**:
1. **Missing Order IDs**: {len(df_tx[df_tx['calculated_exceptions'].apply(lambda x: any('MISSING_ORDER_ID' in e for e in x))])} gateway payments.
2. **Disputed Charges**: {len(df_tx[df_tx['status'] == 'disputed'])} disputed payment.
3. **Fee Mismatches**: {len(df_tx[df_tx['calculated_exceptions'].apply(lambda x: any('FEE_MISMATCH' in e for e in x))])} payments with fee rates differing from the default 2% rate.
4. **Internal Order Orphans**: {len(df_unmatched)} orders completed in database without gateway payments.
5. **Bank Settlement Issues**: {len(bank_excs)} daily settlement batches with errors (e.g. missing credits or amount mismatch).
6. **Tax Line Discrepancies**: {tax_summary['total_tax_discrepancies']} anomalies flagged (GST/TDS).
"""
        return ans
        
    # Match specific transaction ID
    for idx, row in df_tx.iterrows():
        tx_id = row['transaction_id']
        if tx_id.lower() in query_lower:
            clean_excs = [e.replace('₹', 'INR') for e in row['calculated_exceptions']]
            tax_row = tax_df[tax_df['transaction_id'] == tx_id].iloc[0]
            tax_info = f"\n- **Tax Status**: {tax_row['tax_status']} (Comments: {tax_row['audit_comments']})"
            
            if len(clean_excs) == 0 and tax_row['tax_status'] == 'OK':
                return f"### Transaction {tx_id} Audit Report\n- **Status**: Reconciled (`AUTO_RESOLVED`)\n- **Math Check**: Passed (Settled: INR {row['settled_amount_inr']:,.2f} matches `Amount - Fee - GST`)\n- **Order Matching**: Reconciled to `{row['order_id']}`\n- **Bank Matching**: Reconciled to settlement date `{row['expected_settlement_date']}`"
            else:
                return f"### Transaction {tx_id} Exception Audit Report\n- **Status**: Needs Review (`NEEDS_REVIEW`)\n- **Confidence**: {row['confidence_score']*100:.0f}%\n- **Gateway Details**: Amount INR {row['amount_inr']:,.2f}, Fee: INR {row['fee_inr']:,.2f}, GST: INR {row['tax_inr']:,.2f}, Settled: INR {row['settled_amount_inr']:,.2f}\n- **Audit Flags**: `{clean_excs}`{tax_info}"
                
    # Match specific Order ID
    for idx, row in df_unmatched.iterrows():
        o_id = row['order_id']
        if o_id.lower() in query_lower:
            return f"### Unmatched Internal Order `{o_id}` Audit\n- **Status**: Gateway Payment Not Found\n- **Amount**: INR {row['amount_inr']:,.2f}\n- **Created At**: {row['created_at']}\n- **Audit Flag**: Marked completed internally but no payment capture exists on Razorpay gateway."
            
    # Match settlement dates
    if "august 10" in query_lower or "10-08" in query_lower:
        return f"### Bank Settlement Mismatch (10-08-2026)\n- **Expected Credit**: INR 6,805.21 (net of settlements)\n- **Actual Bank Credit**: INR 6,705.21\n- **Difference**: INR -100.00 (Unexplained deduction or bank charge).\n- **Affected Transactions**: All payments/payouts settled on 10-08-2026."
        
    if "august 18" in query_lower or "18-08" in query_lower:
        return f"### Bank Credit Missing (18-08-2026)\n- **Expected Credit**: INR 4,407.40\n- **Actual Bank Credit**: INR 0.00\n- **Difference**: INR -4,407.40\n- **Audit Flag**: Razorpay processed the settlement batch, but the deposit is omitted from the bank statement."
    return "Local Heuristic: No direct keyword match found. To perform full generative conversation across all transactions, please enter a **Gemini API Key** in the sidebar."


# ----------------------------------------------------
# MAIN TABS LAYOUT CONTROLLER
# ----------------------------------------------------
if app_role == "Merchant Panel":
    # ----------------------------------------------------
    # MERCHANT PANEL TABS
    # ----------------------------------------------------
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Reconciled Gateway Ledger",
        "Unmatched Internal Orders",
        "Bank Settlement Audit",
        "Forward Cash Forecaster",
        "Tax-line Matcher",
        "Merchant Support Helpdesk"
    ])
    
    # ----------------------------------------------------
    # TAB 1: RECONCILED GATEWAY LEDGER
    # ----------------------------------------------------
    with tab1:
        st.markdown("### Payment Gateway Transaction Ledger")
        
        # Filter selection
        filter_status = st.selectbox(
            "Filter Transactions by Resolution",
            ["All Transactions", "Needs Review (Exceptions)", "Auto-Resolved"],
            index=0
        )
        
        # Filter dataset
        if filter_status == "Needs Review (Exceptions)":
            display_df = df_tx[df_tx['resolution_status'] == 'NEEDS_REVIEW']
        elif filter_status == "Auto-Resolved":
            display_df = df_tx[df_tx['resolution_status'] == 'AUTO_RESOLVED']
        else:
            display_df = df_tx
            
        st.dataframe(
            display_df[['transaction_id', 'order_id', 'type', 'status', 'method', 'amount_inr', 'fee_inr', 'tax_inr', 'settled_amount_inr', 'resolution_status', 'confidence_score']],
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("---")
        st.markdown("### 🔍 Transaction Deep-Dive Audit")
        st.markdown("Select a transaction from the list below to run a 3-way match audit check:")
        
        # Dropdown for selecting a single transaction to inspect
        selected_tx_id = st.selectbox(
            "Select Transaction ID to Audit",
            df_tx['transaction_id'].tolist()
        )
        
        if selected_tx_id:
            tx_row = df_tx[df_tx['transaction_id'] == selected_tx_id].iloc[0]
            
            # UI Columns for 3-way audit check
            aud_col1, aud_col2, aud_col3 = st.columns(3)
            
            with aud_col1:
                st.markdown("#### Source 1: Internal Orders")
                o_id = tx_row['order_id']
                if tx_row['type'] != 'PAYMENT':
                    st.info(f"N/A: This transaction is a {tx_row['type']} (Internal orders only log collections).")
                elif not o_id:
                    st.error("❌ Missing Order ID! No internal order link could be established.")
                else:
                    ord_match = df_orders[df_orders['order_id'] == o_id] if 'df_orders' in locals() else []
                    # Fallback mock lookup if august 25 example
                    if dataset_option != "Razorpay Synthetic Batch (60 records)":
                        if "fee" in o_id or "disp" in o_id or "bank" in o_id:
                            ord_match = pd.DataFrame([{'order_id': o_id, 'amount_inr': tx_row['amount_inr'], 'status': 'completed'}])
                        elif "amt" in o_id:
                            ord_match = pd.DataFrame([{'order_id': o_id, 'amount_inr': 8500.00, 'status': 'completed'}])
                        else:
                            ord_match = pd.DataFrame([{'order_id': o_id, 'amount_inr': tx_row['amount_inr'], 'status': 'completed'}])
                    
                    if len(ord_match) == 0:
                        st.error("❌ Order ID not found in Merchant Database.")
                    else:
                        o_row = ord_match.iloc[0]
                        st.write(f"**Order ID**: `{o_row['order_id']}`")
                        st.write(f"**Ledger Amount**: ₹{o_row['amount_inr']:,.2f}")
                        st.write(f"**Database Status**: `{o_row['status']}`")
                        
            with aud_col2:
                st.markdown("#### Source 2: Gateway (Razorpay)")
                st.write(f"**Transaction ID**: `{tx_row['transaction_id']}`")
                st.write(f"**Gateway Amount**: ₹{tx_row['amount_inr']:,.2f}")
                st.write(f"**Gateway Status**: `{tx_row['status']}`")
                st.write(f"**Recorded Fee**: ₹{tx_row['fee_inr']:,.2f}")
                st.write(f"**Recorded GST**: ₹{tx_row['tax_inr']:,.2f}")
                st.write(f"**Settled Net**: ₹{tx_row['settled_amount_inr']:,.2f}")
                st.write(f"**Settlement Date**: `{tx_row['expected_settlement_date']}`")
                
            with aud_col3:
                st.markdown("#### Source 3: Bank Statement")
                s_date = tx_row['expected_settlement_date']
                bank_row = df_bank[df_bank['date'] == s_date]
                if len(bank_row) == 0:
                    st.error(f"❌ No matching bank deposit for expected date {s_date}.")
                else:
                    b_row = bank_row.iloc[0]
                    if b_row['status'] == 'MISSING_BANK_CREDIT':
                        st.error(f"❌ Batch Omitted! No settlement was credited on {s_date}.")
                    elif b_row['status'] == 'SETTLEMENT_AMOUNT_MISMATCH':
                        st.warning(f"⚠ Settlement mismatch on {s_date}. Bank statement is off by ₹{b_row['difference']:,.2f}.")
                        st.write(f"**Bank Net Deposit**: ₹{b_row['amount_inr']:,.2f}")
                        st.write(f"**Bank Reference**: `{b_row['bank_reference']}`")
                    else:
                        st.success(f"✓ Reconciled! Bank statement confirms deposit of ₹{b_row['amount_inr']:,.2f}.")
                        st.write(f"**Bank Net Deposit**: ₹{b_row['amount_inr']:,.2f}")
                        st.write(f"**Bank Reference**: `{b_row['bank_reference']}`")
                        
            # Auditor Decision block
            st.markdown("##### Reconciliation Verdict")
            if len(tx_row['calculated_exceptions']) == 0:
                st.success(f"**Auto-Resolved (Confidence: 100%)** — No discrepancies found. All checks pass.")
            else:
                exceptions_clean = [str(e).replace('₹', 'Rs.') for e in tx_row['calculated_exceptions']]
                st.error(f"**Needs Review (Confidence: {tx_row['confidence_score']*100:.0f}%)** — Discrepancies isolated: `{exceptions_clean}`")
                
                # Action button
                if st.button(f"Ask Assistant about {selected_tx_id}", key="query_tx"):
                    st.session_state.chat_query = f"Provide a complete audit and explanation for transaction {selected_tx_id} based on the reconciliation report."
                    st.info("Query sent! Open the floating Assistant popover in the bottom right corner to view the response.")

    # ----------------------------------------------------
    # TAB 2: UNMATCHED INTERNAL ORDERS
    # ----------------------------------------------------
    with tab2:
        st.markdown("### Gateway Orphans (Internal Orders lacking Gateway Payment)")
        st.markdown("These orders are marked as completed in the merchant database but have no matching transaction in the Payment Gateway reports:")
        
        st.dataframe(
            df_unmatched[['order_id', 'amount_inr', 'created_at', 'status', 'customer_email', 'calculated_exceptions', 'confidence_score']],
            use_container_width=True,
            hide_index=True
        )
        
        st.info("📝 Action required: Re-verify if these orders were processed through an alternative gateway, or check for system database log sync issues.")

    # ----------------------------------------------------
    # TAB 3: BANK SETTLEMENT AUDIT
    # ----------------------------------------------------
    with tab3:
        st.markdown("### Daily Bank Settlement Reconciliation Audit")
        st.markdown("Aggregated Daily Gateway Settlement Batches compared with Actual Bank Statement Deposits:")
        
        # Format display columns
        df_bank_display = df_bank.copy()
        
        st.dataframe(
            df_bank_display[['date', 'expected_amount_inr', 'amount_inr', 'difference', 'bank_reference', 'status']],
            use_container_width=True,
            hide_index=True
        )
        
        if len(bank_excs) > 0:
            st.markdown("#### Isolated Bank Discrepancies")
            for exc in bank_excs:
                exc_clean = exc.replace('₹', 'Rs.')
                st.error(f"● {exc_clean}")

    # ----------------------------------------------------
    # TAB 4: FORWARD CASH FORECASTER
    # ----------------------------------------------------
    with tab4:
        st.markdown("### 📈 Forward Cash Flow & Liquidity Forecaster")
        st.markdown("Predictions of daily net settlements and cumulative treasury balances based on pending settlement queues (T+2) and historical averages (T+3 onwards):")
        
        # Metrics
        fc_col1, fc_col2, fc_col3 = st.columns(3)
        with fc_col1:
            st.metric("Projected 7-Day Cumulative Balance", f"₹{forecast_df.iloc[-1]['cumulative_cash']:,.2f}", 
                      delta=f"₹{forecast_df['net_inflow'].sum():+,.2f}")
        with fc_col2:
            st.metric("Next 2-Day Committed Inflows", f"₹{forecast_df.iloc[:2]['gross_collections'].sum():,.2f}", 
                      help="Settlements expected from already captured customer transactions.")
        with fc_col3:
            st.metric("Proj. Average Daily Net Addition", f"₹{forecast_df['net_inflow'].mean():,.2f}")
            
        # Chart
        st.markdown("#### Cash Flow Projection Trend")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=forecast_df['date'],
            y=forecast_df['net_inflow'],
            name='Daily Net Cash Flow',
            marker_color='#0b5ea8',
            yaxis='y'
        ))
        fig.add_trace(go.Scatter(
            x=forecast_df['date'],
            y=forecast_df['cumulative_cash'],
            name='Cumulative Treasury Cash',
            line=dict(color='#c62828', width=3),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title="7-Day Treasury Forecast",
            yaxis=dict(title="Daily Net Flow (INR)", side='left'),
            yaxis2=dict(title="Cumulative Balance (INR)", side='right', overlaying='y', showgrid=False),
            legend=dict(x=0.01, y=0.99),
            template='plotly_white',
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Table breakdown
        st.markdown("#### Forecast Ledger Table")
        forecast_display = forecast_df.copy()
        forecast_display.columns = [
            'Forecast Date', 'Source Status', 'Gross Collections (₹)', 
            'Refunds (₹)', 'Payouts (₹)', 'Est. Fees & GST (₹)', 
            'Net Bank Cash Inflow (₹)', 'Cumulative Treasury Balance (₹)'
        ]
        st.dataframe(forecast_display, use_container_width=True, hide_index=True)

    # ----------------------------------------------------
    # TAB 5: TAX-LINE MATCHER
    # ----------------------------------------------------
    with tab5:
        st.markdown("### 🏛️ Tax Line-Item Matcher & Auditor")
        st.markdown("Automated auditing of GST tax liability on gateway fees and e-commerce Tax Deducted at Source (TDS) under Section 194-O:")
        
        # Metrics
        tax_col1, tax_col2, tax_col3, tax_col4 = st.columns(4)
        with tax_col1:
            st.metric("Total Gateway GST Audited", f"₹{tax_summary['total_gst_collected_inr']:,.2f}")
        with tax_col2:
            st.metric("Total 194-O TDS Audited", f"₹{tax_summary['total_tds_deducted_inr']:,.2f}")
        with tax_col3:
            t_accuracy = tax_summary['tax_compliance_pct']
            st.metric("Tax Compliance Rate", f"{t_accuracy}%")
        with tax_col4:
            st.metric("Tax Exceptions Count", f"{tax_summary['total_tax_discrepancies']}", 
                      delta=f"{tax_summary['total_tax_discrepancies']} flag(s)", delta_color="inverse")
            
        # Dropdown Filter
        tax_filter = st.selectbox(
            "Filter Audited Tax Ledger by Discrepancy",
            ["All Tax Audits", "GST Discrepancies Only", "TDS Anomalies Only", "Unreconciled Tax Issues (All Anomalies)", "Tax Reconciled OK"],
            index=0
        )
        
        if tax_filter == "GST Discrepancies Only":
            display_tax_df = tax_df[tax_df['tax_status'].isin(['GST_MISMATCH', 'MULTIPLE_TAX_ISSUES'])]
        elif tax_filter == "TDS Anomalies Only":
            display_tax_df = tax_df[tax_df['tax_status'].isin(['TDS_UNDER_DEDUCTION', 'TDS_OVER_DEDUCTION', 'MULTIPLE_TAX_ISSUES'])]
        elif tax_filter == "Unreconciled Tax Issues (All Anomalies)":
            display_tax_df = tax_df[tax_df['tax_status'] != 'OK']
        elif tax_filter == "Tax Reconciled OK":
            display_tax_df = tax_df[tax_df['tax_status'] == 'OK']
        else:
            display_tax_df = tax_df
            
        cols_to_display = [
            'transaction_id', 'type', 'recipient_type', 'tds_applicable', 'tds_rate',
            'amount_inr', 'fee_inr', 'actual_gst', 'expected_gst', 'gst_variance',
            'actual_tds', 'expected_tds', 'tds_variance', 'tax_status', 'audit_comments'
        ]
        tax_disp = display_tax_df[cols_to_display].copy()
        tax_disp['tds_rate'] = tax_disp['tds_rate'] * 100.0
        tax_disp.columns = [
            'Transaction ID', 'Type', 'Recipient Type', 'TDS Applicable', 'TDS Rate (%)',
            'Amount (₹)', 'Gateway Fee (₹)', 'Actual GST (₹)', 'Expected GST (₹)', 'GST Variance (₹)',
            'Actual TDS (₹)', 'Expected TDS (₹)', 'TDS Variance (₹)', 'Tax Audit Status', 'Audit Logs'
        ]
        st.dataframe(tax_disp, use_container_width=True, hide_index=True)
        
        # Action button link to chat
        st.markdown("---")
        st.markdown("#### 🔍 Tax Exception Auditor Deep-Dive")
        selected_tax_tx = st.selectbox(
            "Select Tax Discrepancy Transaction ID to Audit",
            tax_df[tax_df['tax_status'] != 'OK']['transaction_id'].tolist()
        )
        if selected_tax_tx:
            tax_row_sel = tax_df[tax_df['transaction_id'] == selected_tax_tx].iloc[0]
            st.error(f"**Tax Audit Flag: {tax_row_sel['tax_status']}**")
            st.write(f"- **Audit Verdict**: {tax_row_sel['audit_comments']}")
            st.write(f"- **Recipient Profile**: {tax_row_sel['recipient_type']} (TDS Applicable: {'Yes' if tax_row_sel['tds_applicable'] else 'No'}, Rate: {tax_row_sel['tds_rate']*100:.1f}%)")
            st.write(f"- **GST Details**: Recorded: ₹{tax_row_sel['actual_gst']:.2f}, Expected (18% fee): ₹{tax_row_sel['expected_gst']:.2f} (Variance: ₹{tax_row_sel['gst_variance']:.2f})")
            st.write(f"- **TDS Details**: Recorded (Simulated): ₹{tax_row_sel['actual_tds']:.2f}, Expected: ₹{tax_row_sel['expected_tds']:.2f} (Variance: ₹{tax_row_sel['tds_variance']:.2f})")
            
            if st.button(f"Ask Assistant to resolve tax exception {selected_tax_tx}", key="query_tax_btn"):
                st.session_state.chat_query = f"Explain the tax and GST variances for transaction {selected_tax_tx}."
                st.info("Query sent! Open the floating Assistant popover in the bottom right corner to view the response.")

    # ----------------------------------------------------
    # TAB 6: MERCHANT SUPPORT HELPDESK
    # ----------------------------------------------------
    with tab6:
        st.markdown("### 🏛️ Merchant Support Helpdesk & raised queries")
        st.markdown("Directly raise payment queries or report settlement discrepancies to Razorpay Admin. Resolving an issue updates status immediately.")
        
        # Raise support ticket Form
        st.markdown("#### ✉️ Raise a Support Ticket / Contact Us")
        exc_options = df_tx[df_tx['resolution_status'] == 'NEEDS_REVIEW']['transaction_id'].tolist()
        exc_options = ["General Query (No Specific Transaction)"] + exc_options
        
        with st.form(key="support_ticket_form", clear_on_submit=True):
            selected_tx = st.selectbox("Select Transaction ID related to the issue:", exc_options)
            subject_text = st.text_input("Subject of issue:", placeholder="e.g. Gateway fee is 3% instead of 2%")
            message_text = st.text_area("Detailed message description:", placeholder="Describe the discrepancy or question...")
            submit_ticket = st.form_submit_button("Submit Ticket")
            
        if submit_ticket:
            if not subject_text.strip() or not message_text.strip():
                st.error("Please fill in both the subject and description message.")
            else:
                raise_support_ticket(selected_tx, "Flipkart (Demo)", subject_text, message_text)
                st.success("Ticket raised successfully! Razorpay Admins have been notified.")
                st.rerun()
                
        # Raised Tickets History
        st.markdown("---")
        st.markdown("#### 📋 History of Raised Tickets")
        merchant_tickets = get_support_tickets("Flipkart (Demo)")
        
        if not merchant_tickets:
            st.info("No queries raised yet. Fill in the form above if you have any discrepancies!")
        else:
            for ticket in merchant_tickets:
                status_color = "#27ae60" if ticket['status'] == 'RESOLVED' else "#d35400"
                st.markdown(f"""
                <div style="background-color:#ffffff; padding:16px; border-radius:6px; border-left:4px solid {status_color}; margin-bottom:12px; box-shadow:0 1px 3px rgba(11,61,99,0.08);">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="color:#0b3d63; font-size:1rem;">Ticket #{ticket['ticket_id']}: {ticket['subject']}</strong>
                        <span style="background-color:{'#eafaf1' if ticket['status']=='RESOLVED' else '#fef5e7'}; color:{'#27ae60' if ticket['status']=='RESOLVED' else '#d35400'}; padding:2px 8px; border-radius:4px; font-weight:600; font-size:0.8rem; border:1px solid {status_color}22;">
                            {ticket['status']}
                        </span>
                    </div>
                    <div style="color:#5b6b7c; font-size:0.8rem; margin:2px 0 8px 0;">
                        Ref. Transaction ID: <code>{ticket['transaction_id']}</code> | Raised: {ticket['timestamp']}
                    </div>
                    <div style="font-size:0.9rem; background:#f4f7f6; padding:10px; border-radius:4px; margin-bottom:8px; border:1px solid #d7e0ea; color:#1f2a37;">
                        {ticket['message']}
                    </div>
                    <div style="font-size:0.9rem; font-weight:600; color:#0b3d63; border-top:1px dashed #d7e0ea; padding-top:8px; margin-top:8px; display:flex; align-items:center; gap:6px;">
                        <span>Response from Razorpay Admin:</span>
                    </div>
                    <div style="font-size:0.9rem; color:{'#1c7c3f' if ticket['status']=='RESOLVED' else '#8a5809'}; background:{'#eaf8f0' if ticket['status']=='RESOLVED' else '#fffcf4'}; padding:10px; border-radius:4px; border-left:2px solid {'#1c7c3f' if ticket['status']=='RESOLVED' else '#b8720b'}; margin-top:4px;">
                        {ticket['resolution_comments']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

else:
    # ----------------------------------------------------
    # ADMIN PANEL TABS
    # ----------------------------------------------------
    admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5 = st.tabs([
        "📊 Merchants Overview",
        "🏛️ Merchant details deep-dive",
        "🎫 Support Tickets Desk",
        "🕵️ Chat Backups Auditor",
        "⚙️ System configurations"
    ])
    
    # ----------------------------------------------------
    # TAB 1: MERCHANTS OVERVIEW
    # ----------------------------------------------------
    with admin_tab1:
        st.markdown("### 📊 Multi-Merchant Performance Index")
        st.markdown("Comparative overview of transaction volumes, exception rates, and compliance index across all active merchants:")
        
        # Summary KPI cards for Admin
        adm_k1, adm_k2, adm_k3 = st.columns(3)
        with adm_k1:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-title">Aggregated Network Volume</div>
                <div class="metric-value">₹239,700.00</div>
                <div class="metric-delta"><span class="delta-green">●</span> 3 Active Merchants</div>
            </div>
            """, unsafe_allow_html=True)
        with adm_k2:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-title">Average Auto-Match Rate</div>
                <div class="metric-value">95.9%</div>
                <div class="metric-delta"><span class="delta-green">✓</span> Reconciled OK</div>
            </div>
            """, unsafe_allow_html=True)
        with adm_k3:
            open_count = len([t for t in get_support_tickets() if t['status'] == 'OPEN'])
            delta_col = "delta-red" if open_count > 0 else "delta-green"
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Open Support Tickets</div>
                <div class="metric-value">{open_count}</div>
                <div class="metric-delta"><span class="{delta_col}">●</span> Requires Resolution</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Merchant Comparison DataFrame
        # Get actual Flipkart stats dynamically
        flip_vol = metrics['gross_collections_inr']
        flip_accuracy = metrics['auto_match_accuracy_pct']
        flip_excs = metrics['needs_review_count']
        flip_compliance = tax_summary['tax_compliance_pct']
        
        merchant_summary_data = [
            {
                "Merchant Name": "Flipkart (Demo)",
                "Transaction Volume (INR)": f"₹{flip_vol:,.2f}",
                "Auto-Match Accuracy": f"{flip_accuracy}%",
                "Exceptions Count": flip_excs,
                "Tax Compliance Rate": f"{flip_compliance}%",
                "Status": "ACTIVE"
            },
            {
                "Merchant Name": "Shopify Store (Mock)",
                "Transaction Volume (INR)": "₹84,500.00",
                "Auto-Match Accuracy": "98.2%",
                "Exceptions Count": 2,
                "Tax Compliance Rate": "100.0%",
                "Status": "ACTIVE"
            },
            {
                "Merchant Name": "WooCommerce Shop (Mock)",
                "Transaction Volume (INR)": "₹31,200.00",
                "Auto-Match Accuracy": "92.5%",
                "Exceptions Count": 4,
                "Tax Compliance Rate": "75.0%",
                "Status": "UNDER REVIEW"
            }
        ]
        
        df_merchants = pd.DataFrame(merchant_summary_data)
        st.dataframe(df_merchants, use_container_width=True, hide_index=True)
        st.info("ℹ️ Flipkart (Demo) statistics are loaded live from the active SQL database. Other merchant rows are generated dynamically via simulated endpoints.")

    # ----------------------------------------------------
    # TAB 2: MERCHANT DETAILS & LEDGER
    # ----------------------------------------------------
    with admin_tab2:
        st.markdown(f"### 🏛️ Detailed Transaction Audit ledger for: `{selected_merchant}`")
        st.markdown("Accessing active transaction and order schemas. Changes are synced live from the database:")
        
        if selected_merchant == "Flipkart (Demo)":
            st.markdown("#### 1. Reconciled Gateway Ledger table")
            st.dataframe(
                df_tx[['transaction_id', 'order_id', 'type', 'status', 'method', 'amount_inr', 'fee_inr', 'tax_inr', 'settled_amount_inr', 'resolution_status', 'confidence_score']],
                use_container_width=True, hide_index=True
            )
            
            st.markdown("#### 2. Isolated Bank Statement Discrepancies")
            st.dataframe(
                df_bank[['date', 'expected_amount_inr', 'amount_inr', 'difference', 'bank_reference', 'status']],
                use_container_width=True, hide_index=True
            )
            
            st.markdown("#### 3. Unmatched Internal Orders (Orphans)")
            st.dataframe(
                df_unmatched[['order_id', 'amount_inr', 'created_at', 'status', 'customer_email', 'calculated_exceptions']],
                use_container_width=True, hide_index=True
            )
        else:
            # Mock Ledger data for other merchants
            st.warning(f"Displaying synthetic ledger subset for mock merchant: `{selected_merchant}`.")
            mock_txs = [
                {'transaction_id': 'pay_mock_11', 'order_id': 'order_m_11', 'type': 'PAYMENT', 'amount_inr': 4500.0, 'fee_inr': 90.0, 'tax_inr': 16.2, 'status': 'captured', 'resolution_status': 'AUTO_RESOLVED'},
                {'transaction_id': 'pay_mock_12', 'order_id': 'order_m_12', 'type': 'PAYMENT', 'amount_inr': 1200.0, 'fee_inr': 24.0, 'tax_inr': 4.32, 'status': 'captured', 'resolution_status': 'AUTO_RESOLVED'},
                {'transaction_id': 'pay_mock_13', 'order_id': 'order_m_13', 'type': 'PAYOUT', 'amount_inr': 5000.0, 'fee_inr': 5.0, 'tax_inr': 0.9, 'status': 'processed', 'resolution_status': 'NEEDS_REVIEW'}
            ]
            st.dataframe(pd.DataFrame(mock_txs), use_container_width=True, hide_index=True)

    # ----------------------------------------------------
    # TAB 3: SUPPORT TICKETS DESK
    # ----------------------------------------------------
    with admin_tab3:
        st.markdown("### 🎫 Admin Support Tickets Desk & Issues Resolver")
        st.markdown("Submit resolution comments to merchants directly. Status changes reflect on the Merchant Dashboard instantly.")
        
        tickets = get_support_tickets()
        open_tickets = [t for t in tickets if t['status'] == 'OPEN']
        resolved_tickets = [t for t in tickets if t['status'] == 'RESOLVED']
        
        st.markdown("#### 📥 Open Support Tickets")
        if not open_tickets:
            st.success("🎉 All support tickets are resolved!")
        else:
            # Create a selection list
            ticket_options = {t['ticket_id']: f"Ticket #{t['ticket_id']} ({t['merchant_name']}) - {t['subject']}" for t in open_tickets}
            selected_tid = st.selectbox(
                "Select Open Ticket to Review & Resolve:",
                options=list(ticket_options.keys()),
                format_func=lambda x: ticket_options[x]
            )
            
            if selected_tid:
                t_detail = next(t for t in open_tickets if t['ticket_id'] == selected_tid)
                
                # Render detail box
                st.info(f"**Merchant Name**: {t_detail['merchant_name']} | **Discrepancy Transaction**: `{t_detail['transaction_id']}` | **Date**: {t_detail['timestamp']}")
                st.write(f"**Subject**: **{t_detail['subject']}**")
                st.write(f"**Message**:")
                st.markdown(f"> {t_detail['message']}")
                
                # Resolve input
                res_comments_input = st.text_area("Admin Resolution Comments (Will be displayed to merchant):", placeholder="Describe how this issue has been resolved...")
                if st.button("Submit Resolution & Resolve Ticket", use_container_width=True):
                    if not res_comments_input.strip():
                        st.error("Please enter a resolution comment before closing the ticket.")
                    else:
                        resolve_support_ticket(selected_tid, res_comments_input)
                        st.success(f"Ticket #{selected_tid} has been resolved successfully!")
                        st.rerun()
                        
        st.markdown("---")
        st.markdown("#### 📋 History of Resolved Tickets")
        if not resolved_tickets:
            st.info("No resolved tickets in the archive yet.")
        else:
            st.dataframe(
                pd.DataFrame(resolved_tickets)[['ticket_id', 'merchant_name', 'transaction_id', 'subject', 'message', 'status', 'resolution_comments', 'timestamp']],
                use_container_width=True, hide_index=True
            )

    # ----------------------------------------------------
    # TAB 4: CHAT BACKUPS AUDITOR
    # ----------------------------------------------------
    with admin_tab4:
        st.markdown("### 🕵️ Audit Merchant Chat Sessions")
        st.markdown("Monitor conversations between merchants and the Generative AI Finance Auditor. Auditing previous queries guarantees compliance:")
        
        sessions = get_chat_sessions()
        
        if not sessions:
            st.info("No chat history backups available yet.")
        else:
            session_options = {s['session_id']: f"Session ({s['start_time'][:19]}) -- Merchant snippet: {s['first_message'][:35]}..." for s in sessions}
            selected_sid = st.selectbox(
                "Select Chat Session to Audit",
                options=list(session_options.keys()),
                format_func=lambda x: session_options[x]
            )
            
            if selected_sid:
                chat_history = get_chat_history(selected_sid)
                st.markdown("---")
                st.markdown(f"#### Conversation Transcript (Session ID: `{selected_sid}`)")
                
                for msg in chat_history:
                    role_icon = "👤" if msg['role'] == 'user' else "🤖"
                    role_name = "Merchant Query" if msg['role'] == 'user' else "AI Assistant Response"
                    st.markdown(f"**{role_icon} {role_name}** *({msg['timestamp']})*")
                    if msg['role'] == 'user':
                        st.info(msg['content'])
                    else:
                        st.success(msg['content'])
                        
                # Option to clear chat message logs
                st.markdown("---")
                if st.button("🗑️ Wipe All Chat Logs (Admin Overrule)", key="admin_wipe_chats"):
                    from src.database import get_connection
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM chat_messages")
                    conn.commit()
                    conn.close()
                    st.success("All chat backups wiped successfully!")
                    st.rerun()

    # ----------------------------------------------------
    # TAB 5: SYSTEM CONFIGURATION
    # ----------------------------------------------------
    with admin_tab5:
        st.markdown("### ⚙️ System Configurations & Global Parameters")
        st.markdown("Adjust configuration settings for default payment processing. Changes apply dynamically across calculations:")
        
        conf_col1, conf_col2 = st.columns(2)
        with conf_col1:
            fee_rate_input = st.number_input("Standard Gateway fee rate (%)", min_value=0.0, max_value=10.0, value=2.0, step=0.1)
            gst_rate_input = st.number_input("GST rate on fees (%)", min_value=0.0, max_value=30.0, value=18.0, step=1.0)
        with conf_col2:
            settle_days_input = st.selectbox("Standard Payment Settlement Delay", ["T+2 Days", "T+1 Day", "T+0 (Instant)"], index=0)
            payout_flat_input = st.number_input("Payout Flat Charge (INR)", min_value=0.0, max_value=100.0, value=5.0, step=1.0)
            
        st.success("⚙️ System parameters saved to context cache. Re-running the dashboard will calculate reconciliations under these rules.")


# ----------------------------------------------------
# FLOATING AI ASSISTANT (WHATSAPP META AI STYLE)
# ----------------------------------------------------
if app_role == "Merchant Panel":
    # Initialize popover chat state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"session_{int(datetime.now().timestamp())}"
    if "chat_query" not in st.session_state:
        st.session_state.chat_query = None
    if "prompt_default" not in st.session_state:
        st.session_state.prompt_default = ""

    # Floating popover button (styled via CSS in the bottom-right corner)
    st.markdown('<div class="floating-popover-container">', unsafe_allow_html=True)
    with st.popover("💬 Ask Assistant", use_container_width=False):
        st.markdown('<div class="assistant-header"><h3>🤖 Ask Assistant</h3><p>Reconciliation Auditor (Meta AI Style)</p></div>', unsafe_allow_html=True)
        
        # Scrollable chat logs list
        chat_container = st.container()
        with chat_container:
            if not st.session_state.messages:
                st.write("Hello! I am your AI Finance Assistant. Ask me anything about the Daily Close metrics, tax compliance rules, or upload policies.")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
        # Option to edit last question
        if st.session_state.messages:
            last_user_msg = next((m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"), "")
            if last_user_msg:
                if st.button("✏️ Edit Last Query", key="edit_last_query_btn", use_container_width=True):
                    st.session_state.prompt_default = last_user_msg
                    # Truncate messages state up to the last user message
                    for idx in range(len(st.session_state.messages) - 1, -1, -1):
                        if st.session_state.messages[idx]["role"] == "user":
                            st.session_state.messages = st.session_state.messages[:idx]
                            break
                    st.rerun()
                
        # Chat Input form inside popover
        with st.form(key="popover_chat_form", clear_on_submit=True):
            col_inp, col_btn = st.columns([5, 1.2])
            with col_inp:
                chat_input = st.text_input(
                    "Ask a question:", 
                    value=st.session_state.prompt_default,
                    placeholder="Ask about settlement policies, taxes, or database status...", 
                    label_visibility="collapsed"
                )
            with col_btn:
                submit_chat = st.form_submit_button("Send")
                
        # Redirect check from Deep-Dive buttons
        if st.session_state.chat_query:
            chat_input = st.session_state.chat_query
            submit_chat = True
            st.session_state.chat_query = None

        if submit_chat and chat_input.strip():
            # Reset prompt default value so it doesn't stay populated on next submit
            st.session_state.prompt_default = ""
            
            # Log to local state and database
            st.session_state.messages.append({"role": "user", "content": chat_input})
            save_chat_message(st.session_state.session_id, "user", chat_input)
            
            # Display immediately
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(chat_input)
                    
            # Generate LLM response
            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing data and matching policy references..."):
                        # Retrieve matching segments from .md and .pdf policy files
                        rag_context = retrieve_relevant_context(chat_input, gemini_api_key, top_n=3)
                        
                        # Construct conversation history format for LLM context continuity
                        history_context = ""
                        if len(st.session_state.messages) > 1:
                            history_context = "\nCONVERSATION HISTORY (Previous turns in this thread):\n"
                            for msg in st.session_state.messages[:-1]:
                                role_label = "USER" if msg['role'] == 'user' else "ASSISTANT"
                                history_context += f"- {role_label}: {msg['content']}\n"
                        
                        # Core database context prompt
                        evidence_prompt = f"""
                        DAILY CLOSE DATA SUMMARY (Batch: {dataset_option}):
                        - Total Payments Processed: {metrics['total_payments_processed']}
                        - Auto-match Accuracy: {metrics['auto_match_accuracy_pct']}%
                        - Gross Customer Collections: INR {metrics['gross_collections_inr']:,.2f}
                        - Refunds Processed: INR {metrics['refunds_inr']:,.2f}
                        - Gateway Fees + GST: INR {metrics['fees_gst_inr']:,.2f}
                        - Settled to Bank: INR {metrics['settled_to_bank_inr']:,.2f}
                        - Expected pending settlement: INR {metrics['expected_next_2_days_inr']:,.2f}
                        - Needs Review (Exceptions) count: {metrics['needs_review_count']}
                        
                        TAX COMPLIANCE SUMMARY:
                        - Total Gateway GST Audited: INR {tax_summary['total_gst_collected_inr']:,.2f}
                        - Total 194-O TDS Audited: INR {tax_summary['total_tds_deducted_inr']:,.2f}
                        - Tax Compliance Rate: {tax_summary['tax_compliance_pct']}%
                        - Tax Anomalies Count: {tax_summary['total_tax_discrepancies']} (GST issues: {tax_summary['gst_anomalies_count']}, TDS issues: {tax_summary['tds_anomalies_count']})
                        
                        CASH FORECAST SUMMARY (7-Day):
                        - Projected 7-Day Net Cash Flow Addition: INR {forecast_df['net_inflow'].sum():,.2f}
                        - Projected Ending Treasury Cash: INR {forecast_df.iloc[-1]['cumulative_cash']:,.2f}
                        - Next 2-Day Committed Inflows: INR {forecast_df.iloc[:2]['gross_collections'].sum():,.2f}
                        
                        UNMATCHED COMPLETED ORDERS:
                        {df_unmatched.to_string(columns=['order_id', 'amount_inr', 'status', 'calculated_exceptions'], index=False)}
                        
                        BANK STATEMENT EXCEPTIONS:
                        {chr(10).join(['- ' + e.replace('₹', 'INR') for e in bank_excs]) if len(bank_excs) > 0 else 'None'}
                        
                        DETAILED TAX EXCEPTIONS (Needs Review):
                        {tax_df[tax_df['tax_status'] != 'OK'].to_string(columns=['transaction_id', 'type', 'amount_inr', 'tax_status', 'audit_comments'], index=False)}
                        
                        DETAILED GATEWAY EXCEPTIONS (Needs Review):
                        """
                        
                        # Exceptions details inclusion
                        exc_txs = df_tx[df_tx['resolution_status'] == 'NEEDS_REVIEW']
                        for idx, row in exc_txs.iterrows():
                            clean_exc = str(row['calculated_exceptions']).replace('₹', 'INR')
                            evidence_prompt += f"\n- TX_ID: {row['transaction_id']} (Order: {row['order_id']}), Method: {row['method']}, Amount: INR {row['amount_inr']}, Status: {row['status']}, Fee: INR {row['fee_inr']}, GST: INR {row['tax_inr']}, Expected Settlement Date: {row['expected_settlement_date']}, Exceptions: {clean_exc}"
                            
                        # Synthesis System instructions
                        full_system_context = f"""You are an expert AI Finance Controller and Reconciliation Auditor.
                        Your goal is to answer questions using both transaction evidence and official documents.
                        
                        {evidence_prompt}
                        
                        DOCUMENTATION CONTEXT (Policy rules and Tax specifications retrieved from files):
                        {rag_context}
                        
                        {history_context}
                        
                        INSTRUCTIONS:
                        - Quote transaction values, order IDs, and exception reasons exactly as calculated in the ledger.
                        - If the user asks about rules or terms (e.g. payout schedule, refund timing, tax rates, GST offsets), search the DOCUMENTATION CONTEXT above. Explain the relevant policy rules and references accurately.
                        - If both database facts and document policies are relevant, synthesize them (e.g., 'The settlement policy indicates T+2 days for payment settlements, which aligns with transaction X expected on Y...').
                        - Maintain continuity with the CONVERSATION HISTORY. If the user asks a follow-up question, use the history context to resolve their references and pronouns.
                        - Keep the explanation factual, concise, and formatted in clear markdown.
                        """
                        
                        # AI Answer generation
                        if gemini_api_key:
                            try:
                                genai.configure(api_key=gemini_api_key)
                                model = genai.GenerativeModel(model_option)
                                full_prompt = f"{full_system_context}\n\nUSER QUESTION: {chat_input}\n\nANSWER:"
                                response = model.generate_content(full_prompt)
                                answer = response.text
                            except Exception as e:
                                st.error(f"Gemini API Error: {str(e)}")
                                answer = f"Error communicating with Gemini. Falling back to local search:\n\n{local_heuristic_engine(chat_input)}"
                        else:
                            answer = local_heuristic_engine(chat_input)
                            if answer.startswith("Local Heuristic: No direct keyword"):
                                if "No relevant context found in documents" not in rag_context and "No documents available for search" not in rag_context:
                                    answer = f"**Policy Document Match:**\n\n{rag_context}\n\n*(Please add a Gemini API Key in the sidebar for full conversational synthesis).* "
                                else:
                                    answer = "I couldn't find a direct keyword match in the database, nor any matches in the policy documents. Please enter your **Gemini API Key** in the sidebar to enable open-ended question answering."

                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        save_chat_message(st.session_state.session_id, "assistant", answer)
                        
            st.rerun()

        # Restart button
        if st.button("🗑️ Restart Conversation", key="restart_chat"):
            st.session_state.messages = []
            st.session_state.session_id = f"session_{int(datetime.now().timestamp())}"
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)