"""Experiment: does Little's Law hold in steady state and break in the transition?

Question the README asks: Little's Law turns WIP and throughput into an implied
cycle time with no hindsight. How closely does it track the reported average while
the system is stable, and how far do they diverge once demand outruns capacity?
This reports the mean absolute divergence over a steady span and a transition
span, and the ratio between them.
"""

from __future__ import annotations

from _common import print_table, write_result

from flowmetrics.analysis import analyze, summary
from flowmetrics.fixtures import load_transitions


def run() -> dict:
    transitions = load_transitions("data/events.csv")
    analysis = analyze(transitions, weeks=26)
    s = summary(analysis)

    payload = {
        "steady_divergence_pct": s["littles_divergence_steady_pct"],
        "transition_divergence_pct": s["littles_divergence_transition_pct"],
        "ratio": s["littles_divergence_ratio"],
    }
    write_result("littles_divergence", payload)
    print_table(
        "Little's Law: steady vs transition divergence",
        [
            ("mean abs divergence, steady (%)", s["littles_divergence_steady_pct"]),
            ("mean abs divergence, transition (%)", s["littles_divergence_transition_pct"]),
            ("ratio (transition / steady)", s["littles_divergence_ratio"]),
        ],
    )
    return payload


if __name__ == "__main__":
    run()
