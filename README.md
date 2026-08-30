# Budget Tracker

![CI](https://github.com/adityajain-11/budget-tracker/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A small personal-finance CLI for logging expenses, setting monthly budgets per category, and visualising spending. Built as a clean, tested Python package rather than a single script.

## Features

**Core**
- Add, edit, and delete expenses
- Categories, normalised and validated on entry
- Persistence via SQLite (no external database required)
- Monthly budgets per category, with an over-budget flag

**Analytics**
- Spend by category and by month
- Top-spending categories
- Month-over-month comparison, overall and per category
- Auto-generated plain-English spending insights

**Standout features**
- **Recurring expenses**: define a monthly rule (e.g. rent on the 1st) and generate that month's entry on demand. Safe to re-run without double-booking.
- **Spending insights**: a short list of observations (spend trend vs. last month, biggest category, fastest-growing category, budget overruns), generated from the analytics above rather than hardcoded.

**Other**
- CSV export for opening data in a spreadsheet
- Charts: category pie chart or month-by-month bar chart (matplotlib)
- Typed, tested, and CI-checked. A pytest suite, mypy, ruff, and GitHub Actions running on every push across Python 3.10-3.12.

## Architecture

The app is split into layers so each piece can be tested and swapped in isolation:

```
budget_tracker/
├── models.py      # Expense, BudgetLimit, RecurringExpense: validated dataclasses
├── storage.py      # Storage protocol + SqliteStorage implementation
├── tracker.py      # BudgetTracker: business logic, analytics, insights
├── visualize.py     # matplotlib chart generation (pie / monthly bar)
└── cli.py          # argparse subcommands: the command-line front-end
```

`Storage` is defined as a `Protocol` (Python's structural-typing interface), so `BudgetTracker` doesn't know or care that it's backed by SQLite. A different backend just needs to implement the same methods.

## Installation

```bash
git clone https://github.com/adityajain-11/budget-tracker.git
cd budget-tracker
python3 -m pip install -e ".[dev]"
```

## Usage

```bash
# record expenses
python3 -m budget_tracker.cli add --category food --amount 450 --note "groceries"
python3 -m budget_tracker.cli add --category transport --amount 120

# see, edit, and manage what's logged
python3 -m budget_tracker.cli list
python3 -m budget_tracker.cli edit 1 --amount 470
python3 -m budget_tracker.cli delete 2

# totals and analytics
python3 -m budget_tracker.cli summary
python3 -m budget_tracker.cli top --n 3
python3 -m budget_tracker.cli compare
python3 -m budget_tracker.cli insights

# set a monthly limit and check status
python3 -m budget_tracker.cli budget set --category food --limit 400
python3 -m budget_tracker.cli budget status

# recurring expenses (e.g. rent)
python3 -m budget_tracker.cli recurring add --category rent --amount 15000 --day 1
python3 -m budget_tracker.cli recurring apply
python3 -m budget_tracker.cli recurring list

# charts
python3 -m budget_tracker.cli chart --type pie
python3 -m budget_tracker.cli chart --type monthly

# export to CSV
python3 -m budget_tracker.cli export --out expenses.csv
```

Each command also accepts `--db path/to/file.db` for a database other than the default `budget.db` in the current directory.

(If installed with `pip install -e .`, you can also drop the `python3 -m budget_tracker.cli` prefix and just run `budget-tracker ...`, provided your Python scripts folder is on your PATH.)

## Running the tests

```bash
python3 -m pytest       # run the test suite
python3 -m ruff check .  # lint
python3 -m mypy budget_tracker  # type-check
```

All three run automatically in CI on every push and pull request.

## Possible next steps

- A Streamlit dashboard on top of the same `BudgetTracker` API
- Search/filter transactions
- Multi-currency support
