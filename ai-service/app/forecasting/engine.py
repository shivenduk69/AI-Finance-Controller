import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_cash_forecast(df_rp: pd.DataFrame, df_bank: pd.DataFrame, days=7, gateway_fee_rate=0.02, gst_rate=0.18, payout_fee=5.0):
    """Generates an N-day rolling cash flow forecast combining:
    - Days 1-2 (T+1 and T+2): Fully committed settlements queued from gateway.
    - Days 3+: Projected collections, payouts, and fee deductions using rolling daily averages.
    """
    df_rp_clean = df_rp.copy()
    if not df_rp_clean.empty and 'timestamp' in df_rp_clean.columns:
        df_rp_clean['timestamp_dt'] = pd.to_datetime(df_rp_clean['timestamp'], format="%d-%m-%Y %H:%M", errors='coerce')
    else:
        expected_dts = pd.to_datetime(df_rp_clean.get('expected_settlement_date', pd.Series()), format="%d-%m-%Y", errors='coerce')
        timestamps = []
        for idx in range(len(df_rp_clean)):
            edt = expected_dts.iloc[idx] if idx < len(expected_dts) else None
            if pd.isna(edt) or edt is None:
                timestamps.append(datetime.now())
            else:
                timestamps.append(edt - timedelta(days=2))
        df_rp_clean['timestamp_dt'] = timestamps

    settlement_dates = []
    for idx, row in df_rp_clean.iterrows():
        dt = row.get('timestamp_dt')
        if pd.isna(dt):
            settlement_dates.append(None)
        elif row.get('type') == 'PAYMENT':
            settlement_dates.append(dt + timedelta(days=2))
        else:
            settlement_dates.append(dt)
            
    df_rp_clean['expected_settlement_dt'] = settlement_dates
    df_rp_clean['expected_settlement_date_str'] = df_rp_clean['expected_settlement_dt'].apply(
        lambda x: x.strftime("%d-%m-%Y") if not pd.isna(x) and x is not None else ""
    )
    
    # 2. Determine forecast start date
    df_bank_clean = df_bank.copy()
    if not df_bank_clean.empty and 'date' in df_bank_clean.columns:
        df_bank_clean['date_dt'] = pd.to_datetime(df_bank_clean['date'], format="%d-%m-%Y", errors='coerce')
    else:
        df_bank_clean['date_dt'] = pd.Series(dtype='datetime64[ns]')
        
    if not df_bank_clean.empty and not df_bank_clean['date_dt'].isna().all():
        latest_bank_date = df_bank_clean['date_dt'].max()
    elif not df_rp_clean.empty and not df_rp_clean['timestamp_dt'].isna().all():
        latest_bank_date = df_rp_clean['timestamp_dt'].max()
    else:
        latest_bank_date = datetime.now()
        
    start_date = latest_bank_date + timedelta(days=1)
    
    # 3. Calculate historical daily averages (using active days)
    df_captured = df_rp_clean[df_rp_clean['status'].isin(['captured', 'processed', 'completed'])].copy()
    
    if not df_captured.empty:
        df_captured['date_only'] = df_captured['timestamp_dt'].dt.date
        daily_groups = df_captured.groupby(['date_only', 'type'])['amount_inr'].sum().unstack(fill_value=0.0)
        
        avg_payment = daily_groups.get('PAYMENT', pd.Series([0.0])).mean()
        avg_refund = daily_groups.get('REFUND', pd.Series([0.0])).mean()
        avg_payout = daily_groups.get('PAYOUT', pd.Series([0.0])).mean()
    else:
        avg_payment = 8000.00
        avg_refund = 500.00
        avg_payout = 1500.00
        
    if pd.isna(avg_payment) or avg_payment == 0:
        avg_payment = 8000.00
    if pd.isna(avg_refund):
        avg_refund = 500.00
    if pd.isna(avg_payout):
        avg_payout = 1500.00
        
    # 4. Generate the N-day forecast list
    forecast_records = []
    
    if not df_bank_clean.empty and 'amount_inr' in df_bank_clean.columns:
        current_cash = float(df_bank_clean['amount_inr'].sum())
        if current_cash <= 0:
            current_cash = 75000.00
    else:
        current_cash = 75000.00
        
    for i in range(days):
        forecast_dt = start_date + timedelta(days=i)
        forecast_date_str = forecast_dt.strftime("%d-%m-%Y")
        
        day_rp_txs = df_rp_clean[df_rp_clean['expected_settlement_date_str'] == forecast_date_str]
        
        committed_payments = 0.0
        committed_refunds = 0.0
        committed_payouts = 0.0
        committed_fees_gst = 0.0
        
        for _, row in day_rp_txs.iterrows():
            if row.get('status') in ['captured', 'processed']:
                amt = float(row.get('amount_inr', 0.0))
                fee_tax = float(row.get('fee_inr', 0.0)) + float(row.get('tax_inr', 0.0))
                t_type = row.get('type')
                
                if t_type == 'PAYMENT':
                    committed_payments += amt
                    committed_fees_gst += fee_tax
                elif t_type == 'REFUND':
                    committed_refunds += amt
                    committed_fees_gst += fee_tax
                elif t_type == 'PAYOUT':
                    committed_payouts += amt
                    committed_fees_gst += fee_tax
                    
        is_committed = (i < 2)
        
        if is_committed:
            payments = committed_payments
            refunds = committed_refunds
            payouts = committed_payouts
            fees_gst = committed_fees_gst
            status_label = "COMMITTED (T+2 queue)"
        else:
            payments = float(avg_payment)
            refunds = float(avg_refund)
            payouts = float(avg_payout)
            eff_fee_rate = float(gateway_fee_rate) * (1.0 + float(gst_rate))
            eff_payout_fee = float(payout_fee) * (1.0 + float(gst_rate))
            fees_gst = (payments * eff_fee_rate) + ((payouts > 0) * eff_payout_fee) + (refunds * eff_fee_rate)
            status_label = "PROJECTED (Daily Average)"
            
        net_inflow = payments - refunds - payouts - fees_gst
        current_cash += net_inflow
        
        forecast_records.append({
            'date': forecast_date_str,
            'status': status_label,
            'gross_collections': round(float(payments), 2),
            'refunds': round(float(refunds), 2),
            'payouts': round(float(payouts), 2),
            'fees_gst': round(float(fees_gst), 2),
            'net_inflow': round(float(net_inflow), 2),
            'cumulative_cash': round(float(current_cash), 2)
        })
        
    return pd.DataFrame(forecast_records)
