"""Build the self-contained HTML report the tool produces.

This file exists to turn an ``Analysis`` into one HTML page a reviewer can open,
and that the screenshot tool can photograph. Every CSS class used in the markup
has a rule in the one embedded stylesheet (a test asserts this), because an
earlier project in this portfolio shipped a verdict badge that rendered invisible
when a class had no rule. The verdict badge carries an explicit color and
background so the screenshot tool can read its contrast back and fail if it is
illegible.
"""

from __future__ import annotations

from flowmetrics.analysis import Analysis, summary
from flowmetrics.charts import Series, line_chart

_CSS = """
body { font-family: Segoe UI, Arial, sans-serif; color: #1a1a1a; background: #ffffff;
       margin: 0; padding: 32px; }
h1 { font-size: 22px; margin: 0 0 4px 0; }
h2 { font-size: 16px; margin: 28px 0 8px 0; border-bottom: 1px solid #e2e2e2;
     padding-bottom: 4px; }
.subtitle { color: #555; font-size: 13px; margin-bottom: 20px; }
.badge { display: inline-block; padding: 6px 14px; border-radius: 4px; font-weight: 700;
         font-size: 14px; color: #ffffff; background: #b32020; }
.badge.clear { background: #1a7f37; }
.cards { display: flex; gap: 16px; flex-wrap: wrap; margin: 16px 0; }
.card { border: 1px solid #e2e2e2; border-radius: 6px; padding: 14px 16px; min-width: 150px; }
.card .n { font-size: 24px; font-weight: 700; }
.card .l { font-size: 12px; color: #555; }
.fig { margin: 14px 0; }
table { border-collapse: collapse; font-size: 12px; margin-top: 8px; }
th, td { border: 1px solid #e2e2e2; padding: 4px 8px; text-align: right; }
th { background: #f5f5f5; }
td.l, th.l { text-align: left; }
.note { font-size: 12px; color: #555; max-width: 680px; }
"""


def _card(n: str, label: str) -> str:
    return f'<div class="card"><div class="n">{n}</div><div class="l">{label}</div></div>'


def build_report(analysis: Analysis, scenario_name: str = "capacity_drop") -> str:
    s = summary(analysis)
    rows = analysis.rows
    weeks = analysis.weeks

    verdict_clear = not s["leading_signal"]
    verdict_class = "badge clear" if verdict_clear else "badge"
    verdict_text = (
        "NO LEADING SLOWDOWN SIGNAL"
        if verdict_clear
        else f"LEADING SLOWDOWN SIGNAL (WIP week {s['wip_signal_week']})"
    )

    wip_chart = line_chart(
        "Work in progress vs the cycle-time average",
        "count / days",
        weeks,
        [
            Series("WIP (end of wk)", [float(r.wip_end) for r in rows], "#1f6feb"),
            Series(
                "mean cycle (d)",
                [r.mean_cycle_time for r in rows],
                "#d1680a",
            ),
        ],
        band_upper=s["wip_band_upper"],
        onset_week=s["onset_week"],
        signal_weeks={
            "WIP break": s["wip_signal_week"],
            "cycle break": s["cycle_signal_week"],
        },
    )

    littles_chart = line_chart(
        "Little's Law implied cycle time vs the reported average",
        "days",
        weeks,
        [
            Series(
                "implied (WIP/thpt)",
                [row.implied_ct_days for row in analysis.littles],
                "#1f6feb",
            ),
            Series(
                "reported mean",
                [row.reported_ct_days for row in analysis.littles],
                "#d1680a",
            ),
        ],
        onset_week=s["onset_week"],
    )

    # Weekly table (compact).
    trows = []
    for r, lr in zip(rows, analysis.littles):
        mct = "" if r.mean_cycle_time is None else f"{r.mean_cycle_time:.1f}"
        imp = "" if lr.implied_ct_days is None else f"{lr.implied_ct_days:.1f}"
        trows.append(
            f"<tr><td>{r.week}</td><td>{r.wip_end}</td><td>{r.throughput}</td>"
            f"<td>{mct}</td><td>{imp}</td></tr>"
        )
    table = (
        '<table><tr><th class="l">week</th><th>WIP</th><th>throughput</th>'
        "<th>mean CT (d)</th><th>implied CT (d)</th></tr>" + "".join(trows) + "</table>"
    )

    cards = "".join(
        [
            _card(f"{s['lead_weeks']}", "weeks WIP led the average"),
            _card(f"{s['flat_weeks']}", "weeks the average stayed flat"),
            _card(f"{s['survivorship_gap_pct']:.0f}%", "the average understated eventual CT"),
            _card(f"{s['littles_divergence_ratio']:.0f}x", "wider Little's gap in the transition"),
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>flow-metrics report ({scenario_name})</title>
<style>{_CSS}</style></head>
<body>
<h1>flow-metrics report</h1>
<div class="subtitle">scenario: {scenario_name} &middot; {s['weeks']} weeks &middot;
{s['issues_total']} issues</div>
<span class="{verdict_class}">{verdict_text}</span>
<div class="cards">{cards}</div>

<h2>WIP rises before the cycle-time average moves</h2>
<div class="fig">{wip_chart}</div>
<p class="note">WIP (blue) crossed its normal ceiling at week {s['wip_signal_week']},
the same regime change that the mean cycle time (orange) did not reflect until week
{s['cycle_signal_week']}: a lead of {s['lead_weeks']} weeks. The average is built only from
items that have finished, so during the slowdown it reports on the fast work that got
done, not the slow work piling up.</p>

<h2>What the average hid: survivorship</h2>
<p class="note">At week {s['survivorship_worst_week']} the dashboard reported a mean cycle
time of {s['reported_ct_at_worst_days']} days. The work actually alive that week went on to
take {s['eventual_ct_at_worst_days']} days on average: the reported figure understated the
eventual experience by {s['survivorship_gap_pct']:.0f}%.</p>

<h2>Little's Law: implied vs reported cycle time</h2>
<div class="fig">{littles_chart}</div>
<p class="note">Little's Law turns WIP and throughput into an implied cycle time that needs
no hindsight. It tracks the reported average within
{s['littles_divergence_steady_pct']:.0f}% in steady state and diverges to
{s['littles_divergence_transition_pct']:.0f}% during the transition, a gap
{s['littles_divergence_ratio']:.0f} times wider.</p>

<h2>Weekly series</h2>
{table}
</body></html>
"""
