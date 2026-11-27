"""The detector: when WIP breaks its baseline, when the cycle-time average
finally follows, and how far apart those two weeks are.

This file exists to make the project's one-sentence claim measurable. It learns a
"normal" band for WIP and for the cycle-time average from a baseline window, then
finds the first week each series breaks its own band and stays broken. The gap
between those two weeks (WIP first, cycle time later) is the lead the tool buys
you. The survivorship measure is here too, because it answers the obvious
objection: the cycle-time average is not merely late, it is biased downward during
a slowdown, since the slowest work is still open and therefore uncounted.

Nothing in this module knows where the onset is. It learns the band from data and
scans. That is the point: on a real board you do not get told the onset day.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev

from flowmetrics.config import DEFAULT, FlowConfig
from flowmetrics.flow import WeeklyFlow
from flowmetrics.model import Issue


@dataclass(frozen=True)
class Band:
    mean: float
    stdev: float
    upper: float


def _band(values: list[float], sigma: float) -> Band:
    m = mean(values)
    s = pstdev(values) if len(values) > 1 else 0.0
    return Band(mean=m, stdev=s, upper=m + sigma * s)


def _first_persistent_break(
    series: list[float | None],
    upper: float,
    start_week: int,
    persistence: int,
) -> int | None:
    """First week at or after ``start_week`` that begins a run of ``persistence``
    consecutive weeks strictly above ``upper``.

    Returns the first week of the run, which is the week a watching team would
    have seen the band broken for the first time, not the week the run was
    confirmed. Confirmation latency is a separate, honest cost discussed in the
    README's trade-off table.
    """
    n = len(series)
    for w in range(start_week, n):
        window = series[w : w + persistence]
        if len(window) < persistence:
            return None
        if all(v is not None and v > upper for v in window):
            return w
    return None


@dataclass(frozen=True)
class DetectorResult:
    wip_band: Band
    cycle_band: Band
    wip_signal_week: int | None
    cycle_signal_week: int | None
    lead_weeks: int | None
    flat_weeks_while_wip_over_band: int
    # Survivorship: worst week, the reported mean vs the eventual mean, and the gap.
    survivorship_worst_week: int | None
    reported_ct_at_worst: float | None
    eventual_ct_at_worst: float | None
    survivorship_gap_pct: float | None


# A week's survivorship cohort must have at least this many eventually-finished
# open items before its gap is trusted. A gap computed from one or two long-pole
# items is small-sample noise, not a signal, and would otherwise let a quiet
# baseline week win the "worst" slot.
_MIN_COHORT = 6


def _eventual_cohort(issues: list[Issue], day_end: int) -> list[int]:
    """Eventual cycle times of the issues open at this week's end.

    Computed with hindsight, after the whole window has run, so it is explicitly
    not a number a team could read in the moment. It is the yardstick that shows
    how far the in-the-moment reported average fell short. Open issues that never
    finish within the window are excluded, which makes this a conservative
    (under-)estimate of the true gap.
    """
    return [
        iss.cycle_time_days
        for iss in issues
        if iss.start_day <= day_end
        and (iss.done_day is None or iss.done_day > day_end)
        and iss.cycle_time_days is not None
    ]


def detect(
    rows: list[WeeklyFlow],
    issues: list[Issue],
    config: FlowConfig = DEFAULT,
) -> DetectorResult:
    base_lo = config.baseline_start_week
    base_hi = config.baseline_start_week + config.baseline_weeks
    baseline = rows[base_lo:base_hi]

    wip_band = _band([float(r.wip_end) for r in baseline], config.band_sigma)
    cycle_vals = [r.mean_cycle_time for r in baseline if r.mean_cycle_time is not None]
    cycle_band = _band(cycle_vals, config.band_sigma)

    wip_series: list[float | None] = [float(r.wip_end) for r in rows]
    cycle_series: list[float | None] = [r.mean_cycle_time for r in rows]

    scan_from = base_hi
    wip_week = _first_persistent_break(
        wip_series, wip_band.upper, scan_from, config.persistence_weeks
    )
    cycle_week = _first_persistent_break(
        cycle_series, cycle_band.upper, scan_from, config.persistence_weeks
    )

    lead = None
    if wip_week is not None and cycle_week is not None:
        lead = cycle_week - wip_week

    # Weeks where WIP is over its band but the cycle-time average is still inside
    # its own band: the window during which the lagging number says "fine".
    flat = 0
    if wip_week is not None:
        upper_to = cycle_week if cycle_week is not None else len(rows)
        for w in range(wip_week, upper_to):
            cv = rows[w].mean_cycle_time
            if rows[w].wip_end > wip_band.upper and (cv is None or cv <= cycle_band.upper):
                flat += 1

    # Survivorship: scan post-baseline weeks for the largest shortfall of the
    # reported average against the eventual average of the cohort alive that week.
    # The scan starts after the baseline so a small-sample quiet week cannot win,
    # and requires a minimum cohort so the gap rests on real work, not one
    # long-pole item.
    worst_week = None
    worst_reported = None
    worst_eventual = None
    worst_gap = None
    for r in rows[base_hi:]:
        reported = r.mean_cycle_time
        cohort = _eventual_cohort(issues, r.day_end)
        if reported is None or len(cohort) < _MIN_COHORT:
            continue
        eventual = mean(cohort)
        if eventual <= 0:  # pragma: no cover - defensive; cycle times are always positive
            continue
        gap = (eventual - reported) / eventual * 100.0
        if worst_gap is None or gap > worst_gap:
            worst_gap = gap
            worst_week = r.week
            worst_reported = reported
            worst_eventual = eventual

    return DetectorResult(
        wip_band=wip_band,
        cycle_band=cycle_band,
        wip_signal_week=wip_week,
        cycle_signal_week=cycle_week,
        lead_weeks=lead,
        flat_weeks_while_wip_over_band=flat,
        survivorship_worst_week=worst_week,
        reported_ct_at_worst=worst_reported,
        eventual_ct_at_worst=worst_eventual,
        survivorship_gap_pct=worst_gap,
    )


def has_leading_signal(result: DetectorResult) -> bool:
    """True when WIP broke its band and did so before the cycle-time average.

    This is the condition the CLI turns into exit code 2. A WIP break with no
    cycle-time break yet still counts: that is precisely the early-warning case.
    """
    if result.wip_signal_week is None:
        return False
    if result.cycle_signal_week is None:
        return True
    return result.wip_signal_week <= result.cycle_signal_week
