import os
import sys
import pytest
import pandas as pd
import numpy as np

# Add project root and ai-service to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_SERVICE_DIR = os.path.join(PROJECT_ROOT, "ai-service")
if AI_SERVICE_DIR not in sys.path:
    sys.path.insert(0, AI_SERVICE_DIR)

from app.reconciliation.engine import run_3way_reconciliation
from app.tax.engine import run_tax_audit
from app.forecasting.engine import get_cash_forecast
from app.core.database import load_financial_data

class TestMigrationParity:
    """Rigorous mathematical parity verification ensuring the migrated 
    AI & Data Processing microservice matches baseline truth values to the exact penny (₹0.00 delta).
    """

    def test_dataset_loading_parity(self):
        """Verify that PostgreSQL dataset loaded by AI Service matches expected counts."""
        ai_rp, ai_orders, ai_bank = load_financial_data()

        assert len(ai_rp) == 120, "Total transactions count must equal 120"
        assert len(ai_orders) == 89, "Internal orders count must equal 89"
        assert len(ai_bank) == 83, "Bank statements count must equal 83"

    def test_3way_reconciliation_summary_parity(self):
        """Verify that 3-way reconciliation summary KPIs match baseline truth to the exact penny (₹0.00 delta)."""
        summary, txs, unmatched, bank_reconciled, bank_excs = run_3way_reconciliation(
            gateway_fee_rate=0.02, gst_rate=0.18, settlement_delay_days=2
        )

        # 1. Counts parity
        assert summary["total_transactions"] == 120
        assert summary["total_payments_processed"] == 90
        assert summary["auto_resolved_count"] == 84
        assert summary["needs_review_count"] == 38
        assert abs(summary["auto_match_accuracy_pct"] - 68.9) < 0.1

        # 2. Financial Amount Parity (to the exact penny)
        assert abs(summary["gross_collections_inr"] - 196373.71) < 0.01, \
            f"Gross collections mismatch: ₹{summary['gross_collections_inr']}"

        assert abs(summary["refunds_inr"] - 42720.96) < 0.01, \
            f"Refunds mismatch: ₹{summary['refunds_inr']}"

        assert abs(summary["fees_gst_inr"] - 5576.10) < 0.01, \
            f"Fees & GST mismatch: ₹{summary['fees_gst_inr']}"

        assert abs(summary["settled_to_bank_inr"] - 123016.09) < 0.01, \
            f"Bank settled mismatch: ₹{summary['settled_to_bank_inr']}"

        assert abs(summary["expected_next_2_days_inr"] - 16681.47) < 0.01, \
            f"Expected next 2 days mismatch: ₹{summary['expected_next_2_days_inr']}"

    def test_transaction_level_detail_parity(self):
        """Verify that key exception transactions are classified with exact mathematical accuracy."""
        _, ai_df, _, _, _ = run_3way_reconciliation()
        ai_txs = ai_df.set_index("transaction_id")

        assert len(ai_txs) == 120

        # Disputed transaction check
        if "pay_39587039" in ai_txs.index:
            row = ai_txs.loc["pay_39587039"]
            assert row["resolution_status"] == "NEEDS_REVIEW"
            assert any("INTERNAL_AMOUNT_MISMATCH" in str(e) for e in row["calculated_exceptions"])

    def test_multi_tenant_reconciliation_parity(self):
        """Verify that tenant-scoped reconciliation matches partition baselines."""
        # Flipkart partition
        fk_sum, _, _, _, _ = run_3way_reconciliation(merchant_id="flipkart")
        assert fk_sum["total_transactions"] == 60
        assert abs(fk_sum["gross_collections_inr"] - 90843.89) < 0.01

        # Amazon partition
        az_sum, _, _, _, _ = run_3way_reconciliation(merchant_id="amazon")
        assert az_sum["total_transactions"] == 60

    def test_tax_audit_parity(self):
        """Verify Section 194-O TDS & GST compliance calculation matches baseline."""
        ai_rp, _, _ = load_financial_data()
        a_summary, a_df = run_tax_audit(ai_rp)

        assert a_summary["total_audited_records"] == 120
        assert a_summary["total_tax_discrepancies"] == 11
        assert abs(a_summary["tax_compliance_pct"] - 90.8) < 0.1
        assert abs(a_summary["total_gst_collected_inr"] - 838.32) < 0.01
        assert abs(a_summary["total_tds_deducted_inr"] - 1761.56) < 0.01

        # Check injected tax discrepancy flags
        records = a_df.set_index("transaction_id")
        assert records.loc["pay_95822412"]["tax_status"] == "TDS_UNDER_DEDUCTION"
        assert records.loc["pay_81016525"]["tax_status"] == "TDS_OVER_DEDUCTION"

    def test_cash_forecasting_parity(self):
        """Verify 7-day rolling cash flow projection matches baseline."""
        ai_rp, _, ai_bank = load_financial_data()
        a_df = get_cash_forecast(ai_rp, ai_bank, days=7)

        assert len(a_df) == 7
        # Day 1 and 2 must be committed
        assert "COMMITTED" in a_df.iloc[0]["status"]
        assert "COMMITTED" in a_df.iloc[1]["status"]
        # Day 3+ must be projected
        assert "PROJECTED" in a_df.iloc[2]["status"]
