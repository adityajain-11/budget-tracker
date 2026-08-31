"""Streamlit dashboard for Budget Tracker.

A second front-end on top of the same BudgetTracker used by the CLI.
Run with: streamlit run app.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from budget_tracker.storage import SqliteStorage
from budget_tracker.tracker import BudgetTracker

st.set_page_config(page_title="Budget Tracker", page_icon="💰")


@st.cache_resource
def get_tracker() -> BudgetTracker:
    storage = SqliteStorage("budget.db")
    return BudgetTracker(storage)


tracker = get_tracker()

st.title("💰 Budget Tracker")

with st.form("add_expense", clear_on_submit=True):
    category = st.text_input("Category")
    amount = st.number_input("Amount", min_value=0.0, step=10.0)
    note = st.text_input("Note (optional)")
    if st.form_submit_button("Add"):
        if not category or amount <= 0:
            st.error("Category and a positive amount are required.")
        else:
            tracker.add_expense(category, amount, note, date.today())
            st.success(f"Added {category}: {amount:.2f}")
            st.rerun()

st.subheader("All expenses")
expenses = tracker.all_expenses()
if not expenses:
    st.info("No expenses yet, add one above.")
else:
    df = pd.DataFrame([e.to_row() for e in expenses])
    st.dataframe(df, use_container_width=True, hide_index=True)
