"""Reconstruct issues from a transition stream and roll them up by week.

This file exists to turn a flat event log into the three weekly series the rest
of the tool reasons about: work in progress at week end (WIP), items completed in
the week (throughput), and the mean cycle time of the items completed that week.
The ordering of these three matters for the argument the project makes, so they
are computed together and kept together in one ``WeeklyFlow`` row.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from flowmetrics.config import DEFAULT, FlowConfig
from flowmetrics.model import DONE_STATE, Issue, Transition


def reconstruct_issues(transitions: list[Transition]) -> list[Issue]:
    """Stitch transitions into issues, keyed by issue id.

    The first entry into in_progress sets the start day; the first entry into done
    sets the done day. Later transitions for the same issue are ignored on
    purpose: a reopened-and-reclosed issue is out of scope for this model, and
    ADR-001 records that as a stated boundary rather than a silent one.
    """
    starts: dict[str, int] = {}
    dones: dict[str, int] = {}
    order: list[str] = []
    for t in transitions:
        if t.issue_id not in starts and t.issue_id not in dones:
            order.append(t.issue_id)
        if t.to_state == "in_progress" and t.issue_id not in starts:
            starts[t.issue_id] = t.day
        elif t.to_state == DONE_STATE and t.issue_id not in dones:
            dones[t.issue_id] = t.day

    issues: list[Issue] = []
    for iid in order:
        if iid not in starts:
            # A done event with no in_progress entry: unusable for cycle time.
            # We keep the model honest by skipping it rather than inventing a
            # start day. In the committed fixture this never happens.
            continue
        issues.append(Issue(issue_id=iid, start_day=starts[iid], done_day=dones.get(iid)))
    return issues


@dataclass(frozen=True)
class WeeklyFlow:
    """One week's flow numbers.

    ``mean_cycle_time`` is ``None`` for a week with no completions. That is not a
    rounding convenience: a week that finished nothing has no cycle-time average,
    and forcing it to zero would drag the trailing mean down exactly when the
    system has stalled, which is the opposite of the truth.

    Two WIP numbers are kept on purpose. ``wip_end`` is the end-of-week snapshot, a
    board reading, and it is what the detector bands because that is what a team
    watches. ``avg_wip`` is the time-average over the week's days, which is the
    quantity Little's Law actually relates to throughput; using the snapshot there
    would make the law look broken in steady state (see ADR-003).
    """

    week: int
    day_end: int
    wip_end: int
    avg_wip: float
    throughput: int
    mean_cycle_time: float | None


def _week_of_day(day: int, week_length: int) -> int:
    return day // week_length


def daily_wip(issues: list[Issue], days: int) -> list[int]:
    """WIP on each day: issues started on or before the day and not yet done.

    An issue counts on its done day too (it was worked that day), so completion is
    counted at end of day. This is the series Little's Law needs time-averaged.
    """
    series = []
    for d in range(days):
        series.append(
            sum(1 for i in issues if i.start_day <= d and (i.done_day is None or i.done_day >= d))
        )
    return series


def weekly_flow(
    issues: list[Issue],
    weeks: int,
    config: FlowConfig = DEFAULT,
) -> list[WeeklyFlow]:
    """Build the per-week series over ``weeks`` weeks.

    WIP at week end counts issues that had started by the last day of the week and
    were not yet done by that day. Throughput counts issues whose done day fell in
    the week. The cycle-time average is over exactly those completed issues.
    """
    wl = config.week_length_days
    dwip = daily_wip(issues, weeks * wl)
    rows: list[WeeklyFlow] = []
    for w in range(weeks):
        day_start = w * wl
        day_end = (w + 1) * wl - 1
        wip = 0
        completed_cts: list[int] = []
        throughput = 0
        for iss in issues:
            if iss.start_day > day_end:
                continue
            if iss.done_day is None or iss.done_day > day_end:
                wip += 1
            if iss.done_day is not None and _week_of_day(iss.done_day, wl) == w:
                throughput += 1
                ct = iss.cycle_time_days
                if ct is not None:
                    completed_cts.append(ct)
        mct = mean(completed_cts) if completed_cts else None
        avg_wip = mean(dwip[day_start : day_end + 1])
        rows.append(
            WeeklyFlow(
                week=w,
                day_end=day_end,
                wip_end=wip,
                avg_wip=avg_wip,
                throughput=throughput,
                mean_cycle_time=mct,
            )
        )
    return rows
