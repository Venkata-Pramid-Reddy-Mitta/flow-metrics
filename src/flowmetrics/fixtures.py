"""Read and write the committed event fixture.

This file exists so the default analytics path reads a committed CSV rather than
calling the generator, which keeps the reproduced numbers independent of any
future change to the generator. The CSV is the contract; the generator is how the
contract was produced. Both are in the repository, and ``make fixture`` rebuilds
the CSV from the seed so the two can never silently diverge.
"""

from __future__ import annotations

import csv
from pathlib import Path

from flowmetrics.model import Transition

_HEADER = ("issue_id", "to_state", "day")


def save_transitions(transitions: list[Transition], path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(_HEADER)
        for t in transitions:
            writer.writerow([t.issue_id, t.to_state, t.day])


def load_transitions(path: str | Path) -> list[Transition]:
    """Load a transition stream from CSV, validating as it goes.

    Validation happens in ``Transition.__post_init__``, so a malformed row raises
    ``FlowError`` here rather than producing a wrong answer three modules later.
    """
    p = Path(path)
    out: list[Transition] = []
    with p.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header != list(_HEADER):
            from flowmetrics.model import FlowError

            raise FlowError(f"expected header {_HEADER}, got {header}")
        for row in reader:
            if not row:
                continue
            issue_id, to_state, day = row[0], row[1], int(row[2])
            out.append(Transition(issue_id=issue_id, to_state=to_state, day=day))
    return out
