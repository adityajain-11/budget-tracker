"""Persistence layer.

Defines a small `Storage` protocol so the rest of the app doesn't care how
expenses are actually stored. `SqliteStorage` is the default implementation;
swapping in a different backend (e.g. Postgres) only means writing a new
class that satisfies the same interface.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Protocol

from budget_tracker.models import BudgetLimit, Expense, RecurringExpense


class Storage(Protocol):
    """Interface any storage backend must implement."""

    def add_expense(self, expense: Expense) -> Expense: ...

    def update_expense(self, expense: Expense) -> bool: ...

    def list_expenses(self) -> list[Expense]: ...

    def delete_expense(self, expense_id: int) -> bool: ...

    def set_budget(self, budget: BudgetLimit) -> None: ...

    def get_budgets(self) -> dict[str, float]: ...

    def add_recurring(self, rule: RecurringExpense) -> RecurringExpense: ...

    def list_recurring(self, active_only: bool = False) -> list[RecurringExpense]: ...

    def delete_recurring(self, rule_id: int) -> bool: ...

    def mark_recurring_applied(self, rule_id: int, month: str) -> None: ...


class SqliteStorage:
    """SQLite-backed storage. Creates the schema on first use."""

    def __init__(self, db_path: str | Path = "budget.db") -> None:
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                note TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS recurring_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                day_of_month INTEGER NOT NULL,
                note TEXT DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                last_applied_month TEXT
            );
            """
        )
        self._conn.commit()

    def add_expense(self, expense: Expense) -> Expense:
        cur = self._conn.execute(
            "INSERT INTO expenses (category, amount, date, note) VALUES (?, ?, ?, ?)",
            (expense.category, expense.amount, expense.date.isoformat(), expense.note),
        )
        self._conn.commit()
        expense.id = cur.lastrowid
        return expense

    def update_expense(self, expense: Expense) -> bool:
        if expense.id is None:
            raise ValueError("expense must have an id to be updated")
        cur = self._conn.execute(
            "UPDATE expenses SET category = ?, amount = ?, date = ?, note = ? WHERE id = ?",
            (expense.category, expense.amount, expense.date.isoformat(), expense.note, expense.id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def list_expenses(self) -> list[Expense]:
        rows = self._conn.execute(
            "SELECT id, category, amount, date, note FROM expenses ORDER BY date"
        ).fetchall()
        return [Expense.from_row(dict(row)) for row in rows]

    def delete_expense(self, expense_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def set_budget(self, budget: BudgetLimit) -> None:
        self._conn.execute(
            """
            INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)
            ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit
            """,
            (budget.category, budget.limit),
        )
        self._conn.commit()

    def get_budgets(self) -> dict[str, float]:
        rows = self._conn.execute("SELECT category, monthly_limit FROM budgets").fetchall()
        return {row["category"]: row["monthly_limit"] for row in rows}

    def add_recurring(self, rule: RecurringExpense) -> RecurringExpense:
        cur = self._conn.execute(
            """
            INSERT INTO recurring_expenses
                (category, amount, day_of_month, note, active, last_applied_month)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (rule.category, rule.amount, rule.day_of_month, rule.note, int(rule.active), rule.last_applied_month),
        )
        self._conn.commit()
        rule.id = cur.lastrowid
        return rule

    def list_recurring(self, active_only: bool = False) -> list[RecurringExpense]:
        query = "SELECT * FROM recurring_expenses"
        if active_only:
            query += " WHERE active = 1"
        rows = self._conn.execute(query).fetchall()
        return [
            RecurringExpense(
                id=row["id"],
                category=row["category"],
                amount=row["amount"],
                day_of_month=row["day_of_month"],
                note=row["note"],
                active=bool(row["active"]),
                last_applied_month=row["last_applied_month"],
            )
            for row in rows
        ]

    def delete_recurring(self, rule_id: int) -> bool:
        cur = self._conn.execute("DELETE FROM recurring_expenses WHERE id = ?", (rule_id,))
        self._conn.commit()
        return cur.rowcount > 0

    def mark_recurring_applied(self, rule_id: int, month: str) -> None:
        self._conn.execute(
            "UPDATE recurring_expenses SET last_applied_month = ? WHERE id = ?", (month, rule_id)
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def export_to_csv(expenses: list[Expense], filename: str | Path = "expenses.csv") -> Path:
    """Export expenses to CSV, e.g. for spreadsheets or backups."""
    path = Path(filename)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "category", "amount", "date", "note"])
        writer.writeheader()
        for expense in expenses:
            writer.writerow(expense.to_row())
    return path
