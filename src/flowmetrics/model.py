"""The data model: what a transition is, and what an issue becomes once its
transitions are stitched together.

This file exists to keep one rule in one place: cycle time is measured from the
day an issue enters ``in_progress`` to the day it enters ``done``, inclusive of
both ends. Everything downstream (flow reconstruction, Little's Law, the
detector) depends on that definition, so it lives here with the validation that
protects it, not scattered across call sites.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The three states the board models. A deliberately small set: see
# docs/adr/ADR-001. "blocked" and "in review" are folded into "in_progress" on
# purpose, and ADR-001 states what that costs.
STATES = ("todo", "in_progress", "done")

# The two transitions that carry timing information. An issue may be created
# directly into in_progress (committed work), so a todo->in_progress event is
# optional, but an entry into in_progress and an entry into done are the two
# events cycle time is built from.
COMMIT_STATE = "in_progress"
DONE_STATE = "done"


class FlowError(ValueError):
    """Raised when a transition stream cannot be interpreted.

    A distinct type so the CLI can tell "the input was malformed" (exit 1) apart
    from "the tool ran and the answer was no" (exit 0). Conflating the two is the
    single most common way a gate becomes untrustworthy: a crash that looks like
    a pass.
    """


@dataclass(frozen=True)
class Transition:
    """One state change for one issue on one day.

    ``day`` is an integer day index, not a wall-clock timestamp. The analytics
    never read a clock, so "day 84" means the same thing on every machine and in
    every timezone. A real Jira export is mapped onto this index at the edge, in
    the loader, so the core stays timezone-free (ADR-005).
    """

    issue_id: str
    to_state: str
    day: int

    def __post_init__(self) -> None:
        if self.to_state not in STATES:
            raise FlowError(
                f"issue {self.issue_id!r}: unknown state {self.to_state!r}, "
                f"expected one of {STATES}"
            )
        if not isinstance(self.day, int):
            raise FlowError(f"issue {self.issue_id!r}: day must be an int, got {self.day!r}")


@dataclass
class Issue:
    """An issue reconstructed from its transitions.

    ``start_day`` is the day it entered in_progress; ``done_day`` is the day it
    entered done, or ``None`` if it is still open at the end of the window. The
    separation matters more than it looks: the whole project turns on the fact
    that an open issue has no cycle time yet, so a mean of cycle times silently
    excludes exactly the issues that are aging.
    """

    issue_id: str
    start_day: int
    done_day: int | None = None
    extra: dict = field(default_factory=dict)

    @property
    def is_done(self) -> bool:
        return self.done_day is not None

    @property
    def cycle_time_days(self) -> int | None:
        """Inclusive commit-to-done duration in days, or None while still open.

        Returning None rather than 0 or a sentinel is intentional: a caller that
        averages cycle times must decide, explicitly, what to do about the issues
        that have none. Making that a None forces the decision instead of hiding
        it behind a zero.
        """
        if self.done_day is None:
            return None
        return self.done_day - self.start_day + 1

    def age_days(self, as_of_day: int) -> int:
        """How long the issue has been in the system as of a given day.

        Defined for open and closed issues alike. For an open issue this is the
        censored age; for a closed one it is the age up to ``as_of_day``. Used by
        the survivorship measure, which compares what a week reported against what
        the issues alive that week eventually cost.
        """
        closed_before = self.done_day is not None and self.done_day < as_of_day
        end = self.done_day if closed_before else as_of_day
        return end - self.start_day + 1
