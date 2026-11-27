"""Little's Law as a cross-check on the reported cycle-time average.

Little's Law says that for a stable system the average time in the system equals
the average work in progress divided by the average throughput: W = L / lambda.
This file exists to turn that identity into a second, independent estimate of
cycle time, computed only from WIP and throughput, and to compare it against the
cycle time the dashboard actually reports (the mean of completed items).

The two estimates agree while the system is in steady state. They diverge during a
slowdown, and the direction of the divergence is the whole point: WIP rises the
moment demand outruns capacity, so the law implies a longer cycle time at once,
while the reported average (built only from items that have finished) stays flat
because the slow items have not finished yet. The divergence is therefore a
leading indicator built from the same board data, and it does not need hindsight.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from flowmetrics.config import DEFAULT, FlowConfig
from flowmetrics.flow import WeeklyFlow


@dataclass(frozen=True)
class LittlesRow:
    week: int
    # Trailing mean WIP (items), a window average of end-of-week WIP.
    avg_wip: float | None
    # Trailing mean throughput (items per week).
    throughput_rate: float | None
    # Little's Law implied cycle time, in days: avg_wip / throughput_rate, in weeks,
    # converted to days. This is the cycle time the WIP and throughput imply.
    implied_ct_days: float | None
    # The cycle time the dashboard reports: trailing mean of completed items, days.
    reported_ct_days: float | None
    # Signed relative divergence (implied - reported) / implied, as a percentage.
    # Positive means the law implies a slower system than the reported average admits.
    divergence_pct: float | None


def _trailing(rows: list[WeeklyFlow], w: int, window: int) -> list[WeeklyFlow]:
    lo = max(0, w - window + 1)
    return rows[lo : w + 1]


def littles_series(rows: list[WeeklyFlow], config: FlowConfig = DEFAULT) -> list[LittlesRow]:
    """Compute the implied-vs-reported cycle time and their divergence per week.

    Everything is trailing-windowed (default four weeks) so a single quiet week
    does not whipsaw the estimate. A window with no completions yields a ``None``
    reported cycle time and therefore no divergence, rather than a fabricated zero.
    """
    wl = config.week_length_days
    out: list[LittlesRow] = []
    for w in range(len(rows)):
        window = _trailing(rows, w, config.trailing_weeks)
        avg_wip = mean([r.avg_wip for r in window]) if window else None
        tps = [r.throughput for r in window]
        tp_rate = mean(tps) if tps else None
        cts = [r.mean_cycle_time for r in window if r.mean_cycle_time is not None]
        reported_days = mean(cts) if cts else None

        if avg_wip is not None and tp_rate and tp_rate > 0:
            implied_weeks = avg_wip / tp_rate
            implied_days = implied_weeks * wl
        else:
            implied_days = None

        if implied_days is not None and implied_days > 0 and reported_days is not None:
            divergence = (implied_days - reported_days) / implied_days * 100.0
        else:
            divergence = None

        out.append(
            LittlesRow(
                week=w,
                avg_wip=avg_wip,
                throughput_rate=tp_rate,
                implied_ct_days=implied_days,
                reported_ct_days=reported_days,
                divergence_pct=divergence,
            )
        )
    return out


def divergence_summary(
    littles: list[LittlesRow],
    steady_weeks: range,
    transition_weeks: range,
) -> dict:
    """Mean absolute divergence over a steady span and a transition span, and the
    ratio between them.

    The ratio is the machine-independent headline: a pure number saying how many
    times wider the gap between Little's Law and the reported average is during the
    transition than during steady state.
    """

    def _mean_abs(span: range) -> float | None:
        vals = [
            abs(littles[w].divergence_pct)
            for w in span
            if littles[w].divergence_pct is not None
        ]
        return mean(vals) if vals else None

    steady = _mean_abs(steady_weeks)
    transition = _mean_abs(transition_weeks)
    ratio = (transition / steady) if (steady and transition and steady > 0) else None
    return {
        "steady_mean_abs_divergence_pct": steady,
        "transition_mean_abs_divergence_pct": transition,
        "ratio": ratio,
    }
