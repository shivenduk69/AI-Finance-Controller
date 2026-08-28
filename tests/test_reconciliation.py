import unittest
import pandas as pd
from src.reconciliation import run_3way_reconciliation
from src.forecaster import get_cash_forecast
from src.tax_matcher import run_tax_audit

class TestReconciliation(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Run reconciliation once for all tests
        cls.metrics, cls.df_tx, cls.df_unmatched, cls.df_bank, cls.bank_excs = run_3way_reconciliation()
        
    def test_metrics_integrity(self):
        # Verify metric keys are present
        keys = [
            'total_payments_processed', 'total_transactions', 
            'auto_resolved_count', 'needs_review_count', 
            'auto_match_accuracy_pct', 'gross_collections_inr', 
            'refunds_inr', 'fees_gst_inr', 'settled_to_bank_inr', 
            'expected_next_2_days_inr', 'unreconciled_review_inr'
        ]
        for key in keys:
            self.assertIn(key, self.metrics)
            
        # Total payments in Razorpay synthetic data must be 45
        self.assertEqual(self.metrics['total_payments_processed'], 45)
        self.assertEqual(self.metrics['total_transactions'], 60)
        
    def test_original_gateway_exceptions(self):
        # Verify the 5 original gateway exceptions are caught
        needs_review_txids = self.df_tx[self.df_tx['resolution_status'] == 'NEEDS_REVIEW']['transaction_id'].tolist()
        
        # 1 & 2: Fee/Settlement Mismatches
        self.assertIn('pay_24716857', needs_review_txids)
        self.assertIn('pay_16789850', needs_review_txids)
        
        # 3 & 4: Missing Order IDs
        self.assertIn('pay_99639081', needs_review_txids)
        self.assertIn('pay_33357554', needs_review_txids)
        
        # 5: Disputed transaction
        self.assertIn('pay_92228802', needs_review_txids)
        
    def test_internal_order_discrepancies(self):
        # 1. Amount mismatch on order_70291817 (TX: pay_39587039)
        pay_amt_mismatch = self.df_tx[self.df_tx['transaction_id'] == 'pay_39587039'].iloc[0]
        self.assertEqual(pay_amt_mismatch['resolution_status'], 'NEEDS_REVIEW')
        self.assertTrue(any('INTERNAL_AMOUNT_MISMATCH' in e for e in pay_amt_mismatch['calculated_exceptions']))
        
        # 2. Status mismatch on order_38898923 (TX: pay_30868105)
        pay_stat_mismatch = self.df_tx[self.df_tx['transaction_id'] == 'pay_30868105'].iloc[0]
        self.assertEqual(pay_stat_mismatch['resolution_status'], 'NEEDS_REVIEW')
        self.assertTrue(any('INTERNAL_STATUS_MISMATCH' in e for e in pay_stat_mismatch['calculated_exceptions']))
        
        # 3. Unmatched internal order (order_99999999)
        unmatched_ids = self.df_unmatched['order_id'].tolist()
        self.assertIn('order_99999999', unmatched_ids)
        
    def test_bank_statement_discrepancies(self):
        # 1. Settlement mismatch on 10-08-2026 (expected deposit diff = -100)
        bank_10 = self.df_bank[self.df_bank['date'] == '10-08-2026'].iloc[0]
        self.assertEqual(bank_10['status'], 'SETTLEMENT_AMOUNT_MISMATCH')
        self.assertAlmostEqual(bank_10['difference'], -100.00, places=2)
        
        # 2. Omitted settlement batch on 18-08-2026 (missing bank credit)
        bank_18 = self.df_bank[self.df_bank['date'] == '18-08-2026'].iloc[0]
        self.assertEqual(bank_18['status'], 'MISSING_BANK_CREDIT')
        self.assertAlmostEqual(bank_18['difference'], -4407.40, places=2)
    def test_cash_forecaster(self):
        forecast_df = get_cash_forecast(self.df_tx, self.df_bank, days=7)
        self.assertEqual(len(forecast_df), 7)
        self.assertIn('date', forecast_df.columns)
        self.assertIn('gross_collections', forecast_df.columns)
        self.assertIn('net_inflow', forecast_df.columns)
        self.assertIn('cumulative_cash', forecast_df.columns)
        # Cumulative cash should reflect treasury change
        self.assertNotEqual(forecast_df.iloc[-1]['cumulative_cash'], forecast_df.iloc[0]['cumulative_cash'])
        
    def test_tax_matcher(self):
        tax_summary, tax_df = run_tax_audit(self.df_tx)
        self.assertIn('total_audited_records', tax_summary)
        self.assertIn('gst_anomalies_count', tax_summary)
        self.assertIn('tds_anomalies_count', tax_summary)
        self.assertIn('tax_compliance_pct', tax_summary)
        
        # Test simulated TDS discrepancies
        # pay_95822412 should have TDS_UNDER_DEDUCTION
        tx_958 = tax_df[tax_df['transaction_id'] == 'pay_95822412'].iloc[0]
        self.assertEqual(tx_958['tax_status'], 'TDS_UNDER_DEDUCTION')
        
        # pay_81016525 should have TDS_OVER_DEDUCTION
        tx_810 = tax_df[tax_df['transaction_id'] == 'pay_81016525'].iloc[0]
        self.assertEqual(tx_810['tax_status'], 'TDS_OVER_DEDUCTION')
        
        # pay_24716857 should have MULTIPLE_TAX_ISSUES (GST mismatch + TDS mismatch)
        tx_247 = tax_df[tax_df['transaction_id'] == 'pay_24716857'].iloc[0]
        self.assertEqual(tx_247['tax_status'], 'MULTIPLE_TAX_ISSUES')

    def test_configurable_tds(self):
        # 1. Test formula correctness on default run
        tax_summary, tax_df = run_tax_audit(self.df_tx)
        
        # Check that the new columns are present
        self.assertIn('recipient_type', tax_df.columns)
        self.assertIn('tds_applicable', tax_df.columns)
        self.assertIn('tds_rate', tax_df.columns)
        self.assertIn('tds_amount', tax_df.columns)
        
        # Verify formula: ExpectedTDS = Amount * Rate if tds_applicable else 0
        for idx, row in tax_df.iterrows():
            if row['tds_applicable']:
                self.assertAlmostEqual(row['expected_tds'], round(row['amount_inr'] * row['tds_rate'], 2), places=2)
            else:
                self.assertEqual(row['expected_tds'], 0.00)
                
        # 2. Test custom configuration changes computed ExpectedTDS
        custom_config = {
            'PAYMENT': {
                'Individual': {'applicable': True, 'rate': 0.05},  # Set to 5% rate
                'Company': {'applicable': False, 'rate': 0.00},   # Disable TDS for Company
                'Non-Resident': {'applicable': True, 'rate': 0.10} # Enable for Non-Resident at 10%
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
        
        _, custom_tax_df = run_tax_audit(self.df_tx, tds_config=custom_config)
        
        for idx, row in custom_tax_df.iterrows():
            rec_type = row['recipient_type']
            tx_type = row['type']
            
            if tx_type == 'PAYMENT':
                if rec_type == 'Individual':
                    self.assertTrue(row['tds_applicable'])
                    self.assertEqual(row['tds_rate'], 0.05)
                    self.assertAlmostEqual(row['expected_tds'], round(row['amount_inr'] * 0.05, 2), places=2)
                elif rec_type == 'Company':
                    self.assertFalse(row['tds_applicable'])
                    self.assertEqual(row['expected_tds'], 0.00)
                elif rec_type == 'Non-Resident':
                    self.assertTrue(row['tds_applicable'])
                    self.assertEqual(row['tds_rate'], 0.10)
                    self.assertAlmostEqual(row['expected_tds'], round(row['amount_inr'] * 0.10, 2), places=2)
            else:
                self.assertFalse(row['tds_applicable'])
                self.assertEqual(row['expected_tds'], 0.00)

if __name__ == '__main__':
    unittest.main()
