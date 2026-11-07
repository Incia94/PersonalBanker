"""Fictional account profile and mock monthly commitments."""

from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
TRANSACTIONS_PATH = ROOT_DIR / "data" / "transactions.json"


def get_transactions(month: str | None = None) -> list[dict[str, Any]]:
    """Return fictional INR transactions, optionally filtered by YYYY-MM."""
    import json

    if month is not None:
        if len(month) != 7 or month[4] != "-":
            raise ValueError("Month must use YYYY-MM format.")
        try:
            year, month_number = (int(part) for part in month.split("-"))
        except ValueError as exc:
            raise ValueError("Month must use YYYY-MM format.") from exc
        if year < 1 or not 1 <= month_number <= 12:
            raise ValueError("Month must be a valid calendar month.")

    with TRANSACTIONS_PATH.open(encoding="utf-8") as file:
        records = json.load(file)
    if not isinstance(records, list):
        raise ValueError("Mock transactions must be a JSON list.")
    if month is None:
        return records
    return [record for record in records if record["date"].startswith(month)]


def get_sample_account() -> dict[str, Any]:
    """Return a fictional Indian customer profile and monthly take-home income."""
    return {
        "customer_name": "Aarav Sharma",
        "account_name": "Everyday account",
        "currency": "INR",
        "monthly_income": 100_000,
    }


def get_fixed_expenses() -> list[dict[str, Any]]:
    """Return mock recurring obligations in Indian rupees."""
    return [
        {"name": "Rent", "amount": 25_000},
        {"name": "Utilities and phone", "amount": 5_000},
        {"name": "Loan EMI", "amount": 6_000},
    ]


def get_spending_limits() -> dict[str, float]:
    """Return fictional INR monthly category limits."""
    return {
        "Dining": 8_000,
        "Groceries": 12_000,
        "Shopping": 20_000,
        "Transport": 5_000,
        "Entertainment": 4_000,
    }
