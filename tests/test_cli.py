from budget_tracker.cli import main


def test_add_and_list(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    assert main(["--db", db, "add", "--category", "food", "--amount", "20"]) == 0
    assert main(["--db", db, "list"]) == 0
    out = capsys.readouterr().out
    assert "Food" in out
    assert "20.00" in out


def test_summary_reports_total(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    main(["--db", db, "add", "--category", "food", "--amount", "20"])
    main(["--db", db, "add", "--category", "transport", "--amount", "10"])
    main(["--db", db, "summary"])
    out = capsys.readouterr().out
    assert "Total: 30.00" in out


def test_add_rejects_negative_amount(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    code = main(["--db", db, "add", "--category", "food", "--amount", "-5"])
    assert code == 1
    assert "Error" in capsys.readouterr().err


def test_edit_command_updates_expense(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    main(["--db", db, "add", "--category", "food", "--amount", "20"])
    main(["--db", db, "edit", "1", "--amount", "35"])
    main(["--db", db, "list"])
    out = capsys.readouterr().out
    assert "35.00" in out


def test_top_command(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    main(["--db", db, "add", "--category", "food", "--amount", "20"])
    main(["--db", db, "add", "--category", "transport", "--amount", "50"])
    main(["--db", db, "top", "--n", "1"])
    out = capsys.readouterr().out
    assert "1. Transport" in out


def test_compare_command_runs(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    main(["--db", db, "add", "--category", "food", "--amount", "20"])
    code = main(["--db", db, "compare"])
    assert code == 0
    assert "Food" in capsys.readouterr().out


def test_insights_command_runs(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    main(["--db", db, "add", "--category", "food", "--amount", "20"])
    code = main(["--db", db, "insights"])
    assert code == 0
    assert capsys.readouterr().out.strip() != ""


def test_budget_set_and_status(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    main(["--db", db, "budget", "set", "--category", "food", "--limit", "100"])
    main(["--db", db, "add", "--category", "food", "--amount", "50"])
    main(["--db", db, "budget", "status"])
    out = capsys.readouterr().out
    assert "Food" in out
    assert "50.00" in out


def test_recurring_add_apply_list(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    main(["--db", db, "recurring", "add", "--category", "rent", "--amount", "15000", "--day", "1"])
    main(["--db", db, "recurring", "apply"])
    main(["--db", db, "recurring", "list"])
    out = capsys.readouterr().out
    assert "Rent" in out
