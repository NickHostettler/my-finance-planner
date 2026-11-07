"""Modern Dash dashboard for Swiss personal finance planning."""

import math
import sqlite3
from typing import Dict, List, Optional, Tuple

import dash
import plotly.graph_objects as go
from dash import Input, Output, State, ctx, dcc, html, no_update

from personal_finance import config, scenario_store
from personal_finance import ahv
from personal_finance.calculator import FinanceCalculator
from personal_finance.deductions import DeductionsCalculator
from personal_finance.pillar_2 import Pillar2Calculator, Pillar2Result


COLORS = {
    "ink": "#13251f",
    "muted": "#65756e",
    "green": "#16734b",
    "green_light": "#e9f5ee",
    "blue": "#4c7fe8",
    "blue_light": "#edf2ff",
    "gold": "#c18a32",
    "gold_light": "#fbf3e5",
    "surface": "#ffffff",
    "canvas": "#f4f7f5",
    "border": "#e5ebe7",
    "red": "#a63d40",
}

app = dash.Dash(__name__, title="Finanzplan | Schweizer Vorsorge")


def _field(label: str, component, hint: str = "", label_id: str = None, hint_id: str = None):
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


def _input(
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


def _dropdown(component_id: str, options: List[Dict], value):
    return dcc.Dropdown(
        id=component_id,
        options=options,
        value=value,
        clearable=False,
        searchable=False,
        className="modern-dropdown",
    )


app.layout = html.Div(
    [
        html.Header(
            [
                html.Div(
                    [
                        html.Div("F", className="brand-mark"),
                        html.Div(
                            [
                                html.Div("FINANZPLAN", className="brand-name"),
                                html.Div("Persönliche Vorsorgeplanung", className="brand-caption"),
                            ]
                        ),
                    ],
                    className="brand",
                ),
                html.Div(
                    [html.Span(className="status-dot"), "Schweizer Vorsorge"],
                    className="header-chip",
                ),
            ],
            className="topbar",
        ),
        html.Main(
            [
                html.Section(
                    [
                        html.Div(
                            [
                                html.Div("DEIN FINANZKOMPASS", className="eyebrow"),
                                html.H1(["Heute planen.", html.Br(), "Morgen sicherer sein."]),
                                html.P(
                                    "Entdecke, wie sich deine Sparbeiträge bis zur Pensionierung "
                                    "entwickeln können – transparent, flexibel und in CHF."
                                ),
                            ],
                            className="hero-copy",
                        ),
                        html.Div(
                            [
                                html.Div("DEIN PLAN AUF EINEN BLICK", className="hero-note-label"),
                                html.Div("2. Säule", className="hero-note-title"),
                                html.Div(
                                    "Berufliche Vorsorge, gebundene 3a und freies Sparen "
                                    "in einer persönlichen Projektion.",
                                    className="hero-note-copy",
                                ),
                                html.Div(
                                    [
                                        html.Span("2. Säule", className="hero-tag"),
                                        html.Span("3a", className="hero-tag"),
                                        html.Span("3b", className="hero-tag"),
                                    ],
                                    className="hero-tags",
                                ),
                            ],
                            className="hero-note",
                        ),
                    ],
                    className="hero",
                ),
                html.Div(
                    [
                        html.Section(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Div("01", className="section-index"),
                                                html.Div(
                                                    [
                                                        html.H2("Deine Ausgangslage"),
                                                        html.P(
                                                            "Passe die Werte an – die Prognose aktualisiert sich automatisch."
                                                        ),
                                                    ],
                                                    className="section-heading-copy",
                                                ),
                                            ],
                                            className="section-heading",
                                        ),
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.Div("SZENARIEN", className="subsection-title"),
                                                        html.P(
                                                            "Speichere deine Eingaben lokal und lade sie später "
                                                            "zum Vergleichen wieder. Gleiche Namen überschreiben "
                                                            "das vorhandene Szenario. Deine letzten Eingaben "
                                                            "werden automatisch lokal gemerkt. Die SQLite-Datei "
                                                            "ist nicht verschlüsselt.",
                                                            className="section-hint",
                                                        ),
                                                    ],
                                                    className="scenario-copy",
                                                ),
                                                html.Div(
                                                    [
                                                        dcc.Input(
                                                            id="scenario-name-input",
                                                            type="text",
                                                            placeholder="Name, z. B. Teilzeit ab 50",
                                                            maxLength=scenario_store.MAX_SCENARIO_NAME_LENGTH,
                                                            className="scenario-name-input",
                                                        ),
                                                        html.Button(
                                                            "Szenario speichern",
                                                            id="scenario-save-button",
                                                            n_clicks=0,
                                                            className="scenario-button scenario-save",
                                                        ),
                                                    ],
                                                    className="scenario-save-controls",
                                                ),
                                                html.Div(
                                                    [
                                                        dcc.Dropdown(
                                                            id="scenario-select",
                                                            options=[],
                                                            value=None,
                                                            placeholder="Gespeichertes Szenario auswählen",
                                                            clearable=True,
                                                            searchable=True,
                                                            className="modern-dropdown",
                                                        ),
                                                        html.Button(
                                                            "Laden",
                                                            id="scenario-load-button",
                                                            n_clicks=0,
                                                            className="scenario-button",
                                                        ),
                                                        html.Button(
                                                            "Löschen",
                                                            id="scenario-delete-button",
                                                            n_clicks=0,
                                                            className="scenario-button scenario-delete",
                                                        ),
                                                    ],
                                                    className="scenario-load-controls",
                                                ),
                                                html.Div(id="scenario-status", className="scenario-status"),
                                                dcc.Interval(
                                                    id="scenario-initial-load",
                                                    interval=1,
                                                    max_intervals=1,
                                                ),
                                                dcc.Interval(
                                                    id="last-inputs-initial-load",
                                                    interval=1,
                                                    max_intervals=1,
                                                ),
                                                html.Div(
                                                    id="last-inputs-status",
                                                    className="scenario-status",
                                                ),
                                            ],
                                            className="scenario-manager",
                                        ),
                                        html.Div("EINKOMMEN & PLANUNG", className="subsection-title"),
                                        html.Div(
                                            [
                                                _field(
                                                    "Einkommen (Netto)",
                                                    _input(
                                                        "monthly-income-input",
                                                        5000,
                                                        0,
                                                        100,
                                                        "CHF",
                                                        suffix_id="income-suffix",
                                                    ),
                                                    "Einkommen nach Abzügen",
                                                    label_id="income-label",
                                                    hint_id="income-hint",
                                                ),
                                                _field(
                                                    "Zeitraum",
                                                    _dropdown(
                                                        "income-period-input",
                                                        [
                                                            {"label": "Monatlich", "value": "monthly"},
                                                            {"label": "Jährlich", "value": "yearly"},
                                                        ],
                                                        "monthly",
                                                    ),
                                                ),
                                                _field(
                                                    "Einkommensart",
                                                    _dropdown(
                                                        "income-type-input",
                                                        [
                                                            {"label": "Netto", "value": "net"},
                                                            {"label": "Brutto", "value": "gross"},
                                                        ],
                                                        "net",
                                                    ),
                                                ),
                                                _field(
                                                    "Dein aktuelles Alter",
                                                    _dropdown(
                                                        "current-age-input",
                                                        [
                                                            {"label": f"{age} Jahre", "value": age}
                                                            for age in range(18, 81)
                                                        ],
                                                        35,
                                                    ),
                                                    "In vollen Jahren",
                                                ),
                                                _field(
                                                    "Geplantes Pensionierungsalter",
                                                    _dropdown(
                                                        "retirement-age-input",
                                                        [
                                                            {"label": f"{age} Jahre", "value": age}
                                                            for age in range(55, 81)
                                                        ],
                                                        65,
                                                    ),
                                                    "Abhängig von deinem persönlichen Plan",
                                                ),
                                            ],
                                            className="field-grid field-grid-income",
                                        ),
                                        html.Div(
                                            _field(
                                                "Kanton für Nettoschätzung",
                                                _dropdown(
                                                    "canton-input",
                                                    [
                                                        {"label": f"{name} ({code})", "value": code}
                                                        for code, name in [
                                                            ("ZH", "Zürich"), ("BE", "Bern"),
                                                            ("LU", "Luzern"), ("UR", "Uri"),
                                                            ("SZ", "Schwyz"), ("OW", "Obwalden"),
                                                            ("NW", "Nidwalden"), ("GL", "Glarus"),
                                                            ("ZG", "Zug"), ("FR", "Freiburg"),
                                                            ("SO", "Solothurn"), ("BS", "Basel-Stadt"),
                                                            ("BL", "Basel-Landschaft"), ("SH", "Schaffhausen"),
                                                            ("AR", "Appenzell Ausserrhoden"), ("AI", "Appenzell Innerrhoden"),
                                                            ("SG", "St. Gallen"), ("GR", "Graubünden"),
                                                            ("AG", "Aargau"), ("TG", "Thurgau"),
                                                            ("TI", "Tessin"), ("VD", "Waadt"),
                                                            ("VS", "Wallis"), ("NE", "Neuenburg"),
                                                            ("GE", "Genf"), ("JU", "Jura"),
                                                        ]
                                                    ],
                                                    "ZH",
                                                ),
                                                "Nur für Brutto relevant; wird zur groben Steuer-Nettoschätzung verwendet.",
                                            ),
                                            id="canton-control",
                                            className="canton-control",
                                            style={"display": "none"},
                                        ),
                                        html.Div(
                                            id="income-preview",
                                            className="income-preview",
                                        ),
                                        html.Div(className="section-divider"),
                                        _field(
                                            "Darstellung der Prognose",
                                            _dropdown(
                                                "display-basis-input",
                                                [
                                                    {"label": "Nominal · zukünftige CHF", "value": "nominal"},
                                                    {"label": "Real · heutige Kaufkraft", "value": "real"},
                                                ],
                                                "nominal",
                                            ),
                                            "Realwerte berücksichtigen die hinterlegte jährliche Inflation.",
                                        ),
                                        html.Div(className="section-divider"),
                                        html.Div(
                                            [
                                                html.Div("BISHERIGE SITUATION", className="subsection-title"),
                                                html.P(
                                                    "Deine bereits vorhandenen Guthaben in der Vorsorge.",
                                                    className="section-hint",
                                                ),
                                                html.Div(
                                                    [
                                                        _field(
                                                            "Aktuelles 3a-Guthaben",
                                                            _input(
                                                                "pillar3a-initial-input",
                                                                0,
                                                                0,
                                                                1000,
                                                                "CHF",
                                                            ),
                                                            "Optional; leer entspricht 0 CHF",
                                                        ),
                                                        _field(
                                                            "Aktuelles BVG-/2.-Säule-Guthaben",
                                                            _input(
                                                                "pillar2-initial-input",
                                                                0,
                                                                0,
                                                                1000,
                                                                "CHF",
                                                            ),
                                                            "Stand gemäss aktuellem PK-Ausweis",
                                                        ),
                                                        _field(
                                                            "Aktuelles 3b-Guthaben",
                                                            _input(
                                                                "pillar3b-initial-input",
                                                                0,
                                                                0,
                                                                1000,
                                                                "CHF",
                                                            ),
                                                            "Optional; leer entspricht 0 CHF",
                                                        ),
                                                    ],
                                                    className="field-grid current-balance-grid",
                                                ),
                                            ],
                                            className="current-situation",
                                        ),
                                        html.Div(className="section-divider"),
                                        html.Div(
                                            [
                                                html.Div(
                                                    "AHV-RENTENSCHÄTZUNG",
                                                    className="subsection-title",
                                                ),
                                                html.P(
                                                    "Die AHV ist eine Rente und kein persönliches "
                                                    "Altersguthaben. Die unverbindliche Schätzung verwendet "
                                                    "dein durchschnittliches Jahreseinkommen und die "
                                                    "Beitragsjahre bei Pensionierung.",
                                                    className="section-hint",
                                                ),
                                                html.Div(
                                                    [
                                                        _field(
                                                            "Massgebendes durchschnittliches Jahreseinkommen",
                                                            _input(
                                                                "ahv-average-income-input",
                                                                    100000,
                                                                0,
                                                                1000,
                                                                "CHF/Jahr",
                                                            ),
                                                            "Für die Schätzung; wenn möglich aus IK/AHV-Auszug",
                                                        ),
                                                        _field(
                                                            "Beitragsjahre bei Pensionierung",
                                                            _input(
                                                                "ahv-contribution-years-input",
                                                                44,
                                                                0,
                                                                1,
                                                                "von 44",
                                                                44,
                                                            ),
                                                            "Anpassen, falls du Beitragslücken erwartest",
                                                        ),
                                                    ],
                                                    className="field-grid ahv-input-grid",
                                                ),
                                            ],
                                            className="ahv-input-section",
                                        ),
                                        html.Div(className="section-divider"),
                                        html.Div(
                                            [
                                                html.Div(
                                                    "DEINE MONATLICHEN SPARBEITRÄGE",
                                                    className="subsection-title strategy-section-title",
                                                ),
                                                html.Div(
                                                    [
                                                        _field(
                                                            "Berechnungsgrundlage 2. Säule",
                                                            _dropdown(
                                                                "pillar2-mode-input",
                                                                [
                                                                    {
                                                                        "label": "Vereinfachte BVG-Schätzung",
                                                                        "value": "minimum",
                                                                    },
                                                                    {
                                                                        "label": "Eigene PK-Werte verwenden",
                                                                        "value": "custom",
                                                                    },
                                                                ],
                                                                "minimum",
                                                            ),
                                                            "Die BVG-Schätzung ist vereinfacht; dein PK-Ausweis ist genauer.",
                                                        ),
                                                        html.Div(
                                                            [
                                                                _field(
                                                                    "Dein monatlicher Arbeitnehmerbeitrag",
                                                                    _input(
                                                                        "pillar2-employee-input",
                                                                            None,
                                                                        0,
                                                                        10,
                                                                        "CHF",
                                                                    ),
                                                                ),
                                                                _field(
                                                                    "Monatlicher Arbeitgeberbeitrag",
                                                                    _input(
                                                                        "pillar2-employer-input",
                                                                            None,
                                                                        0,
                                                                        10,
                                                                        "CHF",
                                                                    ),
                                                                ),
                                                                _field(
                                                                    "Verzinsung gemäss PK-Ausweis",
                                                                    _input(
                                                                        "pillar2-return-input",
                                                                            None,
                                                                        0,
                                                                        0.05,
                                                                        "%",
                                                                        20,
                                                                    ),
                                                                ),
                                                            ],
                                                            id="pillar2-custom-fields",
                                                            className="field-grid pillar2-custom-grid",
                                                            style={"display": "none"},
                                                        ),
                                                    ],
                                                    className="pillar2-settings",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Div("DEINE 3A-STRATEGIE", className="subsection-title"),
                                                        _field(
                                                            "Beitragsart",
                                                            _dropdown(
                                                                "savings-mode-input",
                                                                [
                                                                    {"label": "Sparquote vom Einkommen", "value": "rate"},
                                                                    {"label": "Fester Monatsbetrag", "value": "amount"},
                                                                ],
                                                                "rate",
                                                            ),
                                                        ),
                                                        html.Div(
                                                            _field(
                                                                "Sparquote",
                                                                _input(
                                                                    "pillar3a-rate-input",
                                                                    10,
                                                                    0,
                                                                    0.5,
                                                                    "%",
                                                                    100,
                                                                ),
                                                                "Wird auf das modellierte 3a-Maximum begrenzt",
                                                            ),
                                                            id="rate-control",
                                                        ),
                                                        html.Div(
                                                            _field(
                                                                "Monatlicher 3a-Betrag",
                                                                _input(
                                                                    "pillar3a-amount-input",
                                                                    350,
                                                                    0,
                                                                    0.01,
                                                                    "CHF",
                                                                    config.PILLAR3A_MONTHLY_MAX,
                                                                ),
                                                                (
                                                                    f"Modell-Limit: CHF {config.PILLAR3A_ANNUAL_MAX:,.0f}/Jahr "
                                                                    f"(ca. CHF {config.PILLAR3A_MONTHLY_MAX:,.2f}/Monat)"
                                                                ).replace(",", "’"),
                                                            ),
                                                            id="amount-control",
                                                            style={"display": "none"},
                                                        ),
                                                    ],
                                                    className="strategy-panel strategy-3a",
                                                ),
                                                html.Div(
                                                    [
                                                        html.Div("DEIN FREIES SPAREN", className="subsection-title"),
                                                        _field(
                                                            "Monatlicher 3b-Beitrag",
                                                            _input(
                                                                "pillar3b-amount-input",
                                                                500,
                                                                0,
                                                                100,
                                                                "CHF",
                                                            ),
                                                            "Flexibles Sparen ohne 3a-Modell-Limit",
                                                        ),
                                                        _field(
                                                            "Angenommene Rendite",
                                                            _dropdown(
                                                                "return-input",
                                                                [
                                                                    {"label": "Vorsichtig · 2 %", "value": 0.02},
                                                                    {"label": "Ausgewogen · 4 %", "value": 0.04},
                                                                    {"label": "Chancenorientiert · 6 %", "value": 0.06},
                                                                ],
                                                                0.04,
                                                            ),
                                                            "Gilt für 3a und 3b",
                                                        ),
                                                    ],
                                                    className="strategy-panel strategy-3b",
                                                ),
                                            ],
                                            className="strategy-section",
                                        ),
                                    ],
                                    className="panel input-panel",
                                ),
                                html.Div(id="calculation-notice", className="calculation-notice"),
                                html.Div(id="results-section"),
                                html.Div(
                                    [
                                        html.Span("i", className="disclaimer-icon"),
                                        html.Div(
                                            [
                                                html.Strong("Modell statt Beratung"),
                                                html.P(
                                                    "Die Projektion basiert auf vereinfachten Annahmen und "
                                                    "ersetzt keine individuelle Finanz- oder Steuerberatung. "
                                                    "BVG- und 3a-Werte können je nach Vorsorgeplan und "
                                                    "geltenden gesetzlichen Limiten abweichen."
                                                ),
                                            ]
                                        ),
                                    ],
                                    className="disclaimer",
                                ),
                            ],
                            className="dashboard-column",
                        ),
                    ],
                    className="content-shell",
                ),
            ],
            className="page-shell",
        ),
        html.Footer("Finanzplan · Schweizer Vorsorge", className="page-footer"),
    ],
    className="app-background",
)


def _money(value: float, decimals: int = 0) -> str:
    return f"CHF {value:,.{decimals}f}".replace(",", "’")


def _metric_card(label: str, value: str, detail: str, tone: str, icon: str):
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


def _chart_card(title: str, subtitle: str, figure, height: int, class_name: str = ""):
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


def _chart_layout(**kwargs) -> Dict:
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


def _projection_figure(
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
        **_chart_layout(
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


def _composition_figure(
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
        _projection_values(
            pillar2.annual_contribution_total,
            years,
            pillar2_return,
            initial_2,
            inflation_rate,
        )[-1]
        + _projection_values(
            pillar3a.annual_savings,
            years,
            pillar3a.assumed_annual_return,
            initial_3a,
            inflation_rate,
        )[-1]
        + _projection_values(
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
        **_chart_layout(
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


def _comparison_figure(
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
            text=[_money(value) for value in values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}<br>CHF %{x:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(
        **_chart_layout(
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


def _projection_values(
    annual_contribution: float,
    years: int,
    annual_return: float,
    initial_balance: float = 0,
    inflation_rate: float = 0,
) -> List[float]:
    values = [initial_balance]
    balance = initial_balance
    for year in range(1, years + 1):
        balance = (balance + annual_contribution) * (1 + annual_return)
        values.append(balance / ((1 + inflation_rate) ** year))
    return values


def _results_view(
    income: float,
    current_age: int,
    retirement_age: int,
    assumed_return: float,
    analysis,
    pillar3a,
    pillar3b,
    pillar2_mode: str,
    pillar2_return: float,
    initial_2: float,
    initial_3a: float,
    initial_3b: float,
    ahv_average_income: Optional[float],
    ahv_contribution_years: int,
    display_basis: str = "nominal",
) -> Tuple[List, str]:
    pillar2 = analysis.pillar2
    years = analysis.years_to_retirement
    inflation_rate = config.INFLATION_RATE if display_basis == "real" else 0
    basis_detail = (
        f"Reale Werte in heutiger Kaufkraft · "
        f"{config.INFLATION_RATE:.0%} Inflation pro Jahr"
        if display_basis == "real"
        else "Nominale CHF · ohne Inflationsbereinigung"
    )
    ahv_estimated_today = (
        ahv.estimate_monthly_old_age_pension(
            ahv_average_income,
            ahv_contribution_years,
        )
        if ahv_average_income is not None
        else None
    )
    ahv_estimated_display = ahv.project_pension_basis(
        ahv_estimated_today,
        years,
        config.INFLATION_RATE,
        display_basis,
    )
    total = (
        _projection_values(
            pillar2.annual_contribution_total,
            years,
            pillar2_return,
            initial_2,
            inflation_rate,
        )[-1]
        + _projection_values(
            pillar3a.annual_savings,
            years,
            assumed_return,
            initial_3a,
            inflation_rate,
        )[-1]
        + _projection_values(
            pillar3b.annual_savings,
            years,
            assumed_return,
            initial_3b,
            inflation_rate,
        )[-1]
    )
    ages = list(range(current_age, retirement_age + 1))
    pillar2_values = _projection_values(
        pillar2.annual_contribution_total,
        years,
        pillar2_return,
        initial_2,
        inflation_rate,
    )
    pillar3a_values = _projection_values(
        pillar3a.annual_savings,
        years,
        assumed_return,
        initial_3a,
        inflation_rate,
    )
    pillar3b_values = _projection_values(
        pillar3b.annual_savings,
        years,
        assumed_return,
        initial_3b,
        inflation_rate,
    )
    growth = _projection_figure(ages, pillar2_values, pillar3a_values, pillar3b_values)
    composition = _composition_figure(
        pillar2,
        pillar3a,
        pillar3b,
        initial_2,
        initial_3a,
        initial_3b,
        pillar2_return,
        inflation_rate,
    )
    comparison = _comparison_figure(
        pillar2_values[-1],
        pillar3a_values[-1],
        pillar3b_values[-1],
        total,
    )
    monthly_savings = pillar3a.monthly_savings + pillar3b.monthly_savings
    savings_rate = monthly_savings / income * 100

    content = [
        html.Div(
            [
                html.Div(
                    [
                        html.Div("02", className="section-index"),
                        html.Div(
                            [
                                html.H2("Dein Vorsorge-Ausblick"),
                                html.P(
                                    f"{years} Jahre Anlagehorizont · "
                                    f"Modellrendite {assumed_return:.0%} für 3a und 3b · "
                                    f"{'reale CHF' if display_basis == 'real' else 'nominale CHF'}"
                                ),
                            ],
                            className="section-heading-copy",
                        ),
                    ],
                    className="section-heading results-heading",
                ),
                html.Div(
                    [
                        _metric_card(
                            "Projiziertes Vorsorgekapital",
                            _money(total),
                            f"bei Pensionierung mit {retirement_age} Jahren · "
                            f"{'heutige Kaufkraft' if display_basis == 'real' else 'nominal'}",
                            "dark",
                            "↗",
                        ),
                        _metric_card(
                            "2. Säule",
                            _money(pillar2_values[-1]),
                            f"AN {_money(pillar2.annual_contribution_employee / 12)} · "
                            f"AG {_money(pillar2.annual_contribution_employer / 12)}/Monat",
                            "green",
                            "Ⅱ",
                        ),
                        _metric_card(
                            "Dein 3a-Plan",
                            _money(pillar3a_values[-1]),
                            f"{_money(pillar3a.monthly_savings)}/Monat · gebunden",
                            "blue",
                            "3a",
                        ),
                        _metric_card(
                            "Dein 3b-Plan",
                            _money(pillar3b_values[-1]),
                            f"{_money(pillar3b.monthly_savings)}/Monat · frei",
                            "gold",
                            "3b",
                        ),
                    ],
                    className="metric-grid",
                ),
                html.Section(
                    [
                        html.Div(
                            [
                                html.H3("AHV-Rente"),
                                html.P(
                                    "Monatliches Ruhestandseinkommen, separat vom angesparten "
                                    "Vorsorgekapital. Die Jahresbeträge berücksichtigen 13 Altersrenten."
                                ),
                            ],
                            className="chart-heading",
                        ),
                        html.Div(
                            [
                                _metric_card(
                                    "Vereinfachte AHV-Schätzung",
                                    (
                                        _money(ahv_estimated_display)
                                        if ahv_estimated_display is not None
                                        else "Angaben fehlen"
                                    ),
                                    (
                                        f"{_money(ahv_estimated_display * 13)} pro Jahr inkl. 13. Rente · "
                                        f"{ahv_contribution_years}/{ahv.FULL_CONTRIBUTION_YEARS} Beitragsjahre"
                                        if ahv_estimated_display is not None
                                        else "Durchschnittliches Jahreseinkommen eingeben"
                                    ),
                                    "green",
                                    "≈",
                                ),
                            ],
                            className="ahv-result-grid",
                        ),
                    ],
                    className="panel ahv-result-panel",
                ),
                html.Div(
                    [
                        _chart_card(
                            "So kann dein Vermögen wachsen",
                            f"Kumulierte Modellprojektion · {basis_detail}",
                            growth,
                            height=390,
                            class_name="growth-card",
                        ),
                        _chart_card(
                            "Einzahlungen & Wachstum",
                            f"Verhältnis der Beiträge zum Zuwachs · {basis_detail}",
                            composition,
                            height=300,
                            class_name="composition-card",
                        ),
                    ],
                    className="charts-grid",
                ),
                _chart_card(
                    "Deine Vorsorgebausteine im Vergleich",
                    f"Projiziertes Kapital bei Pensionierung · {basis_detail}",
                    comparison,
                    height=300,
                    class_name="comparison-card",
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div("DEIN SPARPLAN", className="subsection-title"),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Span(
                                                    "Startguthaben 2. Säule",
                                                    className="detail-label",
                                                ),
                                                html.Strong(_money(initial_2), className="detail-value"),
                                            ],
                                            className="detail-row",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Startguthaben 3a", className="detail-label"),
                                                html.Strong(_money(initial_3a), className="detail-value"),
                                            ],
                                            className="detail-row",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Startguthaben 3b", className="detail-label"),
                                                html.Strong(_money(initial_3b), className="detail-value"),
                                            ],
                                            className="detail-row",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("BVG-Modell", className="detail-label"),
                                                html.Strong(
                                                    (
                                                        f"Eigene PK-Werte · {pillar2_return:.2%} Verzinsung"
                                                        if pillar2_mode == "custom"
                                                        else f"Vereinfachte BVG-Schätzung · {pillar2_return:.0%}"
                                                    ),
                                                    className="detail-value",
                                                ),
                                            ],
                                            className="detail-row",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Monatliches Sparen", className="detail-label"),
                                                html.Strong(_money(monthly_savings), className="detail-value"),
                                            ],
                                            className="detail-row",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Sparquote vom Netto", className="detail-label"),
                                                html.Strong(f"{savings_rate:.1f} %", className="detail-value"),
                                            ],
                                            className="detail-row",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Verbleibend nach 3a & 3b", className="detail-label"),
                                                html.Strong(
                                                    _money(income - monthly_savings),
                                                    className="detail-value",
                                                ),
                                            ],
                                            className="detail-row",
                                        ),
                                    ],
                                    className="detail-list",
                                ),
                            ],
                            className="plan-summary",
                        ),
                        html.Div(
                            [
                                html.Div("MODELLANNAHMEN", className="subsection-title"),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Strong(
                                                    (
                                                        "2. Säule · eigene PK-Werte"
                                                        if pillar2_mode == "custom"
                                                        else "2. Säule · vereinfachte BVG-Schätzung"
                                                    )
                                                ),
                                                html.P(
                                                    (
                                                        "Deine angegebenen Beiträge ersetzen die "
                                                        "vereinfachte Schätzung. Das Dashboard prüft sie "
                                                        "nicht gegen den gesetzlichen Mindestbeitrag oder "
                                                        "das Reglement deiner Pensionskasse."
                                                        if pillar2_mode == "custom"
                                                        else
                                                        "Keine offizielle BVG-Mindestberechnung: Das Modell "
                                                        "zieht einen festen Koordinationsabzug vom "
                                                        "Jahresnettoeinkommen ab, wendet einen "
                                                        "altersabhängigen Beitragssatz an und teilt den "
                                                        "Beitrag 50/50. Reale Eintrittsschwellen, "
                                                        "versicherter Lohn und Reglement deiner PK können "
                                                        "abweichen."
                                                    )
                                                ),
                                            ],
                                            className="assumption-item",
                                        ),
                                        html.Div(
                                            [
                                                html.Strong(
                                                    (
                                                        "2. Säule · gewählte Verzinsung"
                                                        if pillar2_mode == "custom"
                                                        else "2. Säule · Verzinsung der Schätzung"
                                                    )
                                                ),
                                                html.P(
                                                    (
                                                        "Du kannst die Verzinsung im Modus «Eigene PK-Werte» "
                                                        "anhand deines Pensionskassenausweises festlegen. "
                                                        "Deine angegebenen monatlichen Arbeitnehmer- und "
                                                        "Arbeitgeberbeiträge werden auf Jahreswerte "
                                                        "hochgerechnet; Startguthaben und Beiträge werden "
                                                        f"mit deinem gewählten Satz von {pillar2_return:.2%} "
                                                        "pro Jahr verzinst."
                                                        if pillar2_mode == "custom"
                                                        else
                                                        f"Die vereinfachte BVG-Schätzung verwendet fest "
                                                        f"{pillar2_return:.0%} pro Jahr. Dieser Wert ist "
                                                        "nicht in diesem Modus änderbar und muss nicht dem "
                                                        "Zinssatz deiner Pensionskasse entsprechen. Für "
                                                        "einen eigenen Zinssatz wähle oben «Eigene PK-Werte»."
                                                    )
                                                ),
                                            ],
                                            className="assumption-item",
                                        ),
                                        html.Div(
                                            [
                                                html.Strong("3a und 3b · Rendite & Einzahlungen"),
                                                html.P(
                                                    f"Für beide Säulen gilt deine gewählte Rendite von "
                                                    f"{assumed_return:.0%} pro Jahr. Einzahlungen werden "
                                                    "jährlich zu Jahresbeginn gutgeschrieben und danach "
                                                    "verzinst; die nominalen Beiträge werden nicht "
                                                    "automatisch mit der Inflation erhöht. "
                                                    "3a-Einzahlungen sind im Modell auf "
                                                    f"{_money(config.PILLAR3A_ANNUAL_MAX)} pro Jahr begrenzt."
                                                ),
                                            ],
                                            className="assumption-item",
                                        ),
                                        html.Div(
                                            [
                                                html.Strong("AHV-Rente · vereinfachte Schätzung"),
                                                html.P(
                                                    "Die Schätzung interpoliert nur zwischen Mindest- und "
                                                    "Maximalrente der Vollrentenskala 44 und kürzt "
                                                    "proportional nach den eingegebenen Beitragsjahren. "
                                                    "Sie berücksichtigt weder die genaue "
                                                    "Rententabelle noch Erziehungs-/Betreuungsgutschriften, "
                                                    "Einkommensteilung, Beitragslücken im IK oder "
                                                    "Übergangszuschläge. Die 13. Altersrente ist im "
                                                    "Jahresbetrag enthalten. Die AHV wird separat als "
                                                    "Renteneinkommen angezeigt und nicht zum Vorsorgekapital "
                                                    "addiert. Im Nominalmodus wird die Schätzung in heutigen "
                                                    "CHF vereinfachend mit der Inflation hochgerechnet; in "
                                                    "der Realansicht bleibt sie in heutiger Kaufkraft.",
                                                ),
                                                html.Div(
                                                    [
                                                        html.A(
                                                            "AHV-Merkblatt 3.01",
                                                            href=ahv.OFFICIAL_LEAFLET_URL,
                                                            target="_blank",
                                                            rel="noopener noreferrer",
                                                        ),
                                                        " · ",
                                                        html.A(
                                                            "Information zur 13. AHV-Rente",
                                                            href=(
                                                                "https://www.ahv-iv.ch/de/Sozialversicherungen/"
                                                                "Alters-und-Hinterlassenenversicherung-AHV/"
                                                                "13-AHV-Rente"
                                                            ),
                                                            target="_blank",
                                                            rel="noopener noreferrer",
                                                        ),
                                                    ],
                                                    className="assumption-source-links",
                                                ),
                                            ],
                                            className="assumption-item",
                                        ),
                                        html.Div(
                                            [
                                                html.Strong("Inflation & Kaufkraft"),
                                                html.P(
                                                    f"Die Modellannahme beträgt "
                                                    f"{config.INFLATION_RATE:.0%} Inflation pro Jahr. "
                                                    + (
                                                        "In der realen Ansicht wird die jährliche Inflation "
                                                        "von den zukünftigen Kapitalwerten abgezogen. Die "
                                                        "Werte zeigen die Kaufkraft in heutigen CHF."
                                                        if display_basis == "real"
                                                        else
                                                        "In der nominalen Ansicht wird Inflation nicht "
                                                        "abgezogen. Die Werte sind zukünftige CHF und "
                                                        "entsprechen daher nicht der heutigen Kaufkraft."
                                                    )
                                                ),
                                            ],
                                            className="assumption-item",
                                        ),
                                        html.Div(
                                            [
                                                html.Strong("Nicht berücksichtigt"),
                                                html.P(
                                                    "Die AHV-Schätzung ist keine offizielle Rentenberechnung. "
                                                    "Lohn- und Beitragsentwicklung, Änderungen von Rendite "
                                                    "oder PK-Reglement, Gebühren sowie Steuern auf "
                                                    "Vorsorgebeiträge, Renten und Auszahlungen werden nicht "
                                                    "berechnet. Falls du Brutto eingibst, ist auch die "
                                                    "Umrechnung zum Nettolohn nur eine grobe kantonale "
                                                    "Schätzung."
                                                ),
                                            ],
                                            className="assumption-item",
                                        ),
                                    ],
                                    className="assumptions-list",
                                ),
                            ],
                            className="assumptions-summary",
                        ),
                    ],
                    className="panel plan-panel",
                ),
            ],
            className="results-content",
        )
    ]

    return content, ""


@app.callback(
    Output("rate-control", "style"),
    Output("amount-control", "style"),
    Input("savings-mode-input", "value"),
)
def update_savings_controls(mode):
    return (
        {"display": "block" if mode == "rate" else "none"},
        {"display": "block" if mode == "amount" else "none"},
    )


SCENARIO_INPUT_IDS = [
    "monthly-income-input",
    "income-period-input",
    "income-type-input",
    "canton-input",
    "current-age-input",
    "retirement-age-input",
    "savings-mode-input",
    "pillar3a-rate-input",
    "pillar3a-amount-input",
    "pillar3b-amount-input",
    "pillar3a-initial-input",
    "pillar3b-initial-input",
    "pillar2-initial-input",
    "pillar2-mode-input",
    "pillar2-employee-input",
    "pillar2-employer-input",
    "pillar2-return-input",
    "return-input",
    "display-basis-input",
    "ahv-average-income-input",
    "ahv-contribution-years-input",
]


def _scenario_action_response(
    options,
    selected_name,
    message,
    values=None,
    scenario_name_value=no_update,
):
    status_class = (
        "scenario-status-message scenario-status-error"
        if message.startswith("Aktion fehlgeschlagen:")
        else "scenario-status-message"
    )
    status = html.Span(message, className=status_class) if message else ""
    updated_values = (
        [values[field] for field in scenario_store.SCENARIO_FIELDS]
        if values is not None
        else [no_update] * len(SCENARIO_INPUT_IDS)
    )
    return [options, selected_name, status, scenario_name_value, *updated_values]


@app.callback(
    Output("scenario-select", "options"),
    Output("scenario-select", "value"),
    Output("scenario-status", "children"),
    Output("scenario-name-input", "value"),
    *[Output(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
    Input("scenario-initial-load", "n_intervals"),
    Input("scenario-save-button", "n_clicks"),
    Input("scenario-load-button", "n_clicks"),
    Input("scenario-delete-button", "n_clicks"),
    State("scenario-name-input", "value"),
    State("scenario-select", "value"),
    *[State(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
)
def manage_scenarios(
    _initial_load,
    _save_clicks,
    _load_clicks,
    _delete_clicks,
    scenario_name,
    selected_name,
    *input_values,
):
    """Persist or restore all current dashboard input values."""
    try:
        trigger = ctx.triggered_id
        if trigger == "scenario-initial-load":
            saved = scenario_store.list_scenarios()
            options = [{"label": item["name"], "value": item["name"]} for item in saved]
            return _scenario_action_response(options, no_update, "")

        if trigger == "scenario-save-button":
            normalized_name = scenario_store.save_scenario(
                scenario_name or "",
                dict(zip(scenario_store.SCENARIO_FIELDS, input_values)),
            )
            saved = scenario_store.list_scenarios()
            options = [{"label": item["name"], "value": item["name"]} for item in saved]
            return _scenario_action_response(
                options,
                normalized_name,
                f"«{normalized_name}» gespeichert. Ein gleichnamiges Szenario wird aktualisiert.",
                scenario_name_value=normalized_name,
            )

        if trigger == "scenario-load-button":
            if not selected_name:
                raise ValueError("Bitte wähle zuerst ein gespeichertes Szenario aus.")
            values = scenario_store.load_scenario(selected_name)
            saved = scenario_store.list_scenarios()
            options = [{"label": item["name"], "value": item["name"]} for item in saved]
            return _scenario_action_response(
                options,
                selected_name,
                f"«{selected_name}» geladen.",
                values,
                scenario_name_value=selected_name,
            )

        if trigger == "scenario-delete-button":
            if not selected_name:
                raise ValueError("Bitte wähle zuerst ein gespeichertes Szenario aus.")
            if not scenario_store.delete_scenario(selected_name):
                raise ValueError("Das ausgewählte Szenario wurde nicht gefunden.")
            saved = scenario_store.list_scenarios()
            options = [{"label": item["name"], "value": item["name"]} for item in saved]
            return _scenario_action_response(
                options,
                None,
                f"«{selected_name}» gelöscht.",
            )

        return _scenario_action_response([], no_update, "")
    except (ValueError, sqlite3.Error, OSError) as error:
        try:
            saved = scenario_store.list_scenarios()
            options = [{"label": item["name"], "value": item["name"]} for item in saved]
        except (sqlite3.Error, OSError):
            options = no_update
        return _scenario_action_response(
            options,
            no_update,
            f"Aktion fehlgeschlagen: {error}",
        )


@app.callback(
    *[Output(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
    Output("last-inputs-status", "children"),
    Input("last-inputs-initial-load", "n_intervals"),
    *[Input(component_id, "value") for component_id in SCENARIO_INPUT_IDS],
)
def remember_dashboard_inputs(_initial_load, *input_values):
    """Restore the last input snapshot on launch and persist subsequent edits."""
    no_changes = [no_update] * len(SCENARIO_INPUT_IDS)
    try:
        if ctx.triggered_id == "last-inputs-initial-load":
            values = scenario_store.load_last_inputs()
            if values is None:
                return [*no_changes, ""]
            return [
                *[values[field] for field in scenario_store.SCENARIO_FIELDS],
                "",
            ]

        if ctx.triggered_id in SCENARIO_INPUT_IDS:
            scenario_store.save_last_inputs(
                dict(zip(scenario_store.SCENARIO_FIELDS, input_values))
            )
        return [*no_changes, ""]
    except (ValueError, sqlite3.Error, OSError) as error:
        return [
            *no_changes,
            html.Span(
                f"Letzte Eingaben konnten nicht gespeichert oder geladen werden: {error}",
                className="scenario-status-message scenario-status-error",
            ),
        ]


@app.callback(
    Output("pillar2-custom-fields", "style"),
    Input("pillar2-mode-input", "value"),
)
def update_pillar2_controls(mode):
    return {"display": "grid" if mode == "custom" else "none"}


@app.callback(
    Output("retirement-age-input", "options"),
    Output("retirement-age-input", "value"),
    Input("current-age-input", "value"),
    State("retirement-age-input", "value"),
)
def update_retirement_options(current_age, retirement_age):
    age = int(current_age or 35)
    minimum = max(config.MIN_RETIREMENT_AGE, age)
    options = [
        {"label": f"{value} Jahre", "value": value}
        for value in range(minimum, max(config.MAX_RETIREMENT_AGE, minimum) + 1)
    ]
    selected = retirement_age if retirement_age is not None and retirement_age >= minimum else minimum
    return options, selected


def _normalize_income(amount, period: str, income_type: str, age: int, canton: str) -> Tuple[float, float]:
    """Return the equivalent monthly net and gross income."""
    if amount is None or not math.isfinite(float(amount)) or amount <= 0:
        raise ValueError("Bitte gib ein Einkommen größer als 0 CHF ein.")
    if period not in {"monthly", "yearly"}:
        raise ValueError("Bitte wähle einen monatlichen oder jährlichen Zeitraum.")
    if income_type not in {"net", "gross"}:
        raise ValueError("Bitte wähle Brutto oder Netto.")

    monthly_amount = float(amount) / 12 if period == "yearly" else float(amount)
    if income_type == "net":
        return monthly_amount, monthly_amount
    if canton not in config.CANTON_TAX_RATES:
        raise ValueError("Bitte wähle einen gültigen Kanton.")

    employee_pillar2 = Pillar2Calculator(
        annual_net_income=monthly_amount * 12,
        current_age=age,
    ).calculate().annual_contribution_employee / 12
    deductions = DeductionsCalculator(
        gross_monthly_income=monthly_amount,
        employee_pillar2_contribution=employee_pillar2,
        canton=canton,
    ).calculate()
    return max(0.0, deductions.net_monthly_income), monthly_amount


@app.callback(
    Output("income-label", "children"),
    Output("income-suffix", "children"),
    Output("income-hint", "children"),
    Output("canton-control", "style"),
    Input("income-period-input", "value"),
    Input("income-type-input", "value"),
)
def update_income_controls(period, income_type):
    period_label = "jährliches" if period == "yearly" else "monatliches"
    income_label = "Bruttoeinkommen" if income_type == "gross" else "Nettoeinkommen"
    suffix = "CHF/Jahr" if period == "yearly" else "CHF/Monat"
    hint = (
        "Betrag vor Abzügen; das Netto wird anhand deines Kantons geschätzt."
        if income_type == "gross"
        else "Frei verfügbares Einkommen nach Abzügen."
    )
    return (
        f"Dein {period_label} {income_label}",
        suffix,
        hint,
        {"display": "block" if income_type == "gross" else "none"},
    )


@app.callback(
    Output("income-preview", "children"),
    Input("monthly-income-input", "value"),
    Input("income-period-input", "value"),
    Input("income-type-input", "value"),
    Input("current-age-input", "value"),
    Input("canton-input", "value"),
)
def update_income_preview(amount, period, income_type, age, canton):
    try:
        monthly_net, monthly_gross = _normalize_income(
            amount,
            period,
            income_type,
            int(age or 35),
            canton or "ZH",
        )
    except ValueError as error:
        return str(error)

    if income_type == "gross":
        return (
            f"Brutto {_money(monthly_gross)}/Monat · geschätztes Netto "
            f"{_money(monthly_net)}/Monat ({canton})"
        )
    return f"Für die Vorsorgeplanung verwendet: {_money(monthly_net)} netto pro Monat"


@app.callback(
    Output("results-section", "children"),
    Output("calculation-notice", "children"),
    Input("monthly-income-input", "value"),
    Input("income-period-input", "value"),
    Input("income-type-input", "value"),
    Input("canton-input", "value"),
    Input("current-age-input", "value"),
    Input("retirement-age-input", "value"),
    Input("savings-mode-input", "value"),
    Input("pillar3a-rate-input", "value"),
    Input("pillar3a-amount-input", "value"),
    Input("pillar3b-amount-input", "value"),
    Input("pillar3a-initial-input", "value"),
    Input("pillar3b-initial-input", "value"),
    Input("pillar2-initial-input", "value"),
    Input("pillar2-mode-input", "value"),
    Input("pillar2-employee-input", "value"),
    Input("pillar2-employer-input", "value"),
    Input("pillar2-return-input", "value"),
    Input("return-input", "value"),
    Input("display-basis-input", "value"),
    Input("ahv-average-income-input", "value"),
    Input("ahv-contribution-years-input", "value"),
)
def update_results(
    income,
    income_period,
    income_type,
    canton,
    current_age,
    retirement_age,
    savings_mode,
    savings_rate,
    pillar3a_amount,
    pillar3b_amount,
    initial_3a,
    initial_3b,
    initial_2,
    pillar2_mode,
    pillar2_employee,
    pillar2_employer,
    pillar2_return,
    assumed_return,
    display_basis,
    ahv_average_income,
    ahv_contribution_years,
):
    def show_error(message: str):
        return (
            html.Div(
                [html.Strong("Eingaben prüfen"), html.P(message)],
                className="validation-message",
            ),
            "",
        )

    if current_age is None or retirement_age is None:
        return show_error("Bitte wähle dein aktuelles Alter und dein Pensionierungsalter.")
    if current_age < 18 or retirement_age < current_age:
        return show_error("Das Pensionierungsalter muss mindestens deinem aktuellen Alter entsprechen.")
    try:
        monthly_net_income, _ = _normalize_income(
            income,
            income_period,
            income_type,
            int(current_age),
            canton,
        )
    except ValueError as error:
        return show_error(str(error))
    if monthly_net_income <= 0:
        return show_error(
            "Das geschätzte Nettoeinkommen beträgt 0 CHF. Bitte prüfe den Bruttobetrag."
        )
    if savings_mode not in {"rate", "amount"}:
        return show_error("Bitte wähle eine gültige Beitragsart für die 3a.")
    if savings_mode == "rate" and (
        savings_rate is None or not math.isfinite(float(savings_rate)) or not 0 <= savings_rate <= 100
    ):
        return show_error("Die Sparquote muss zwischen 0 und 100 Prozent liegen.")
    if savings_mode == "amount" and (
        pillar3a_amount is None
        or not math.isfinite(float(pillar3a_amount))
        or pillar3a_amount < 0
    ):
        return show_error("Der monatliche 3a-Beitrag muss mindestens 0 CHF betragen.")
    if pillar3b_amount is None or not math.isfinite(float(pillar3b_amount)) or pillar3b_amount < 0:
        return show_error("Der monatliche 3b-Beitrag muss mindestens 0 CHF betragen.")
    initial_3a = 0 if initial_3a is None else initial_3a
    initial_3b = 0 if initial_3b is None else initial_3b
    if not math.isfinite(float(initial_3a)) or initial_3a < 0:
        return show_error("Das aktuelle 3a-Guthaben muss mindestens 0 CHF betragen.")
    if not math.isfinite(float(initial_3b)) or initial_3b < 0:
        return show_error("Das aktuelle 3b-Guthaben muss mindestens 0 CHF betragen.")
    initial_2 = 0 if initial_2 is None else initial_2
    if not math.isfinite(float(initial_2)) or initial_2 < 0:
        return show_error("Das aktuelle BVG-Guthaben muss mindestens 0 CHF betragen.")
    if pillar2_mode not in {"minimum", "custom"}:
        return show_error("Bitte wähle eine Berechnungsgrundlage für die 2. Säule.")
    if pillar2_mode == "custom":
        if pillar2_employee is None or not math.isfinite(float(pillar2_employee)) or pillar2_employee < 0:
            return show_error("Der monatliche Arbeitnehmerbeitrag muss mindestens 0 CHF betragen.")
        if pillar2_employer is None or not math.isfinite(float(pillar2_employer)) or pillar2_employer < 0:
            return show_error("Der monatliche Arbeitgeberbeitrag muss mindestens 0 CHF betragen.")
        if pillar2_return is None or not math.isfinite(float(pillar2_return)) or not 0 <= pillar2_return <= 20:
            return show_error("Die Verzinsung der 2. Säule muss zwischen 0 und 20 Prozent liegen.")
    if assumed_return is None or assumed_return not in {0.02, 0.04, 0.06}:
        return show_error("Bitte wähle eine der angebotenen Renditeannahmen.")
    if display_basis not in {"nominal", "real"}:
        return show_error("Bitte wähle nominale oder reale Werte für die Prognose.")
    if ahv_average_income is not None and (
        not math.isfinite(float(ahv_average_income)) or ahv_average_income < 0
    ):
        return show_error("Das massgebende AHV-Jahreseinkommen muss mindestens 0 CHF betragen.")
    if (
        ahv_contribution_years is None
        or not math.isfinite(float(ahv_contribution_years))
        or not float(ahv_contribution_years).is_integer()
        or not 0 <= ahv_contribution_years <= ahv.FULL_CONTRIBUTION_YEARS
    ):
        return show_error(
            f"Die AHV-Beitragsjahre müssen eine ganze Zahl zwischen 0 und "
            f"{ahv.FULL_CONTRIBUTION_YEARS} sein."
        )

    calculator = FinanceCalculator(
        monthly_net_income=monthly_net_income,
        current_age=int(current_age),
        retirement_age=int(retirement_age),
        assumed_annual_return=float(assumed_return),
    )
    selected_rate = float(savings_rate) / 100 if savings_mode == "rate" else 0
    analysis = calculator.complete_analysis(pillar3a_savings_rate=selected_rate)
    if pillar2_mode == "custom":
        years = analysis.years_to_retirement
        employee_annual = float(pillar2_employee) * 12
        employer_annual = float(pillar2_employer) * 12
        pillar2_return_decimal = float(pillar2_return) / 100
        pillar2_capital = _projection_values(
            employee_annual + employer_annual,
            years,
            pillar2_return_decimal,
            float(initial_2),
        )[-1]
        analysis.pillar2 = Pillar2Result(
            annual_contribution_employee=employee_annual,
            annual_contribution_employer=employer_annual,
            annual_contribution_total=employee_annual + employer_annual,
            coordination_deduction=0,
            insurable_salary=0,
            years_until_retirement=years,
            estimated_capital_at_retirement=pillar2_capital,
        )
    else:
        pillar2_return_decimal = config.ASSUMED_ANNUAL_RETURN
        analysis.pillar2.estimated_capital_at_retirement = _projection_values(
            analysis.pillar2.annual_contribution_total,
            analysis.years_to_retirement,
            pillar2_return_decimal,
            float(initial_2),
        )[-1]
    if savings_mode == "rate":
        pillar3a = calculator.calculate_pillar3a(savings_rate=selected_rate)
        requested_3a_monthly = monthly_net_income * selected_rate
    else:
        pillar3a = calculator.calculate_pillar3a(monthly_amount=float(pillar3a_amount))
        requested_3a_monthly = float(pillar3a_amount)
    pillar3b = calculator.calculate_pillar3b(monthly_amount=float(pillar3b_amount))
    content, notice = _results_view(
        income=monthly_net_income,
        current_age=int(current_age),
        retirement_age=int(retirement_age),
        assumed_return=float(assumed_return),
        analysis=analysis,
        pillar3a=pillar3a,
        pillar3b=pillar3b,
        pillar2_mode=pillar2_mode,
        pillar2_return=pillar2_return_decimal,
        initial_2=float(initial_2),
        initial_3a=float(initial_3a),
        initial_3b=float(initial_3b),
        display_basis=display_basis,
        ahv_average_income=(
            None if ahv_average_income is None else float(ahv_average_income)
        ),
        ahv_contribution_years=int(ahv_contribution_years),
    )
    if requested_3a_monthly > pillar3a.monthly_savings:
        notice = (
            f"Der eingegebene 3a-Beitrag wurde gemäss dem Modell-Limit auf "
            f"{_money(pillar3a.monthly_savings)} pro Monat begrenzt."
        )
    return content, notice


def run_dashboard(debug: bool = False, port: int = 8050):
    """Run the dashboard on localhost."""
    app.run(debug=debug, port=port, host="127.0.0.1")


if __name__ == "__main__":
    run_dashboard(debug=True)
