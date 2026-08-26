"""Core data models for the budget tracker."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class Expense:
    """A single recorded expense."""

    category: str
    amount: float
    date: date = field(default_factory=date.today)
    note: str = ""
    id: int | None = None  # assigned by storage on insert

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        if not self.category.strip():
            raise ValueError("category must not be empty")
        self.category = self.category.strip().title()

    def to_row(self) -> dict[str, str]:
        """Serialise to a flat dict, e.g. for CSV export."""
        return {
            "id": "" if self.id is None else str(self.id),
            "category": self.category,
            "amount": f"{self.amount:.2f}",
            "date": self.date.isoformat(),
            "note": self.note,
        }

    @classmethod
    def from_row(cls, row: dict[str, str]) -> Expense:
        """Build an Expense back from a CSV row."""
        return cls(
            category=row["category"],
            amount=float(row["amount"]),
            date=datetime.strptime(row["date"], "%Y-%m-%d").date(),
            note=row.get("note", ""),
            id=int(row["id"]) if row.get("id") else None,
        )

@dataclass
class BudgetLimit:
    """A monthly spending limit for one category."""

    category: str
    limit: float

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be positive")
        self.category = self.category.strip().title()


@dataclass
class RecurringExpense:
    """A rule that auto-generates an Expense on a given day each month."""

    category: str
    amount: float
    day_of_month: int
    note: str = ""
    active: bool = True
    last_applied_month: str | None = None  # "YYYY-MM" of the last month it fired
    id: int | None = None

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        if not self.category.strip():
            raise ValueError("category must not be empty")
        if not 1 <= self.day_of_month <= 28:
            raise ValueError("day_of_month must be between 1 and 28 (to stay valid every month)")
        self.category = self.category.strip().title()
