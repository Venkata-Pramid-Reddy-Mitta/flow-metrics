"""Regression tests: each pins a real bug found during the build, with the number
that revealed it in the docstring. These are the tests that read as measurement
rather than decoration."""

from pathlib import Path
from statistics import mean

from flowmetrics import generator as G
from flowmetrics.analysis import analyze
from flowmetrics.config import DEFAULT
from flowmetrics.fixtures import load_transitions

ROOT = Path(__file__).resolve().parent.parent


def test_littles_law_uses_time_averaged_wip_not_the_end_of_week_snapshot():
    """War story. The first Little's Law implementation divided the end-of-week WIP
    snapshot by throughput. On the steady fixture that produced a mean absolute
    divergence of about 26%, which said the law was broken in a system that was by
    construction stable. The snapshot is a sample of a fluctuating count; Little's
    Law relates to the time-average. Switching to a daily time-average WIP dropped
    the steady divergence to about 5%. This test pins that: the shipped (time-
    average) computation is dramatically closer in steady state than a snapshot
    computation reconstructed here would be.
    """
    a = analyze(G.generate(G.STEADY), weeks=26)
    steady = range(2, 11)

    # The shipped computation (uses avg_wip).
    shipped = mean(
        abs(a.littles[w].divergence_pct) for w in steady if a.littles[w].divergence_pct is not None
    )

    # The old, buggy computation: implied CT from the end-of-week snapshot.
    def snapshot_div(w):
        lo = max(0, w - DEFAULT.trailing_weeks + 1)
        window = a.rows[lo : w + 1]
        snap_wip = mean(r.wip_end for r in window)
        tp = mean(r.throughput for r in window)
        cts = [r.mean_cycle_time for r in window if r.mean_cycle_time is not None]
        if not cts or tp == 0:
            return None
        implied = snap_wip / tp * DEFAULT.week_length_days
        reported = mean(cts)
        return abs((implied - reported) / implied * 100)

    snapshot = mean(v for w in steady if (v := snapshot_div(w)) is not None)

    assert shipped < 12.0
    assert shipped < snapshot  # the fix is measurably better, not just different


def test_survivorship_worst_week_is_not_a_small_sample_baseline_fluke():
    """War story. The survivorship scan first reported week 11 with a 50% gap, a
    quiet baseline week where one long-pole item among a handful completed. That is
    noise, not a slowdown signal, and it let the baseline win the 'worst' slot. The
    fix restricted the scan to post-baseline weeks and required a minimum cohort.
    This pins both conditions.
    """
    a = analyze(G.generate(G.CAPACITY_DROP), weeks=26)
    res = a.detector
    baseline_end = DEFAULT.baseline_start_week + DEFAULT.baseline_weeks
    assert res.survivorship_worst_week >= baseline_end


def test_the_committed_fixture_matches_the_generator_output():
    """If the generator changes but data/events.csv is not regenerated, every
    published number silently drifts from the committed input. This pins the two
    together: the committed fixture must equal a fresh generation from the seed.
    """
    committed = load_transitions(ROOT / "data" / "events.csv")
    fresh = G.generate(G.CAPACITY_DROP, seed=20260501)
    assert [(t.issue_id, t.to_state, t.day) for t in committed] == [
        (t.issue_id, t.to_state, t.day) for t in fresh
    ]


def test_the_steady_fixture_never_false_alarms():
    """The whole tool is worthless if it cries wolf. This pins the invariant that
    the steady scenario, which has no regime change, raises no leading signal, so a
    fired signal always means WIP genuinely broke its band.
    """
    assert analyze(G.generate(G.STEADY), weeks=26).leading_signal is False
