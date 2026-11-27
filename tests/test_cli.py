"""Tests for the CLI, especially the exit codes, which are the contract a gate
relies on."""

import json

import pytest

from flowmetrics.cli import EXIT_ERROR, EXIT_OK, EXIT_SIGNAL, main


def test_check_on_the_slowdown_fixture_exits_with_the_signal_code(capsys):
    code = main(["check", "--generate", "capacity_drop"])
    assert code == EXIT_SIGNAL
    assert "LEADING SLOWDOWN SIGNAL" in capsys.readouterr().out


def test_check_on_the_steady_fixture_exits_zero(capsys):
    code = main(["check", "--generate", "steady"])
    assert code == EXIT_OK
    assert "No leading slowdown signal" in capsys.readouterr().out


def test_an_unknown_scenario_exits_with_the_error_code_not_the_signal_code(capsys):
    code = main(["check", "--generate", "does_not_exist"])
    assert code == EXIT_ERROR


def test_a_missing_events_file_exits_with_the_error_code(capsys):
    code = main(["check", "--events", "/no/such/file.csv"])
    assert code == EXIT_ERROR
    assert "not found" in capsys.readouterr().err


def test_the_three_exit_codes_are_distinct():
    assert len({EXIT_OK, EXIT_ERROR, EXIT_SIGNAL}) == 3


def test_summary_emits_valid_json(capsys):
    code = main(["summary", "--generate", "capacity_drop"])
    assert code == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert data["lead_weeks"] > 0


def test_report_writes_an_html_file(tmp_path, capsys):
    out = tmp_path / "r.html"
    code = main(["report", "--generate", "steady", "--out", str(out)])
    assert code == EXIT_OK
    assert out.exists() and out.read_text().startswith("<!DOCTYPE html>")


def test_fixture_writes_a_csv(tmp_path, capsys):
    out = tmp_path / "e.csv"
    code = main(["fixture", "--scenario", "steady", "--out", str(out)])
    assert code == EXIT_OK
    assert out.read_text().startswith("issue_id,to_state,day")


def test_check_reads_an_events_file_when_one_is_given(tmp_path, capsys):
    events = tmp_path / "e.csv"
    assert main(["fixture", "--scenario", "capacity_drop", "--out", str(events)]) == EXIT_OK
    capsys.readouterr()
    code = main(["check", "--events", str(events)])
    assert code == EXIT_SIGNAL


def test_no_subcommand_is_a_usage_error():
    with pytest.raises(SystemExit):
        main([])
