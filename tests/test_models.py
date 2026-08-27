import pytest

from budget_tracker.models import BudgetLimit, Expense, RecurringExpense


def test_expense_normalises_category_case():
    e = Expense(category="  food ", amount=10)
    assert e.category == "Food"


def test_expense_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        Expense(category="Food", amount=0)


def test_expense_rejects_empty_category():
    with pytest.raises(ValueError):
        Expense(category="   ", amount=10)


def test_budget_limit_rejects_non_positive_limit():
    with pytest.raises(ValueError):
        BudgetLimit(category="Food", limit=0)


def test_recurring_expense_rejects_day_out_of_range():
    with pytest.raises(ValueError):
        RecurringExpense(category="Rent", amount=100, day_of_month=31)
