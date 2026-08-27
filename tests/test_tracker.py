from datetime import date

import pytest

from budget_tracker.storage import SqliteStorage
from budget_tracker.tracker import BudgetTracker


def make_tracker(tmp_path):
    storage = SqliteStorage(tmp_path / "test.db")
    return BudgetTracker(storage)


def test_total_and_by_category(tmp_path):
    tracker = make_tracker(tmp_path)
    tracker.add_expense("Food", 20)
    tracker.add_expense("Food", 30)
    tracker.add_expense("Transport", 10)

    assert tracker.total() == 60
    assert tracker.by_category() == {"Food": 50, "Transport": 10}


def test_by_month_groups_correctly(tmp_path):
    tracker = make_tracker(tmp_path)
    tracker.add_expense("Food", 20, on=date(2026, 1, 15))
    tracker.add_expense("Food", 30, on=date(2026, 2, 1))

    assert tracker.by_month() == {"2026-01": 20, "2026-02": 30}


def test_budget_status_flags_over_budget(tmp_path):
    tracker = make_tracker(tmp_path)
    tracker.set_budget("Food", 40)
    tracker.add_expense("Food", 50, on=date(2026, 1, 10))

    status = tracker.budget_status("2026-01")
    assert status["Food"]["spent"] == 50
    assert status["Food"]["limit"] == 40
    assert "Food" in tracker.over_budget_categories("2026-01")


def test_edit_expense_updates_fields(tmp_path):
    tracker = make_tracker(tmp_path)
    e = tracker.add_expense("Food", 20, note="lunch")
    updated = tracker.edit_expense(e.id, amount=25, note="dinner")
    assert updated.amount == 25
    assert updated.note == "dinner"
    assert updated.category == "Food"


def test_edit_expense_missing_id_raises(tmp_path):
    tracker = make_tracker(tmp_path)
    with pytest.raises(ValueError):
        tracker.edit_expense(999, amount=10)


def test_top_categories_orders_by_spend(tmp_path):
    tracker = make_tracker(tmp_path)
    tracker.add_expense("Food", 10)
    tracker.add_expense("Transport", 50)
    tracker.add_expense("Food", 5)
    assert tracker.top_categories(1) == [("Transport", 50)]


def test_compare_months_computes_change_pct(tmp_path):
    tracker = make_tracker(tmp_path)
    tracker.add_expense("Food", 100, on=date(2026, 1, 15))
    tracker.add_expense("Food", 150, on=date(2026, 2, 15))
    comparison = tracker.compare_months("2026-02")
    assert comparison["previous_total"] == 100
    assert comparison["current_total"] == 150
    assert comparison["change_pct"] == pytest.approx(50.0)


def test_compare_months_handles_no_previous_spend(tmp_path):
    tracker = make_tracker(tmp_path)
    tracker.add_expense("Food", 100, on=date(2026, 3, 1))
    comparison = tracker.compare_months("2026-03")
    assert comparison["previous_total"] == 0
    assert comparison["change_pct"] is None


def test_recurring_add_list_delete(tmp_path):
    tracker = make_tracker(tmp_path)
    rule = tracker.add_recurring("Rent", 15000, day_of_month=1)
    assert tracker.list_recurring() == [rule]
    assert tracker.delete_recurring(rule.id) is True
    assert tracker.list_recurring() == []


def test_apply_recurring_creates_expense_once_due(tmp_path):
    tracker = make_tracker(tmp_path)
    tracker.add_recurring("Rent", 15000, day_of_month=1)
    created = tracker.apply_recurring(today=date(2026, 4, 5))
    assert len(created) == 1
    assert created[0].category == "Rent"
    assert created[0].date == date(2026, 4, 1)


def test_apply_recurring_skips_if_not_yet_due(tmp_path):
    tracker = make_tracker(tmp_path)
    tracker.add_recurring("Rent", 15000, day_of_month=20)
    created = tracker.apply_recurring(today=date(2026, 4, 5))
    assert created == []


def test_apply_recurring_does_not_double_book_same_month(tmp_path):
    tracker = make_tracker(tmp_path)
    tracker.add_recurring("Rent", 15000, day_of_month=1)
    tracker.apply_recurring(today=date(2026, 4, 5))
    second_run = tracker.apply_recurring(today=date(2026, 4, 10))
    assert second_run == []
    assert tracker.total() == 15000


def test_generate_insights_flags_over_budget(tmp_path):
    tracker = make_tracker(tmp_path)
    tracker.set_budget("Food", 40)
    tracker.add_expense("Food", 60, on=date(2026, 5, 10))
    insights = tracker.generate_insights("2026-05")
    assert any("over budget" in line for line in insights)


def test_generate_insights_handles_empty_data(tmp_path):
    tracker = make_tracker(tmp_path)
    insights = tracker.generate_insights("2026-05")
    assert len(insights) == 1
    assert "Not enough data" in insights[0]
