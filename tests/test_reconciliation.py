import unittest
import pandas as pd
from src.reconciliation import run_3way_reconciliation

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

if __name__ == '__main__':
    unittest.main()
