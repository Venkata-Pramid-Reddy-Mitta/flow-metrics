"""flowmetrics: reconstruct delivery flow from issue state transitions.

The package exists to answer one question a cycle-time average cannot: is a
slowdown already building before the average that is supposed to report it has
moved. Every module here is offline and deterministic. No network, no clock
reads in the analytics path, so a reviewer reproduces every published number
from the committed fixture with one command.
"""

from flowmetrics.flow import WeeklyFlow, reconstruct_issues, weekly_flow
from flowmetrics.model import Issue, Transition

__all__ = [
    "Issue",
    "Transition",
    "WeeklyFlow",
    "reconstruct_issues",
    "weekly_flow",
]

__version__ = "0.1.0"
