"""
AI Revenue Forecast Engine — Monte Carlo Pipeline Projection & Tax Reserve Calculator.
"""

import logging
from datetime import UTC, datetime

from src.finance.schemas import (
    FinancialForecast,
    ForecastMonth,
    TaxReserve,
)

logger = logging.getLogger("RevenueForecastEngine")

_MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


class RevenueForecastEngine:
    """
    Generates 90-day revenue forecasts using opportunity pipeline win probabilities.
    Also produces tax reserve calculations based on YTD income and expenses.
    """

    def generate_forecast(
        self,
        pipeline_opportunities: list[dict],
        ledger_snapshot_collected: float,
        months_ahead: int = 3,
    ) -> FinancialForecast:
        """
        Produce a forward-looking revenue forecast for the next N months.

        Args:
            pipeline_opportunities: List of opportunity dicts with score, budget_max, status.
            ledger_snapshot_collected: YTD gross collected for trend calibration.
            months_ahead: Number of months to forecast (default 3).
        """
        now = datetime.now(UTC)
        current_month = now.month
        current_year = now.year

        # Value entire active pipeline
        pipeline_value = 0.0
        for opp in pipeline_opportunities:
            budget = float(opp.get("budget_max") or opp.get("budget_min") or 0.0)
            score = float(opp.get("score") or 0.0)
            win_prob = min(score / 100.0, 0.95)
            pipeline_value += budget * win_prob

        # If pipeline is thin, use historical average as baseline
        monthly_baseline = max(ledger_snapshot_collected / 12.0, 3000.0) if ledger_snapshot_collected > 0 else 5000.0

        months: list[ForecastMonth] = []
        total_expected = 0.0
        total_conservative = 0.0
        total_optimistic = 0.0

        for i in range(months_ahead):
            m_idx = (current_month + i - 1) % 12
            y = current_year + (current_month + i - 1) // 12
            label = f"{_MONTH_NAMES[m_idx]} {y}"

            # Decay win probability for later months
            decay = 0.85 ** i
            expected = round(pipeline_value * decay / months_ahead + monthly_baseline * 0.3, 2)
            conservative = round(expected * 0.65, 2)
            optimistic = round(expected * 1.45, 2)
            confidence = round(max(90.0 - i * 12.0, 55.0), 1)

            months.append(ForecastMonth(
                month_label=label,
                expected_revenue=expected,
                conservative_revenue=conservative,
                optimistic_revenue=optimistic,
                pipeline_opportunities=max(len(pipeline_opportunities) - i * 2, 1),
                confidence_pct=confidence,
            ))
            total_expected += expected
            total_conservative += conservative
            total_optimistic += optimistic

        # Cash flow alert if conservative scenario < expenses threshold
        cash_flow_alert = None
        if total_conservative < monthly_baseline * months_ahead * 0.5:
            cash_flow_alert = (
                "⚠️ Conservative forecast suggests potential cash flow shortfall. "
                "Consider activating outreach sequences and reducing discretionary expenses."
            )

        return FinancialForecast(
            generated_at=now,
            forecast_horizon_days=months_ahead * 30,
            months=months,
            total_expected=round(total_expected, 2),
            total_conservative=round(total_conservative, 2),
            total_optimistic=round(total_optimistic, 2),
            pipeline_value=round(pipeline_value, 2),
            cash_flow_alert=cash_flow_alert,
        )

    def compute_tax_reserve(
        self,
        ytd_gross_income: float,
        ytd_deductible_expenses: float,
        ytd_reserved: float = 0.0,
        jurisdiction_rate_pct: float = 28.0,
    ) -> TaxReserve:
        """
        Compute tax liability, reserve gap, and monthly savings recommendation.
        """
        taxable_income = max(ytd_gross_income - ytd_deductible_expenses, 0.0)
        estimated_liability = round(taxable_income * jurisdiction_rate_pct / 100.0, 2)
        reserve_gap = round(max(estimated_liability - ytd_reserved, 0.0), 2)

        # Recommended monthly reserve going forward (assume 6 months left in year)
        months_remaining = max(12 - datetime.now(UTC).month, 1)
        monthly_rec = round(reserve_gap / months_remaining, 2) if reserve_gap > 0 else 0.0

        if reserve_gap <= 0:
            advisory = "✅ You are fully funded for your estimated tax liability. Maintain current reserve rate."
        elif reserve_gap < estimated_liability * 0.25:
            advisory = f"🟡 Minor reserve gap of ${reserve_gap:,.2f}. Recommend setting aside ${monthly_rec:,.2f}/month to close it by year-end."
        else:
            advisory = f"🔴 Significant reserve gap of ${reserve_gap:,.2f}. Immediately allocate ${monthly_rec:,.2f}/month to avoid a tax-time shortfall."

        return TaxReserve(
            ytd_gross_income=round(ytd_gross_income, 2),
            ytd_deductible_expenses=round(ytd_deductible_expenses, 2),
            ytd_taxable_income=round(taxable_income, 2),
            jurisdiction_rate_pct=jurisdiction_rate_pct,
            estimated_tax_liability=estimated_liability,
            already_reserved=round(ytd_reserved, 2),
            reserve_gap=reserve_gap,
            recommended_monthly_reserve=monthly_rec,
            advisory=advisory,
        )


# Global Forecast Engine Singleton
GLOBAL_FORECASTER = RevenueForecastEngine()
