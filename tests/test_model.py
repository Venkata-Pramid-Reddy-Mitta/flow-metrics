"""Tests for the data model: the definitions everything downstream depends on."""

import pytest

from flowmetrics.model import STATES, FlowError, Issue, Transition


def test_a_transition_into_a_known_state_is_accepted():
    t = Transition("ISS-1", "in_progress", 5)
    assert t.to_state == "in_progress"


def test_a_transition_into_an_unknown_state_is_refused_at_construction():
    with pytest.raises(FlowError):
        Transition("ISS-1", "in_review", 5)


def test_a_transition_with_a_non_integer_day_is_refused():
    with pytest.raises(FlowError):
        Transition("ISS-1", "done", 5.5)


def test_the_three_states_are_todo_in_progress_done():
    assert STATES == ("todo", "in_progress", "done")


def test_an_open_issue_has_no_cycle_time():
    assert Issue("ISS-1", start_day=3).cycle_time_days is None


def test_cycle_time_is_inclusive_of_both_the_start_and_done_day():
    # start day 3, done day 7 is five calendar days, not four.
    assert Issue("ISS-1", start_day=3, done_day=7).cycle_time_days == 5


def test_a_same_day_start_and_done_is_one_day_of_cycle_time():
    assert Issue("ISS-1", start_day=4, done_day=4).cycle_time_days == 1


def test_is_done_is_false_for_an_open_issue_and_true_for_a_closed_one():
    assert Issue("ISS-1", start_day=1).is_done is False
    assert Issue("ISS-1", start_day=1, done_day=2).is_done is True


def test_age_of_an_open_issue_counts_up_to_the_as_of_day():
    assert Issue("ISS-1", start_day=10).age_days(as_of_day=14) == 5


def test_age_of_a_closed_issue_stops_at_its_done_day():
    iss = Issue("ISS-1", start_day=10, done_day=12)
    assert iss.age_days(as_of_day=20) == 3


def test_age_of_a_closed_issue_before_its_done_day_counts_to_the_as_of_day():
    iss = Issue("ISS-1", start_day=10, done_day=18)
    assert iss.age_days(as_of_day=14) == 5


def test_flow_error_is_a_value_error_so_callers_can_catch_either():
    assert issubclass(FlowError, ValueError)


def test_the_error_message_names_the_offending_issue():
    with pytest.raises(FlowError, match="ISS-9"):
        Transition("ISS-9", "nope", 1)
