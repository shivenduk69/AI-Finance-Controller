from fastapi import APIRouter
from app.api.reconciliation import router as reconciliation_router
from app.api.tax import router as tax_router
from app.api.forecasting import router as forecasting_router
from app.api.rag import router as rag_router

api_router = APIRouter(prefix="/internal")

api_router.include_router(reconciliation_router, tags=["Reconciliation"])
api_router.include_router(tax_router, tags=["Tax Audit"])
api_router.include_router(forecasting_router, tags=["Cash Forecasting"])
api_router.include_router(rag_router, tags=["AI Financial Assistant"])
