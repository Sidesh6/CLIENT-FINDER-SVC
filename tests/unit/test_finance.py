"""Unit tests for Phase 24 Revenue Intelligence & Financial Dashboard."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.finance.forecaster import RevenueForecastEngine
from src.finance.ledger import GLOBAL_LEDGER
from src.finance.schemas import (
    CreateExpenseRequest,
    CreateInvoiceRequest,
    ExpenseCategory,
    InvoiceLineItem,
    InvoiceStatus,
    RecordPaymentRequest,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_ledger_state():
    """Reset singleton state between tests."""
    GLOBAL_LEDGER._invoices.clear()
    GLOBAL_LEDGER._payments.clear()
    GLOBAL_LEDGER._expenses.clear()
    GLOBAL_LEDGER._invoice_counter.clear()


def test_create_invoice_and_payment_flow():
    req = CreateInvoiceRequest(
        client_name="Acme Corp",
        client_email="billing@acme.com",
        line_items=[
            InvoiceLineItem(description="Fullstack App Dev", quantity=10, unit_price=100.0),
            InvoiceLineItem(description="Deployment Setup", quantity=1, unit_price=200.0),
        ],
        tax_rate_pct=10.0,
        due_days=14,
    )
    inv = GLOBAL_LEDGER.create_invoice("tenant_test", req)

    assert inv.invoice_number == "INV-1001"
    assert inv.client_name == "Acme Corp"
    assert inv.taxable_amount == 1200.0
    assert inv.total_amount == 1320.0
    assert inv.amount_paid == 0.0
    assert inv.status == InvoiceStatus.DRAFT

    # Partial payment
    pay_req = RecordPaymentRequest(amount=500.0, notes="Deposit")
    pay = GLOBAL_LEDGER.record_payment(inv.id, "tenant_test", pay_req)
    assert pay is not None
    assert pay.amount == 500.0

    updated_inv = GLOBAL_LEDGER.get_invoice(inv.id)
    assert updated_inv.amount_paid == 500.0
    assert updated_inv.status == InvoiceStatus.PARTIALLY_PAID

    # Full payment
    pay_req2 = RecordPaymentRequest(amount=820.0, notes="Final settlement")
    GLOBAL_LEDGER.record_payment(inv.id, "tenant_test", pay_req2)

    updated_inv2 = GLOBAL_LEDGER.get_invoice(inv.id)
    assert updated_inv2.amount_paid == 1320.0
    assert updated_inv2.status == InvoiceStatus.PAID


def test_expenses_and_revenue_snapshot():
    # Create paid invoice
    inv_req = CreateInvoiceRequest(
        client_name="Beta LLC",
        line_items=[InvoiceLineItem(description="Consulting", quantity=1, unit_price=2000.0)],
        tax_rate_pct=0.0,
    )
    inv = GLOBAL_LEDGER.create_invoice("tenant_test", inv_req)
    GLOBAL_LEDGER.record_payment(inv.id, "tenant_test", RecordPaymentRequest(amount=2000.0))

    # Add expenses
    GLOBAL_LEDGER.record_expense(
        "tenant_test",
        CreateExpenseRequest(
            category=ExpenseCategory.SOFTWARE,
            amount=200.0,
            description="Cloud Hosting",
        ),
    )
    GLOBAL_LEDGER.record_expense(
        "tenant_test",
        CreateExpenseRequest(
            category=ExpenseCategory.MARKETING,
            amount=300.0,
            description="Outreach Ads",
        ),
    )

    snap = GLOBAL_LEDGER.get_revenue_snapshot("tenant_test")
    assert snap.gross_billed == 2000.0
    assert snap.gross_collected == 2000.0
    assert snap.total_expenses == 500.0
    assert snap.net_profit == 1500.0
    # Tax reserve 28% of net profit (1500 * 0.28 = 420.0)
    assert snap.tax_reserve_suggested == 420.0


def test_forecaster_engine():
    engine = RevenueForecastEngine()

    mock_opps = [
        {"title": "Deal 1", "score": 90, "budget_max": 10000.0},
        {"title": "Deal 2", "score": 50, "budget_max": 5000.0},
    ]

    fc = engine.generate_forecast(
        pipeline_opportunities=mock_opps,
        ledger_snapshot_collected=3000.0,
        months_ahead=3,
    )

    assert fc.months is not None
    assert len(fc.months) == 3
    assert fc.total_expected > 0
    assert fc.pipeline_value == 11500.0  # (10000 * 0.90) + (5000 * 0.50)


def test_finance_api_routes():
    # Test POST /api/finance/invoices
    resp = client.post(
        "/api/finance/invoices",
        json={
            "client_name": "API Client",
            "line_items": [{"description": "API Integration", "quantity": 1, "unit_price": 1500.0}],
            "tax_rate_pct": 5.0,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["client_name"] == "API Client"
    assert data["total_amount"] == 1575.0
    inv_id = data["id"]

    # Test GET /api/finance/invoices
    resp_list = client.get("/api/finance/invoices")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1

    # Test POST /api/finance/invoices/{inv_id}/payment
    resp_pay = client.post(
        f"/api/finance/invoices/{inv_id}/payment",
        json={"amount": 1575.0, "notes": "Paid in full"},
    )
    assert resp_pay.status_code == 201
    assert resp_pay.json()["amount"] == 1575.0

    # Test POST /api/finance/expenses
    resp_exp = client.post(
        "/api/finance/expenses",
        json={"category": "SOFTWARE", "amount": 75.0, "description": "SaaS Tool"},
    )
    assert resp_exp.status_code == 201

    # Test GET /api/finance/summary
    resp_sum = client.get("/api/finance/summary")
    assert resp_sum.status_code == 200
    sum_data = resp_sum.json()
    assert sum_data["gross_collected"] == 1575.0
    assert sum_data["total_expenses"] == 75.0
    assert sum_data["net_profit"] == 1500.0

    # Test GET /api/finance/forecast
    resp_fc = client.get("/api/finance/forecast")
    assert resp_fc.status_code == 200
    fc_data = resp_fc.json()
    assert "pipeline_value" in fc_data
    assert "total_expected" in fc_data
