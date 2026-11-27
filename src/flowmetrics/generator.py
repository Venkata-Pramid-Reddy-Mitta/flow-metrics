"""A seeded, deterministic generator of issue state-transition streams.

This file exists because the project's whole claim is reproducibility: a reviewer
must be able to rebuild the exact event log every number is measured from, on any
machine, with no network. So the generator uses ``random.Random`` from the
standard library (whose stream is stable across Python versions and platforms)
rather than a numpy Generator (whose defaults have changed between releases), and
it emits plain integer day indices rather than timestamps.

The simulation is a limited-parallelism, finish-what-you-started queue. Items are
committed into ``in_progress`` at an arrival rate; the team advances the oldest
items first, one worker-day per item per day, up to a daily capacity. When demand
exceeds capacity the backlog of open items grows, which is the phenomenon the tool
is built to catch. ADR-002 explains why the service discipline is oldest-first
rather than processor-sharing, and what that choice does to the numbers.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from flowmetrics.model import DONE_STATE, Transition

# Effort in days an item needs, and the weights it is drawn with. Mean is about
# 4.05 days. These are deliberately lumpy (a few large items) because a flow that
# is all identical small items never produces the survivorship gap the tool
# measures: the gap needs some long-pole items that starve during a slowdown.
_EFFORTS = (2, 3, 4, 5, 6, 8)
_EFFORT_WEIGHTS = (0.15, 0.25, 0.25, 0.15, 0.12, 0.08)

# Daily arrivals (items committed into in_progress), and their weights. Mean is
# about 2.45 items/day, i.e. roughly 17 a week. The board is sized this way on
# purpose: a smaller flow has so much week-to-week variance that a steady system
# trips the detector by chance, which would make every signal suspect.
_ARRIVALS = (1, 2, 3, 4)
_ARRIVAL_WEIGHTS = (0.15, 0.40, 0.30, 0.15)


@dataclass(frozen=True)
class Scenario:
    """A named simulation configuration.

    The three scenarios exist for one reason each: ``steady`` proves the tool
    stays quiet when nothing is wrong (no false alarm), ``capacity_drop`` is the
    slowdown the headline numbers are measured on, and ``transient_burst`` is the
    case the tool deliberately cannot tell apart from a real slowdown in real time
    (ADR-004). The last one is the boundary, not a feature.
    """

    name: str
    weeks: int
    capacity_normal: float
    # Day the regime change happens (0-indexed). None means never.
    onset_day: int | None
    # Capacity after onset (for capacity_drop).
    capacity_after: float
    # Arrival multiplier after onset (for transient_burst).
    arrival_mult_after: float
    # Day the transient burst clears and arrivals return to normal. None means it
    # never clears (a permanent change).
    recovery_day: int | None


STEADY = Scenario(
    name="steady",
    weeks=26,
    capacity_normal=12.0,
    onset_day=None,
    capacity_after=12.0,
    arrival_mult_after=1.0,
    recovery_day=None,
)

CAPACITY_DROP = Scenario(
    name="capacity_drop",
    weeks=26,
    capacity_normal=12.0,
    onset_day=84,  # first day of week 12 (0-indexed)
    capacity_after=7.5,
    arrival_mult_after=1.0,
    recovery_day=None,
)

TRANSIENT_BURST = Scenario(
    name="transient_burst",
    weeks=26,
    capacity_normal=12.0,
    onset_day=84,
    capacity_after=12.0,
    arrival_mult_after=1.7,
    recovery_day=112,  # four weeks of burst, then back to normal
)

SCENARIOS = {s.name: s for s in (STEADY, CAPACITY_DROP, TRANSIENT_BURST)}


def _weighted(rng: random.Random, values: tuple, weights: tuple):
    # random.choices returns a list; take the single element. Kept tiny and
    # explicit so the determinism is obvious: one rng call per draw.
    return rng.choices(values, weights=weights, k=1)[0]


class _Item:
    __slots__ = ("issue_id", "start_day", "effort", "progress", "done_day")

    def __init__(self, issue_id: str, start_day: int, effort: int) -> None:
        self.issue_id = issue_id
        self.start_day = start_day
        self.effort = effort
        self.progress = 0.0
        self.done_day: int | None = None


def _capacity(scenario: Scenario, day: int) -> float:
    if scenario.onset_day is not None and day >= scenario.onset_day:
        return scenario.capacity_after
    return scenario.capacity_normal


def _arrival_mult(scenario: Scenario, day: int) -> float:
    if scenario.onset_day is None or day < scenario.onset_day:
        return 1.0
    if scenario.recovery_day is not None and day >= scenario.recovery_day:
        return 1.0
    return scenario.arrival_mult_after


# Unrecorded days simulated before day 0 so the board is already in its natural
# steady state when the recorded window begins. Without this the first weeks are a
# cold-start transient and the detector's baseline learns a shape that is not the
# real normal. Six weeks is comfortably longer than a few mean cycle times.
_BURN_IN_DAYS = 42


def generate(scenario: Scenario = CAPACITY_DROP, seed: int = 20260501) -> list[Transition]:
    """Simulate the scenario and return a flat, day-ordered transition stream.

    The return is the same shape a Jira export is mapped to: a list of
    (issue_id, to_state, day) transitions. The simulation starts empty at day
    ``-42`` and runs a burn-in so that by day 0 it is in steady state; only
    transitions touching the recorded window (day >= 0, plus the in_progress entry
    of any item still open at day 0) are emitted, so the fixture starts mid-flight.
    """
    rng = random.Random(seed)
    days = scenario.weeks * 7
    transitions: list[Transition] = []
    in_progress: list[_Item] = []
    all_items: list[_Item] = []
    counter = 0

    for day in range(-_BURN_IN_DAYS, days):
        # Arrivals: commit new items directly into in_progress.
        base = _weighted(rng, _ARRIVALS, _ARRIVAL_WEIGHTS)
        mult = _arrival_mult(scenario, day)
        # Expand by the multiplier deterministically: integer part plus a seeded
        # extra for the fractional part.
        n_arr = int(base * mult)
        frac = base * mult - n_arr
        if frac > 0 and rng.random() < frac:
            n_arr += 1
        for _ in range(n_arr):
            counter += 1
            iid = f"ISS-{counter:04d}"
            effort = _weighted(rng, _EFFORTS, _EFFORT_WEIGHTS)
            item = _Item(iid, day, effort)
            in_progress.append(item)
            all_items.append(item)

        # Service: shortest-remaining-first, one worker-day per item per day, total
        # capacity worker-days. This models a team that triages toward the work
        # closest to done, which is what keeps throughput up and the completed
        # cycle-time average flat while large items starve under overload. ADR-002
        # defends this discipline and quantifies how much the headline lead would
        # shrink under oldest-first (FIFO) instead.
        budget = _capacity(scenario, day)
        ordering = sorted(in_progress, key=lambda it: (it.effort - it.progress, it.issue_id))
        for item in ordering:
            if budget <= 1e-9:
                break
            grant = min(1.0, budget)
            item.progress += grant
            budget -= grant

        # Completion: anything whose progress has reached its effort enters done
        # today.
        finished = [it for it in in_progress if it.progress >= it.effort - 1e-9]
        for item in finished:
            item.done_day = day
        done_ids = {it.issue_id for it in finished}
        in_progress = [it for it in in_progress if it.issue_id not in done_ids]

    # Emit transitions only for items that touch the recorded window: still open at
    # day 0, or completed on day 0 or later. Items that both started and finished
    # during the burn-in are discarded, so the fixture begins mid-flight in a
    # steady system rather than from an empty board.
    for item in all_items:
        if item.done_day is not None and item.done_day < 0:
            continue
        transitions.append(Transition(item.issue_id, "in_progress", item.start_day))
        if item.done_day is not None:
            transitions.append(Transition(item.issue_id, DONE_STATE, item.done_day))

    # Day-order the stream the way a real export would arrive. Stable on
    # (day, issue_id, to_state) so two runs are byte-identical.
    transitions.sort(key=lambda t: (t.day, t.issue_id, t.to_state))
    return transitions
