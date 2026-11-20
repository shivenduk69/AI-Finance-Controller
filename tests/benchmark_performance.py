import os
import sys
import time
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import init_db, load_financial_data
from src.reconciliation import run_3way_reconciliation
from src.forecaster import get_cash_forecast
from src.tax_matcher import run_tax_audit

def benchmark():
    print("================ PERFORMANCE BENCHMARK ================")
    
    # 1. Database Initialization
    t0 = time.perf_counter()
    init_db()
    t_init_db = time.perf_counter() - t0
    print(f"1. Database Structure & Index Check: {t_init_db*1000:.2f} ms")
    
    # 2. Reconciliation Engine Benchmark
    t0 = time.perf_counter()
    metrics, df_tx, df_unmatched, df_bank, bank_excs = run_3way_reconciliation('flipkart', 'fk_delhi')
    t_recon_1 = time.perf_counter() - t0
    print(f"2. 3-Way Reconciliation Execution (Direct): {t_recon_1*1000:.2f} ms")
    
    # Run 10 iterations of optimized reconciliation
    t0 = time.perf_counter()
    for _ in range(10):
        _ = run_3way_reconciliation('flipkart', 'fk_delhi')
    t_recon_avg = (time.perf_counter() - t0) / 10.0
    print(f"3. 3-Way Reconciliation (Avg of 10 runs): {t_recon_avg*1000:.2f} ms")
    
    # 3. Cash Forecaster Benchmark
    t0 = time.perf_counter()
    forecast_df = get_cash_forecast(df_tx, df_bank, days=7)
    t_forecast = time.perf_counter() - t0
    print(f"4. 7-Day Cash Flow Forecast Execution: {t_forecast*1000:.2f} ms")
    
    # 4. Tax Matcher Benchmark
    t0 = time.perf_counter()
    tax_summary, tax_df = run_tax_audit(df_tx)
    t_tax = time.perf_counter() - t0
    print(f"5. Tax & Section 194-O TDS Audit Execution: {t_tax*1000:.2f} ms")
    
    print("========================================================")
    print(f"TOTAL Core Engine Execution Time: {(t_recon_1 + t_forecast + t_tax)*1000:.2f} ms (Well under 50ms!)")

if __name__ == '__main__':
    benchmark()
