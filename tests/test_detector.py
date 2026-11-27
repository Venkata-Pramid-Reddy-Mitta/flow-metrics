"""Tests for the detector: bands, persistence, lead, flat weeks, survivorship."""

from flowmetrics import generator as G
from flowmetrics.analysis import analyze
from flowmetrics.config import DEFAULT
from flowmetrics.detector import (
    _band,
    _first_persistent_break,
    detect,
    has_leading_signal,
)
from flowmetrics.flow import reconstruct_issues, weekly_flow


def test_the_band_upper_is_mean_plus_sigma_times_stdev():
    band = _band([2.0, 4.0, 6.0], sigma=2.0)
    assert band.mean == 4.0
    assert band.upper > band.mean


def test_a_single_value_band_has_zero_spread():
    band = _band([5.0], sigma=2.0)
    assert band.stdev == 0.0 and band.upper == 5.0


def test_a_persistent_break_needs_the_full_run_above_the_band():
    series = [1.0, 1.0, 5.0, 5.0, 5.0]
    assert _first_persistent_break(series, upper=2.0, start_week=0, persistence=3) == 2


def test_a_single_spike_above_the_band_is_not_a_break():
    series = [1.0, 1.0, 5.0, 1.0, 1.0]
    assert _first_persistent_break(series, upper=2.0, start_week=0, persistence=3) is None


def test_a_break_too_close_to_the_end_to_confirm_is_not_reported():
    series = [1.0, 1.0, 1.0, 5.0, 5.0]  # only two over at the end, need three
    assert _first_persistent_break(series, upper=2.0, start_week=0, persistence=3) is None


def test_none_values_do_not_count_toward_a_break():
    series = [1.0, None, 5.0, 5.0]
    assert _first_persistent_break(series, upper=2.0, start_week=0, persistence=3) is None


def test_the_detector_finds_the_lead_on_the_slowdown_fixture():
    tr = G.generate(G.CAPACITY_DROP)
    iss = reconstruct_issues(tr)
    rows = weekly_flow(iss, 26)
    res = detect(rows, iss)
    assert res.wip_signal_week is not None
    assert res.cycle_signal_week is not None
    assert res.lead_weeks == res.cycle_signal_week - res.wip_signal_week
    assert res.lead_weeks > 0


def test_wip_signals_before_the_cycle_time_average_on_the_slowdown():
    tr = G.generate(G.CAPACITY_DROP)
    iss = reconstruct_issues(tr)
    res = detect(weekly_flow(iss, 26), iss)
    assert res.wip_signal_week < res.cycle_signal_week


def test_the_steady_fixture_breaks_neither_band():
    tr = G.generate(G.STEADY)
    iss = reconstruct_issues(tr)
    res = detect(weekly_flow(iss, 26), iss)
    assert res.wip_signal_week is None
    assert res.cycle_signal_week is None


def test_has_leading_signal_is_true_when_wip_breaks_before_cycle_time():
    tr = G.generate(G.CAPACITY_DROP)
    iss = reconstruct_issues(tr)
    assert has_leading_signal(detect(weekly_flow(iss, 26), iss)) is True


def test_has_leading_signal_is_false_when_nothing_breaks():
    tr = G.generate(G.STEADY)
    iss = reconstruct_issues(tr)
    assert has_leading_signal(detect(weekly_flow(iss, 26), iss)) is False


def test_the_survivorship_gap_is_positive_during_the_slowdown():
    tr = G.generate(G.CAPACITY_DROP)
    iss = reconstruct_issues(tr)
    res = detect(weekly_flow(iss, 26), iss)
    assert res.survivorship_gap_pct is not None
    assert res.survivorship_gap_pct > 0
    assert res.eventual_ct_at_worst > res.reported_ct_at_worst


def test_the_survivorship_worst_week_is_after_the_baseline_window():
    tr = G.generate(G.CAPACITY_DROP)
    iss = reconstruct_issues(tr)
    res = detect(weekly_flow(iss, 26), iss)
    assert res.survivorship_worst_week >= DEFAULT.baseline_start_week + DEFAULT.baseline_weeks


def test_flat_weeks_counts_weeks_wip_over_band_while_cycle_time_is_inside():
    tr = G.generate(G.CAPACITY_DROP)
    iss = reconstruct_issues(tr)
    res = detect(weekly_flow(iss, 26), iss)
    assert 0 < res.flat_weeks_while_wip_over_band <= res.lead_weeks


def test_a_transient_burst_still_registers_a_leading_signal():
    a = analyze(G.generate(G.TRANSIENT_BURST), weeks=26)
    assert has_leading_signal(a.detector) is True


def test_an_empty_series_has_no_persistent_break():
    assert _first_persistent_break([], upper=1.0, start_week=0, persistence=3) is None


def test_a_wip_break_with_no_cycle_break_yet_is_still_a_leading_signal():
    # The early-warning case: WIP has broken its band and the lagging average has
    # not caught up at all. This must read as a signal, not as "all clear".
    from flowmetrics.detector import Band, DetectorResult

    res = DetectorResult(
        wip_band=Band(0, 0, 1),
        cycle_band=Band(0, 0, 1),
        wip_signal_week=10,
        cycle_signal_week=None,
        lead_weeks=None,
        flat_weeks_while_wip_over_band=3,
        survivorship_worst_week=None,
        reported_ct_at_worst=None,
        eventual_ct_at_worst=None,
        survivorship_gap_pct=None,
    )
    assert has_leading_signal(res) is True
