"""Experiment: can the tool tell a real slowdown from a transient burst at the
moment the alarm fires?

This is the boundary the README leads toward, not a win. A permanent capacity drop
and a four-week arrival burst both push WIP over its band at essentially the same
week, so the detector fires on both. Only later, once the burst's WIP turns back
down while the real slowdown keeps climbing, can they be told apart. This script
measures how close the two WIP paths are in the weeks right after the alarm, and
how many weeks pass before they have clearly diverged.
"""

from __future__ import annotations

from _common import print_table, write_result

from flowmetrics.analysis import analyze
from flowmetrics.generator import SCENARIOS, generate


def _wip(scenario_name: str) -> list[int]:
    a = analyze(generate(SCENARIOS[scenario_name]), weeks=26)
    return [r.wip_end for r in a.rows]


def run() -> dict:
    drop = analyze(generate(SCENARIOS["capacity_drop"]), weeks=26)
    burst = analyze(generate(SCENARIOS["transient_burst"]), weeks=26)
    drop_wip = [r.wip_end for r in drop.rows]
    burst_wip = [r.wip_end for r in burst.rows]

    drop_sig = drop.detector.wip_signal_week
    burst_sig = burst.detector.wip_signal_week
    alarm = max(w for w in (drop_sig, burst_sig) if w is not None)

    # Max relative difference between the two WIP paths over the first three weeks
    # after the later alarm: small means indistinguishable at alarm time.
    window = range(alarm, min(alarm + 3, 26))
    rel_diffs = [
        abs(drop_wip[w] - burst_wip[w]) / max(drop_wip[w], burst_wip[w], 1) for w in window
    ]
    max_rel_diff_early_pct = round(max(rel_diffs) * 100, 1)

    # First week after the alarm where the paths have clearly diverged: the burst
    # has fallen at least 25% below its own running peak while the drop is still at
    # or above its band. This is the earliest a watcher could call it.
    diverge_week = None
    burst_peak = 0
    for w in range(alarm, 26):
        burst_peak = max(burst_peak, burst_wip[w])
        burst_down = burst_wip[w] <= 0.75 * burst_peak
        drop_up = drop_wip[w] >= drop.detector.wip_band.upper
        if burst_down and drop_up:
            diverge_week = w
            break

    ambiguous_weeks = None if diverge_week is None else diverge_week - alarm

    payload = {
        "drop_wip_signal_week": drop_sig,
        "burst_wip_signal_week": burst_sig,
        "alarm_week": alarm,
        "max_rel_wip_diff_first_3wk_pct": max_rel_diff_early_pct,
        "distinguishable_from_week": diverge_week,
        "ambiguous_weeks": ambiguous_weeks,
    }
    write_result("indistinguishable_onset", payload)
    print_table(
        "Indistinguishable onset: slowdown vs transient burst",
        [
            ("capacity_drop WIP signal week", drop_sig),
            ("transient_burst WIP signal week", burst_sig),
            ("alarm week (the later of the two)", alarm),
            ("max WIP difference, first 3 weeks (%)", max_rel_diff_early_pct),
            ("distinguishable from week", diverge_week),
            ("weeks of ambiguity after the alarm", ambiguous_weeks),
        ],
    )
    return payload


if __name__ == "__main__":
    run()
