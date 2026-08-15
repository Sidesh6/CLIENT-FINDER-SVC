"""
Freelance Financial Ledger — In-Memory Invoice Registry, Payment Tracking & Expense Management.
"""

import logging
import uuid
from datetime import UTC, date, datetime

from src.finance.schemas import (
    CreateExpenseRequest,
    CreateInvoiceRequest,
    ExpenseRecord,
    InvoiceLineItem,
    InvoiceRecord,
    InvoiceStatus,
    PaymentRecord,
    RecordPaymentRequest,
    RevenueSnapshot,
)

logger = logging.getLogger("FreelanceLedger")


class FreelanceLedger:
    """
    Central in-memory financial ledger managing invoices, payments, and expenses.
    """

    def __init__(self) -> None:
        self._invoices: dict[str, InvoiceRecord] = {}
        self._payments: dict[str, list[PaymentRecord]] = {}  # invoice_id -> payments
        self._expenses: dict[str, ExpenseRecord] = {}
        self._invoice_counter: dict[str, int] = {}  # tenant_id -> counter

        # Seed demo data so dashboard always has content on first load
        self._seed_demo_data()

    def _next_invoice_number(self, tenant_id: str) -> str:
        self._invoice_counter[tenant_id] = self._invoice_counter.get(tenant_id, 1000) + 1
        return f"INV-{self._invoice_counter[tenant_id]}"

    def _seed_demo_data(self) -> None:
        """Seed realistic demo invoices and expenses for instant dashboard exploration."""
        tenant_id = "default_tenant"
        now = datetime.now(UTC)
        today = date.today()

        demo_invoices = [
            {
                "client": "Acme Corp", "email": "billing@acme.com",
                "items": [("FastAPI REST API Development", 40, 150.0), ("Code Review & Architecture", 8, 150.0)],
                "tax": 10.0, "status": InvoiceStatus.PAID, "due_offset": -30, "paid_amt": 7200.0,
            },
            {
                "client": "NovaTech Solutions", "email": "accounts@novatech.io",
                "items": [("Next.js E-Commerce Frontend", 60, 130.0), ("CI/CD Pipeline Setup", 10, 130.0)],
                "tax": 10.0, "status": InvoiceStatus.SENT, "due_offset": 14, "paid_amt": 0.0,
            },
            {
                "client": "DataStream AI", "email": "finance@datastream.ai",
                "items": [("Machine Learning Model Integration", 30, 175.0)],
                "tax": 0.0, "status": InvoiceStatus.PARTIALLY_PAID, "due_offset": 7, "paid_amt": 2500.0,
            },
            {
                "client": "UrbanPulse Media", "email": "ap@urbanpulse.com",
                "items": [("Real-Time Dashboard & WebSocket Streaming", 25, 140.0)],
                "tax": 10.0, "status": InvoiceStatus.OVERDUE, "due_offset": -10, "paid_amt": 0.0,
            },
        ]

        for i, inv_data in enumerate(demo_invoices):
            inv_id = f"inv_demo_{i + 1:03d}"
            number = f"INV-100{i + 1}"
            line_items = [
                InvoiceLineItem(description=desc, quantity=qty, unit_price=price)
                for desc, qty, price in inv_data["items"]
            ]
            due = date.fromordinal(today.toordinal() + inv_data["due_offset"])
            issued = date.fromordinal(due.toordinal() - 30)
            invoice = InvoiceRecord(
                id=inv_id,
                invoice_number=number,
                tenant_id=tenant_id,
                client_name=inv_data["client"],
                client_email=inv_data["email"],
                line_items=line_items,
                tax_rate_pct=inv_data["tax"],
                status=inv_data["status"],
                issued_date=issued,
                due_date=due,
                paid_date=today if inv_data["status"] == InvoiceStatus.PAID else None,
                amount_paid=inv_data["paid_amt"],
                created_at=now,
                updated_at=now,
            )
            self._invoices[inv_id] = invoice

        demo_expenses = [
            ("GitHub Copilot Subscription", "SOFTWARE", 19.0, "GitHub"),
            ("AWS Cloud Credits", "SOFTWARE", 145.50, "Amazon Web Services"),
            ("Udemy — FastAPI Advanced Course", "EDUCATION", 14.99, "Udemy"),
            ("Figma Professional Plan", "SOFTWARE", 45.0, "Figma Inc"),
            ("Business Insurance Q3", "INSURANCE", 320.0, "Hiscox"),
        ]
        for j, (desc, cat_str, amt, vendor) in enumerate(demo_expenses):
            from src.finance.schemas import ExpenseCategory
            exp_id = f"exp_demo_{j + 1:03d}"
            self._expenses[exp_id] = ExpenseRecord(
                id=exp_id,
                tenant_id=tenant_id,
                description=desc,
                category=ExpenseCategory(cat_str),
                amount=amt,
                vendor=vendor,
                is_tax_deductible=True,
                expense_date=date.fromordinal(today.toordinal() - (j * 7)),
                recorded_at=now,
            )

    # ----- Invoice CRUD -----

    def create_invoice(self, tenant_id: str, req: CreateInvoiceRequest) -> InvoiceRecord:
        """Create and store a new invoice."""
        now = datetime.now(UTC)
        today = date.today()
        inv_id = f"inv_{uuid.uuid4().hex[:10]}"
        number = self._next_invoice_number(tenant_id)
        due = date.fromordinal(today.toordinal() + req.due_days)
        invoice = InvoiceRecord(
            id=inv_id,
            invoice_number=number,
            tenant_id=tenant_id,
            client_name=req.client_name,
            client_email=req.client_email,
            project_id=req.project_id,
            line_items=req.line_items,
            tax_rate_pct=req.tax_rate_pct,
            discount_pct=req.discount_pct,
            currency=req.currency,
            notes=req.notes,
            status=InvoiceStatus.DRAFT,
            issued_date=today,
            due_date=due,
            created_at=now,
            updated_at=now,
        )
        self._invoices[inv_id] = invoice
        logger.info("Created invoice %s for client '%s' (total: %.2f)", number, req.client_name, invoice.total_amount)
        return invoice

    def list_invoices(self, tenant_id: str, status_filter: InvoiceStatus | None = None) -> list[InvoiceRecord]:
        """List invoices for a tenant, optionally filtered by status."""
        self._auto_mark_overdue(tenant_id)
        invoices = [inv for inv in self._invoices.values() if inv.tenant_id == tenant_id]
        if status_filter:
            invoices = [inv for inv in invoices if inv.status == status_filter]
        return sorted(invoices, key=lambda x: x.due_date, reverse=True)

    def get_invoice(self, inv_id: str) -> InvoiceRecord | None:
        return self._invoices.get(inv_id)

    def update_invoice_status(self, inv_id: str, new_status: InvoiceStatus) -> InvoiceRecord | None:
        """Update invoice status and set paid_date if marking as PAID."""
        inv = self._invoices.get(inv_id)
        if not inv:
            return None
        inv.status = new_status
        inv.updated_at = datetime.now(UTC)
        if new_status == InvoiceStatus.PAID and not inv.paid_date:
            inv.paid_date = date.today()
            inv.amount_paid = inv.total_amount
        return inv

    def _auto_mark_overdue(self, tenant_id: str) -> None:
        """Automatically transitions SENT/VIEWED invoices past due date to OVERDUE."""
        today = date.today()
        for inv in self._invoices.values():
            if inv.tenant_id != tenant_id:
                continue
            if inv.status in (InvoiceStatus.SENT, InvoiceStatus.VIEWED, InvoiceStatus.PARTIALLY_PAID):
                if inv.due_date < today:
                    inv.status = InvoiceStatus.OVERDUE
                    inv.updated_at = datetime.now(UTC)

    # ----- Payment Recording -----

    def record_payment(self, inv_id: str, tenant_id: str, req: RecordPaymentRequest) -> PaymentRecord | None:
        """Record a payment against an invoice and update its status."""
        inv = self._invoices.get(inv_id)
        if not inv or inv.tenant_id != tenant_id:
            return None

        now = datetime.now(UTC)
        pay_id = f"pay_{uuid.uuid4().hex[:10]}"
        payment = PaymentRecord(
            id=pay_id,
            invoice_id=inv_id,
            tenant_id=tenant_id,
            amount=req.amount,
            method=req.method,
            reference=req.reference,
            notes=req.notes,
            received_date=req.received_date or date.today(),
            recorded_at=now,
        )
        if inv_id not in self._payments:
            self._payments[inv_id] = []
        self._payments[inv_id].append(payment)

        inv.amount_paid = round(inv.amount_paid + req.amount, 2)
        inv.updated_at = now
        if inv.amount_paid >= inv.total_amount:
            inv.status = InvoiceStatus.PAID
            inv.paid_date = payment.received_date
        elif inv.amount_paid > 0:
            inv.status = InvoiceStatus.PARTIALLY_PAID

        logger.info("Recorded payment of %.2f against invoice %s (total paid: %.2f)", req.amount, inv_id, inv.amount_paid)
        return payment

    # ----- Expense Tracking -----

    def record_expense(self, tenant_id: str, req: CreateExpenseRequest) -> ExpenseRecord:
        """Log a new business expense."""
        exp_id = f"exp_{uuid.uuid4().hex[:10]}"
        expense = ExpenseRecord(
            id=exp_id,
            tenant_id=tenant_id,
            description=req.description,
            category=req.category,
            amount=req.amount,
            currency=req.currency,
            vendor=req.vendor,
            is_tax_deductible=req.is_tax_deductible,
            expense_date=req.expense_date or date.today(),
            recorded_at=datetime.now(UTC),
        )
        self._expenses[exp_id] = expense
        logger.info("Recorded expense: %s (%.2f %s)", req.description, req.amount, req.currency)
        return expense

    def list_expenses(self, tenant_id: str) -> list[ExpenseRecord]:
        """List all expenses for a tenant, most recent first."""
        expenses = [e for e in self._expenses.values() if e.tenant_id == tenant_id]
        return sorted(expenses, key=lambda x: x.expense_date, reverse=True)

    # ----- Revenue Aggregation -----

    def get_revenue_snapshot(self, tenant_id: str) -> RevenueSnapshot:
        """Compute aggregated financial KPIs for the tenant."""
        self._auto_mark_overdue(tenant_id)
        invoices = [inv for inv in self._invoices.values() if inv.tenant_id == tenant_id]
        expenses = [e for e in self._expenses.values() if e.tenant_id == tenant_id]

        gross_billed = sum(inv.total_amount for inv in invoices if inv.status not in (InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED))
        gross_collected = sum(inv.amount_paid for inv in invoices)
        outstanding_ar = sum(inv.amount_outstanding for inv in invoices if inv.status not in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED, InvoiceStatus.DRAFT))
        total_expenses = sum(e.amount for e in expenses if e.is_tax_deductible)
        net_profit = round(gross_collected - total_expenses, 2)
        effective_tax_rate = 28.0  # default; configurable
        tax_reserve = round(max(net_profit, 0) * effective_tax_rate / 100.0, 2)

        return RevenueSnapshot(
            period_label="YTD",
            invoices_issued=len([inv for inv in invoices if inv.status != InvoiceStatus.DRAFT]),
            invoices_paid=len([inv for inv in invoices if inv.status == InvoiceStatus.PAID]),
            gross_billed=round(gross_billed, 2),
            gross_collected=round(gross_collected, 2),
            outstanding_ar=round(outstanding_ar, 2),
            total_expenses=round(total_expenses, 2),
            net_profit=net_profit,
            effective_tax_rate_pct=effective_tax_rate,
            tax_reserve_suggested=tax_reserve,
        )


# Global Ledger Singleton
GLOBAL_LEDGER = FreelanceLedger()
