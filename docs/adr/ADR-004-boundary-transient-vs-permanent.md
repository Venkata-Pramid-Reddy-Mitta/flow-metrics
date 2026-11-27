# ADR-004: The boundary, transient versus permanent

Status: accepted

## Context

The most tempting overclaim for a tool like this is that it detects slowdowns. It
does not, quite. It detects that flow has broken its normal band. Whether that break
is a permanent regime change or a temporary burst that will clear is a different
question, and this ADR records that the tool deliberately does not answer it.

## Decision

Ship the detector as a band-break detector, and state the boundary explicitly in the
README and here, rather than tuning the fixture to hide it.

## The evidence

The `transient_burst` scenario is a four-week arrival spike that recovers, against
the `capacity_drop` scenario which is permanent. Both push WIP over its band at
essentially the same week, so the detector fires on both. The
`exp_indistinguishable_onset` experiment measures how long they stay
indistinguishable: they are not clearly told apart until week 18, which is five weeks
of ambiguity after the alarm.

The subtle part, and the one worth saying out loud in an interview: the burst's WIP
is actually **higher** than the slowdown's in the first weeks, yet it is the less
dangerous of the two, because it clears. Magnitude at alarm time says nothing about
eventual damage. Only persistence does, and persistence is precisely what is not yet
observable when the alarm fires. A tool that claimed to rank the two by severity at
alarm time would be lying.

## Consequences

- The CLI exit code 2 means "flow broke its band", not "a permanent slowdown is
  underway". A gate on it will fire on bursts too. That is the correct behavior
  for an early warning: escalate and look, do not pre-judge.
- A future online detector could reduce the ambiguity window by watching for the
  WIP turn-down, but it cannot eliminate it: the information simply is not present at
  alarm time.

## Revisit when

There is a real cost model for acting on a false alarm versus missing a real
slowdown, at which point the persistence threshold can be tuned to that cost rather
than to the fixture.
