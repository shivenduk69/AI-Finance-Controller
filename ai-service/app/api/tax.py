from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import pandas as pd
import numpy as np
from app.core.security import verify_internal_secret
from app.core.database import load_financial_data
from app.tax.engine import run_tax_audit, DEFAULT_TDS_CONFIG

router = APIRouter(dependencies=[Depends(verify_internal_secret)])

class TaxAuditRequest(BaseModel):
    merchant_id: Optional[str] = None
    store_id: Optional[str] = None
    tds_config: Optional[Dict[str, Any]] = None

def clean_dataframe_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Converts a DataFrame to a list of dicts, converting all NaN/NaT values to JSON-safe None."""
    if df.empty:
        return []
    records = []
    for row in df.to_dict('records'):
        clean_row = {}
        for k, v in row.items():
            if isinstance(v, (list, dict, tuple)):
                clean_row[k] = v
            elif v is None:
                clean_row[k] = None
            elif isinstance(v, (float, np.floating)) and np.isnan(v):
                clean_row[k] = None
            elif pd.isna(v):
                clean_row[k] = None
            else:
                clean_row[k] = v
        records.append(clean_row)
    return records

@router.post("/tax/audit")
def audit_taxes(payload: TaxAuditRequest):
    """Audits Section 194-O TDS deductions and 18% GST calculations for transactions."""
    df_rp, _, _ = load_financial_data(payload.merchant_id, payload.store_id)
    tds_cfg = payload.tds_config if payload.tds_config else DEFAULT_TDS_CONFIG
    
    summary, df_audited = run_tax_audit(df_rp, tds_config=tds_cfg)
    audited_list = clean_dataframe_records(df_audited)
    
    return {
        "success": True,
        "summary": summary,
        "audited_records": audited_list
    }
