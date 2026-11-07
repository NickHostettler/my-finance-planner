"""Static page layout of the dashboard."""


from dash import dcc, html

from personal_finance import config
from personal_finance.dashboard.components import (
    dropdown,
    field,
    number_input,
)
from personal_finance.storage import scenario_store


layout = html.Div(
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
                                                field(
                                                    "Einkommen (Netto)",
                                                    number_input(
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
                                                field(
                                                    "Zeitraum",
                                                    dropdown(
                                                        "income-period-input",
                                                        [
                                                            {"label": "Monatlich", "value": "monthly"},
                                                            {"label": "Jährlich", "value": "yearly"},
                                                        ],
                                                        "monthly",
                                                    ),
                                                ),
                                                field(
                                                    "Einkommensart",
                                                    dropdown(
                                                        "income-type-input",
                                                        [
                                                            {"label": "Netto", "value": "net"},
                                                            {"label": "Brutto", "value": "gross"},
                                                        ],
                                                        "net",
                                                    ),
                                                ),
                                                field(
                                                    "Dein aktuelles Alter",
                                                    dropdown(
                                                        "current-age-input",
                                                        [
                                                            {"label": f"{age} Jahre", "value": age}
                                                            for age in range(18, 81)
                                                        ],
                                                        35,
                                                    ),
                                                    "In vollen Jahren",
                                                ),
                                                field(
                                                    "Geplantes Pensionierungsalter",
                                                    dropdown(
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
                                            field(
                                                "Kanton für Nettoschätzung",
                                                dropdown(
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
                                        field(
                                            "Darstellung der Prognose",
                                            dropdown(
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
                                                        field(
                                                            "Aktuelles 3a-Guthaben",
                                                            number_input(
                                                                "pillar3a-initial-input",
                                                                0,
                                                                0,
                                                                1000,
                                                                "CHF",
                                                            ),
                                                            "Optional; leer entspricht 0 CHF",
                                                        ),
                                                        field(
                                                            "Aktuelles BVG-/2.-Säule-Guthaben",
                                                            number_input(
                                                                "pillar2-initial-input",
                                                                0,
                                                                0,
                                                                1000,
                                                                "CHF",
                                                            ),
                                                            "Stand gemäss aktuellem PK-Ausweis",
                                                        ),
                                                        field(
                                                            "Aktuelles 3b-Guthaben",
                                                            number_input(
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
                                                        field(
                                                            "Massgebendes durchschnittliches Jahreseinkommen",
                                                            number_input(
                                                                "ahv-average-income-input",
                                                                    100000,
                                                                0,
                                                                1000,
                                                                "CHF/Jahr",
                                                            ),
                                                            "Für die Schätzung; wenn möglich aus IK/AHV-Auszug",
                                                        ),
                                                        field(
                                                            "Beitragsjahre bei Pensionierung",
                                                            number_input(
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
                                                        field(
                                                            "Berechnungsgrundlage 2. Säule",
                                                            dropdown(
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
                                                                field(
                                                                    "Dein monatlicher Arbeitnehmerbeitrag",
                                                                    number_input(
                                                                        "pillar2-employee-input",
                                                                            None,
                                                                        0,
                                                                        10,
                                                                        "CHF",
                                                                    ),
                                                                ),
                                                                field(
                                                                    "Monatlicher Arbeitgeberbeitrag",
                                                                    number_input(
                                                                        "pillar2-employer-input",
                                                                            None,
                                                                        0,
                                                                        10,
                                                                        "CHF",
                                                                    ),
                                                                ),
                                                                field(
                                                                    "Verzinsung gemäss PK-Ausweis",
                                                                    number_input(
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
                                                        field(
                                                            "Beitragsart",
                                                            dropdown(
                                                                "savings-mode-input",
                                                                [
                                                                    {"label": "Sparquote vom Einkommen", "value": "rate"},
                                                                    {"label": "Fester Monatsbetrag", "value": "amount"},
                                                                ],
                                                                "rate",
                                                            ),
                                                        ),
                                                        html.Div(
                                                            field(
                                                                "Sparquote",
                                                                number_input(
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
                                                            field(
                                                                "Monatlicher 3a-Betrag",
                                                                number_input(
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
                                                        field(
                                                            "Monatlicher 3b-Beitrag",
                                                            number_input(
                                                                "pillar3b-amount-input",
                                                                500,
                                                                0,
                                                                100,
                                                                "CHF",
                                                            ),
                                                            "Flexibles Sparen ohne 3a-Modell-Limit",
                                                        ),
                                                        field(
                                                            "Angenommene Rendite",
                                                            dropdown(
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
