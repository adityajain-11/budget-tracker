from budget_tracker.models import BudgetLimit, Expense, RecurringExpense
from budget_tracker.storage import SqliteStorage


def make_storage(tmp_path):
    return SqliteStorage(tmp_path / "test.db")


def test_add_and_list_expense(tmp_path):
    storage = make_storage(tmp_path)
    storage.add_expense(Expense(category="Food", amount=20))
    expenses = storage.list_expenses()
    assert len(expenses) == 1
    assert expenses[0].category == "Food"
    assert expenses[0].id is not None
    storage.close()


def test_delete_expense(tmp_path):
    storage = make_storage(tmp_path)
    e = storage.add_expense(Expense(category="Food", amount=20))
    assert storage.delete_expense(e.id) is True
    assert storage.list_expenses() == []
    assert storage.delete_expense(999) is False
    storage.close()


def test_update_expense(tmp_path):
    storage = make_storage(tmp_path)
    e = storage.add_expense(Expense(category="Food", amount=20))
    e.amount = 30
    e.note = "updated"
    assert storage.update_expense(e) is True
    reloaded = storage.list_expenses()[0]
    assert reloaded.amount == 30
    assert reloaded.note == "updated"
    storage.close()


def test_set_and_get_budgets(tmp_path):
    storage = make_storage(tmp_path)
    storage.set_budget(BudgetLimit(category="Food", limit=100))
    storage.set_budget(BudgetLimit(category="Food", limit=150))  # update, not duplicate
    budgets = storage.get_budgets()
    assert budgets == {"Food": 150}
    storage.close()


def test_recurring_crud(tmp_path):
    storage = make_storage(tmp_path)
    rule = storage.add_recurring(RecurringExpense(category="Rent", amount=15000, day_of_month=1))
    assert rule.id is not None
    assert storage.list_recurring() == [rule]

    storage.mark_recurring_applied(rule.id, "2026-04")
    reloaded = storage.list_recurring()[0]
    assert reloaded.last_applied_month == "2026-04"

    assert storage.delete_recurring(rule.id) is True
    assert storage.list_recurring() == []
    storage.close()
