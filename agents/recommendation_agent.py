

"""Recommendation specialist; suggestions are optional, not financial advice."""

from typing import Any


class RecommendationAgent:
    name = "Recommendation Agent"

    def recommend(
        self, summary: dict[str, Any], comparison: dict[str, Any]
    ) -> list[str]:
        if not summary["transaction_count"]:
            return ["There are no sample transactions for this month to base suggestions on."]

        recommendations: list[str] = []
        dining = summary["category_totals"].get("Dining", 0)
        dining_change = comparison["category_changes"].get("Dining", 0)
        if dining:
            if dining_change > 0:
                recommendations.append(
                    f"Dining rose by ₹{dining_change:,.0f} versus last month. "
                    "If that matters to you, consider setting a weekly dining limit."
                )
            else:
                recommendations.append(
                    f"Dining was ₹{dining:,.0f}. You could set a flexible weekly target "
                    "that still leaves room for meals you enjoy."
                )

        largest_category = max(
            summary["category_totals"].items(), key=lambda item: item[1]
        )
        recommendations.append(
            f"{largest_category[0]} is your largest category at "
            f"₹{largest_category[1]:,.0f}; reviewing it may help you find a goal "
            "that fits your priorities."
        )
        return recommendations
