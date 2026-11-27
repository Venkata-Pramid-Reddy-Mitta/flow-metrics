"""Experiment: how far does the reported cycle-time average understate the
eventual experience during the slowdown?

Question the README asks: the completed-cycle mean excludes the items still open,
which are exactly the ones aging. By how much does that bias the number a team
reads, at its worst, on the fixture? This reports the worst week, the reported
mean that week, the eventual mean of the work alive that week, and the gap.
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
        "worst_week": s["survivorship_worst_week"],
        "reported_ct_days": s["reported_ct_at_worst_days"],
        "eventual_ct_days": s["eventual_ct_at_worst_days"],
        "survivorship_gap_pct": s["survivorship_gap_pct"],
    }
    write_result("survivorship", payload)
    print_table(
        "Survivorship bias in the reported average",
        [
            ("worst week", s["survivorship_worst_week"]),
            ("reported mean cycle time (days)", s["reported_ct_at_worst_days"]),
            ("eventual mean of work alive that week (days)", s["eventual_ct_at_worst_days"]),
            ("understatement (%)", s["survivorship_gap_pct"]),
        ],
    )
    return payload


if __name__ == "__main__":
    run()
