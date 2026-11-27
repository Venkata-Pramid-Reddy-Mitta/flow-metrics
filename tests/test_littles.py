"""Tests for the Little's Law cross-check."""

from flowmetrics import generator as G
from flowmetrics.analysis import analyze
from flowmetrics.flow import WeeklyFlow
from flowmetrics.littles import divergence_summary, littles_series


def _row(week, wip, avg_wip, tp, mct):
    return WeeklyFlow(week=week, day_end=week * 7 + 6, wip_end=wip, avg_wip=avg_wip,
                      throughput=tp, mean_cycle_time=mct)


def test_implied_cycle_time_is_avg_wip_over_throughput_in_days():
    # avg_wip 10, throughput 5/week -> 2 weeks -> 14 days.
    rows = [_row(0, 10, 10.0, 5, 7.0)]
    ls = littles_series(rows)
    assert ls[0].implied_ct_days == 14.0


def test_a_week_with_zero_throughput_has_no_implied_cycle_time():
    rows = [_row(0, 10, 10.0, 0, None)]
    ls = littles_series(rows)
    assert ls[0].implied_ct_days is None


def test_divergence_is_positive_when_the_law_implies_a_slower_system():
    # implied 14 days, reported 7 days -> (14-7)/14 = 50%.
    rows = [_row(0, 10, 10.0, 5, 7.0)]
    ls = littles_series(rows)
    assert abs(ls[0].divergence_pct - 50.0) < 1e-6


def test_divergence_is_none_when_either_estimate_is_missing():
    rows = [_row(0, 10, 10.0, 0, None)]
    ls = littles_series(rows)
    assert ls[0].divergence_pct is None


def test_rates_use_a_trailing_window_so_a_single_quiet_week_does_not_whipsaw():
    rows = [_row(w, 10, 10.0, 5, 7.0) for w in range(4)]
    rows[3] = _row(3, 10, 10.0, 1, 7.0)  # one quiet week
    ls = littles_series(rows)
    # trailing throughput at week 3 averages (5,5,5,1)=4, not 1.
    assert ls[3].throughput_rate == 4.0


def test_on_the_steady_fixture_little_law_tracks_the_reported_average_closely():
    a = analyze(G.generate(G.STEADY), weeks=26)
    summ = divergence_summary(a.littles, range(2, 11), range(14, 24))
    assert summ["steady_mean_abs_divergence_pct"] < 12.0


def test_on_the_slowdown_the_divergence_is_several_times_wider_in_the_transition():
    a = analyze(G.generate(G.CAPACITY_DROP), weeks=26)
    summ = divergence_summary(a.littles, range(2, 11), range(14, 24))
    assert summ["ratio"] > 3.0


def test_divergence_summary_returns_none_for_an_empty_span():
    a = analyze(G.generate(G.STEADY), weeks=26)
    summ = divergence_summary(a.littles, range(0, 0), range(0, 0))
    assert summ["steady_mean_abs_divergence_pct"] is None
    assert summ["ratio"] is None
