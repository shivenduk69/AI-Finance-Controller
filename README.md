# AI Finance Controller - Multi-Source Reconciliation Agent

An automated, intelligent financial reconciliation agent that performs 3-way matching across internal merchant orders, payment gateway (Razorpay) reports, and bank statements. The system isolates fee anomalies, metadata mismatches, missing bank credits, and unresolved payment status variances, presenting them in a premium visual dashboard with a built-in generative AI auditor.

---

## 📂 Directory Structure

The project directory is structured as follows:

```text
AI Finance Controller/
├── data/                               # Data folder containing synthetic CSV files
│   ├── razorpay_synthetic_buildathon_data.csv  # Raw gateway transactions (provided)
│   ├── internal_orders.csv            # Merchant orders ledger (generated)
│   └── bank_statement.csv             # Bank statement settlements (generated)
├── src/                                # Core logic package
│   ├── __init__.py
│   ├── reconciliation.py               # 3-way rules reconciliation engine
│   └── mock_generator.py               # Synthetic orders and bank statements generator
├── tests/                              # Automated test suite package
│   ├── __init__.py
│   └── test_reconciliation.py          # Unit tests checking mathematical audit rules
├── app.py                              # Main Streamlit web application entry point
├── requirements.txt                    # List of third-party python dependencies
├── .gitignore                          # Standard git ignore definitions
└── README.md                           # Documentation (this file)
```

---

## ⚙️ Requirements & Installation

1. Clone or copy the project files to your system.
2. Install the required python packages:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 Running the Project

### 1. Generate Synthetic Data
Generate the merchant orders database and bank statement deposits based on the Razorpay gateway transaction list:
```bash
python src/mock_generator.py
```
This will populate `data/internal_orders.csv` and `data/bank_statement.csv` with simulated discrepancies (e.g. amount mismatches, omitted deposits, and status variances).

### 2. Run Automated Verification Tests
Verify the mathematical checks and reconciliation engine using the test suite:
```bash
python -m unittest tests/test_reconciliation.py
```

### 3. Launch the Streamlit Dashboard
Run the web application locally:
```bash
streamlit run app.py
```
Once the server initializes, open **`http://localhost:8501`** in your browser.

---

## 🤖 AI Financial Assistant Configuration

The dashboard includes a conversational **AI Financial Assistant** in Tab 4, allowing you to ask queries such as:
- *"Give me a summary of the daily close report."*
- *"Why did transaction pay_24716857 fail reconciliation?"*
- *"Explain the settlement issues on August 10 and 18."*

To enable generative answers:
1. Provide your **Google Gemini API Key** in the Sidebar password input field.
2. If no key is provided, the dashboard automatically falls back to a **local rule-based heuristic search engine** to ensure full diagnostic functionality.

---

## ☁️ Deployment

This application is ready to deploy directly to cloud hosting platforms:
- **Streamlit Community Cloud**: Connect this repository to Streamlit Community Cloud for instant public/private deployment. Set `GEMINI_API_KEY` as a Streamlit Secret.
- **Docker**: Containerize by adding a basic `Dockerfile` installing the `requirements.txt` dependencies and executing `ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]`.
