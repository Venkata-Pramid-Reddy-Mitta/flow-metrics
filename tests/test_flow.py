"""Tests for flow reconstruction and the weekly roll-up, on hand-built events so
the expected numbers can be computed by hand."""

from flowmetrics.config import DEFAULT
from flowmetrics.flow import daily_wip, reconstruct_issues, weekly_flow
from flowmetrics.model import Issue, Transition


def _t(issue, state, day):
    return Transition(issue, state, day)


def test_an_issue_is_reconstructed_from_its_start_and_done_transitions():
    issues = reconstruct_issues([_t("A", "in_progress", 2), _t("A", "done", 5)])
    assert issues == [Issue("A", start_day=2, done_day=5)]


def test_an_issue_still_in_progress_has_no_done_day():
    issues = reconstruct_issues([_t("A", "in_progress", 2)])
    assert issues[0].done_day is None


def test_a_done_event_with_no_start_is_skipped_rather_than_invented():
    issues = reconstruct_issues([_t("A", "done", 5)])
    assert issues == []


def test_only_the_first_start_and_first_done_are_used():
    # A reopened issue is out of scope (ADR-001); later transitions are ignored.
    issues = reconstruct_issues(
        [_t("A", "in_progress", 2), _t("A", "done", 5), _t("A", "in_progress", 8)]
    )
    assert issues[0].start_day == 2 and issues[0].done_day == 5


def test_issue_order_follows_first_appearance():
    issues = reconstruct_issues(
        [_t("B", "in_progress", 1), _t("A", "in_progress", 2), _t("B", "done", 3)]
    )
    assert [i.issue_id for i in issues] == ["B", "A"]


def test_wip_at_week_end_counts_started_but_not_yet_done_issues():
    # Two issues start in week 0; one finishes in week 0, one is still open.
    issues = [Issue("A", 0, 3), Issue("B", 1, None)]
    rows = weekly_flow(issues, weeks=1)
    assert rows[0].wip_end == 1


def test_throughput_counts_issues_finished_in_that_week():
    issues = [Issue("A", 0, 3), Issue("B", 1, 6)]  # A done wk0, B done wk0 (day6)
    rows = weekly_flow(issues, weeks=2)
    assert rows[0].throughput == 2
    assert rows[1].throughput == 0


def test_mean_cycle_time_is_over_exactly_the_items_completed_that_week():
    issues = [Issue("A", 0, 2), Issue("B", 0, 4)]  # cts 3 and 5, both done wk0
    rows = weekly_flow(issues, weeks=1)
    assert rows[0].mean_cycle_time == 4.0


def test_a_week_with_no_completions_has_a_none_cycle_time_not_zero():
    issues = [Issue("A", 0, None)]
    rows = weekly_flow(issues, weeks=1)
    assert rows[0].mean_cycle_time is None


def test_daily_wip_counts_an_issue_on_its_done_day():
    # Issue open days 2..5 inclusive: counted on day 5.
    issues = [Issue("A", 2, 5)]
    series = daily_wip(issues, days=7)
    assert series[5] == 1
    assert series[6] == 0


def test_daily_wip_is_zero_before_an_issue_starts():
    issues = [Issue("A", 3, 5)]
    series = daily_wip(issues, days=7)
    assert series[2] == 0 and series[3] == 1


def test_avg_wip_is_the_time_average_over_the_week_not_the_end_snapshot():
    # One issue open the whole week (7 days): avg and end both 1. Add one that is
    # open only the first day: avg should be below the max but end excludes it.
    issues = [Issue("A", 0, 20), Issue("B", 0, 0)]
    rows = weekly_flow(issues, weeks=1)
    assert rows[0].wip_end == 1  # B finished day 0
    assert 1.0 < rows[0].avg_wip <= 2.0


def test_week_day_boundaries_use_the_configured_week_length():
    assert DEFAULT.week_length_days == 7
    issues = [Issue("A", 7, 7)]  # starts and ends on first day of week 1
    rows = weekly_flow(issues, weeks=2)
    assert rows[1].throughput == 1 and rows[0].throughput == 0
