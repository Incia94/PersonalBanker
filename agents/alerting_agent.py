"""Alert specialist for explainable, mock-data spending signals."""

from typing import Any


class AlertingAgent:
    name = "Alerting Agent"

    def find_alerts(
        self,
        current: dict[str, Any],
        previous: dict[str, Any],
        transactions: list[dict[str, Any]] | None = None,
        spending_limits: dict[str, float] | None = None,
    ) -> list[str]:
        if not current["transaction_count"]:
            return []

        alerts: list[str] = []
        for category, limit in (spending_limits or {}).items():
            amount = current["category_totals"].get(category, 0)
            if amount > limit:
                alerts.append(
                    f"{category} spending breached its ₹{limit:,.0f} monthly limit "
                    f"by ₹{amount - limit:,.0f}."
                )
        for category, amount in current["category_totals"].items():
            previous_amount = previous["category_totals"].get(category, 0)
            if previous_amount and amount >= previous_amount * 1.5 and amount - previous_amount >= 20:
                increase = amount - previous_amount
                percent = round((increase / previous_amount) * 100)
                alerts.append(
                    f"{category} spending is up {percent}% "
                    f"(₹{increase:,.0f}) from last month."
                )
        if current["total"] > previous["total"] * 1.2 and previous["total"]:
            alerts.append(
                f"Total spending is up ₹{current['total'] - previous['total']:,.0f} "
                "from last month."
            )

        seen_transactions: set[tuple[str, str, float]] = set()
        previous_merchants = set(previous.get("merchant_totals", {}))
        for transaction in transactions or []:
            merchant = transaction["merchant"]
            amount = float(transaction["amount"])
            key = (transaction["date"], merchant.casefold(), amount)
            if key in seen_transactions:
                alerts.append(
                    f"Possible duplicate: {merchant} charged ₹{amount:,.0f} more than "
                    f"once on {transaction['date']}. Review the transactions."
                )
            seen_transactions.add(key)
            if amount >= 250:
                alerts.append(
                    f"Possible fraud review signal: unusually large transaction of "
                    f"₹{amount:,.0f} at {merchant} on {transaction['date']}. "
                    "Verify it if you don't recognize it; this is not a fraud determination."
                )
            elif amount >= 100 and merchant not in previous_merchants:
                alerts.append(
                    f"Possible unfamiliar merchant: ₹{amount:,.0f} at {merchant}. "
                    "Check whether you recognize this transaction."
                )
        return alerts