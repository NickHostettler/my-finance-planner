"""Reusable Dash building blocks (form fields, cards, formatting)."""

from typing import Dict, List

from dash import dcc, html


def field(label: str, component, hint: str = "", label_id: str = None, hint_id: str = None):
    label_props = {"className": "field-label"}
    if label_id:
        label_props["id"] = label_id
    children = [html.Label(label, **label_props), component]
    if hint:
        hint_props = {"className": "field-hint"}
        if hint_id:
            hint_props["id"] = hint_id
        children.append(html.Div(hint, **hint_props))
    return html.Div(children, className="field")


def number_input(
    component_id: str,
    value: float,
    minimum: float,
    step: float,
    suffix: str = "",
    maximum: float = None,
    suffix_id: str = None,
):
    suffix_component = None
    if suffix:
        suffix_props = {"className": "input-suffix"}
        if suffix_id:
            suffix_props["id"] = suffix_id
        suffix_component = html.Span(suffix, **suffix_props)
    return html.Div(
        [
            dcc.Input(
                id=component_id,
                type="number",
                value=value,
                min=minimum,
                max=maximum,
                step=step,
                debounce=0.5,
                className="number-input",
            ),
            suffix_component,
        ],
        className="input-wrap",
    )


def dropdown(component_id: str, options: List[Dict], value):
    return dcc.Dropdown(
        id=component_id,
        options=options,
        value=value,
        clearable=False,
        searchable=False,
        className="modern-dropdown",
    )


def money(value: float, decimals: int = 0) -> str:
    return f"CHF {value:,.{decimals}f}".replace(",", "’")


def metric_card(label: str, value: str, detail: str, tone: str, icon: str):
    return html.Div(
        [
            html.Div(
                [html.Span(icon, className="metric-icon"), html.Span(label, className="metric-label")],
                className="metric-topline",
            ),
            html.Div(value, className="metric-value"),
            html.Div(detail, className="metric-detail"),
        ],
        className=f"metric-card metric-{tone}",
    )


def chart_card(title: str, subtitle: str, figure, height: int, class_name: str = ""):
    return html.Section(
        [
            html.Div(
                [html.H3(title), html.P(subtitle)],
                className="chart-heading",
            ),
            dcc.Graph(
                figure=figure,
                config={"displayModeBar": False, "responsive": True},
                style={"height": f"{height}px"},
                className="dashboard-graph",
            ),
        ],
        className=f"panel chart-card {class_name}".strip(),
    )
