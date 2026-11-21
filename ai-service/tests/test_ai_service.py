import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add ai-service to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from app.core.config import settings

client = TestClient(app)
VALID_HEADERS = {"x-internal-secret": settings.INTERNAL_API_SECRET}

def test_healthcheck():
    """Verify healthcheck endpoint returns 200 and healthy status without auth."""
    response = client.get("/internal/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-service"

def test_internal_secret_security():
    """Verify that requests missing or with invalid internal secret are rejected with 403."""
    # Missing header
    res_missing = client.post("/internal/reconciliation/run", json={})
    assert res_missing.status_code == 403

    # Invalid header
    res_invalid = client.post("/internal/reconciliation/run", json={}, headers={"x-internal-secret": "wrong_key"})
    assert res_invalid.status_code == 403

def test_reconciliation_run():
    """Verify 3-way reconciliation endpoint runs all 7 rules and returns accurate summary."""
    response = client.post(
        "/internal/reconciliation/run",
        json={"gateway_fee_rate": 0.02, "gst_rate": 0.18, "settlement_delay_days": 2},
        headers=VALID_HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    summary = data["summary"]
    
    # Check baseline dataset numbers (120 transactions loaded in seeds)
    assert summary["total_transactions"] == 120
    assert summary["total_payments_processed"] == 90
    assert summary["gross_collections_inr"] > 0
    assert summary["settled_to_bank_inr"] > 0
    assert "auto_match_accuracy_pct" in summary
    assert len(data["transactions"]) == 120
    assert len(data["unmatched_orders"]) >= 0

def test_reconciliation_tenant_scoping():
    """Verify reconciliation respects tenant merchant_id filter."""
    response = client.post(
        "/internal/reconciliation/run",
        json={"merchant_id": "flipkart"},
        headers=VALID_HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Flipkart transactions only
    for tx in data["transactions"]:
        assert tx["merchant_id"] == "flipkart"

def test_tax_audit():
    """Verify Section 194-O TDS and 18% GST audit endpoint detects discrepancies."""
    response = client.post(
        "/internal/tax/audit",
        json={},
        headers=VALID_HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    summary = data["summary"]
    assert summary["total_audited_records"] == 120
    assert summary["total_tax_discrepancies"] > 0
    assert summary["tax_compliance_pct"] > 0
    
    # Verify injected discrepancy detection
    records = {r["transaction_id"]: r for r in data["audited_records"]}
    if "pay_95822412" in records:
        assert records["pay_95822412"]["tax_status"] in ["TDS_UNDER_DEDUCTION", "MULTIPLE_TAX_ISSUES"]
    if "pay_81016525" in records:
        assert records["pay_81016525"]["tax_status"] in ["TDS_OVER_DEDUCTION", "MULTIPLE_TAX_ISSUES"]

def test_cash_forecast():
    """Verify rolling cash flow forecast endpoint projects T+2 committed queue and daily averages."""
    response = client.post(
        "/internal/forecast/cashflow",
        json={"days": 7},
        headers=VALID_HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["days"] == 7
    forecast_rows = data["data"]
    assert len(forecast_rows) == 7
    
    # Days 0 and 1 are committed settlements
    assert "COMMITTED" in forecast_rows[0]["status"]
    assert "COMMITTED" in forecast_rows[1]["status"]
    # Days 2+ are projected settlements
    assert "PROJECTED" in forecast_rows[2]["status"]
    
    # Cumulative cash should exist and be numeric
    assert isinstance(forecast_rows[0]["cumulative_cash"], (int, float))

def test_ai_query_heuristic():
    """Verify AI Intelligence query endpoint returns financial close report via heuristic engine."""
    response = client.post(
        "/internal/ai/query",
        json={"query": "Generate a financial close summary report for our recent close."},
        headers=VALID_HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Heuristic Financial Close Summary Report" in data["answer"]
    assert "Total Payments" in data["answer"]

def test_ai_query_transaction_audit():
    """Verify AI query correctly investigates a specific transaction."""
    response = client.post(
        "/internal/ai/query",
        json={"query": "Audit transaction pay_95822412 please."},
        headers=VALID_HEADERS
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "pay_95822412" in data["answer"]

def test_rabbitmq_event_bus():
    """Verify RabbitMQ worker connects and publishes to finance_events exchange."""
    from app.core.rabbitmq import rabbitmq_worker
    connected = rabbitmq_worker.connect()
    assert connected is True
    
    # Test publishing a batch job
    published = rabbitmq_worker.publish_job(
        "reconciliation.job",
        {"jobId": "pytest_reconciliation_test", "merchant_id": "flipkart"}
    )
    assert published is True
    rabbitmq_worker.close()
