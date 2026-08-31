"""Streamlit dashboard for Budget Tracker.

A second front-end on top of the same BudgetTracker used by the CLI.
Run with: streamlit run app.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from budget_tracker.storage import SqliteStorage, export_to_csv
from budget_tracker.tracker import BudgetTracker

st.set_page_config(page_title="Budget Tracker", page_icon="💰", layout="wide")


@st.cache_resource
def get_tracker() -> BudgetTracker:
    storage = SqliteStorage("budget.db")
    return BudgetTracker(storage)


tracker = get_tracker()

# Recurring expenses fire automatically once, on load, same idea as the
# CLI's `recurring apply`, so rent/subscriptions show up without manual entry.
newly_applied = tracker.apply_recurring()

st.title("💰 Budget Tracker")

with st.sidebar:
    st.header("Add expense")
    with st.form("add_expense", clear_on_submit=True):
        category = st.text_input("Category")
        amount = st.number_input("Amount", min_value=0.0, step=10.0)
        note = st.text_input("Note (optional)")
        expense_date = st.date_input("Date", value=date.today())
        if st.form_submit_button("Add"):
            if not category or amount <= 0:
                st.error("Category and a positive amount are required.")
            else:
                tracker.add_expense(category, amount, note, expense_date)
                st.success(f"Added {category}: {amount:.2f}")
                st.rerun()

    st.divider()
    st.header("Set a budget")
    with st.form("set_budget", clear_on_submit=True):
        b_category = st.text_input("Category", key="budget_category")
        b_limit = st.number_input("Monthly limit", min_value=0.0, step=50.0)
        if st.form_submit_button("Set"):
            if not b_category or b_limit <= 0:
                st.error("Category and a positive limit are required.")
            else:
                tracker.set_budget(b_category, b_limit)
                st.success(f"Budget set for {b_category}: {b_limit:.2f}/month")
                st.rerun()

    st.divider()
    st.header("Recurring expenses")
    with st.form("add_recurring", clear_on_submit=True):
        r_category = st.text_input("Category", key="recurring_category")
        r_amount = st.number_input("Amount", min_value=0.0, step=100.0, key="recurring_amount")
        r_day = st.number_input("Day of month", min_value=1, max_value=28, value=1)
        if st.form_submit_button("Add rule"):
            if not r_category or r_amount <= 0:
                st.error("Category and a positive amount are required.")
            else:
                tracker.add_recurring(r_category, r_amount, int(r_day))
                st.success(f"Recurring rule added for {r_category}")
                st.rerun()

if newly_applied:
    for e in newly_applied:
        st.toast(f"Recurring: added {e.category} {e.amount:.2f}")

expenses = tracker.all_expenses()

if not expenses:
    st.info("No expenses yet, add one from the sidebar to get started.")
else:
    tab_overview, tab_expenses, tab_budgets, tab_recurring, tab_insights = st.tabs(
        ["Overview", "Expenses", "Budgets", "Recurring", "Insights"]
    )

    with tab_overview:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total spent", f"{tracker.total():.2f}")
        comparison = tracker.compare_months()
        change = comparison["change_pct"]
        col2.metric(
            "This month",
            f"{comparison['current_total']:.2f}",
            delta=None if change is None else f"{change:+.1f}% vs last month",
        )
        top = tracker.top_categories(1)
        col3.metric("Top category", top[0][0] if top else "—", f"{top[0][1]:.2f}" if top else "")

        left, right = st.columns(2)
        with left:
            st.subheader("Spend by category")
            by_cat = tracker.by_category()
            if by_cat:
                st.bar_chart(pd.Series(by_cat, name="Amount"))
        with right:
            st.subheader("Spend by month")
            by_month = tracker.by_month()
            if by_month:
                st.bar_chart(pd.Series(by_month, name="Amount"))

    with tab_expenses:
        st.subheader("All expenses")
        df = pd.DataFrame([e.to_row() for e in expenses])
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.subheader("Edit or delete")
        expense_ids = [e.id for e in expenses]
        selected_id = st.selectbox("Expense id", expense_ids)
        selected = next(e for e in expenses if e.id == selected_id)
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            new_amount = st.number_input("Amount", value=float(selected.amount), key="edit_amount")
        with col_b:
            new_note = st.text_input("Note", value=selected.note, key="edit_note")
        with col_c:
            st.write("")
            st.write("")
            if st.button("Save changes"):
                tracker.edit_expense(selected_id, amount=new_amount, note=new_note)
                st.success("Updated.")
                st.rerun()
            if st.button("Delete", type="secondary"):
                tracker.delete_expense(selected_id)
                st.success("Deleted.")
                st.rerun()

        csv_path = export_to_csv(expenses, "expenses_export.csv")
        with open(csv_path, "rb") as f:
            st.download_button("Download CSV", f, file_name="expenses.csv")

    with tab_budgets:
        st.subheader("Budget status this month")
        status = tracker.budget_status()
        if not status:
            st.info("No budgets set yet, add one from the sidebar.")
        for cat, s in status.items():
            limit = s["limit"]
            spent = s["spent"]
            if limit:
                pct = min(spent / limit, 1.0)
                st.write(f"**{cat}**: {spent:.2f} / {limit:.2f}")
                st.progress(pct)
                if spent > limit:
                    st.error(f"Over budget by {spent - limit:.2f}")
            else:
                st.write(f"**{cat}**: {spent:.2f} spent (no limit set)")

    with tab_recurring:
        st.subheader("Recurring rules")
        rules = tracker.list_recurring()
        if not rules:
            st.info("No recurring rules yet, add one from the sidebar.")
        for r in rules:
            col_a, col_b = st.columns([4, 1])
            with col_a:
                state = "active" if r.active else "paused"
                st.write(f"**{r.category}**: {r.amount:.2f} on day {r.day_of_month} [{state}]")
            with col_b:
                if st.button("Remove", key=f"remove_{r.id}"):
                    tracker.delete_recurring(r.id)
                    st.rerun()

    with tab_insights:
        st.subheader("This month's insights")
        for line in tracker.generate_insights():
            st.write(f"- {line}")

        st.subheader("Month-over-month")
        comparison = tracker.compare_months()
        rows = [{"category": cat, **stats} for cat, stats in comparison["by_category"].items()]
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
