"""Render the architecture diagram to a committed SVG.

This file exists so the README's diagram is produced by code in the repository and
embeds as a plain ``<img>``. It does not use Mermaid: GitHub intermittently fails
to render a Mermaid fence (ci-and-rendering-traps.md, trap 7), and a Mermaid SVG
with HTML labels is not well-formed XML and fails to load as an image (trap 8). A
hand-built SVG avoids both: it is valid XML, carries intrinsic width and height
(trap 9), and paints a light background so edge labels stay legible in a dark
theme (trap 10).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "diagrams" / "architecture.svg"

_W, _H = 860, 360
_BOX_FILL = "#eef3fb"
_BOX_STROKE = "#1f6feb"
_OUT_FILL = "#fbf0e6"
_OUT_STROKE = "#d1680a"
_INK = "#1a1a1a"


def _box(x, y, w, h, title, sub, fill, stroke):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.5"/>'
        f'<text x="{x + w / 2:.0f}" y="{y + 20}" font-size="13" font-weight="600" '
        f'text-anchor="middle" fill="{_INK}">{title}</text>'
        f'<text x="{x + w / 2:.0f}" y="{y + 38}" font-size="10.5" '
        f'text-anchor="middle" fill="#555">{sub}</text>'
    )


def _arrow(x1, y1, x2, y2):
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{_INK}" '
        f'stroke-width="1.2" marker-end="url(#a)"/>'
    )


def build_svg() -> str:
    p: list[str] = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_W}" height="{_H}" '
        f'viewBox="0 0 {_W} {_H}" font-family="Segoe UI, Arial, sans-serif">'
    )
    p.append(
        '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" '
        'orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#1a1a1a"/></marker></defs>'
    )
    p.append(f'<rect x="0" y="0" width="{_W}" height="{_H}" fill="#ffffff"/>')
    p.append(
        f'<text x="20" y="28" font-size="15" font-weight="700" fill="{_INK}">'
        "flow-metrics: from transition log to a leading signal</text>"
    )

    # Row 1: input -> reconstruct -> weekly
    p.append(_box(20, 60, 150, 54, "events.csv", "state transitions", _BOX_FILL, _BOX_STROKE))
    p.append(_box(210, 60, 150, 54, "reconstruct", "issues: start, done", _BOX_FILL, _BOX_STROKE))
    p.append(_box(400, 60, 170, 54, "weekly flow", "WIP, throughput, CT", _BOX_FILL, _BOX_STROKE))
    p.append(_arrow(170, 87, 210, 87))
    p.append(_arrow(360, 87, 400, 87))

    # Row 2: two analyses from weekly
    p.append(
        _box(400, 150, 170, 54, "detector", "bands, lead, survivorship", _BOX_FILL, _BOX_STROKE)
    )
    p.append(
        _box(400, 230, 170, 54, "Little's Law", "implied vs reported CT", _BOX_FILL, _BOX_STROKE)
    )
    p.append(_arrow(485, 114, 485, 150))
    p.append(_arrow(485, 204, 485, 230))

    # Outputs
    p.append(_box(620, 150, 170, 54, "CLI check", "exit 0 / 2 / 1", _OUT_FILL, _OUT_STROKE))
    p.append(_box(620, 230, 170, 54, "HTML report", "charts + verdict", _OUT_FILL, _OUT_STROKE))
    p.append(_arrow(570, 177, 620, 177))
    p.append(_arrow(570, 257, 620, 257))

    # Receipts loop
    p.append(
        _box(210, 230, 150, 54, "receipts", "collect + check numbers", _OUT_FILL, _OUT_STROKE)
    )
    p.append(_arrow(400, 257, 360, 257))
    p.append(
        '<text x="295" y="306" font-size="10" text-anchor="middle" fill="#555">'
        "every figure re-measured</text>"
    )

    # Generator feeds the fixture.
    p.append(_box(20, 150, 150, 54, "generator", "seeded, 3 scenarios", _BOX_FILL, _BOX_STROKE))
    p.append(_arrow(95, 150, 95, 114))
    p.append(
        '<text x="30" y="132" font-size="10" fill="#555">builds the fixture</text>'
    )

    p.append("</svg>")
    return "\n".join(p)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_svg(), encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
