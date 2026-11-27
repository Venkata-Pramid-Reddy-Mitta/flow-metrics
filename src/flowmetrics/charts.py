"""Hand-built SVG line charts, drawn deterministically from the weekly series.

This file exists so the report's figures are produced by code in the repository
with no plotting dependency and no rendering nondeterminism: the same data always
yields byte-identical SVG. A committed SVG also embeds cleanly on GitHub as an
``<img>`` (unlike a Mermaid fence, which GitHub sometimes fails to render), and it
is legible in a dark theme because every chart paints its own light background.

The charts are intentionally plain: axes, a labeled band, two series, a marked
onset. Everything carries units, because an unlabelled axis measures nothing.
"""

from __future__ import annotations

from dataclasses import dataclass

# A restrained, color-blind-safe pair plus neutral ink. Not a brand palette, just
# two hues that stay distinct in grayscale.
_INK = "#1a1a1a"
_GRID = "#d9d9d9"
_WIP = "#1f6feb"  # blue: the leading signal
_CYCLE = "#d1680a"  # orange: the lagging signal
_BAND = "#e8eef7"
_ONSET = "#9a9a9a"
_BG = "#ffffff"


@dataclass(frozen=True)
class Series:
    label: str
    values: list  # list of float | None
    color: str


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def line_chart(
    title: str,
    y_label: str,
    weeks: int,
    series: list[Series],
    *,
    band_upper: float | None = None,
    onset_week: int | None = None,
    signal_weeks: dict | None = None,
    width: int = 760,
    height: int = 320,
) -> str:
    """Render a multi-series weekly line chart to a standalone SVG string.

    ``band_upper`` draws a shaded "normal" ceiling. ``signal_weeks`` maps a label
    to a week index and draws a vertical marker, used to show where each series
    first broke its band. Missing values (``None``) break the line, which is
    correct: a week with no completions has no cycle-time point to plot.
    """
    pad_l, pad_r, pad_t, pad_b = 64, 150, 44, 44
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    all_vals = [v for s in series for v in s.values if v is not None]
    if band_upper is not None:
        all_vals.append(band_upper)
    y_max = max(all_vals) * 1.1 if all_vals else 1.0
    y_min = 0.0

    def x(week: int) -> float:
        return pad_l + (week / max(1, weeks - 1)) * plot_w

    def y(val: float) -> float:
        return pad_t + plot_h - (val - y_min) / (y_max - y_min) * plot_h

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Segoe UI, Arial, sans-serif">'
    )
    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{_BG}"/>')
    parts.append(
        f'<text x="{pad_l}" y="24" font-size="15" font-weight="600" fill="{_INK}">'
        f"{_esc(title)}</text>"
    )

    # Normal band (shaded area from 0 to band_upper).
    if band_upper is not None:
        by = y(band_upper)
        parts.append(
            f'<rect x="{pad_l}" y="{by:.1f}" width="{plot_w}" height="{(pad_t + plot_h) - by:.1f}" '
            f'fill="{_BAND}"/>'
        )
        parts.append(
            f'<line x1="{pad_l}" y1="{by:.1f}" x2="{pad_l + plot_w}" y2="{by:.1f}" '
            f'stroke="{_WIP}" stroke-dasharray="4 3" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{pad_l + plot_w + 6}" y="{by + 4:.1f}" font-size="11" fill="{_INK}">'
            f"normal ceiling</text>"
        )

    # Axes.
    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h}" '
        f'stroke="{_INK}" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" '
        f'stroke="{_INK}" stroke-width="1"/>'
    )
    # Y ticks.
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        val = y_min + frac * (y_max - y_min)
        yy = y(val)
        parts.append(
            f'<line x1="{pad_l - 4}" y1="{yy:.1f}" x2="{pad_l + plot_w}" y2="{yy:.1f}" '
            f'stroke="{_GRID}" stroke-width="0.5"/>'
        )
        parts.append(
            f'<text x="{pad_l - 8}" y="{yy + 4:.1f}" font-size="10" text-anchor="end" '
            f'fill="{_INK}">{val:.0f}</text>'
        )
    parts.append(
        f'<text x="14" y="{pad_t + plot_h / 2:.1f}" font-size="11" fill="{_INK}" '
        f'transform="rotate(-90 14 {pad_t + plot_h / 2:.1f})" text-anchor="middle">'
        f"{_esc(y_label)}</text>"
    )
    # X ticks every 4 weeks.
    for wk in range(0, weeks, 4):
        xx = x(wk)
        parts.append(
            f'<text x="{xx:.1f}" y="{pad_t + plot_h + 18}" font-size="10" text-anchor="middle" '
            f'fill="{_INK}">w{wk}</text>'
        )
    parts.append(
        f'<text x="{pad_l + plot_w / 2:.1f}" y="{height - 6}" font-size="11" '
        f'text-anchor="middle" fill="{_INK}">week</text>'
    )

    # Onset marker.
    if onset_week is not None:
        ox = x(onset_week)
        parts.append(
            f'<line x1="{ox:.1f}" y1="{pad_t}" x2="{ox:.1f}" y2="{pad_t + plot_h}" '
            f'stroke="{_ONSET}" stroke-dasharray="2 3" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{ox + 3:.1f}" y="{pad_t + 12}" font-size="10" fill="{_INK}">onset</text>'
        )

    # Signal markers.
    for label, wk in (signal_weeks or {}).items():
        if wk is None:
            continue
        sx = x(wk)
        parts.append(
            f'<line x1="{sx:.1f}" y1="{pad_t}" x2="{sx:.1f}" y2="{pad_t + plot_h}" '
            f'stroke="{_INK}" stroke-dasharray="1 2" stroke-width="0.8"/>'
        )
        parts.append(
            f'<text x="{sx + 3:.1f}" y="{pad_t + plot_h - 6:.1f}" font-size="9" '
            f'fill="{_INK}">{_esc(label)}</text>'
        )

    # Series lines.
    for s in series:
        segments: list[str] = []
        pen_down = False
        for wk, v in enumerate(s.values):
            if v is None:
                pen_down = False
                continue
            cmd = "L" if pen_down else "M"
            segments.append(f"{cmd}{x(wk):.1f},{y(v):.1f}")
            pen_down = True
        if segments:
            parts.append(
                f'<path d="{" ".join(segments)}" fill="none" stroke="{s.color}" '
                f'stroke-width="2"/>'
            )

    # Legend.
    ly = pad_t + 4
    for s in series:
        parts.append(
            f'<rect x="{pad_l + plot_w + 6}" y="{ly}" width="10" height="10" fill="{s.color}"/>'
        )
        parts.append(
            f'<text x="{pad_l + plot_w + 20}" y="{ly + 9}" font-size="10" fill="{_INK}">'
            f"{_esc(s.label)}</text>"
        )
        ly += 18

    parts.append("</svg>")
    return "\n".join(parts)


# Palette exported so the report and the diagram tool stay visually consistent.
PALETTE = {"wip": _WIP, "cycle": _CYCLE, "ink": _INK, "band": _BAND}
