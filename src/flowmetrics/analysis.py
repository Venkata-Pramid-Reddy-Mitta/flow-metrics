"""One analysis path, shared by the CLI, the report, the experiments and the
receipts tooling.

This file exists so there is exactly one way the numbers are produced. If the CLI
computed the lead one way and the report another, a reviewer could not trust that
the screenshot and the headline agree. Everything funnels through ``analyze`` and
``summary``.
"""

from __future__ import annotations

from dataclasses import dataclass

from flowmetrics.config import DEFAULT, FlowConfig
from flowmetrics.detector import DetectorResult, detect, has_leading_signal
from flowmetrics.flow import WeeklyFlow, reconstruct_issues, weekly_flow
from flowmetrics.littles import LittlesRow, divergence_summary, littles_series
from flowmetrics.model import Issue, Transition


@dataclass(frozen=True)
class Analysis:
    weeks: int
    issues: list[Issue]
    rows: list[WeeklyFlow]
    littles: list[LittlesRow]
    detector: DetectorResult
    config: FlowConfig

    @property
    def leading_signal(self) -> bool:
        return has_leading_signal(self.detector)


def analyze(
    transitions: list[Transition],
    weeks: int,
    config: FlowConfig = DEFAULT,
) -> Analysis:
    issues = reconstruct_issues(transitions)
    rows = weekly_flow(issues, weeks, config)
    littles = littles_series(rows, config)
    det = detect(rows, issues, config)
    return Analysis(
        weeks=weeks, issues=issues, rows=rows, littles=littles, detector=det, config=config
    )


def _onset_guess(weeks: int) -> int:
    # The fixture's onset is week 12 by construction. The detector never uses this;
    # it is only for drawing the onset marker and for the steady/transition spans
    # the divergence summary compares. Kept here so the report and experiments mark
    # the same week.
    return 12


def summary(analysis: Analysis) -> dict:
    """A flat, JSON-serialisable dict of every published figure.

    This is the single source the report prints and the receipts tooling checks.
    No figure is computed anywhere else for publication.
    """
    d = analysis.detector
    onset = _onset_guess(analysis.weeks)
    steady_span = range(2, onset - 1)
    transition_span = range(onset + 2, min(onset + 12, analysis.weeks))
    div = divergence_summary(analysis.littles, steady_span, transition_span)

    peak_wip = max(r.wip_end for r in analysis.rows)
    return {
        "weeks": analysis.weeks,
        "issues_total": len(analysis.issues),
        "onset_week": onset,
        "wip_signal_week": d.wip_signal_week,
        "cycle_signal_week": d.cycle_signal_week,
        "lead_weeks": d.lead_weeks,
        "flat_weeks": d.flat_weeks_while_wip_over_band,
        "leading_signal": analysis.leading_signal,
        "survivorship_worst_week": d.survivorship_worst_week,
        "reported_ct_at_worst_days": _round(d.reported_ct_at_worst),
        "eventual_ct_at_worst_days": _round(d.eventual_ct_at_worst),
        "survivorship_gap_pct": _round(d.survivorship_gap_pct),
        "peak_wip": peak_wip,
        "wip_band_upper": _round(d.wip_band.upper),
        "cycle_band_upper": _round(d.cycle_band.upper),
        "littles_divergence_steady_pct": _round(div["steady_mean_abs_divergence_pct"]),
        "littles_divergence_transition_pct": _round(div["transition_mean_abs_divergence_pct"]),
        "littles_divergence_ratio": _round(div["ratio"]),
    }


def _round(x: float | None, ndigits: int = 1) -> float | None:
    return None if x is None else round(x, ndigits)
