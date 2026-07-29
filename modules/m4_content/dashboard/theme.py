"""Chart theme.

One place for every colour the dashboard draws with, so a chart never invents
its own hue. The categorical order is fixed: a series keeps its slot regardless
of how many other series are on screen, because colour follows the entity, not
its rank.
"""

import altair as alt

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

# Fixed categorical order. The first three slots are the only ones safe for
# scatter/all-pairs forms; bars and stacks may use the full list.
CATEGORICAL = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]

SEQUENTIAL = ["#86b6ef", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95"]

STATUS = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}

DELTA_UP = "#006300"
DELTA_DOWN = "#d03b3b"

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'


def register() -> None:
    """Install the theme as Altair's active config."""

    def _theme():
        return {
            "config": {
                "background": SURFACE,
                "font": FONT,
                "view": {"stroke": "transparent", "continuousWidth": 560,
                         "continuousHeight": 300},
                "axis": {
                    "labelColor": INK_MUTED,
                    "titleColor": INK_SECONDARY,
                    "labelFontSize": 12,
                    "titleFontSize": 12,
                    "titleFontWeight": "normal",
                    "gridColor": GRIDLINE,
                    "domainColor": BASELINE,
                    "tickColor": BASELINE,
                    "labelFont": FONT,
                    "titleFont": FONT,
                },
                "legend": {
                    "labelColor": INK_SECONDARY,
                    "titleColor": INK_SECONDARY,
                    "labelFontSize": 12,
                    "titleFontSize": 12,
                    "titleFontWeight": "normal",
                    "labelFont": FONT,
                    "titleFont": FONT,
                    "symbolType": "square",
                    "symbolSize": 90,
                },
                "title": {
                    "color": INK_PRIMARY,
                    "fontSize": 15,
                    "fontWeight": 600,
                    "anchor": "start",
                    "font": FONT,
                    "subtitleColor": INK_MUTED,
                    "subtitleFontSize": 12,
                },
                "range": {
                    "category": CATEGORICAL,
                    "ramp": SEQUENTIAL,
                    "heatmap": SEQUENTIAL,
                },
                "bar": {"cornerRadiusEnd": 4},
            }
        }

    # Altair 5.5 replaced enable/register with a themes plugin registry; both
    # spellings exist in the wild, so try the new API and fall back.
    try:
        alt.theme.register("research", enable=True)(_theme)
    except AttributeError:  # pragma: no cover - older Altair
        alt.themes.register("research", _theme)
        alt.themes.enable("research")


def color_scale(domain: list[str]) -> alt.Scale:
    """Pin each named series to its slot so filtering never repaints survivors."""
    return alt.Scale(domain=domain, range=CATEGORICAL[: len(domain)])
