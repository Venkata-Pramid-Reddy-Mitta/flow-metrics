"""Tests for the seeded generator: determinism and the scenarios' behavior."""

from flowmetrics import generator as G
from flowmetrics.analysis import analyze
from flowmetrics.flow import reconstruct_issues


def test_the_same_seed_produces_a_byte_identical_transition_stream():
    a = G.generate(G.CAPACITY_DROP, seed=20260501)
    b = G.generate(G.CAPACITY_DROP, seed=20260501)
    assert [(t.issue_id, t.to_state, t.day) for t in a] == [
        (t.issue_id, t.to_state, t.day) for t in b
    ]


def test_a_different_seed_produces_a_different_stream():
    a = G.generate(G.CAPACITY_DROP, seed=1)
    b = G.generate(G.CAPACITY_DROP, seed=2)
    assert a != b


def test_the_stream_is_ordered_by_day_then_issue_then_state():
    tr = G.generate(G.CAPACITY_DROP)
    keys = [(t.day, t.issue_id, t.to_state) for t in tr]
    assert keys == sorted(keys)


def test_no_transition_belongs_to_an_item_that_both_started_and_finished_in_burn_in():
    # Every emitted issue must touch the recorded window: open at day 0 or done on
    # or after day 0. An item fully inside the burn-in would have a done day < 0.
    issues = reconstruct_issues(G.generate(G.CAPACITY_DROP))
    for iss in issues:
        assert iss.done_day is None or iss.done_day >= 0


def test_some_issues_start_before_day_zero_so_the_window_begins_mid_flight():
    issues = reconstruct_issues(G.generate(G.CAPACITY_DROP))
    assert any(iss.start_day < 0 for iss in issues)


def test_the_steady_scenario_raises_no_leading_signal():
    a = analyze(G.generate(G.STEADY), weeks=26)
    assert a.leading_signal is False


def test_the_capacity_drop_scenario_raises_a_leading_signal():
    a = analyze(G.generate(G.CAPACITY_DROP), weeks=26)
    assert a.leading_signal is True


def test_the_transient_burst_also_raises_a_leading_signal_at_onset():
    # The boundary: a burst that will clear trips the same alarm as a real slowdown.
    a = analyze(G.generate(G.TRANSIENT_BURST), weeks=26)
    assert a.leading_signal is True


def test_the_capacity_drop_wip_keeps_climbing_while_the_burst_recovers():
    drop = analyze(G.generate(G.CAPACITY_DROP), weeks=26).rows
    burst = analyze(G.generate(G.TRANSIENT_BURST), weeks=26).rows
    assert drop[-1].wip_end > drop[20].wip_end  # still rising at the end
    assert burst[-1].wip_end < max(r.wip_end for r in burst)  # fell back from its peak


def test_every_scenario_is_registered_by_name():
    assert set(G.SCENARIOS) == {"steady", "capacity_drop", "transient_burst"}


def test_arrivals_scale_up_after_onset_in_the_burst_scenario():
    # More issues are created in the burst than in steady over the same window.
    steady = len(reconstruct_issues(G.generate(G.STEADY)))
    burst = len(reconstruct_issues(G.generate(G.TRANSIENT_BURST)))
    assert burst > steady


def test_capacity_is_the_normal_value_before_onset_and_lower_after():
    assert G._capacity(G.CAPACITY_DROP, 0) == 12.0
    assert G._capacity(G.CAPACITY_DROP, 200) == 7.5


def test_arrival_multiplier_is_one_before_onset_and_elevated_during_the_burst():
    assert G._arrival_mult(G.TRANSIENT_BURST, 0) == 1.0
    assert G._arrival_mult(G.TRANSIENT_BURST, 90) > 1.0


def test_arrival_multiplier_returns_to_one_after_the_burst_recovers():
    assert G._arrival_mult(G.TRANSIENT_BURST, 200) == 1.0
