# budget_tracker.py
import csv
import cs50
import pandas as pd
import matplotlib.pyplot as plt

expenses = []  # global list

def main():
    load_from_csv()  # load saved data at start
    while True:
        print("\n1. Add Expense\n2. View Summary\n3. View Pie Chart\n4. Save & Exit")
        choice = cs50.get_string("\nChoose an option: ")

        if choice == "1":
            category = cs50.get_string("Enter category: ")
            amount = cs50.get_int("Enter amount: ")
            add_expense(category, amount)
        elif choice == "2":
            view_summary()
        elif choice == "3":
            visualize_expenses()
        elif choice == "4":
            save_to_csv()
            print("Expenses saved. Goodbye!")
            break
        else:
            print("Invalid choice. Try again.")

def save_to_csv(filename="expenses.csv"):
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "amount"])
        writer.writeheader()
        writer.writerows(expenses)

def load_from_csv(filename="expenses.csv"):
    global expenses
    try:
        with open(filename, "r") as f:
            reader = csv.DictReader(f)
            expenses = [row for row in reader]
            for e in expenses:
                e["amount"] = int(e["amount"])  # convert from string
    except FileNotFoundError:
        expenses = []

def add_expense(category, amount):
    expenses.append({"category": category, "amount": amount})

def view_summary():
    if not expenses:
        print("\nNo expenses recorded yet.")
        return
    total = sum(exp["amount"] for exp in expenses)
    print(f"\nTotal expenses: ₹{total}")
    for category in set(exp["category"] for exp in expenses):
        cat_total = sum(exp["amount"] for exp in expenses if exp["category"] == category)
        print(f"{category}: ₹{cat_total}")

def visualize_expenses():
    if not expenses:
        print("\nNo expenses to visualize.")
        return
    df = pd.DataFrame(expenses)
    df.groupby("category").sum().plot(kind="pie", y="amount", autopct='%1.1f%%')
    plt.title("Expense Breakdown by Category")
    plt.ylabel("")  # cleaner chart
    plt.show()

if __name__ == "__main__":
    main()
