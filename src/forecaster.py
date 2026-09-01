import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_cash_forecast(df_rp, df_bank, days=7, gateway_fee_rate=0.02, gst_rate=0.18, payout_fee=5.0):
    """
    Generates a cash flow forecast using dynamic gateway fee and tax configuration.
    """
    # 1. Preprocess dates
    df_rp_clean = df_rp.copy()
    if 'timestamp' in df_rp_clean.columns:
        df_rp_clean['timestamp_dt'] = pd.to_datetime(df_rp_clean['timestamp'], format="%d-%m-%Y %H:%M", errors='coerce')
    else:
        # Construct dummy timestamp from expected_settlement_date
        expected_dts = pd.to_datetime(df_rp_clean['expected_settlement_date'], format="%d-%m-%Y", errors='coerce')
        timestamps = []
        for idx, row in df_rp_clean.iterrows():
            edt = expected_dts.iloc[idx]
            if pd.isna(edt):
                timestamps.append(datetime.now())
            else:
                timestamps.append(edt - timedelta(days=2))
        df_rp_clean['timestamp_dt'] = timestamps

    settlement_dates = []
    for idx, row in df_rp_clean.iterrows():
        dt = row['timestamp_dt']
        if pd.isna(dt):
            settlement_dates.append(None)
        elif row['type'] == 'PAYMENT':
            settlement_dates.append(dt + timedelta(days=2))
        else:
            settlement_dates.append(dt)
            
    df_rp_clean['expected_settlement_dt'] = settlement_dates
    df_rp_clean['expected_settlement_date_str'] = df_rp_clean['expected_settlement_dt'].apply(
        lambda x: x.strftime("%d-%m-%Y") if not pd.isna(x) else ""
    )
    
    # 2. Determine forecast start date
    df_bank_clean = df_bank.copy()
    df_bank_clean['date_dt'] = pd.to_datetime(df_bank_clean['date'], format="%d-%m-%Y", errors='coerce')
    
    # Find latest bank date or fall back to latest transaction date
    if not df_bank_clean.empty and not df_bank_clean['date_dt'].isna().all():
        latest_bank_date = df_bank_clean['date_dt'].max()
    elif not df_rp_clean.empty and not df_rp_clean['timestamp_dt'].isna().all():
        latest_bank_date = df_rp_clean['timestamp_dt'].max()
    else:
        latest_bank_date = datetime.now()
        
    start_date = latest_bank_date + timedelta(days=1)
    
    # 3. Calculate historical daily averages (using active days)
    # Filter for successful transactions
    df_captured = df_rp_clean[df_rp_clean['status'].isin(['captured', 'processed', 'completed'])]
    
    # Group by transaction date (day only)
    df_captured['date_only'] = df_captured['timestamp_dt'].dt.date
    daily_groups = df_captured.groupby(['date_only', 'type'])['amount_inr'].sum().unstack(fill_value=0.0)
    
    if len(daily_groups) > 0:
        avg_payment = daily_groups.get('PAYMENT', pd.Series([0.0])).mean()
        avg_refund = daily_groups.get('REFUND', pd.Series([0.0])).mean()
        avg_payout = daily_groups.get('PAYOUT', pd.Series([0.0])).mean()
    else:
        # Fallbacks if no data is found
        avg_payment = 8000.00
        avg_refund = 500.00
        avg_payout = 1500.00
        
    # Standard fallback safety limits
    if pd.isna(avg_payment) or avg_payment == 0: avg_payment = 8000.00
    if pd.isna(avg_refund): avg_refund = 500.00
    if pd.isna(avg_payout): avg_payout = 1500.00
    
    # 4. Generate the N-day forecast list
    forecast_records = []
    
    # Let's assume a baseline starting cash in the bank (e.g. from bank statement total net or Rs. 50,000 base)
    if not df_bank_clean.empty:
        # Sum of actual deposits minus withdrawals (if any negative settled amount is withdrawal)
        current_cash = df_bank_clean['amount_inr'].sum()
        if current_cash <= 0:
            current_cash = 75000.00  # Default premium treasury base
    else:
        current_cash = 75000.00
        
    for i in range(days):
        forecast_dt = start_date + timedelta(days=i)
        forecast_date_str = forecast_dt.strftime("%d-%m-%Y")
        
        # Check if we have committed transactions for this expected settlement date
        day_rp_txs = df_rp_clean[df_rp_clean['expected_settlement_date_str'] == forecast_date_str]
        
        committed_payments = 0.0
        committed_refunds = 0.0
        committed_payouts = 0.0
        committed_fees_gst = 0.0
        
        # Separating committed values
        for _, row in day_rp_txs.iterrows():
            if row['status'] in ['captured', 'processed']:
                if row['type'] == 'PAYMENT':
                    committed_payments += row['amount_inr']
                    committed_fees_gst += (row['fee_inr'] + row['tax_inr'])
                elif row['type'] == 'REFUND':
                    committed_refunds += row['amount_inr']
                    committed_fees_gst += (row['fee_inr'] + row['tax_inr'])
                elif row['type'] == 'PAYOUT':
                    committed_payouts += row['amount_inr']
                    committed_fees_gst += (row['fee_inr'] + row['tax_inr'])
        
        # Determine if we rely on committed or projected data
        # Payments settle T+2, so T+1 and T+2 are fully committed.
        # Day 1 & Day 2 (index 0 and 1) are committed.
        # Payouts/Refunds settle T+0, so in future days they are projected since we can't know future payouts.
        is_committed = (i < 2)
        
        if is_committed:
            payments = committed_payments
            refunds = committed_refunds
            payouts = committed_payouts
            fees_gst = committed_fees_gst
            status_label = "COMMITTED (T+2 queue)"
        else:
            payments = avg_payment
            refunds = avg_refund
            payouts = avg_payout
            # Estimate fees using dynamic configured rates
            eff_fee_rate = float(gateway_fee_rate) * (1.0 + float(gst_rate))
            eff_payout_fee = float(payout_fee) * (1.0 + float(gst_rate))
            fees_gst = (payments * eff_fee_rate) + ((payouts > 0) * eff_payout_fee) + (refunds * eff_fee_rate)
            status_label = "PROJECTED (Daily Average)"
            
        net_inflow = payments - refunds - payouts - fees_gst
        current_cash += net_inflow
        
        forecast_records.append({
            'date': forecast_date_str,
            'status': status_label,
            'gross_collections': round(payments, 2),
            'refunds': round(refunds, 2),
            'payouts': round(payouts, 2),
            'fees_gst': round(fees_gst, 2),
            'net_inflow': round(net_inflow, 2),
            'cumulative_cash': round(current_cash, 2)
        })
        
    return pd.DataFrame(forecast_records)
