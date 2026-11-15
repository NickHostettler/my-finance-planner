"""Plotly figure factories for the dashboard."""

from typing import Dict, List, Sequence

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


def withdrawal_figure(
    ages: List[int],
    pillar2_without: List[float],
    pillar2_with: List[float],
    pillar3a_without: List[float],
    pillar3a_with: List[float],
) -> go.Figure:
    """2nd pillar and 3a with the withdrawals for the purchase (solid) and without (dotted)."""
    figure = go.Figure()
    series = [
        ("2. Säule ohne Kauf", pillar2_without, COLORS["green"], "dot"),
        ("2. Säule mit Kauf", pillar2_with, COLORS["green"], "solid"),
        ("3a ohne Kauf", pillar3a_without, COLORS["blue"], "dot"),
        ("3a mit Kauf", pillar3a_with, COLORS["blue"], "solid"),
    ]
    for label, values, color, dash in series:
        figure.add_trace(
            go.Scatter(
                x=ages,
                y=values,
                name=label,
                mode="lines",
                line={"color": color, "width": 2.5 if dash == "solid" else 1.8, "dash": dash},
                hovertemplate=f"<b>{label}</b><br>Alter %{{x}}<br>%{{y:,.0f}} CHF<extra></extra>",
            )
        )
    figure.update_layout(
        **chart_layout(
            height=320,
            hovermode="x unified",
            xaxis={"showgrid": False, "zeroline": False, "title": None, "dtick": 5},
        )
    )
    return figure


def wealth_figure(
    ages: List[int],
    savings: List[float],
    property_value: List[float],
    debt: List[float],
    net_wealth: List[float],
) -> go.Figure:
    """Savings and the home (stacked), the mortgage debt and the net wealth over time."""
    figure = go.Figure()
    for label, values, color in [
        ("Vorsorge und Vermögen", savings, COLORS["green"]),
        ("Immobilie (Kaufpreis)", property_value, COLORS["gold"]),
    ]:
        figure.add_trace(
            go.Scatter(
                x=ages,
                y=values,
                name=label,
                mode="lines",
                stackgroup="assets",
                line={"color": color, "width": 1.5},
                fillcolor=color,
                opacity=0.5,
                hovertemplate=f"<b>{label}</b><br>Alter %{{x}}<br>%{{y:,.0f}} CHF<extra></extra>",
            )
        )
    for label, values, color, dash, width in [
        ("Hypothekarschuld", debt, COLORS["red"], "dash", 2.5),
        ("Nettovermögen", net_wealth, COLORS["ink"], "solid", 3),
    ]:
        figure.add_trace(
            go.Scatter(
                x=ages,
                y=values,
                name=label,
                mode="lines",
                line={"color": color, "width": width, "dash": dash},
                hovertemplate=f"<b>{label}</b><br>Alter %{{x}}<br>%{{y:,.0f}} CHF<extra></extra>",
            )
        )
    figure.update_layout(
        **chart_layout(
            height=360,
            hovermode="x unified",
            xaxis={"showgrid": False, "zeroline": False, "title": None, "dtick": 5},
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
    per_year=None,
) -> go.Figure:
    """Initial balances, contributions and growth until retirement.

    ``per_year`` (2nd pillar, 3a, 3b) gives the contributions of each year, e.g. with life
    phases; otherwise they follow the plan.
    """
    initial_balance = initial_2 + initial_3a + initial_3b
    years = pillar2.years_until_retirement
    if per_year is None:
        pillar2_contributions = pillar2.contributions()
        if not isinstance(pillar2_contributions, Sequence):
            pillar2_contributions = [pillar2_contributions] * years
        per_year = (
            pillar2_contributions,
            [pillar3a.annual_savings] * years,
            [pillar3b.annual_savings] * years,
        )
    pillar2_contributions, pillar3a_contributions, pillar3b_contributions = per_year
    contributions = sum(
        (
            pillar2_contributions[year - 1]
            + pillar3a_contributions[year - 1]
            + pillar3b_contributions[year - 1]
        )
        / ((1 + inflation_rate) ** year)
        for year in range(1, years + 1)
    )
    projected_total = (
        project_balance(
            list(pillar2_contributions), years, pillar2_return, initial_2, inflation_rate
        )[-1]
        + project_balance(
            list(pillar3a_contributions),
            years,
            pillar3a.assumed_annual_return,
            initial_3a,
            inflation_rate,
        )[-1]
        + project_balance(
            list(pillar3b_contributions),
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
            legend={
                "orientation": "h",
                "y": -0.02,
                "x": 0.5,
                "xanchor": "center",
                "font": {"size": 11},
            },
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


def phases_figure(
    ages: Sequence[int],
    workloads: Sequence[float],
    monthly_incomes: Sequence[float],
    birth_ages: Sequence[int],
) -> go.Figure:
    """Workload (bars, right axis in %) and income per month (line) over the years (#33).

    A marker on the age axis shows each birth.
    """
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=list(ages),
            y=[workload * 100 for workload in workloads],
            name="Pensum",
            yaxis="y2",
            marker={"color": COLORS["green_light"], "line": {"color": COLORS["green"], "width": 1}},
            hovertemplate="Alter %{x}<br>Pensum %{y:.0f} %<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=list(ages),
            y=list(monthly_incomes),
            name="Einkommen pro Monat",
            mode="lines",
            line={"color": COLORS["green"], "width": 2.5, "shape": "hv"},
            hovertemplate="Alter %{x}<br>%{y:,.0f} CHF pro Monat<extra></extra>",
        )
    )
    births = [age for age in birth_ages if ages and ages[0] <= age <= ages[-1]]
    if births:
        figure.add_trace(
            go.Scatter(
                x=births,
                y=[112] * len(births),  # above the workload bars (right axis)
                yaxis="y2",
                name="Geburt",
                mode="markers",
                marker={"symbol": "star", "size": 13, "color": COLORS["gold"]},
                hovertemplate="Geburt mit %{x}<extra></extra>",
            )
        )
    figure.update_layout(
        **chart_layout(
            height=300,
            hovermode="x unified",
            bargap=0.15,
            margin={"l": 12, "r": 44, "t": 18, "b": 12},  # room for the % labels
            xaxis={"showgrid": False, "zeroline": False, "title": None, "dtick": 5},
            yaxis={
                "gridcolor": "#edf1ee",
                "zeroline": False,
                "title": None,
                "tickprefix": "CHF ",
                "separatethousands": True,
                "rangemode": "tozero",  # the income drop is not exaggerated
            },
            yaxis2={
                "overlaying": "y",
                "side": "right",
                "range": [0, 120],
                "tickvals": [0, 25, 50, 75, 100],
                "ticktext": ["0 %", "25 %", "50 %", "75 %", "100 %"],
                "showgrid": False,
                "title": None,
            },
        )
    )
    return figure


def gap_figure(ages: Sequence[int], plan: Sequence[float], full_time: Sequence[float]) -> go.Figure:
    """Retirement capital with the life phases (solid) and at 100 % (dotted)."""
    figure = go.Figure()
    for label, values, color, dash in [
        ("Bei 100 % bis zur Pensionierung", full_time, COLORS["muted"], "dot"),
        ("Mit deinen Lebensphasen", plan, COLORS["green"], "solid"),
    ]:
        figure.add_trace(
            go.Scatter(
                x=list(ages),
                y=list(values),
                name=label,
                mode="lines",
                line={"color": color, "width": 2.5, "dash": dash},
                hovertemplate=f"<b>{label}</b><br>Alter %{{x}}<br>%{{y:,.0f}} CHF<extra></extra>",
            )
        )
    figure.update_layout(
        **chart_layout(
            height=300,
            hovermode="x unified",
            xaxis={"showgrid": False, "zeroline": False, "title": None, "dtick": 5},
        )
    )
    return figure
