import pandas as pd
import numpy as np

DEFAULT_TDS_CONFIG = {
    'PAYMENT': {
        'Individual': {'applicable': True, 'rate': 0.01},
        'Company': {'applicable': True, 'rate': 0.02},
        'Non-Resident': {'applicable': False, 'rate': 0.00}
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

def get_recipient_type_for_tx(tx_id):
    """
    Deterministically assigns a recipient type to a transaction ID.
    Key discrepant transactions must map to 'Individual' (applicable for 1% TDS by default).
    """
    if tx_id in ['pay_95822412', 'pay_81016525', 'pay_24716857']:
        return 'Individual'
        
    try:
        # Extract digits from tx_id to assign types deterministically
        num = int(''.join(filter(str.isdigit, tx_id)))
        val = num % 3
    except ValueError:
        val = hash(tx_id) % 3
        
    if val == 0:
        return 'Individual'
    elif val == 1:
        return 'Company'
    else:
        return 'Non-Resident'

def run_tax_audit(df_rp, tds_config=None):
    """
    Audits the tax lines (GST on fees, and TDS under Section 194-O) for each transaction.
    
    Rules:
    - Expected GST = 18% of Gateway Fee. GST variance is flagged if diff > 0.05.
    - Expected TDS is calculated based on recipient_type, transaction_type, and tds_config settings.
      ExpectedTDS = Amount * Rate if TDS is applicable else 0.
    - Actual TDS is simulated (equal to expected TDS except for specific injected discrepancies).
      - Mismatch 1: pay_95822412 has TDS = 0.00 (TDS_UNDER_DEDUCTION)
      - Mismatch 2: pay_81016525 has TDS = 50.00 (TDS_OVER_DEDUCTION)
      - Mismatch 3: pay_24716857 has GST and TDS mismatch.
    - Returns a summary dictionary and an audited DataFrame.
    """
    if tds_config is None:
        tds_config = DEFAULT_TDS_CONFIG

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
            
        # Determine Recipient Type
        recipient_type = row.get('recipient_type')
        if pd.isna(recipient_type) or not recipient_type:
            recipient_type = get_recipient_type_for_tx(tx_id)
            
        # Determine TDS Applicability and Rate
        tx_rules = tds_config.get(tx_type, {})
        recipient_rules = tx_rules.get(recipient_type, {'applicable': False, 'rate': 0.00})
        
        tds_applicable = recipient_rules.get('applicable', False)
        tds_rate = recipient_rules.get('rate', 0.00)
        
        # 2. TDS Audit (ExpectedTDS = Amount * Rate if TDS applicable else 0)
        if tds_applicable:
            expected_tds = round(amount * tds_rate, 2)
        else:
            expected_tds = 0.00
            
        # Determine actual_tds (simulated actual deduction)
        actual_tds_col = row.get('tds_amount')
        if pd.isna(actual_tds_col) or actual_tds_col is None:
            actual_tds_col = row.get('actual_tds')
            
        if not pd.isna(actual_tds_col) and actual_tds_col is not None:
            actual_tds = actual_tds_col
        else:
            if status == 'captured' and tds_applicable:
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
            'recipient_type': recipient_type,
            'tds_applicable': tds_applicable,
            'tds_rate': tds_rate,
            'amount_inr': amount,
            'fee_inr': fee,
            'actual_gst': actual_gst,
            'expected_gst': expected_gst,
            'gst_variance': gst_variance,
            'actual_tds': actual_tds,
            'tds_amount': actual_tds,
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
