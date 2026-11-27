"""Every tunable number the analytics use, in one dataclass.

This file exists so that paths, window sizes and detector thresholds are
configuration rather than magic constants buried in functions. A reviewer who
disagrees with the four-week trailing window or the two-sigma band changes one
field here and re-runs, instead of grepping for a literal. The defaults are the
values the published figures were measured at.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FlowConfig:
    # --- windowing ---
    week_length_days: int = 7
    # Weeks used to learn the "normal" baseline before the detector starts
    # scanning. Kept well before any onset so the baseline is not contaminated by
    # the event it is meant to catch.
    baseline_weeks: int = 8
    # First week the baseline is considered valid. Week 0 is a warm-start artifact
    # of the fixture, so the baseline learns from week 1 onward.
    baseline_start_week: int = 1
    # Trailing window for the Little's Law rates and for the cycle-time average.
    trailing_weeks: int = 4

    # --- detector ---
    # Upper band = baseline mean + band_sigma * baseline stdev. Chosen at 2.5
    # rather than 2.0 because at this board size ordinary week-to-week variance
    # crosses a two-sigma band often enough to false-alarm on the steady fixture;
    # 2.5 keeps the steady scenario silent while still catching the slowdown early.
    band_sigma: float = 2.5
    # A signal must persist this many consecutive weeks above the band before it
    # is reported. One or two weeks over the band is noise at this scale;
    # three consecutive weeks is the signal. This trades a little detection latency
    # for no false alarms on the steady fixture, a trade the README prices.
    persistence_weeks: int = 3

    # --- paths ---
    fixture_path: str = "data/events.csv"
    metrics_path: str = "docs/metrics.json"
    report_path: str = "docs/report.html"
    experiments_dir: str = "docs/experiments"


DEFAULT = FlowConfig()
