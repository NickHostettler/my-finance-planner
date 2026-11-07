"""Plotly figure factories for the dashboard."""

from typing import Dict, List

import plotly.graph_objects as go

from personal_finance.core.projection import project_balance
from personal_finance.dashboard.components import (
    money,
)
from personal_finance.dashboard.theme import COLORS


def chart_layout(**kwargs) -> Dict:
    layout = {
        "template": "plotly_white",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "Inter, Segoe UI, sans-serif", "color": COLORS["muted"], "size": 12},
        "margin": {"l": 12, "r": 18, "t": 18, "b": 12},
        "legend": {"orientation": "h", "y": 1.12, "x": 0, "font": {"size": 11}},
        "hoverlabel": {"bgcolor": "#13251f", "font": {"color": "#ffffff"}},
        "xaxis": {"showgrid": False, "zeroline": False, "title": None},
        "yaxis": {
            "gridcolor": "#edf1ee",
            "zeroline": False,
            "title": None,
            "tickprefix": "CHF ",
            "separatethousands": True,
        },
        "autosize": True,
    }
    layout.update(kwargs)
    return layout


def projection_figure(
    ages: List[int],
    pillar2_values: List[float],
    pillar3a_values: List[float],
    pillar3b_values: List[float],
) -> go.Figure:
    figure = go.Figure()
    series = [
        ("2. Säule", pillar2_values, COLORS["green"]),
        ("3a · gebunden", pillar3a_values, COLORS["blue"]),
        ("3b · frei", pillar3b_values, COLORS["gold"]),
    ]
    for label, values, color in series:
        figure.add_trace(
            go.Scatter(
                x=ages,
                y=values,
                name=label,
                mode="lines",
                stackgroup="wealth",
                line={"color": color, "width": 2},
                fillcolor=color,
                hovertemplate=f"<b>{label}</b><br>Alter %{{x}}<br>%{{y:,.0f}} CHF<extra></extra>",
            )
        )
    figure.update_layout(
        **chart_layout(
            height=390,
            hovermode="x unified",
            xaxis={"showgrid": False, "zeroline": False, "title": None, "dtick": 5},
            yaxis={
                "gridcolor": "#edf1ee",
                "zeroline": False,
                "title": None,
                "tickprefix": "CHF ",
                "separatethousands": True,
            },
        )
    )
    return figure


def composition_figure(
    pillar2,
    pillar3a,
    pillar3b,
    initial_2: float,
    initial_3a: float,
    initial_3b: float,
    pillar2_return: float,
    inflation_rate: float = 0,
) -> go.Figure:
    initial_balance = initial_2 + initial_3a + initial_3b
    years = pillar2.years_until_retirement
    contributions_per_year = (
        pillar2.annual_contribution_total
        + pillar3a.annual_savings
        + pillar3b.annual_savings
    )
    contributions = sum(
        contributions_per_year / ((1 + inflation_rate) ** year)
        for year in range(1, years + 1)
    )
    projected_total = (
        project_balance(
            pillar2.annual_contribution_total,
            years,
            pillar2_return,
            initial_2,
            inflation_rate,
        )[-1]
        + project_balance(
            pillar3a.annual_savings,
            years,
            pillar3a.assumed_annual_return,
            initial_3a,
            inflation_rate,
        )[-1]
        + project_balance(
            pillar3b.annual_savings,
            years,
            pillar3b.assumed_annual_return,
            initial_3b,
            inflation_rate,
        )[-1]
    )
    gains = max(0, projected_total - initial_balance - contributions)
    figure = go.Figure(
        go.Pie(
            labels=["Bisheriges Startguthaben", "Neue Einzahlungen", "Verzinsung & Anlagezuwachs"],
            values=[initial_balance, contributions, gains],
            hole=0.72,
            sort=False,
            marker={
                "colors": [COLORS["blue"], COLORS["green"], "#b9d9c6"],
                "line": {"color": "#ffffff", "width": 4},
            },
            textinfo="none",
            hovertemplate="%{label}<br>CHF %{value:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(
        **chart_layout(
            height=300,
            showlegend=True,
            legend={"orientation": "h", "y": -0.02, "x": 0.5, "xanchor": "center", "font": {"size": 11}},
            annotations=[
                {
                    "text": "Bis zur<br>Pensionierung",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 13, "color": COLORS["muted"]},
                }
            ],
        )
    )
    return figure


def comparison_figure(
    pillar2_value: float,
    pillar3a_value: float,
    pillar3b_value: float,
    projected_total: float,
) -> go.Figure:
    labels = ["2. Säule", "3a · dein Plan", "3b · dein Plan", "Gesamtprognose"]
    values = [
        pillar2_value,
        pillar3a_value,
        pillar3b_value,
        projected_total,
    ]
    colors = [COLORS["green"], COLORS["blue"], COLORS["gold"], COLORS["ink"]]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker={"color": colors},
            text=[money(value) for value in values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>CHF %{x:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(
        **chart_layout(
            height=300,
            showlegend=False,
            margin={"l": 10, "r": 90, "t": 14, "b": 12},
            xaxis={
                "showgrid": True,
                "gridcolor": "#edf1ee",
                "zeroline": False,
                "title": None,
                "tickprefix": "CHF ",
                "separatethousands": True,
            },
            yaxis={"showgrid": False, "zeroline": False, "title": None, "autorange": "reversed"},
        )
    )
    return figure
