# ADR-002: Shortest-remaining-first service, and what it does to the lead

Status: accepted

## Context

The generator has to decide, each day, which in-progress items the finite team
capacity advances. That choice is not cosmetic: it determines which items finish
during a slowdown, and therefore what the completed-cycle average reports while WIP
is climbing. The headline lead of 8 weeks is a direct consequence of this decision,
so it has to be made in the open.

## Decision

Advance the items with the least remaining work first (shortest-remaining-first,
SRPT), one worker-day per item per day, up to the day's capacity.

## Why

It models a real behavior. Under delivery pressure a team triages toward the work
closest to done, both because finishing something feels like progress and because
throughput is what gets reported. SRPT captures that: quick wins keep completing,
so the completed-cycle average stays low and flat, while large items starve and
age unseen. That is exactly the pathology the tool exists to expose.

## The alternative, measured

Oldest-first (FIFO) is the obvious alternative: advance the items that started
earliest. On the same fixture and seed, the measured lead collapses from 8 weeks to
**zero**. The reason is instructive: FIFO forces the aged items to completion, so
the completed-cycle average rises in lockstep with WIP and there is no early warning
to buy. The 8-week lead is therefore a property of the assumed discipline, not a
universal constant, and the README says so in its "what this cannot measure"
section.

This is the honest center of the project: the tool measures a real effect, but the
magnitude of the effect depends on how the modeled team behaves, and the dependence
is large enough that it must be disclosed rather than buried.

## Consequences

- The published lead is defensible only alongside this ADR. In an interview the
  right answer to "why 8 weeks" is "because the fixture models quick-wins-first
  triage; under oldest-first it is zero".
- Real teams are a mix of the two disciplines, so a real board's lead would fall
  somewhere between. The tool does not claim to predict where.

## Revisit when

A real Jira export is available and the actual service discipline can be inferred
from the data, at which point the generator's assumption can be replaced by a
measurement.
