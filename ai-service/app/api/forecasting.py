from typing import Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.security import verify_internal_secret
from app.core.database import load_financial_data
from app.forecasting.engine import get_cash_forecast

router = APIRouter(dependencies=[Depends(verify_internal_secret)])

class CashForecastRequest(BaseModel):
    merchant_id: Optional[str] = None
    store_id: Optional[str] = None
    days: int = Field(default=7, ge=1, le=60)
    gateway_fee_rate: float = Field(default=0.02, ge=0.0, le=1.0)
    gst_rate: float = Field(default=0.18, ge=0.0, le=1.0)
    payout_fee: float = Field(default=5.0, ge=0.0)

@router.post("/forecast/cashflow")
def forecast_cashflow(payload: CashForecastRequest):
    """Generates rolling cash flow projections based on T+2 committed queue and daily averages."""
    df_rp, _, df_bank = load_financial_data(payload.merchant_id, payload.store_id)
    
    df_forecast = get_cash_forecast(
        df_rp=df_rp,
        df_bank=df_bank,
        days=payload.days,
        gateway_fee_rate=payload.gateway_fee_rate,
        gst_rate=payload.gst_rate,
        payout_fee=payload.payout_fee
    )
    
    forecast_list = df_forecast.to_dict('records') if not df_forecast.empty else []
    
    return {
        "success": True,
        "days": payload.days,
        "data": forecast_list
    }
