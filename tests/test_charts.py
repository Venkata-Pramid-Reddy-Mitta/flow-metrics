"""Tests for the hand-built SVG charts. The rendering traps these guard against are
documented in references/ci-and-rendering-traps.md (traps 8 to 10)."""

import xml.etree.ElementTree as ET

from flowmetrics.charts import Series, line_chart


def _chart(**kw):
    return line_chart(
        "Title",
        "y label",
        weeks=10,
        series=[Series("a", [1.0, 2.0, 3.0] + [None] * 7, "#1f6feb")],
        **kw,
    )


def test_the_svg_is_well_formed_xml():
    # htmlLabels-style foreignObject output is not well formed and fails as <img>.
    # A chart that parses as XML cannot have that problem.
    ET.fromstring(_chart())


def test_the_svg_has_intrinsic_width_and_height_not_a_percentage():
    root = ET.fromstring(_chart())
    assert root.get("width") and not root.get("width").endswith("%")
    assert root.get("height") and not root.get("height").endswith("%")


def test_the_svg_keeps_a_viewbox_so_it_still_scales():
    root = ET.fromstring(_chart())
    assert root.get("viewBox")


def test_the_chart_paints_a_light_background_rectangle():
    # Transparent backgrounds render dark labels unreadable in a dark theme.
    assert 'fill="#ffffff"' in _chart()


def test_a_none_value_breaks_the_line_rather_than_plotting_zero():
    svg = _chart()
    # The path should start with a single M and not plot the seven None weeks.
    path_cmds = [p for p in svg.split('d="') if "M" in p]
    assert path_cmds  # a path exists
    # Only three points plotted (weeks 0,1,2); the rest are None.
    first_path = svg.split('<path d="')[1].split('"')[0]
    assert first_path.count("M") + first_path.count("L") == 3


def test_a_band_upper_draws_a_normal_ceiling_label():
    assert "normal ceiling" in _chart(band_upper=5.0)


def test_an_onset_week_draws_an_onset_marker():
    assert "onset" in _chart(onset_week=4)


def test_signal_weeks_draw_their_labels():
    svg = _chart(signal_weeks={"WIP break": 5})
    assert "WIP break" in svg


def test_axis_titles_are_present_so_the_chart_is_not_unlabelled():
    svg = _chart()
    assert "y label" in svg and "week" in svg
