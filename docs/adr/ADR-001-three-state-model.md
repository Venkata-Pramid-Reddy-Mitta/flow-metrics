# ADR-001: A three-state flow model, and cycle time as commit-to-done

Status: accepted

## Context

A real Jira workflow has many states: backlog, selected, in progress, blocked, in
review, in test, done, and often more. Cycle time can be measured between any two
of them, and teams argue about which. The tool needs one definition, applied
everywhere, or none of the downstream numbers mean the same thing twice.

## Decision

Model three states only: `todo`, `in_progress`, `done`. Measure cycle time from the
day an issue enters `in_progress` to the day it enters `done`, inclusive of both
ends. Fold blocked and in-review time into `in_progress`.

## Alternatives considered

A full multi-state workflow with per-stage durations. Rejected for the first
version: it multiplies the fixture's surface area and the detector's parameters
without changing the phenomenon the project is about, which is visible with a
single in-progress state. The leading-versus-lagging gap does not depend on how
many stages the work passes through.

## Consequences

- The model cannot attribute a slowdown to a stage. It can say flow slowed; it
  cannot say the bottleneck was code review. That is a stated boundary, not a bug,
  and it is listed in the README's "what this cannot measure" section.
- Blocked time inflates the in_progress duration, which is the honest thing to do
  for a cycle-time measure a stakeholder reads, but it means the tool cannot
  separate "slow because waiting" from "slow because hard".
- Reopened issues (a second entry into in_progress after done) are out of scope:
  only the first start and first done are used. The committed fixture never
  produces one, and `reconstruct_issues` ignores later transitions rather than
  inventing a second cycle.

## Revisit when

Someone needs to attribute a detected slowdown to a specific stage. That is the
trigger to add per-stage states, and it is the second item of future work.
