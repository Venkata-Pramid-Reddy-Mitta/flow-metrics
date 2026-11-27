"""The command line interface, with exit codes that mean something.

This file exists to make flow-metrics usable as a gate, which is only possible if
"the tool ran and found no leading signal" is a different exit code from "the tool
could not run". The three codes below encode exactly that distinction, and they
are documented in the README so a CI author can rely on them:

    0  ran successfully, no leading slowdown signal in the window
    2  ran successfully, a leading slowdown signal was detected
    1  the tool failed to answer (bad input, missing file, usage error)

Using 2 rather than 1 for "signal found" is deliberate: a shell treats any
non-zero as failure, so a gate that should block on a detected slowdown still
works, while a script that wants to tell a real slowdown apart from a crashed tool
can check for exactly 2.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from flowmetrics.analysis import analyze, summary
from flowmetrics.config import DEFAULT
from flowmetrics.fixtures import load_transitions, save_transitions
from flowmetrics.generator import SCENARIOS, generate
from flowmetrics.model import FlowError

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_SIGNAL = 2


def _load(args) -> tuple[list, int]:
    if args.generate:
        if args.generate not in SCENARIOS:
            raise FlowError(
                f"unknown scenario {args.generate!r}, expected one of {sorted(SCENARIOS)}"
            )
        scenario = SCENARIOS[args.generate]
        return generate(scenario, seed=args.seed), scenario.weeks
    path = Path(args.events or DEFAULT.fixture_path)
    if not path.exists():
        raise FlowError(f"events file not found: {path}. Run `flow-metrics fixture` first.")
    transitions = load_transitions(path)
    return transitions, args.weeks


def cmd_check(args) -> int:
    transitions, weeks = _load(args)
    analysis = analyze(transitions, weeks)
    s = summary(analysis)
    if analysis.leading_signal:
        print(
            f"LEADING SLOWDOWN SIGNAL: WIP broke its band at week {s['wip_signal_week']}, "
            f"{s['lead_weeks']} weeks before the cycle-time average "
            f"(week {s['cycle_signal_week']})."
        )
        return EXIT_SIGNAL
    print("No leading slowdown signal: WIP stayed within its normal band.")
    return EXIT_OK


def cmd_report(args) -> int:
    from flowmetrics.report import build_report

    transitions, weeks = _load(args)
    analysis = analyze(transitions, weeks)
    scenario = args.generate or "fixture"
    html = build_report(analysis, scenario_name=scenario)
    out = Path(args.out or DEFAULT.report_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({len(html)} bytes)")
    return EXIT_OK


def cmd_summary(args) -> int:
    transitions, weeks = _load(args)
    analysis = analyze(transitions, weeks)
    print(json.dumps(summary(analysis), indent=2))
    return EXIT_OK


def cmd_fixture(args) -> int:
    scenario = SCENARIOS[args.scenario]
    transitions = generate(scenario, seed=args.seed)
    save_transitions(transitions, args.out or DEFAULT.fixture_path)
    print(
        f"wrote {args.out or DEFAULT.fixture_path}: {len(transitions)} transitions "
        f"from scenario {scenario.name!r} seed {args.seed}"
    )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flow-metrics",
        description="Reconstruct delivery flow and detect a slowdown before the "
        "cycle-time average moves.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    def add_source(sp):
        sp.add_argument("--events", help="path to an events CSV (default: the committed fixture)")
        sp.add_argument(
            "--generate",
            help="generate a scenario instead of reading a file "
            "(steady, capacity_drop, transient_burst)",
        )
        sp.add_argument("--weeks", type=int, default=26, help="weeks in the window (default 26)")
        sp.add_argument("--seed", type=int, default=20260501, help="generator seed")

    c = sub.add_parser("check", help="exit 2 if a leading slowdown signal is found, else 0")
    add_source(c)
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("report", help="write the HTML report")
    add_source(r)
    r.add_argument("--out", help="output HTML path (default docs/report.html)")
    r.set_defaults(func=cmd_report)

    s = sub.add_parser("summary", help="print the summary metrics as JSON")
    add_source(s)
    s.set_defaults(func=cmd_summary)

    f = sub.add_parser("fixture", help="regenerate the committed events fixture from the seed")
    f.add_argument("--scenario", default="capacity_drop", choices=sorted(SCENARIOS))
    f.add_argument("--seed", type=int, default=20260501)
    f.add_argument("--out", help="output CSV path (default data/events.csv)")
    f.set_defaults(func=cmd_fixture)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FlowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
