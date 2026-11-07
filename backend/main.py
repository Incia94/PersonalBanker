"""Application services shared by the Streamlit chat and tests."""

from typing import Any

from langchain_core.language_models import BaseChatModel

from agents.planner_agent import PlannerAgent
from backend.api_client import MockBankClient
from backend.memory import SQLiteMemory


class AgentOrchestrator:
    def __init__(
        self,
        memory: SQLiteMemory,
        api: MockBankClient,
        model: BaseChatModel | None = None,
    ) -> None:
        self.memory = memory
        self.api = api
        self.planner = PlannerAgent(memory, api, model=model)

    @property
    def last_workflow(self) -> list[str]:
        return self.planner.last_workflow

    def run_analysis(self, month: str = "") -> dict[str, Any]:
        return self.planner.analyze(month)

    def answer(
        self,
        question: str,
        thread_id: str,
        history: list[dict[str, Any]],
        month: str = "",
    ) -> tuple[str, str]:
        return self.planner.answer(question, thread_id, history, month)

    def close(self) -> None:
        self.api.close()
