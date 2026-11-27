"""Re-measure every published figure and write docs/metrics.json.

Nothing in this file types a number by hand. The test count and line coverage are
read from the machine-readable reports pytest and coverage write (not parsed from a
progress line, which quietly becomes whatever the last run printed), and every
analytical figure comes from running the experiments and reading their JSON. The
anchors that guard each figure live here too, so collect and check never disagree
about what phrase protects what number.

Run order matters (see references/ci-and-rendering-traps.md, trap 4): run pytest as
its own step with --junitxml and --cov-report=json, then call this with
--skip-tests so a red test surfaces as a failed test step, not as a traceback from
a metrics script.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

JUNIT = ROOT / "junit.xml"
COV_JSON = ROOT / "coverage.json"
METRICS = ROOT / "docs" / "metrics.json"

# Each metric maps to the anchor phrases that guard it. Anchors are alternatives:
# any one matching with the value substituted is enough. Each frame is short (a
# number and two or three words) so it survives markdown line wrapping, and each is
# distinctive so two metrics never share a frame (which would make one look stale
# when the other is quoted nearby).
ANCHORS = {
    "tests_total": ["{} tests"],
    "coverage_line_pct": ["{}% line coverage", "{}% statement coverage"],
    "issues_total": ["{} issues"],
    "onset_week": ["onset in week {}", "slowdown begins in week {}"],
    "wip_signal_week": ["band at week {}", "WIP signaled in week {}"],
    "cycle_signal_week": ["cross until week {}", "cycle-time average in week {}"],
    "lead_weeks": ["lead of {} weeks", "{}-week lead", "{} weeks ahead"],
    "flat_weeks": ["flat for {} weeks", "its band for {} weeks"],
    "survivorship_gap_pct_display": ["understated ... by {}%", "by {}%"],
    "reported_ct_worst_days": ["cycle time of {} days", "reported mean of {} days"],
    "eventual_ct_worst_days": ["went on to take {} days", "to {} days on average"],
    "littles_steady_pct_display": ["within {}% in steady state", "to within {}%"],
    "littles_transition_pct_display": ["to {}% during the transition", "{}% during the transition"],
    "littles_ratio_display": ["{} times wider", "{}x wider"],
    "ambiguous_weeks": ["{} weeks of ambiguity", "{} more weeks to tell"],
    "distinguishable_week": ["apart until week {}", "distinguishable only in week {}"],
    "peak_wip": ["peaks at {} items", "{} items in progress"],
    "survivorship_worst_week": ["worst week (week {}"],
    "snapshot_divergence_steady_pct": ["divergence of {}%", "{}% on the steady fixture"],
}

CHECKED_DOCUMENTS = [
    "README.md",
    "docs/adr/ADR-002-service-discipline.md",
    "docs/adr/ADR-004-boundary-transient-vs-permanent.md",
]

# Numbers that legitimately appear in the README without being a re-measured metric:
# configuration constants, structural counts and version-like tokens. The reverse
# check in check_numbers.py flags any other bare number, so this list is the
# conscious record of every non-metric number the prose is allowed to contain.
ALLOWED_NON_METRIC_NUMBERS = [
    "0",
    "1",  # exit codes, "one command"
    "2",  # exit code 2
    "2.5",  # band sigma
    "3",  # persistence weeks, three python versions
    "4",  # trailing window weeks
    "7.5",  # capacity after onset
    "8",  # baseline weeks (also lead; allowed either way)
    "12",  # capacity normal (also onset week)
    "26",  # weeks in the window
    "42",  # burn-in days
    "2026",  # license year
    "3.9",
    "3.11",
    "3.12",  # python versions
    "95",  # coverage floor
    "001",
    "002",
    "003",
    "004",
    "005",  # ADR numbers
    "100",  # percentages in prose like "100%" if any
]


def _run_tests() -> None:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        f"--junitxml={JUNIT}",
        "--cov=flowmetrics",
        "--cov-report=json",
        "--cov-report=term-missing",
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)


def _read_test_count() -> int:
    tree = ET.parse(JUNIT)
    root = tree.getroot()
    # junit root may be <testsuites> or a single <testsuite>.
    suites = root.findall("testsuite") or [root]
    return sum(int(s.get("tests", "0")) for s in suites)


def _read_line_coverage() -> float:
    data = json.loads(COV_JSON.read_text())
    totals = data["totals"]
    covered = totals["covered_lines"]
    statements = totals["num_statements"]
    pct = 100.0 * covered / statements if statements else 0.0
    return round(pct, 1)


def _run_experiments() -> dict:
    import exp_indistinguishable_onset
    import exp_lead_time
    import exp_littles_divergence
    import exp_survivorship

    lead = exp_lead_time.run()
    surv = exp_survivorship.run()
    little = exp_littles_divergence.run()
    inds = exp_indistinguishable_onset.run()
    return {"lead": lead, "surv": surv, "little": little, "inds": inds}


def _snapshot_steady_divergence() -> int:
    """Reproduce the war-story number: Little's Law divergence on the steady fixture
    if WIP were taken from the end-of-week snapshot instead of the time-average.
    This is the buggy path that first made the law look broken in a stable system;
    publishing it keeps the war story a measured fact, not an anecdote.
    """
    from statistics import mean

    from flowmetrics.analysis import analyze
    from flowmetrics.config import DEFAULT
    from flowmetrics.generator import STEADY, generate

    a = analyze(generate(STEADY), weeks=26)

    def snap(w: int):
        lo = max(0, w - DEFAULT.trailing_weeks + 1)
        window = a.rows[lo : w + 1]
        snap_wip = mean(r.wip_end for r in window)
        tp = mean(r.throughput for r in window)
        cts = [r.mean_cycle_time for r in window if r.mean_cycle_time is not None]
        if not cts or tp == 0:
            return None
        implied = snap_wip / tp * DEFAULT.week_length_days
        return abs((implied - mean(cts)) / implied * 100)

    vals = [v for w in range(2, 11) if (v := snap(w)) is not None]
    return round(mean(vals))


def build_metrics(skip_tests: bool) -> dict:
    if not skip_tests:
        _run_tests()
    tests_total = _read_test_count()
    coverage = _read_line_coverage()
    exp = _run_experiments()

    lead, surv, little, inds = exp["lead"], exp["surv"], exp["little"], exp["inds"]

    metrics = {
        "tests_total": tests_total,
        "coverage_line_pct": coverage,
        "issues_total": 468,
        "onset_week": lead["onset_week"],
        "wip_signal_week": lead["wip_signal_week"],
        "cycle_signal_week": lead["cycle_signal_week"],
        "lead_weeks": lead["lead_weeks"],
        "flat_weeks": lead["flat_weeks"],
        "survivorship_gap_pct_display": round(surv["survivorship_gap_pct"]),
        "reported_ct_worst_days": surv["reported_ct_days"],
        "eventual_ct_worst_days": surv["eventual_ct_days"],
        "littles_steady_pct_display": round(little["steady_divergence_pct"]),
        "littles_transition_pct_display": round(little["transition_divergence_pct"]),
        "littles_ratio_display": round(little["ratio"]),
        "ambiguous_weeks": inds["ambiguous_weeks"],
        "distinguishable_week": inds["distinguishable_from_week"],
        "peak_wip": 55,
    }
    # issues_total and peak_wip are structural facts of the fixture; re-derive them
    # so they are measured, not asserted.
    from flowmetrics.analysis import analyze
    from flowmetrics.fixtures import load_transitions

    a = analyze(load_transitions(ROOT / "data" / "events.csv"), weeks=26)
    metrics["issues_total"] = len(a.issues)
    metrics["peak_wip"] = max(r.wip_end for r in a.rows)
    metrics["survivorship_worst_week"] = surv["worst_week"]
    metrics["snapshot_divergence_steady_pct"] = _snapshot_steady_divergence()

    payload = {
        "metrics": metrics,
        "anchors": ANCHORS,
        "checked_documents": CHECKED_DOCUMENTS,
        "allowed_non_metric_numbers": ALLOWED_NON_METRIC_NUMBERS,
        "note": "every value here is produced by running the suite and the experiments",
    }
    return payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--skip-tests",
        action="store_true",
        help="read junit.xml and coverage.json instead of running pytest",
    )
    args = ap.parse_args(argv)
    payload = build_metrics(args.skip_tests)
    METRICS.parent.mkdir(parents=True, exist_ok=True)
    METRICS.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {METRICS} with {len(payload['metrics'])} metrics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
