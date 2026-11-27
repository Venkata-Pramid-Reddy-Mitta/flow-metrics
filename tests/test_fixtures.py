"""Tests for the CSV fixture loader and saver."""

import pytest

from flowmetrics.fixtures import load_transitions, save_transitions
from flowmetrics.generator import generate
from flowmetrics.model import FlowError, Transition


def test_save_then_load_round_trips_a_stream(tmp_path):
    original = generate()
    path = tmp_path / "events.csv"
    save_transitions(original, path)
    loaded = load_transitions(path)
    assert [(t.issue_id, t.to_state, t.day) for t in original] == [
        (t.issue_id, t.to_state, t.day) for t in loaded
    ]


def test_loading_a_file_with_a_wrong_header_is_refused(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("id,state,when\nA,done,1\n")
    with pytest.raises(FlowError):
        load_transitions(path)


def test_loading_a_file_with_a_bad_state_is_refused(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("issue_id,to_state,day\nA,frozen,1\n")
    with pytest.raises(FlowError):
        load_transitions(path)


def test_blank_lines_in_the_csv_are_skipped(tmp_path):
    path = tmp_path / "events.csv"
    path.write_text("issue_id,to_state,day\nA,in_progress,1\n\nA,done,3\n")
    loaded = load_transitions(path)
    assert loaded == [Transition("A", "in_progress", 1), Transition("A", "done", 3)]


def test_save_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "dir" / "events.csv"
    save_transitions([Transition("A", "done", 1)], path)
    assert path.exists()
