"""Spending analysis specialist and its deterministic analysis tools."""

from collections import defaultdict
from datetime import date
from typing import Any


class SpendingAgent:
    name = "Spending Agent"

    def summarize(self, transactions: list[dict[str, Any]]) -> dict[str, Any]:
        category_totals: dict[str, float] = defaultdict(float)
        merchant_totals: dict[str, float] = defaultdict(float)
        for transaction in transactions:
            category_totals[transaction["category"]] += float(transaction["amount"])
            merchant_totals[transaction["merchant"]] += float(transaction["amount"])
        return {
            "transaction_count": len(transactions),
            "total": round(sum(category_totals.values()), 2),
            "category_totals": {
                category: round(amount, 2)
                for category, amount in sorted(category_totals.items())
            },
            "merchant_totals": {
                merchant: round(amount, 2)
                for merchant, amount in sorted(merchant_totals.items())
            },
        }

    def compare(
        self, current: dict[str, Any], previous: dict[str, Any]
    ) -> dict[str, Any]:
        categories = set(current["category_totals"]) | set(previous["category_totals"])
        changes = {
            category: round(
                current["category_totals"].get(category, 0)
                - previous["category_totals"].get(category, 0),
                2,
            )
            for category in sorted(categories)
        }
        return {
            "total_change": round(current["total"] - previous["total"], 2),
            "category_changes": changes,
        }

    def generate_insights(
        self, current: dict[str, Any], previous: dict[str, Any]
    ) -> list[str]:
        insights: list[str] = []
        for category, amount in sorted(
            current["category_totals"].items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            previous_amount = previous["category_totals"].get(category, 0)
            if not previous_amount:
                insights.append(
                    f"{category} spending was ₹{amount:.2f}; there is no previous-month "
                    "spending to compare."
                )
                continue
            change = amount - previous_amount
            percent = round(abs(change) / previous_amount * 100)
            direction = "up" if change > 0 else "down" if change < 0 else "unchanged"
            insights.append(
                f"{category} spending is {direction} {percent}% "
                f"(₹{abs(change):,.2f}) from last month."
            )
        return insights

    @staticmethod
    def top_merchants(transactions: list[dict[str, Any]], limit: int = 3) -> list[tuple[str, float]]:
        totals: dict[str, float] = defaultdict(float)
        for transaction in transactions:
            totals[transaction["merchant"]] += float(transaction["amount"])
        return sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]

    @staticmethod
    def parse_month(month: str) -> date:
        return date.fromisoformat(f"{month}-01")