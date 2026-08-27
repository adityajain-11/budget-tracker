"""Chart generation. Kept separate so core logic has no plotting dependency."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless-safe: no display needed to save a PNG
import matplotlib.pyplot as plt


def pie_by_category(totals: dict[str, float], filename: str | Path = "expenses_pie.png") -> Path:
    if not totals:
        raise ValueError("no expenses to chart")
    fig, ax = plt.subplots()
    ax.pie(list(totals.values()), labels=list(totals.keys()), autopct="%1.1f%%")
    ax.set_title("Expense Breakdown by Category")
    fig.savefig(filename)
    plt.close(fig)
    return Path(filename)


def bar_by_month(totals: dict[str, float], filename: str | Path = "expenses_by_month.png") -> Path:
    if not totals:
        raise ValueError("no expenses to chart")
    fig, ax = plt.subplots()
    ax.bar(list(totals.keys()), list(totals.values()))
    ax.set_title("Spending by Month")
    ax.set_ylabel("Amount")
    fig.autofmt_xdate(rotation=45)
    fig.savefig(filename)
    plt.close(fig)
    return Path(filename)
