"""Fail the build when a checked document quotes a figure the code no longer
produces, or quotes a number nothing re-measures.

Two checks. The forward check: for every metric, if a document contains the
literal words of one of its anchors next to a number, that number must equal the
metric's current value. A stale value (right words, wrong number) fails the build.
The reverse check: every bare number in the README that is neither a metric value
nor an explicitly allowed constant is reported, because an unguarded number is one
nothing re-measures. Fenced code, inline code spans and HTML attributes are
excluded from the reverse check, so an example invocation may contain a made-up
count without training the reader to ignore the section.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
METRICS = ROOT / "docs" / "metrics.json"

_NUM = r"(\d+(?:\.\d+)?)"


def _fmt(value) -> str:
    # Render a metric value the way prose does: ints without a trailing .0.
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _anchor_regex(template: str) -> re.Pattern:
    # Turn "lead of {} weeks" into a regex that matches the literal words with any
    # number in the slot. "..." in a template means "any short run of text", used
    # where prose puts words between the frame and the number.
    parts = template.split("{}")
    escaped = [re.escape(p).replace(r"\.\.\.", r".{0,40}?") for p in parts]
    return re.compile(escaped[0] + _NUM + escaped[1], re.IGNORECASE)


def _strip_code(text: str) -> str:
    # Remove fenced blocks and inline code so the reverse check ignores example
    # invocations and literal command output.
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    # Remove HTML tags and their attributes (width="760", viewBox values, etc.).
    text = re.sub(r"<[^>]+>", " ", text)
    # Remove URLs: badge and link targets carry encoded numbers (%20, %25) and
    # version fragments that are not prose claims.
    text = re.sub(r"https?://\S+", " ", text)
    return text


def forward_check(payload: dict) -> list[str]:
    metrics = payload["metrics"]
    anchors = payload["anchors"]
    failures: list[str] = []
    for doc_rel in payload["checked_documents"]:
        doc = ROOT / doc_rel
        if not doc.exists():
            failures.append(f"{doc_rel}: checked document is missing")
            continue
        text = doc.read_text(encoding="utf-8")
        for metric, templates in anchors.items():
            if metric not in metrics or metrics[metric] is None:
                continue
            expected = _fmt(metrics[metric])
            for template in templates:
                rx = _anchor_regex(template)
                for m in rx.finditer(text):
                    found = m.group(1)
                    if found != expected:
                        failures.append(
                            f"{doc_rel}: anchor {template!r} for {metric} found "
                            f"{found!r} but code now produces {expected!r}"
                        )
    return failures


def reverse_check(payload: dict) -> list[str]:
    metrics = payload["metrics"]
    allowed = set(payload.get("allowed_non_metric_numbers", []))
    metric_values = {_fmt(v) for v in metrics.values() if v is not None}
    readme = ROOT / "README.md"
    text = _strip_code(readme.read_text(encoding="utf-8"))
    unguarded: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(_NUM, text):
        num = m.group(1)
        if num in metric_values or num in allowed:
            continue
        if num in seen:
            continue
        seen.add(num)
        unguarded.append(num)
    return [f"README.md: unguarded number {n!r} (not a metric, not an allowed constant)"
            for n in unguarded]


def main() -> int:
    if not METRICS.exists():
        print(f"error: {METRICS} missing; run tools/collect_metrics.py first", file=sys.stderr)
        return 1
    payload = json.loads(METRICS.read_text(encoding="utf-8"))
    failures = forward_check(payload) + reverse_check(payload)
    if failures:
        print("check_numbers FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    n = len(payload["metrics"])
    print(f"check_numbers passed: {n} metrics guarded across "
          f"{len(payload['checked_documents'])} documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
