import pandas as pd
import numpy as np

def run_tax_audit(df_rp):
    """
    Audits the tax lines (GST on fees, and TDS under Section 194-O) for each transaction.
    
    Rules:
    - Expected GST = 18% of Gateway Fee. GST variance is flagged if diff > 0.05.
    - Expected TDS = 1% of transaction amount for captured PAYMENT transactions.
    - Actual TDS is simulated (equal to expected TDS except for specific injected discrepancies).
      - Mismatch 1: pay_95822412 has TDS = 0.00 (TDS_UNDER_DEDUCTION)
      - Mismatch 2: pay_81016525 has TDS = 50.00 (TDS_OVER_DEDUCTION)
      - Mismatch 3: pay_24716857 has GST and TDS mismatch.
    - Returns a summary dictionary and an audited DataFrame.
    """
    audited_records = []
    
    gst_anomalies_count = 0
    tds_anomalies_count = 0
    
    for idx, row in df_rp.iterrows():
        tx_id = row['transaction_id']
        tx_type = row['type']
        status = row['status']
        amount = row['amount_inr']
        fee = row['fee_inr']
        actual_gst = row['tax_inr']
        
        # 1. GST Audit on Gateway Fee
        expected_gst = round(fee * 0.18, 2)
        gst_variance = round(actual_gst - expected_gst, 2)
        
        has_gst_issue = False
        if abs(gst_variance) > 0.05:
            has_gst_issue = True
            
        # 2. TDS Audit (Section 194-O: 1% of gross payment)
        if tx_type == 'PAYMENT' and status == 'captured':
            expected_tds = round(amount * 0.01, 2)
            
            # Inject simulated actual TDS with discrepancies
            if tx_id == 'pay_95822412':
                actual_tds = 0.00
            elif tx_id == 'pay_81016525':
                actual_tds = 50.00  # expected was ~36.06
            elif tx_id == 'pay_24716857':
                actual_tds = 0.00  # expected was ~34.06
            else:
                actual_tds = expected_tds
        else:
            expected_tds = 0.00
            actual_tds = 0.00
            
        tds_variance = round(actual_tds - expected_tds, 2)
        has_tds_issue = False
        if abs(tds_variance) > 0.05:
            has_tds_issue = True
            
        # Determine Tax Status & Comments
        comments = []
        if has_gst_issue:
            gst_anomalies_count += 1
            comments.append(f"GST mismatch (Expected: Rs. {expected_gst:.2f}, Actual: Rs. {actual_gst:.2f}, Var: Rs. {gst_variance:.2f})")
            
        if has_tds_issue:
            tds_anomalies_count += 1
            if tds_variance < 0:
                comments.append(f"TDS under-deducted by Rs. {abs(tds_variance):.2f} (Expected: Rs. {expected_tds:.2f}, Actual: Rs. {actual_tds:.2f})")
            else:
                comments.append(f"TDS over-deducted by Rs. {abs(tds_variance):.2f} (Expected: Rs. {expected_tds:.2f}, Actual: Rs. {actual_tds:.2f})")
                
        if has_gst_issue and has_tds_issue:
            tax_status = "MULTIPLE_TAX_ISSUES"
        elif has_gst_issue:
            tax_status = "GST_MISMATCH"
        elif has_tds_issue:
            tax_status = "TDS_UNDER_DEDUCTION" if tds_variance < 0 else "TDS_OVER_DEDUCTION"
        else:
            tax_status = "OK"
            comments.append("Tax lines reconciled successfully.")
            
        audited_records.append({
            'transaction_id': tx_id,
            'type': tx_type,
            'amount_inr': amount,
            'fee_inr': fee,
            'actual_gst': actual_gst,
            'expected_gst': expected_gst,
            'gst_variance': gst_variance,
            'actual_tds': actual_tds,
            'expected_tds': expected_tds,
            'tds_variance': tds_variance,
            'tax_status': tax_status,
            'audit_comments': "; ".join(comments)
        })
        
    df_audited = pd.DataFrame(audited_records)
    
    # Calculate summary metrics
    total_records = len(df_audited)
    total_anomalies = gst_anomalies_count + tds_anomalies_count
    tax_compliance_pct = round(((total_records - total_anomalies) / total_records) * 100, 1) if total_records > 0 else 100.0
    
    summary = {
        'total_audited_records': total_records,
        'gst_anomalies_count': gst_anomalies_count,
        'tds_anomalies_count': tds_anomalies_count,
        'total_tax_discrepancies': total_anomalies,
        'tax_compliance_pct': tax_compliance_pct,
        'total_gst_collected_inr': round(df_audited['actual_gst'].sum(), 2),
        'total_tds_deducted_inr': round(df_audited['actual_tds'].sum(), 2)
    }
    
    return summary, df_audited
