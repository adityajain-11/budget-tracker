"""Business logic: the BudgetTracker orchestrates storage + budget rules."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from budget_tracker.models import BudgetLimit, Expense, RecurringExpense
from budget_tracker.storage import Storage


def _shift_month(month: str, delta: int) -> str:
    """Shift a "YYYY-MM" string by `delta` months (can be negative)."""
    year, mon = (int(part) for part in month.split("-"))
    total = year * 12 + (mon - 1) + delta
    return f"{total // 12}-{total % 12 + 1:02d}"


def _pct_change(previous: float, current: float) -> float | None:
    """Percent change from `previous` to `current`, or None if previous was 0."""
    if previous == 0:
        return None
    return (current - previous) / previous * 100


class BudgetTracker:
    """High-level API used by the CLI (and any future UI)."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    # ---- Expenses -----------------------------------------------------------

    def add_expense(
        self, category: str, amount: float, note: str = "", on: date | None = None
    ) -> Expense:
        expense = Expense(category=category, amount=amount, date=on or date.today(), note=note)
        return self.storage.add_expense(expense)

    def edit_expense(
        self,
        expense_id: int,
        category: str | None = None,
        amount: float | None = None,
        note: str | None = None,
        on: date | None = None,
    ) -> Expense:
        """Update one or more fields of an existing expense."""
        existing = next((e for e in self.all_expenses() if e.id == expense_id), None)
        if existing is None:
            raise ValueError(f"no expense with id {expense_id}")
        updated = Expense(
            category=category if category is not None else existing.category,
            amount=amount if amount is not None else existing.amount,
            date=on if on is not None else existing.date,
            note=note if note is not None else existing.note,
            id=expense_id,
        )
        self.storage.update_expense(updated)
        return updated

    def delete_expense(self, expense_id: int) -> bool:
        return self.storage.delete_expense(expense_id)

    def all_expenses(self) -> list[Expense]:
        return self.storage.list_expenses()

    def total(self) -> float:
        return sum(e.amount for e in self.all_expenses())

    def by_month(self) -> dict[str, float]:
        totals: dict[str, float] = defaultdict(float)
        for expense in self.all_expenses():
            key = expense.date.strftime("%Y-%m")
            totals[key] += expense.amount
        return dict(sorted(totals.items()))

    # ---- Analytics ------------------------------------------------------------

    def _expenses_in_month(self, month: str) -> list[Expense]:
        return [e for e in self.all_expenses() if e.date.strftime("%Y-%m") == month]

    def by_category(self, month: str | None = None) -> dict[str, float]:
        source = self._expenses_in_month(month) if month else self.all_expenses()
        totals: dict[str, float] = defaultdict(float)
        for expense in source:
            totals[expense.category] += expense.amount
        return dict(sorted(totals.items(), key=lambda kv: -kv[1]))

    def top_categories(self, n: int = 3, month: str | None = None) -> list[tuple[str, float]]:
        """The n biggest-spend categories, largest first."""
        return list(self.by_category(month).items())[:n]

    def compare_months(self, month: str | None = None) -> dict:
        """Current month's spend vs. the previous month, overall and per category."""
        month = month or date.today().strftime("%Y-%m")
        previous_month = _shift_month(month, -1)

        current_by_cat = self.by_category(month)
        previous_by_cat = self.by_category(previous_month)

        current_total = sum(current_by_cat.values())
        previous_total = sum(previous_by_cat.values())

        categories = set(current_by_cat) | set(previous_by_cat)
        by_category = {}
        for category in categories:
            current_amt = current_by_cat.get(category, 0.0)
            previous_amt = previous_by_cat.get(category, 0.0)
            by_category[category] = {
                "current": current_amt,
                "previous": previous_amt,
                "change_pct": _pct_change(previous_amt, current_amt),
            }

        return {
            "month": month,
            "previous_month": previous_month,
            "current_total": current_total,
            "previous_total": previous_total,
            "change_pct": _pct_change(previous_total, current_total),
            "by_category": by_category,
        }

    # ---- Budgets ------------------------------------------------------------

    def set_budget(self, category: str, limit: float) -> None:
        self.storage.set_budget(BudgetLimit(category=category, limit=limit))

    def budget_status(self, month: str | None = None) -> dict[str, dict[str, float]]:
        """Spend vs. limit per category for a given month (default: current month).

        Returns e.g. {"Food": {"spent": 120.0, "limit": 200.0, "remaining": 80.0}}
        """
        month = month or date.today().strftime("%Y-%m")
        budgets = self.storage.get_budgets()
        spent: dict[str, float] = defaultdict(float)
        for expense in self.all_expenses():
            if expense.date.strftime("%Y-%m") == month:
                spent[expense.category] += expense.amount

        status: dict[str, dict[str, float]] = {}
        categories = set(budgets) | set(spent)
        for category in categories:
            limit = budgets.get(category, 0.0)
            amount_spent = spent.get(category, 0.0)
            status[category] = {
                "spent": amount_spent,
                "limit": limit,
                "remaining": limit - amount_spent if limit else float("inf"),
            }
        return status

    def over_budget_categories(self, month: str | None = None) -> list[str]:
        status = self.budget_status(month)
        return [cat for cat, s in status.items() if s["limit"] and s["spent"] > s["limit"]]

    # ---- Recurring expenses ------------------------------------------------

    def add_recurring(self, category: str, amount: float, day_of_month: int, note: str = "") -> RecurringExpense:
        rule = RecurringExpense(category=category, amount=amount, day_of_month=day_of_month, note=note)
        return self.storage.add_recurring(rule)

    def list_recurring(self, active_only: bool = False) -> list[RecurringExpense]:
        return self.storage.list_recurring(active_only)

    def delete_recurring(self, rule_id: int) -> bool:
        return self.storage.delete_recurring(rule_id)

    def apply_recurring(self, today: date | None = None) -> list[Expense]:
        """Generate this month's expense for every active recurring rule that
        hasn't already fired this month and whose day has arrived. Safe to
        call repeatedly — it won't double-book.
        """
        today = today or date.today()
        current_month = today.strftime("%Y-%m")
        created: list[Expense] = []

        for rule in self.list_recurring(active_only=True):
            if rule.last_applied_month == current_month:
                continue
            if today.day < rule.day_of_month:
                continue
            expense_date = date(today.year, today.month, rule.day_of_month)
            expense = self.add_expense(rule.category, rule.amount, rule.note, on=expense_date)
            self.storage.mark_recurring_applied(rule.id, current_month)  # type: ignore[arg-type]
            created.append(expense)

        return created

    # ---- Insights ------------------------------------------------------------

    def generate_insights(self, month: str | None = None) -> list[str]:
        """Plain-English observations about spending this month."""
        month = month or date.today().strftime("%Y-%m")
        insights: list[str] = []

        comparison = self.compare_months(month)
        if comparison["previous_total"] > 0:
            change = comparison["change_pct"]
            if change is not None and abs(change) >= 1:
                direction = "up" if change > 0 else "down"
                insights.append(
                    f"Total spending is {direction} {abs(change):.0f}% vs. {comparison['previous_month']} "
                    f"({comparison['previous_total']:.2f} -> {comparison['current_total']:.2f})."
                )

        top = self.top_categories(1, month)
        if top:
            category, amount = top[0]
            insights.append(f"{category} is your biggest category this month at {amount:.2f}.")

        biggest_increase: tuple[str, float] | None = None
        for category, stats in comparison["by_category"].items():
            pct = stats["change_pct"]
            if pct is not None and pct > 0 and (biggest_increase is None or pct > biggest_increase[1]):
                biggest_increase = (category, pct)
        if biggest_increase:
            category, pct = biggest_increase
            insights.append(f"{category} spending grew the most vs. last month, up {pct:.0f}%.")

        over_budget = self.over_budget_categories(month)
        for category in over_budget:
            status = self.budget_status(month)[category]
            over_by = status["spent"] - status["limit"]
            insights.append(f"{category} is over budget by {over_by:.2f} this month.")

        if not insights:
            insights.append("Not enough data yet for insights — add a few more expenses.")

        return insights
