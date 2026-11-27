"""Tests for the analysis facade and the summary dict the receipts tooling reads."""

from flowmetrics import generator as G
from flowmetrics.analysis import analyze, summary


def _summary(scenario):
    return summary(analyze(G.generate(scenario), weeks=26))


def test_summary_exposes_every_published_figure_by_key():
    s = _summary(G.CAPACITY_DROP)
    for key in (
        "lead_weeks",
        "flat_weeks",
        "survivorship_gap_pct",
        "littles_divergence_ratio",
        "wip_signal_week",
        "cycle_signal_week",
    ):
        assert key in s


def test_summary_is_json_serialisable_with_no_custom_types():
    import json

    json.dumps(_summary(G.CAPACITY_DROP))


def test_summary_lead_matches_the_signal_week_difference():
    s = _summary(G.CAPACITY_DROP)
    assert s["lead_weeks"] == s["cycle_signal_week"] - s["wip_signal_week"]


def test_summary_marks_the_steady_scenario_as_no_leading_signal():
    assert _summary(G.STEADY)["leading_signal"] is False


def test_summary_reports_the_fixture_issue_count():
    s = _summary(G.CAPACITY_DROP)
    assert s["issues_total"] > 0


def test_summary_peak_wip_is_the_maximum_weekly_wip():
    a = analyze(G.generate(G.CAPACITY_DROP), weeks=26)
    assert summary(a)["peak_wip"] == max(r.wip_end for r in a.rows)


def test_summary_rounds_floats_to_one_decimal():
    s = _summary(G.CAPACITY_DROP)
    assert s["reported_ct_at_worst_days"] == round(s["reported_ct_at_worst_days"], 1)
