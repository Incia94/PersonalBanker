"""SQLite-backed conversation history and customer savings goals."""

import json
import sqlite3
from pathlib import Path
from typing import Any


class SQLiteMemory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS messages_thread_id_id
                    ON messages(thread_id, id);
                CREATE TABLE IF NOT EXISTS savings_goals (
                    id INTEGER PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    target_amount REAL NOT NULL,
                    currency TEXT NOT NULL DEFAULT 'INR',
                    target_month TEXT NOT NULL,
                    plan_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def add_message(self, thread_id: str, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Message role must be user or assistant.")
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO messages(thread_id, role, content) VALUES (?, ?, ?)",
                (thread_id, role, content),
            )

    def get_messages(self, thread_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT role, content, created_at FROM messages "
                "WHERE thread_id = ? ORDER BY id",
                (thread_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_goal(
        self,
        thread_id: str,
        target_amount: float,
        target_month: str,
        plan: dict[str, Any],
    ) -> None:
        if target_amount <= 0:
            raise ValueError("Savings goal must be greater than zero.")
        with self.connect() as connection:
            connection.execute(
                "UPDATE savings_goals SET status = 'replaced' "
                "WHERE thread_id = ? AND status = 'active' AND target_month = ?",
                (thread_id, target_month),
            )
            connection.execute(
                "INSERT INTO savings_goals(thread_id, target_amount, target_month, plan_json) "
                "VALUES (?, ?, ?, ?)",
                (thread_id, target_amount, target_month, json.dumps(plan)),
            )

    def get_active_goal(self, thread_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT target_amount, currency, target_month, plan_json, created_at "
                "FROM savings_goals WHERE thread_id = ? AND status = 'active' "
                "ORDER BY id DESC LIMIT 1",
                (thread_id,),
            ).fetchone()
        if not row:
            return None
        goal = dict(row)
        goal["plan"] = json.loads(goal.pop("plan_json"))
        return goal

    def list_goals(self, thread_id: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT target_amount, currency, target_month, plan_json, status, created_at "
                "FROM savings_goals WHERE thread_id = ? AND status = 'active' ORDER BY id DESC",
                (thread_id,),
            ).fetchall()
        goals = []
        for row in rows:
            goal = dict(row)
            goal["plan"] = json.loads(goal.pop("plan_json"))
            goals.append(goal)
        return goals

    def clear_thread(self, thread_id: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM messages WHERE thread_id = ?", (thread_id,))
            connection.execute(
                "UPDATE savings_goals SET status = 'cleared' "
                "WHERE thread_id = ? AND status = 'active'",
                (thread_id,),
            )
