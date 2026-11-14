"""Reusable Dash building blocks (Mantine inputs, cards, formatting)."""

from typing import Dict, List, Optional

import dash_mantine_components as dmc
from dash import dcc

THOUSAND_SEPARATOR = "’"


def number_input(
    component_id: str,
    label: str,
    value: Optional[float],
    minimum: float,
    step: float,
    unit: str = "",
    maximum: Optional[float] = None,
    description: str = "",
    decimals: Optional[int] = None,
):
    """Number field with Swiss thousand separator; ``unit`` is shown inside the field."""
    optional = {}
    if description:
        optional["description"] = description
    if maximum is not None:
        optional["max"] = maximum
    if decimals is not None:
        optional["decimalScale"] = decimals
    if unit:
        optional["rightSection"] = unit
        optional["rightSectionWidth"] = unit_width(unit)
    return dmc.NumberInput(
        id=component_id,
        label=label,
        value=value,
        min=minimum,
        step=step,
        allowDecimal=decimals != 0,
        allowNegative=minimum < 0,
        thousandSeparator=THOUSAND_SEPARATOR,
        decimalSeparator=".",
        hideControls=True,
        classNames={"section": "input-unit"},
        debounce=500,
        **optional,
    )


def unit_width(unit: str) -> int:
    """Width in px for a unit label inside an input."""
    return max(36, 7 * len(unit) + 14)


def segmented(component_id: str, label: str, data: List[Dict], value: str, description: str = ""):
    """Switch between a few options (all values are strings)."""
    optional = {"description": description} if description else {}
    return dmc.InputWrapper(
        label=label,
        **optional,
        children=dmc.SegmentedControl(
            id=component_id,
            data=data,
            value=value,
            fullWidth=True,
            size="sm",
            mt=4,
        ),
    )


def select(
    component_id: str,
    label: str,
    data: List[Dict],
    value,
    description: str = "",
    searchable: bool = False,
):
    optional = {"description": description} if description else {}
    return dmc.Select(
        id=component_id,
        label=label,
        **optional,
        data=data,
        value=value,
        searchable=searchable,
        allowDeselect=False,
        checkIconPosition="right",
    )


def money(value: float, decimals: int = 0) -> str:
    return f"CHF {value:,.{decimals}f}".replace(",", THOUSAND_SEPARATOR)


def metric_card(label: str, value: str, detail: str, tone: str, icon: str):
    return dmc.Paper(
        [
            dmc.Group(
                [
                    dmc.Text(icon, className="metric-icon", span=True),
                    dmc.Text(label, className="metric-label", span=True),
                ],
                gap=8,
                wrap="nowrap",
            ),
            dmc.Text(value, className="metric-value"),
            dmc.Text(detail, className="metric-detail"),
        ],
        withBorder=True,
        p="md",
        className=f"metric-card metric-{tone}",
    )


def section_card(title: str, subtitle: str, children, class_name: str = ""):
    heading = [dmc.Title(title, order=4, className="card-title")]
    if subtitle:
        heading.append(dmc.Text(subtitle, className="card-subtitle"))
    return dmc.Paper(
        [*heading, *children],
        withBorder=True,
        p="md",
        className=f"section-card {class_name}".strip(),
    )


def chart_card(title: str, subtitle: str, figure, height: int, class_name: str = ""):
    return section_card(
        title,
        subtitle,
        [
            dcc.Graph(
                figure=figure,
                config={"displayModeBar": False, "responsive": True},
                style={"height": f"{height}px"},
                className="dashboard-graph",
            )
        ],
        class_name=f"chart-card {class_name}".strip(),
    )
