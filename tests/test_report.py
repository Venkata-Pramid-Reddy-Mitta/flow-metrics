"""Tests for the HTML report, including the CSS-class invariant that an earlier
project in this portfolio learned the hard way (a verdict badge that rendered
invisible because its class had no rule)."""

import re

from flowmetrics import generator as G
from flowmetrics.analysis import analyze
from flowmetrics.report import _CSS, build_report


def _html(scenario=G.CAPACITY_DROP):
    return build_report(analyze(G.generate(scenario), weeks=26))


def test_the_report_states_the_verdict():
    assert "LEADING SLOWDOWN SIGNAL" in _html()


def test_a_steady_report_shows_the_clear_verdict():
    html = _html(G.STEADY)
    assert "NO LEADING SLOWDOWN SIGNAL" in html
    assert "badge clear" in html


def test_every_css_class_used_in_the_markup_has_a_rule_in_the_stylesheet():
    html = _html()
    body = html.split("</style>", 1)[1]
    used = set(re.findall(r'class="([^"]+)"', body))
    classes = set()
    for group in used:
        classes.update(group.split())
    defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", _CSS))
    missing = classes - defined
    assert not missing, f"classes used with no CSS rule: {missing}"


def test_the_verdict_badge_has_an_explicit_colour_and_background():
    # So the screenshot tool can read its contrast back; green-on-green ships
    # otherwise (references/evidence.md).
    assert ".badge {" in _CSS
    assert "color:" in _CSS and "background:" in _CSS


def test_the_report_embeds_two_charts():
    assert _html().count("<svg") == 2


def test_the_headline_cards_name_the_lead_and_the_survivorship_gap():
    html = _html()
    assert "weeks WIP led the average" in html
    assert "understated eventual CT" in html


def test_the_weekly_table_has_a_row_per_week():
    html = _html()
    body = html.split("Weekly series", 1)[1]
    assert body.count("<tr>") >= 26


def test_the_report_is_a_complete_html_document():
    html = _html()
    assert html.strip().startswith("<!DOCTYPE html>")
    assert html.strip().endswith("</html>")
