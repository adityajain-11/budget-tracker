"""Command-line interface.

Examples:
    budget-tracker add --category food --amount 450 --note "lunch"
    budget-tracker list
    budget-tracker edit 1 --amount 470
    budget-tracker summary
    budget-tracker top --n 3
    budget-tracker compare
    budget-tracker insights
    budget-tracker budget set --category food --limit 5000
    budget-tracker budget status
    budget-tracker recurring add --category rent --amount 15000 --day 1
    budget-tracker recurring apply
    budget-tracker chart --type pie
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from budget_tracker import visualize
from budget_tracker.storage import SqliteStorage, export_to_csv
from budget_tracker.tracker import BudgetTracker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="budget-tracker", description="A personal expense tracker.")
    parser.add_argument("--db", default="budget.db", help="path to the SQLite database file")
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="record a new expense")
    add_p.add_argument("--category", required=True)
    add_p.add_argument("--amount", required=True, type=float)
    add_p.add_argument("--note", default="")
    add_p.add_argument("--date", help="YYYY-MM-DD, defaults to today")

    sub.add_parser("list", help="list all recorded expenses")

    edit_p = sub.add_parser("edit", help="edit an existing expense")
    edit_p.add_argument("id", type=int)
    edit_p.add_argument("--category")
    edit_p.add_argument("--amount", type=float)
    edit_p.add_argument("--note")
    edit_p.add_argument("--date", help="YYYY-MM-DD")

    del_p = sub.add_parser("delete", help="delete an expense by id")
    del_p.add_argument("id", type=int)

    sub.add_parser("summary", help="show totals by category")

    top_p = sub.add_parser("top", help="show the biggest-spend categories")
    top_p.add_argument("--n", type=int, default=3)
    top_p.add_argument("--month", help="YYYY-MM, defaults to all-time")

    compare_p = sub.add_parser("compare", help="compare this month's spend to last month")
    compare_p.add_argument("--month", help="YYYY-MM, defaults to current month")

    insights_p = sub.add_parser("insights", help="show plain-English spending insights")
    insights_p.add_argument("--month", help="YYYY-MM, defaults to current month")

    export_p = sub.add_parser("export", help="export all expenses to CSV")
    export_p.add_argument("--out", default="expenses.csv")

    budget_p = sub.add_parser("budget", help="manage category budget limits")
    budget_sub = budget_p.add_subparsers(dest="budget_command", required=True)
    set_p = budget_sub.add_parser("set", help="set a monthly limit for a category")
    set_p.add_argument("--category", required=True)
    set_p.add_argument("--limit", required=True, type=float)
    status_p = budget_sub.add_parser("status", help="show spend vs. limit for this month")
    status_p.add_argument("--month", help="YYYY-MM, defaults to current month")

    chart_p = sub.add_parser("chart", help="generate a chart image")
    chart_p.add_argument("--type", choices=["pie", "monthly"], default="pie")
    chart_p.add_argument("--out", help="output filename")

    recurring_p = sub.add_parser("recurring", help="manage recurring monthly expenses")
    recurring_sub = recurring_p.add_subparsers(dest="recurring_command", required=True)
    rec_add = recurring_sub.add_parser("add", help="create a recurring rule")
    rec_add.add_argument("--category", required=True)
    rec_add.add_argument("--amount", required=True, type=float)
    rec_add.add_argument("--day", required=True, type=int, help="day of month (1-28) it recurs on")
    rec_add.add_argument("--note", default="")
    recurring_sub.add_parser("list", help="list recurring rules")
    rec_del = recurring_sub.add_parser("delete", help="delete a recurring rule by id")
    rec_del.add_argument("id", type=int)
    recurring_sub.add_parser("apply", help="generate this month's expenses for any due rules")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    storage = SqliteStorage(args.db)
    tracker = BudgetTracker(storage)

    try:
        if args.command == "add":
            on = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else None
            expense = tracker.add_expense(args.category, args.amount, args.note, on)
            print(f"Added #{expense.id}: {expense.category} - {expense.amount:.2f} ({expense.date})")

        elif args.command == "list":
            expenses = tracker.all_expenses()
            if not expenses:
                print("No expenses recorded yet.")
            for e in expenses:
                note = f" — {e.note}" if e.note else ""
                print(f"#{e.id}  {e.date}  {e.category:<15} {e.amount:>10.2f}{note}")

        elif args.command == "edit":
            on = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else None
            expense = tracker.edit_expense(args.id, args.category, args.amount, args.note, on)
            print(f"Updated #{expense.id}: {expense.category} - {expense.amount:.2f} ({expense.date})")

        elif args.command == "delete":
            ok = tracker.delete_expense(args.id)
            print("Deleted." if ok else f"No expense with id {args.id}.")

        elif args.command == "summary":
            totals = tracker.by_category()
            if not totals:
                print("No expenses recorded yet.")
            else:
                print(f"Total: {tracker.total():.2f}\n")
                for category, amount in totals.items():
                    print(f"{category:<15} {amount:>10.2f}")

        elif args.command == "top":
            top = tracker.top_categories(args.n, args.month)
            if not top:
                print("No expenses recorded yet.")
            for rank, (category, amount) in enumerate(top, start=1):
                print(f"{rank}. {category:<15} {amount:>10.2f}")

        elif args.command == "compare":
            c = tracker.compare_months(args.month)
            change = f"{c['change_pct']:+.1f}%" if c["change_pct"] is not None else "n/a"
            print(f"{c['previous_month']}: {c['previous_total']:.2f}")
            print(f"{c['month']}: {c['current_total']:.2f}  ({change})\n")
            for category, s in sorted(c["by_category"].items()):
                cat_change = f"{s['change_pct']:+.1f}%" if s["change_pct"] is not None else "n/a"
                print(f"{category:<15} {s['previous']:>10.2f} -> {s['current']:>10.2f}  ({cat_change})")

        elif args.command == "insights":
            for line in tracker.generate_insights(args.month):
                print(f"- {line}")

        elif args.command == "export":
            path = export_to_csv(tracker.all_expenses(), args.out)
            print(f"Exported to {path}")

        elif args.command == "budget":
            if args.budget_command == "set":
                tracker.set_budget(args.category, args.limit)
                print(f"Budget for {args.category.title()} set to {args.limit:.2f}/month")
            elif args.budget_command == "status":
                status = tracker.budget_status(args.month)
                if not status:
                    print("No budgets or expenses for this period.")
                for category, s in status.items():
                    flag = "  OVER BUDGET" if s["limit"] and s["spent"] > s["limit"] else ""
                    limit_str = f"{s['limit']:.2f}" if s["limit"] else "no limit set"
                    print(f"{category:<15} spent {s['spent']:>10.2f} / {limit_str}{flag}")

        elif args.command == "chart":
            if args.type == "pie":
                out = args.out or "expenses_pie.png"
                path = visualize.pie_by_category(tracker.by_category(), out)
            else:
                out = args.out or "expenses_by_month.png"
                path = visualize.bar_by_month(tracker.by_month(), out)
            print(f"Chart saved to {path}")

        elif args.command == "recurring":
            if args.recurring_command == "add":
                rule = tracker.add_recurring(args.category, args.amount, args.day, args.note)
                print(f"Added recurring rule #{rule.id}: {rule.category} {rule.amount:.2f} on day {rule.day_of_month}")
            elif args.recurring_command == "list":
                rules = tracker.list_recurring()
                if not rules:
                    print("No recurring rules set up.")
                for r in rules:
                    state = "active" if r.active else "paused"
                    print(f"#{r.id}  {r.category:<15} {r.amount:>10.2f}  day {r.day_of_month:>2}  [{state}]")
            elif args.recurring_command == "delete":
                ok = tracker.delete_recurring(args.id)
                print("Deleted." if ok else f"No recurring rule with id {args.id}.")
            elif args.recurring_command == "apply":
                created = tracker.apply_recurring()
                if not created:
                    print("No recurring expenses were due.")
                for e in created:
                    print(f"Added #{e.id}: {e.category} - {e.amount:.2f} ({e.date})")

    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        storage.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
