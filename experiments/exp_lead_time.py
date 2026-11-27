"""Experiment: how many weeks does WIP lead the cycle-time average?

Question the README asks: if WIP is a leading indicator and the completed-cycle
mean is a lagging one, how large is the gap in practice on the fixture? This runs
the analysis on the committed slowdown fixture and reports the week each series
first broke its band and the lead between them.
"""

from __future__ import annotations

from _common import print_table, write_result

from flowmetrics.analysis import analyze, summary
from flowmetrics.fixtures import load_transitions
from flowmetrics.generator import SCENARIOS, generate


def run() -> dict:
    transitions = load_transitions("data/events.csv")
    analysis = analyze(transitions, weeks=26)
    s = summary(analysis)

    # Cross-check: the steady fixture must produce no signal at all.
    steady = analyze(generate(SCENARIOS["steady"]), weeks=26)

    payload = {
        "scenario": "capacity_drop",
        "onset_week": s["onset_week"],
        "wip_signal_week": s["wip_signal_week"],
        "cycle_signal_week": s["cycle_signal_week"],
        "lead_weeks": s["lead_weeks"],
        "flat_weeks": s["flat_weeks"],
        "steady_scenario_signals": steady.leading_signal,
    }
    write_result("lead_time", payload)
    print_table(
        "Lead time: WIP vs the cycle-time average",
        [
            ("onset week", s["onset_week"]),
            ("WIP signal week", s["wip_signal_week"]),
            ("cycle-time signal week", s["cycle_signal_week"]),
            ("lead (weeks)", s["lead_weeks"]),
            ("weeks the average stayed flat", s["flat_weeks"]),
            ("steady fixture raised a signal", steady.leading_signal),
        ],
    )
    return payload


if __name__ == "__main__":
    run()
