"""FastAPI mock-banking API used by the Streamlit app and agent tools."""

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from agents.alerting_agent import AlertingAgent
from agents.spending_agent import SpendingAgent
from agents.recommendation_agent import RecommendationAgent
from backend.mock_api import (
    get_fixed_expenses,
    get_sample_account,
    get_spending_limits,
    get_transactions,
)


app = FastAPI(
    title="Ledgerly Mock Banking API",
    description="Fictional local banking data for the Ledgerly prototype.",
    version="0.1.0",
)
spending_agent = SpendingAgent()
alerting_agent = AlertingAgent()
recommendation_agent = RecommendationAgent()


class SavingsPlanRequest(BaseModel):
    target_amount: float = Field(gt=0, le=10_000_000)
    thread_id: str = "demo"
    reference_month: str | None = None


def _latest_month() -> str:
    all_transactions = get_transactions()
    if not all_transactions:
        raise HTTPException(status_code=404, detail="No mock transaction history is available.")
    return max(transaction["date"][:7] for transaction in all_transactions)


def _previous_month(month: str) -> str:
    parsed = SpendingAgent.parse_month(month)
    year, number = parsed.year, parsed.month - 1
    if number == 0:
        year, number = year - 1, 12
    return f"{year:04d}-{number:02d}"


def _next_month(month: str) -> str:
    parsed = SpendingAgent.parse_month(month)
    year, number = parsed.year, parsed.month + 1
    if number == 13:
        year, number = year + 1, 1
    return f"{year:04d}-{number:02d}"


def _summaries(month: str) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    try:
        current_transactions = get_transactions(month)
        previous_transactions = get_transactions(_previous_month(month))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return (
        current_transactions,
        spending_agent.summarize(current_transactions),
        spending_agent.summarize(previous_transactions),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mock-banking-api"}


@app.get("/account")
def account() -> dict[str, Any]:
    profile = get_sample_account()
    profile["fixed_expenses"] = get_fixed_expenses()
    return profile


@app.get("/transactions")
def transactions(month: str | None = Query(default=None)) -> dict[str, Any]:
    month = month or _latest_month()
    try:
        records = get_transactions(month)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"month": month, "currency": "INR", "transactions": records}


@app.get("/spending/summary")
def spending_summary(month: str | None = Query(default=None)) -> dict[str, Any]:
    month = month or _latest_month()
    current_txns, current, previous = _summaries(month)
    return {
        "month": month,
        "currency": "INR",
        "summary": current,
        "insights": spending_agent.generate_insights(current, previous),
        "top_merchants": spending_agent.top_merchants(current_txns),
    }


@app.get("/spending/recommendations")
def spending_recommendations(month: str | None = Query(default=None)) -> dict[str, Any]:
    month = month or _latest_month()
    _, current, previous = _summaries(month)
    comparison = spending_agent.compare(current, previous)
    return {
        "month": month,
        "recommendations": recommendation_agent.recommend(current, comparison),
    }


@app.get("/spending/alerts")
def spending_alerts(month: str | None = Query(default=None)) -> dict[str, Any]:
    month = month or _latest_month()
    current_txns, current, previous = _summaries(month)
    return {
        "month": month,
        "alerts": alerting_agent.find_alerts(
            current, previous, current_txns, get_spending_limits()
        ),
    }


def build_savings_plan(
    target_amount: float, reference_month: str, thread_id: str = "demo"
) -> dict[str, Any]:
    _, current, _ = _summaries(reference_month)
    profile = get_sample_account()
    income = profile["monthly_income"]
    fixed_expenses = get_fixed_expenses()
    fixed_total = round(sum(item["amount"] for item in fixed_expenses), 2)
    variable_spend = current["total"]
    available = round(income - fixed_total - variable_spend, 2)
    monthly_gap = round(max(0, target_amount - available), 2)
    flexible_categories = ("Shopping", "Dining", "Entertainment")
    category_totals = current["category_totals"]
    cut_capacity = {
        category: round(category_totals.get(category, 0) * 0.15, 2)
        for category in flexible_categories
    }
    remaining = monthly_gap
    cuts: list[dict[str, Any]] = []
    for category in sorted(
        flexible_categories,
        key=lambda name: category_totals.get(name, 0),
        reverse=True,
    ):
        cut = min(remaining, cut_capacity[category])
        if cut:
            cuts.append(
                {
                    "category": category,
                    "suggested_reduction": round(cut, 2),
                    "current_spend": category_totals.get(category, 0),
                    "suggested_cap": round(category_totals.get(category, 0) - cut, 2),
                }
            )
            remaining = round(remaining - cut, 2)
    feasible = remaining <= 0
    target_month = _next_month(reference_month)
    return {
        "thread_id": thread_id,
        "reference_month": reference_month,
        "target_month": target_month,
        "currency": "INR",
        "target_amount": round(target_amount, 2),
        "monthly_income": income,
        "fixed_expenses": fixed_expenses,
        "fixed_expense_total": fixed_total,
        "observed_variable_spend": variable_spend,
        "estimated_available": available,
        "additional_reduction_needed": monthly_gap,
        "suggested_category_cuts": cuts,
        "weekly_savings_target": round(target_amount / 4, 2),
        "feasible_with_suggested_cuts": feasible,
        "message": (
            f"Based on mock income, fixed commitments and {reference_month} spending, "
            f"about ₹{available:,.0f} may be available. "
            + (
                f"To target ₹{target_amount:,.0f} in {target_month}, aim to redirect "
                f"₹{target_amount:,.0f} monthly (about ₹{target_amount / 4:,.0f} weekly)"
                + (
                    f" and trim about ₹{monthly_gap:,.0f} from flexible spending."
                    if monthly_gap
                    else "."
                )
                if feasible
                else f"The target is short by about ₹{remaining:,.0f} even after the "
                "suggested flexible-category reductions; consider a lower target or "
                "a longer timeline."
            )
        ),
    }


@app.post("/savings/plan")
def savings_plan(request: SavingsPlanRequest) -> dict[str, Any]:
    reference_month = request.reference_month or _latest_month()
    try:
        plan = build_savings_plan(
            request.target_amount, reference_month, request.thread_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return plan
