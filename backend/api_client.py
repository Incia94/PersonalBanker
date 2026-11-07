"""HTTP client for the local FastAPI mock-banking service."""

import os
from typing import Any

import httpx


class MockBankClient:
    def __init__(self, base_url: str | None = None, client: Any | None = None) -> None:
        self.base_url = (base_url or os.getenv("BANK_API_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.client = client or httpx.Client(timeout=10)

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        response = self.client.get(f"{self.base_url}{path}", params=params)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.client.post(f"{self.base_url}{path}", json=payload)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if close:
            close()
