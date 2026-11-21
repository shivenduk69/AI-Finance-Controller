from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
from app.core.security import verify_internal_secret
from app.reconciliation.engine import run_3way_reconciliation

router = APIRouter(dependencies=[Depends(verify_internal_secret)])

class ReconciliationRequest(BaseModel):
    merchant_id: Optional[str] = None
    store_id: Optional[str] = None
    gateway_fee_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    gst_rate: float = Field(default=0.18, ge=0.0, le=1.0)
    payout_fee: float = Field(default=5.0, ge=0.0)
    settlement_delay_days: int = Field(default=2, ge=0, le=30)

def clean_dataframe_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Converts a DataFrame to a list of dicts, converting all NaN/NaT values to JSON-safe None."""
    if df.empty:
        return []
    records = []
    for row in df.to_dict('records'):
        clean_row = {}
        for k, v in row.items():
            if k in ('date_dt', 'timestamp_dt', 'created_at_dt', 'expected_settlement_dt'):
                continue
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

@router.post("/reconciliation/run")
def trigger_reconciliation(payload: ReconciliationRequest):
    """Executes deterministic 3-way reconciliation across gateway, orders, and bank records."""
    summary, df_tx, df_unmatched, df_bank, bank_excs = run_3way_reconciliation(
        merchant_id=payload.merchant_id,
        store_id=payload.store_id,
        gateway_fee_rate=payload.gateway_fee_rate,
        gst_rate=payload.gst_rate,
        payout_fee=payload.payout_fee,
        settlement_delay_days=payload.settlement_delay_days
    )
    
    tx_list = clean_dataframe_records(df_tx)
    unmatched_list = clean_dataframe_records(df_unmatched)
    bank_clean = clean_dataframe_records(df_bank)
        
    return {
        "success": True,
        "summary": summary,
        "transactions": tx_list,
        "unmatched_orders": unmatched_list,
        "bank_reconciled": bank_clean,
        "bank_exceptions": bank_excs
    }
