"""LangGraph conversational planner with FastAPI-backed specialist tools."""

import json
import os
from typing import Any

import httpx
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain.tools import tool
from langchain_ollama import ChatOllama
from ollama import ResponseError

from backend.api_client import MockBankClient
from backend.memory import SQLiteMemory


SYSTEM_PROMPT = """\
You are the Planner, a helpful banking assistant. Use specialist tools for
customer data; choose tools based on the request and combine results when useful.
For savings goals, call create_savings_plan with the exact INR amount the
customer requests. Present mock income, expenses, assumptions, suggested cuts,
and feasibility clearly. Never promise a goal is guaranteed. Do not invent
account facts. Alert matches are review signals, not proof of fraud. Suggestions
are optional and are not financial advice. All account data is fictional.
"""

AGENT_NAMES = {
    "spending_analysis": "Spending Agent",
    "recommend_finances": "Recommendation Agent",
    "check_spending_alerts": "Alerting Agent",
    "create_savings_plan": "Planner Agent",
}


class PlannerAgent:
    """Use a local chat model to route natural language to banking tools."""

    def __init__(
        self,
        memory: SQLiteMemory,
        api: MockBankClient,
        model_name: str | None = None,
        model: BaseChatModel | None = None,
    ) -> None:
        self.memory = memory
        self.api = api
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self.last_workflow: list[str] = []
        self.last_tool_results: dict[str, str] = {}
        self.tools = self._build_tools()
        chat_model = model or ChatOllama(
            model=self.model_name,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0,
        )
        self.graph = create_agent(
            model=chat_model,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
            name="Planner Agent",
        )

    def _build_tools(self) -> list[Any]:
        @tool
        def spending_analysis(month: str = "") -> str:
            """Get categorized spending and month-over-month insights from the bank API.

            Args:
                month: Analysis month in YYYY-MM format, or empty for latest data.
            """
            result = self.api.get("/spending/summary", **({"month": month} if month else {}))
            return json.dumps(result)

        @tool
        def recommend_finances(month: str = "") -> str:
            """Get personalized, optional financial-planning suggestions.

            Args:
                month: Analysis month in YYYY-MM format, or empty for latest data.
            """
            result = self.api.get("/spending/recommendations", **({"month": month} if month else {}))
            return json.dumps(result)

        @tool
        def check_spending_alerts(month: str = "") -> str:
            """Check monthly limits, unusual spending, and transaction review signals.

            Args:
                month: Analysis month in YYYY-MM format, or empty for latest data.
            """
            result = self.api.get("/spending/alerts", **({"month": month} if month else {}))
            return json.dumps(result)

        @tool
        def create_savings_plan(target_amount_inr: float) -> str:
            """Create a practical savings plan for an INR target next month.

            Call this when a customer asks how to save or reach a particular
            rupee amount. It uses mock income, fixed expenses and recent spending,
            and saves the requested goal to SQLite.

            Args:
                target_amount_inr: Exact rupee amount the customer wants to save.
            """
            plan = self.api.post(
                "/savings/plan",
                {"target_amount": target_amount_inr, "thread_id": self.thread_id},
            )
            self.memory.save_goal(
                self.thread_id,
                plan["target_amount"],
                plan["target_month"],
                plan,
            )
            return json.dumps(plan, ensure_ascii=False)

        self.thread_id = "demo"
        return [
            spending_analysis,
            recommend_finances,
            check_spending_alerts,
            create_savings_plan,
        ]

    def analyze(self, month: str = "") -> dict[str, Any]:
        params = {"month": month} if month else {}
        summary = self.api.get("/spending/summary", **params)
        recommendations = self.api.get("/spending/recommendations", **params)
        alerts = self.api.get("/spending/alerts", **params)
        account = self.api.get("/account")
        self.last_workflow = [
            "Spending Agent analyzed transactions through FastAPI.",
            "Recommendation Agent generated optional steps through FastAPI.",
            "Alerting Agent checked mock limits and transaction review signals.",
            "Planner Agent combined the specialist results.",
        ]
        return {
            "month": summary["month"],
            "currency": summary["currency"],
            "transactions": self.api.get("/transactions", **params)["transactions"],
            "current": summary["summary"],
            "insights": summary["insights"],
            "recommendations": recommendations["recommendations"],
            "alerts": alerts["alerts"],
            "account": account,
            "active_goal": self.memory.get_active_goal(self.thread_id),
        }

    def answer(
        self,
        question: str,
        thread_id: str,
        history: list[dict[str, Any]],
        month: str = "",
    ) -> tuple[str, str]:
        self.thread_id = thread_id
        messages = [
            {"role": message["role"], "content": message["content"]}
            for message in history
        ]
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Conversation ID: {thread_id}. "
                    f"Use the latest mock transaction month unless a period is specified. "
                    f"Selected dashboard month: {month or 'latest available'}. "
                    f"Customer: {question}"
                ),
            }
        )
        try:
            result = self.graph.invoke({"messages": messages})
        except (httpx.HTTPError, ResponseError) as exc:
            raise RuntimeError(
                "Could not reach the local Ollama model or mock banking API. "
                "Start Ollama and FastAPI, then try again."
            ) from exc

        output_messages = result["messages"]
        latest_user_index = max(
            (i for i, message in enumerate(output_messages) if message.type == "human"),
            default=-1,
        )
        recent_messages = output_messages[latest_user_index + 1 :]
        self.last_tool_results = {
            message.name: str(message.content)
            for message in recent_messages
            if getattr(message, "type", None) == "tool" and message.name in AGENT_NAMES
        }
        self.last_workflow = [
            f"Planner Agent called {AGENT_NAMES[message.name]} (`{message.name}`)."
            for message in recent_messages
            if getattr(message, "type", None) == "tool" and message.name in AGENT_NAMES
        ]
        content = output_messages[-1].content
        if isinstance(content, str):
            return "Planner Agent", content
        return "Planner Agent", "\n".join(
            str(block.get("text", block)) if isinstance(block, dict) else str(block)
            for block in content
        )
