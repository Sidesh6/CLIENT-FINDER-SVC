"""
Pydantic Schemas for AI-Powered Revenue Intelligence & Freelance Financial Dashboard.
Covers invoices, payments, expenses, revenue snapshots, forecasts, and tax reserves.
"""

from datetime import UTC, date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, computed_field


class InvoiceStatus(str, Enum):
    """Invoice lifecycle states."""

    DRAFT = "DRAFT"
    SENT = "SENT"
    VIEWED = "VIEWED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, Enum):
    """Supported payment methods for received payments."""

    BANK_TRANSFER = "BANK_TRANSFER"
    PAYPAL = "PAYPAL"
    STRIPE = "STRIPE"
    WISE = "WISE"
    CRYPTO = "CRYPTO"
    CHECK = "CHECK"
    OTHER = "OTHER"


class ExpenseCategory(str, Enum):
    """Freelance business expense categories."""

    SOFTWARE = "SOFTWARE"
    HARDWARE = "HARDWARE"
    MARKETING = "MARKETING"
    EDUCATION = "EDUCATION"
    TRAVEL = "TRAVEL"
    TAX = "TAX"
    LEGAL = "LEGAL"
    INSURANCE = "INSURANCE"
    MISC = "MISC"


class InvoiceLineItem(BaseModel):
    """A single billable line item on an invoice."""

    description: str = Field(..., description="Service or deliverable description")
    quantity: float = Field(default=1.0, ge=0.0)
    unit_price: float = Field(default=0.0, ge=0.0)

    @computed_field
    @property
    def total(self) -> float:
        return round(self.quantity * self.unit_price, 2)


class InvoiceRecord(BaseModel):
    """A complete freelance invoice with line items and status tracking."""

    id: str
    invoice_number: str
    tenant_id: str = "default_tenant"
    client_name: str
    client_email: str = ""
    project_id: str | None = None
    line_items: list[InvoiceLineItem] = Field(default_factory=list)
    tax_rate_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    discount_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    currency: str = "USD"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    notes: str = ""
    issued_date: date
    due_date: date
    paid_date: date | None = None
    amount_paid: float = 0.0
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def subtotal(self) -> float:
        return round(sum(item.quantity * item.unit_price for item in self.line_items), 2)

    @computed_field
    @property
    def discount_amount(self) -> float:
        return round(self.subtotal * self.discount_pct / 100.0, 2)

    @computed_field
    @property
    def taxable_amount(self) -> float:
        return round(self.subtotal - self.discount_amount, 2)

    @computed_field
    @property
    def tax_amount(self) -> float:
        return round(self.taxable_amount * self.tax_rate_pct / 100.0, 2)

    @computed_field
    @property
    def total_amount(self) -> float:
        return round(self.taxable_amount + self.tax_amount, 2)

    @computed_field
    @property
    def amount_outstanding(self) -> float:
        return round(max(self.total_amount - self.amount_paid, 0.0), 2)


class PaymentRecord(BaseModel):
    """A payment received against an invoice."""

    id: str
    invoice_id: str
    tenant_id: str = "default_tenant"
    amount: float = Field(..., ge=0.0)
    currency: str = "USD"
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    reference: str = ""
    notes: str = ""
    received_date: date
    recorded_at: datetime


class ExpenseRecord(BaseModel):
    """A tracked business expense."""

    id: str
    tenant_id: str = "default_tenant"
    description: str
    category: ExpenseCategory = ExpenseCategory.MISC
    amount: float = Field(..., ge=0.0)
    currency: str = "USD"
    vendor: str = ""
    receipt_url: str = ""
    expense_date: date
    is_tax_deductible: bool = True
    recorded_at: datetime


class RevenueSnapshot(BaseModel):
    """Aggregated financial summary for a period."""

    period_label: str  # e.g. "2026-08", "2026-Q3", "YTD-2026"
    invoices_issued: int
    invoices_paid: int
    gross_billed: float
    gross_collected: float
    outstanding_ar: float
    total_expenses: float
    net_profit: float
    effective_tax_rate_pct: float
    tax_reserve_suggested: float


class ForecastMonth(BaseModel):
    """Single month revenue projection in a forecast."""

    month_label: str  # e.g. "Sep 2026"
    expected_revenue: float
    conservative_revenue: float
    optimistic_revenue: float
    pipeline_opportunities: int
    confidence_pct: float


class FinancialForecast(BaseModel):
    """90-day forward-looking revenue forecast."""

    generated_at: datetime
    forecast_horizon_days: int = 90
    months: list[ForecastMonth]
    total_expected: float
    total_conservative: float
    total_optimistic: float
    pipeline_value: float
    cash_flow_alert: str | None = None


class TaxReserve(BaseModel):
    """Tax reserve estimate and savings recommendation."""

    ytd_gross_income: float
    ytd_deductible_expenses: float
    ytd_taxable_income: float
    jurisdiction_rate_pct: float
    estimated_tax_liability: float
    already_reserved: float
    reserve_gap: float
    recommended_monthly_reserve: float
    advisory: str


class CreateInvoiceRequest(BaseModel):
    """API request payload to create a new invoice."""

    client_name: str
    client_email: str = ""
    project_id: str | None = None
    line_items: list[InvoiceLineItem] = Field(default_factory=list)
    tax_rate_pct: float = 0.0
    discount_pct: float = 0.0
    currency: str = "USD"
    notes: str = ""
    due_days: int = Field(default=30, ge=1, le=365)


class RecordPaymentRequest(BaseModel):
    """API request payload to record a payment against an invoice."""

    amount: float = Field(..., ge=0.01)
    method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    reference: str = ""
    notes: str = ""
    received_date: date | None = None


class CreateExpenseRequest(BaseModel):
    """API request payload to log a new business expense."""

    description: str
    category: ExpenseCategory = ExpenseCategory.MISC
    amount: float = Field(..., ge=0.01)
    currency: str = "USD"
    vendor: str = ""
    is_tax_deductible: bool = True
    expense_date: date | None = None
