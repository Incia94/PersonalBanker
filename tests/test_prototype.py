import tempfile
import unittest
from pathlib import Path
from typing import Any, Sequence

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from agents.alerting_agent import AlertingAgent
from agents.spending_agent import SpendingAgent
from backend.api import app
from backend.api_client import MockBankClient
from backend.main import AgentOrchestrator
from backend.memory import SQLiteMemory
from backend.mock_api import get_transactions


class ToolCallingFakeModel(FakeMessagesListChatModel):
    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "ToolCallingFakeModel":
        if not tools or kwargs.get("tool_choice") not in (None, "auto"):
            raise ValueError("Unexpected fake-model tool binding configuration.")
        return self


def tool_call(name: str, *additional_names: str, arguments: dict[str, Any] | None = None) -> AIMessage:
    args = arguments or {"month": "2026-10"}
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": tool_name,
                "args": args,
                "id": f"call-{index}",
                "type": "tool_call",
            }
            for index, tool_name in enumerate((name, *additional_names), start=1)
        ],
    )


def make_model(*responses: AIMessage) -> ToolCallingFakeModel:
    return ToolCallingFakeModel(responses=list(responses))


def make_orchestrator(path: Path, model: ToolCallingFakeModel) -> AgentOrchestrator:
    memory = SQLiteMemory(path)
    api = MockBankClient("http://testserver", TestClient(app))
    return AgentOrchestrator(memory, api, model)


class MockApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def test_api_serves_inr_account_and_transactions(self) -> None:
        account = self.client.get("/account").json()
        transactions = self.client.get("/transactions", params={"month": "2026-10"}).json()

        self.assertEqual(account["currency"], "INR")
        self.assertEqual(account["monthly_income"], 100_000)
        self.assertEqual(len(transactions["transactions"]), 16)
        self.assertTrue(all(item["currency"] == "INR" for item in transactions["transactions"]))

    def test_api_builds_plan_for_fifteen_thousand_rupee_goal(self) -> None:
        response = self.client.post(
            "/savings/plan",
            json={"target_amount": 15_000, "thread_id": "test", "reference_month": "2026-10"},
        )

        self.assertEqual(response.status_code, 200)
        plan = response.json()
        self.assertEqual(plan["target_month"], "2026-11")
        self.assertEqual(plan["estimated_available"], 12_817)
        self.assertEqual(plan["additional_reduction_needed"], 2_183)
        self.assertTrue(plan["feasible_with_suggested_cuts"])
        self.assertIn("Shopping", [cut["category"] for cut in plan["suggested_category_cuts"]])
        self.assertEqual(plan["weekly_savings_target"], 3_750)

    def test_api_rejects_nonpositive_savings_goal(self) -> None:
        response = self.client.post("/savings/plan", json={"target_amount": 0})

        self.assertEqual(response.status_code, 422)


class SpendingAgentTests(unittest.TestCase):
    def test_summarize_and_compare_sample_months(self) -> None:
        agent = SpendingAgent()
        october = agent.summarize(get_transactions("2026-10"))
        september = agent.summarize(get_transactions("2026-09"))

        self.assertEqual(october["transaction_count"], 16)
        self.assertEqual(october["category_totals"]["Dining"], 6_013)
        self.assertEqual(agent.compare(october, september)["category_changes"]["Dining"], 1_615)
        dining_insight = next(
            insight
            for insight in agent.generate_insights(october, september)
            if insight.startswith("Dining spending")
        )
        self.assertIn("Dining spending is up 37%", dining_insight)
        self.assertIn("₹1,615.00", dining_insight)

    def test_invalid_month_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            get_transactions("2026-13")

    def test_alerting_agent_flags_spike(self) -> None:
        current = {"transaction_count": 1, "total": 90.0, "category_totals": {"Dining": 90.0}}
        previous = {"transaction_count": 1, "total": 40.0, "category_totals": {"Dining": 40.0}}

        alerts = AlertingAgent().find_alerts(current, previous)

        self.assertTrue(any("Dining spending is up 125%" in alert for alert in alerts))

    def test_alerting_agent_flags_limit_and_large_charge(self) -> None:
        transaction = {
            "id": "a",
            "date": "2026-10-30",
            "merchant": "New Shop",
            "amount": 425_000,
            "category": "Shopping",
        }
        current = {
            "transaction_count": 1,
            "total": 425_000,
            "category_totals": {"Shopping": 425_000},
            "merchant_totals": {"New Shop": 425_000},
        }
        previous = {
            "transaction_count": 1,
            "total": 300_000,
            "category_totals": {"Shopping": 300_000},
            "merchant_totals": {"Known Shop": 300_000},
        }

        alerts = AlertingAgent().find_alerts(
            current, previous, [transaction], {"Shopping": 400_000}
        )

        self.assertTrue(any("breached its ₹400,000" in alert for alert in alerts))
        self.assertTrue(any("Possible fraud review signal" in alert for alert in alerts))

    def test_alerting_agent_flags_duplicate_transaction(self) -> None:
        duplicate = {
            "id": "copy",
            "date": "2026-10-30",
            "merchant": "Corner Store",
            "amount": 2_800,
            "category": "Dining",
        }
        current = {
            "transaction_count": 2,
            "total": 5_600,
            "category_totals": {"Dining": 5_600},
            "merchant_totals": {"Corner Store": 5_600},
        }
        previous = {
            "transaction_count": 0,
            "total": 0.0,
            "category_totals": {},
            "merchant_totals": {},
        }

        alerts = AlertingAgent().find_alerts(current, previous, [duplicate, duplicate])

        self.assertTrue(any("Possible duplicate" in alert for alert in alerts))


class MemoryAndOrchestrationTests(unittest.TestCase):
    def test_sqlite_persists_conversations_and_savings_goals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite"
            memory = SQLiteMemory(path)
            memory.add_message("thread", "user", "Help me save ₹15,000 next month.")
            memory.add_message("thread", "assistant", "I will build a savings plan.")
            memory.save_goal(
                "thread",
                15_000,
                "2026-11",
                {"estimated_available": 12_817},
            )

            restored_memory = SQLiteMemory(path)
            self.assertEqual(len(restored_memory.get_messages("thread")), 2)
            goal = restored_memory.get_active_goal("thread")
            self.assertEqual(goal["target_amount"], 15_000)
            self.assertEqual(goal["plan"]["estimated_available"], 12_817)

    def test_agent_calls_savings_tool_and_saves_goal_to_sqlite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            orchestrator = make_orchestrator(
                Path(directory) / "memory.sqlite",
                make_model(
                    tool_call(
                        "create_savings_plan",
                        arguments={"target_amount_inr": 15_000},
                    ),
                    AIMessage(content="Your ₹15,000 goal is achievable with a small spending adjustment."),
                ),
            )
            self.addCleanup(orchestrator.close)
            agent, answer = orchestrator.answer(
                "Help me save Rs15000 next month",
                "thread-savings",
                [],
            )
            goal = orchestrator.memory.get_active_goal("thread-savings")

        self.assertEqual(agent, "Planner Agent")
        self.assertIn("₹15,000", answer)
        self.assertEqual(goal["target_month"], "2026-11")
        self.assertEqual(goal["plan"]["additional_reduction_needed"], 2_183)

    def test_planner_calls_multiple_api_tools_and_combines_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            orchestrator = make_orchestrator(
                Path(directory) / "memory.sqlite",
                make_model(
                    tool_call(
                        "spending_analysis",
                        "recommend_finances",
                        "check_spending_alerts",
                    ),
                    AIMessage(content="Here is your spending summary, suggestions, and alerts."),
                ),
            )
            self.addCleanup(orchestrator.close)
            agent, answer = orchestrator.answer(
                "Summarize my spending, suggest ways to save, and tell me about alerts",
                "thread",
                [],
            )

        self.assertEqual(agent, "Planner Agent")
        self.assertIn("spending summary", answer)
        self.assertEqual(
            set(orchestrator.planner.last_tool_results),
            {"spending_analysis", "recommend_finances", "check_spending_alerts"},
        )

    def test_dashboard_uses_mock_api_and_returns_all_specialist_sections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            orchestrator = make_orchestrator(
                Path(directory) / "memory.sqlite",
                make_model(AIMessage(content="")),
            )
            self.addCleanup(orchestrator.close)
            result = orchestrator.run_analysis("2026-10")

        self.assertEqual(result["currency"], "INR")
        self.assertEqual(result["current"]["category_totals"]["Dining"], 6_013)
        self.assertTrue(result["insights"])
        self.assertTrue(result["recommendations"])
        self.assertTrue(result["alerts"])


if __name__ == "__main__":
    unittest.main()
