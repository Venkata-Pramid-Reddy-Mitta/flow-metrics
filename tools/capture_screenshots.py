"""Capture framed screenshots of the real HTML report.

Generated from the tool's own output so a reviewer can regenerate them. Three
rules, each from a failure recorded in references/evidence.md: frame by a named
heading rather than a pixel offset (a hard crop drifts the first time a paragraph
grows); pass full_page even with a clip (Chromium otherwise clamps the clip to one
viewport); and read back the computed style of the verdict badge and fail if it is
invisible (a badge once shipped green on green because two CSS rules collided).

If the report is missing, this builds it first, so a screenshot is never taken of a
stale report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

REPORT = ROOT / "docs" / "report.html"
SHOTS = ROOT / "docs" / "screenshots"
MANIFEST = SHOTS / "manifest.json"


def _ensure_report() -> None:
    from flowmetrics.analysis import analyze
    from flowmetrics.fixtures import load_transitions
    from flowmetrics.report import build_report

    analysis = analyze(load_transitions(ROOT / "data" / "events.csv"), weeks=26)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(build_report(analysis), encoding="utf-8")


def run() -> dict:
    from playwright.sync_api import sync_playwright

    _ensure_report()
    SHOTS.mkdir(parents=True, exist_ok=True)
    html = REPORT.read_text(encoding="utf-8")

    shots = [
        ("report_overview", "flow-metrics report", "WIP rises before"),
        ("report_wip", "WIP rises before", "What the average hid"),
        ("report_littles", "Little's Law", "Weekly series"),
    ]
    manifest = {"source": "docs/report.html", "shots": []}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 1500})
        page.set_content(html)
        page.wait_for_timeout(200)

        badge = page.evaluate(
            """() => {
              const b = document.querySelector('.badge');
              if (!b) return null;
              const s = getComputedStyle(b);
              return {color: s.color, background: s.backgroundColor,
                      visible: b.offsetWidth > 0 && b.offsetHeight > 0};
            }"""
        )
        if not badge or not badge["visible"] or badge["color"] == badge["background"]:
            raise SystemExit(f"verdict badge is not legible: {badge}")
        manifest["badge"] = badge

        def offset_of(text: str) -> float:
            return page.evaluate(
                """(t) => {
                  const hs = Array.from(document.querySelectorAll('h1,h2'));
                  const el = hs.find(h => h.textContent.includes(t));
                  if (!el) return -1;
                  return el.getBoundingClientRect().top + window.scrollY;
                }""",
                text,
            )

        for name, start_heading, end_heading in shots:
            top = offset_of(start_heading)
            bottom = offset_of(end_heading)
            if top < 0 or bottom < 0:
                raise SystemExit(
                    f"heading missing for {name}: {start_heading!r} or {end_heading!r}. "
                    "The report changed shape; reframe the shot."
                )
            path = SHOTS / f"{name}.png"
            page.screenshot(
                path=str(path),
                full_page=True,
                clip={"x": 0, "y": top - 8, "width": 900, "height": bottom - top + 8},
            )
            manifest["shots"].append(
                {
                    "file": f"docs/screenshots/{name}.png",
                    "framed_by": [start_heading, end_heading],
                }
            )
        browser.close()

    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(manifest['shots'])} screenshots and {MANIFEST}")
    return manifest


if __name__ == "__main__":
    run()
