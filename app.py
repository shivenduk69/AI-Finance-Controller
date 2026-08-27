import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta
import google.generativeai as genai

# Import our reconciliation engine
from src.reconciliation import run_3way_reconciliation

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
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# SIDEBAR CREDENTIALS & OPTIONS
# ----------------------------------------------------
st.sidebar.markdown("<h2 style='text-align: center; color: #ffffff; font-weight: 800; margin-bottom: 4px;'>AI Finance Controller</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; color: #cfe0f0; font-size: 0.8rem; margin-top: 0;'>Multi-Source Reconciliation Agent</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")

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
    ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Core Engine Rules")
st.sidebar.markdown("""
- **Exact ID Matching**: Order ID lookups.
- **Math Checks**: Settled = Amt - Fee - GST.
- **Fee Rate Validation**: 2% Gateway, Flat 5 INR Payouts, T+0 Refunds.
- **Settlement Window**: T+2 bank statement deposit verification.
- **Duplicate Check**: Unique gateway ID check.
""")

st.sidebar.info("💡 Fallback Heuristic engine is active if no Gemini API Key is provided.")

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

# ----------------------------------------------------
# MAIN TABS LAYOUT
# ----------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Reconciled Gateway Ledger",
    "Unmatched Internal Orders",
    "Bank Settlement Audit",
    "AI Financial Assistant"
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
                st.info("Query sent! Switch to the 'AI Financial Assistant' tab to view the answer.")

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
# TAB 4: AI FINANCIAL ASSISTANT (CHAT)
# ----------------------------------------------------
with tab4:
    st.markdown("### 🤖 Generative AI Finance Auditor")
    st.markdown("Ask natural language questions about the daily close, transaction status, or settlement discrepancies. The agent will analyze the calculated audit evidence and explain the results.")

    # Formulate evidence context for prompt
    evidence_prompt = f"""
    You are an expert AI Finance Controller / Reconciliation Auditor. 
    Your task is to explain reconciliation results and answer questions using ONLY calculated evidence from the daily close. Do not make up facts or extrapolate beyond what is documented in the evidence.
    
    DAILY CLOSE DATA SUMMARY (Batch: {dataset_option}):
    - Total Payments Processed: {metrics['total_payments_processed']}
    - Auto-match Accuracy: {metrics['auto_match_accuracy_pct']}%
    - Gross Customer Collections: INR {metrics['gross_collections_inr']:,.2f}
    - Refunds Processed: INR {metrics['refunds_inr']:,.2f}
    - Gateway Fees + GST: INR {metrics['fees_gst_inr']:,.2f}
    - Settled to Bank: INR {metrics['settled_to_bank_inr']:,.2f}
    - Expected pending settlement: INR {metrics['expected_next_2_days_inr']:,.2f}
    - Needs Review (Exceptions) count: {metrics['needs_review_count']}
    
    UNMATCHED COMPLETED ORDERS:
    {df_unmatched.to_string(columns=['order_id', 'amount_inr', 'status', 'calculated_exceptions'], index=False)}
    
    BANK STATEMENT EXCEPTIONS:
    {chr(10).join(['- ' + e.replace('₹', 'INR') for e in bank_excs]) if len(bank_excs) > 0 else 'None'}
    
    DETAILED GATEWAY EXCEPTIONS (Needs Review):
    """
    
    # Add detailed transaction exceptions to prompt (limit to prevent token bloat)
    exc_txs = df_tx[df_tx['resolution_status'] == 'NEEDS_REVIEW']
    for idx, row in exc_txs.iterrows():
        clean_exc = str(row['calculated_exceptions']).replace('₹', 'INR')
        evidence_prompt += f"\n- TX_ID: {row['transaction_id']} (Order: {row['order_id']}), Method: {row['method']}, Amount: INR {row['amount_inr']}, Status: {row['status']}, Fee: INR {row['fee_inr']}, GST: INR {row['tax_inr']}, Expected Settlement Date: {row['expected_settlement_date']}, Exceptions: {clean_exc}"
        
    evidence_prompt += "\n\nINSTRUCTIONS:\n- Be precise, factual, and concise.\n- Quote exact amounts and transaction/order IDs.\n- Do not guess or suggest explanations not supported by the math.\n- Write in clean, professional markdown."

    # Heuristic fallback answers engine if no Gemini API Key is provided
    def local_heuristic_engine(query):
        query_lower = query.lower()
        
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
"""
            return ans
            
        # Match specific transaction ID
        for idx, row in df_tx.iterrows():
            tx_id = row['transaction_id']
            if tx_id.lower() in query_lower:
                clean_excs = [e.replace('₹', 'INR') for e in row['calculated_exceptions']]
                if len(clean_excs) == 0:
                    return f"### Transaction {tx_id} Audit Report\n- **Status**: Reconciled (`AUTO_RESOLVED`)\n- **Math Check**: Passed (Settled: INR {row['settled_amount_inr']:,.2f} matches `Amount - Fee - GST`)\n- **Order Matching**: Reconciled to `{row['order_id']}`\n- **Bank Matching**: Reconciled to settlement date `{row['expected_settlement_date']}`"
                else:
                    return f"### Transaction {tx_id} Exception Audit Report\n- **Status**: Needs Review (`NEEDS_REVIEW`)\n- **Confidence**: {row['confidence_score']*100:.0f}%\n- **Gateway Details**: Amount INR {row['amount_inr']:,.2f}, Fee: INR {row['fee_inr']:,.2f}, GST: INR {row['tax_inr']:,.2f}, Settled: INR {row['settled_amount_inr']:,.2f}\n- **Audit Flags**: `{clean_excs}`"
                    
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

    # Chat UI container
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Check for query from direct-action button
    if "chat_query" in st.session_state and st.session_state.chat_query:
        user_input = st.session_state.chat_query
        st.session_state.chat_query = None # clear
    else:
        user_input = st.chat_input("Ask a question about the close (e.g. 'Why did pay_24716857 fail?')")

    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        # Generate answer
        with st.chat_message("assistant"):
            with st.spinner("Analyzing reconciliation database..."):
                if gemini_api_key:
                    try:
                        genai.configure(api_key=gemini_api_key)
                        model = genai.GenerativeModel(model_option)
                        
                        full_prompt = f"{evidence_prompt}\n\nUSER QUESTION: {user_input}\n\nANSWER:"
                        response = model.generate_content(full_prompt)
                        answer = response.text
                    except Exception as e:
                        st.error(f"Gemini API Error: {str(e)}")
                        answer = f"Error communicating with Gemini. Falling back to local search:\n\n{local_heuristic_engine(user_input)}"
                else:
                    answer = local_heuristic_engine(user_input)
                    
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

    # Suggested Queries buttons
    st.markdown("---")
    st.markdown("💡 **Suggested Questions**")
    sug_col1, sug_col2, sug_col3 = st.columns(3)
    
    with sug_col1:
        if st.button("Generate Close Summary Report", use_container_width=True):
            st.session_state.chat_query = "Give me a summary of the financial close report and list the primary exceptions."
            st.rerun()
            
    with sug_col2:
        if st.button("Audit Transaction pay_24716857", use_container_width=True):
            st.session_state.chat_query = "Provide a complete audit and explanation for transaction pay_24716857."
            st.rerun()
            
    with sug_col3:
        if st.button("Explain bank settlement errors", use_container_width=True):
            st.session_state.chat_query = "What are the settlement discrepancies logged on the bank statement?"
            st.rerun()