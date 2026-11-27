# ADR-003: A trend band, not a control chart, and time-averaged WIP

Status: accepted

## Context

Two decisions about the detector sit here. First, how to decide a series has broken
its normal: a statistical control chart (SPC) with control limits, or a simpler
baseline band. Second, which WIP number Little's Law should use.

## Decision

Use a baseline band: learn the mean and standard deviation of each series over a
baseline window, set the ceiling at mean plus 2.5 standard deviations, and require
three consecutive weeks above it. Use the daily **time-averaged** WIP for Little's
Law, not the end-of-week snapshot.

## Why a band and not a control chart

SPC is the right tool for a count time series with a stable baseline, and a sibling
project in this portfolio, `raid-signal`, is built entirely around control limits on
a RAID open-risk count. Repeating SPC here would blur the two projects into one. The
point of flow-metrics is the **comparison** between a leading series and a lagging
one, and a plain two-band trend break keeps that comparison clean: the same rule is
applied to WIP and to the cycle-time average, and the only thing that differs is
which one breaks first. A control chart would add machinery that distracts from the
one idea.

The 2.5-sigma ceiling and the three-week persistence are not defaults left
unexamined. At this board size a two-sigma band and a two-week rule false-alarm on
the steady fixture; 2.5 and three keep the steady scenario silent while still
catching the slowdown early. That trade is priced in the README.

## Why time-averaged WIP (the war story)

Little's Law relates average WIP to throughput and cycle time. The first
implementation used the end-of-week WIP snapshot and reported a divergence of 26% on
the steady fixture: the law looked broken in a system that was stable by
construction. A snapshot is a single sample of a count that moves every day; the law
relates to the time-average. Averaging WIP over the week's days dropped the steady
divergence to about 5%. The regression test
`test_littles_law_uses_time_averaged_wip_not_the_end_of_week_snapshot` pins it, and
also asserts the fix is measurably better than the snapshot, not merely different.

The detector still bands the end-of-week snapshot, because that is the number a team
reads off a board; only Little's Law needs the time-average.

## Consequences

- The detector has a confirmation latency of up to three weeks by design. A real
  slowdown is flagged a little later in exchange for no false alarms.
- The two WIP numbers (snapshot for the band, time-average for the law) are kept on
  the same weekly row to make the distinction explicit rather than accidental.
