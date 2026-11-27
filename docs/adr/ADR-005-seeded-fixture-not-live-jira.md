# ADR-005: A seeded fixture, not a live Jira export

Status: accepted

## Context

The tool analyzes issue state transitions. The realistic source is a Jira export via
the Jira API. The portfolio-wide rule is that every number must be reproducible by a
reviewer with one command and no network.

## Decision

Default to a committed, seeded, deterministic event fixture under `data/`. Provide a
generator that rebuilds it from a seed, and a loader that reads it. No API client, no
credentials, no network at runtime.

## Why

Reproducibility is worth more than realism here. A reviewer can clone the repository
and reproduce every published figure exactly, on any machine, offline, because the
input is a committed file and the analysis reads a clock nowhere. A live Jira export
would make the headline numbers depend on a snapshot of someone's board that the
reviewer cannot see, which would make the whole receipts mechanism meaningless.

The generator is a stdlib `random.Random` stream, chosen over numpy because its
sequence is stable across Python versions and platforms, so the fixture is
byte-identical everywhere.

## The one claim that would need the real thing

Exactly one claim is out of reach of a synthetic fixture: that the steady-state
Little's Law divergence of about 5% is representative of real boards rather than an
artifact of the generator's smoothness. Real boards may be noisier. Every other
claim, the lead, the survivorship gap, the indistinguishability of a burst, is a
statement about the analysis given an input, and holds for the committed input
whether or not that input came from Jira. That single transfer claim is the first
metric to watch when a real export is wired in (future work).

## Consequences

- The fixture must be honest about its hard cases, which is why the README's "the
  fixture" section lists the benign steady scenario, the deceptive burst and the
  lumpy item sizes explicitly. A corpus of easy cases would measure nothing.
- A test pins the committed CSV to the generator output, so the two cannot drift.

## Revisit when

Someone wants to run the detector on their own board. That is the trigger to build
the Jira importer, and it is the Pivot recorded in the README.
