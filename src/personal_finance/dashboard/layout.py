"""Static page layout of the dashboard (Dash Mantine Components).

Structure: a header with the scenarios menu, the inputs on the left (collapsible groups;
behind a burger menu on phones) and the results on the right in tabs.
"""

import dash_mantine_components as dmc
from dash import dcc, html

from personal_finance import config
from personal_finance.dashboard.components import (
    money,
    number_input,
    segmented,
    select,
)
from personal_finance.dashboard.theme import MANTINE_THEME
from personal_finance.storage import browser_store

# Also the localStorage keys in the browser. Every key uses the "pf-" prefix so that
# "Alle Daten in diesem Browser löschen" can remove all of them at once.
STORAGE_KEY_PREFIX = "pf-"
SCENARIOS_STORE_ID = "pf-scenarios"
LAST_INPUTS_STORE_ID = "pf-last-inputs"
NOTICE_STORE_ID = "pf-notice"

NAVBAR_WIDTH = 350
MOBILE_BREAKPOINT = 768  # px; below this the inputs move behind the burger menu

CANTONS = [
    ("ZH", "Zürich"), ("BE", "Bern"), ("LU", "Luzern"), ("UR", "Uri"), ("SZ", "Schwyz"),
    ("OW", "Obwalden"), ("NW", "Nidwalden"), ("GL", "Glarus"), ("ZG", "Zug"),
    ("FR", "Freiburg"), ("SO", "Solothurn"), ("BS", "Basel-Stadt"),
    ("BL", "Basel-Landschaft"), ("SH", "Schaffhausen"), ("AR", "Appenzell Ausserrhoden"),
    ("AI", "Appenzell Innerrhoden"), ("SG", "St. Gallen"), ("GR", "Graubünden"),
    ("AG", "Aargau"), ("TG", "Thurgau"), ("TI", "Tessin"), ("VD", "Waadt"),
    ("VS", "Wallis"), ("NE", "Neuenburg"), ("GE", "Genf"), ("JU", "Jura"),
]

RETURN_OPTIONS = [
    {"label": "2 %", "value": "0.02"},
    {"label": "4 %", "value": "0.04"},
    {"label": "6 %", "value": "0.06"},
]


def _group(value: str, title: str, icon: str, children):
    return dmc.AccordionItem(
        [
            dmc.AccordionControl(
                title,
                icon=dmc.ThemeIcon(icon, variant="light", size="md", radius="md"),
            ),
            dmc.AccordionPanel(dmc.Stack(children, gap="sm")),
        ],
        value=value,
    )


# --- header ----------------------------------------------------------------------------

_scenario_manager = dmc.Stack(
    [
        dmc.Text("Szenarien", fw=700),
        dmc.Text(
            "Speichere deine Eingaben und lade sie später zum Vergleichen wieder. Gleiche Namen "
            "überschreiben das vorhandene Szenario. Deine letzten Eingaben werden automatisch "
            "gemerkt. Alles bleibt nur in diesem Browser auf deinem Gerät, der Server speichert "
            "nichts. Wer dieses Gerät und Browserprofil nutzt, kann die Daten sehen.",
            size="xs",
            c="dimmed",
        ),
        dmc.Group(
            [
                dmc.TextInput(
                    id="scenario-name-input",
                    placeholder="Name, z. B. Teilzeit ab 50",
                    inputProps={"maxLength": browser_store.MAX_SCENARIO_NAME_LENGTH},
                    flex=1,
                ),
                dmc.Button("Speichern", id="scenario-save-button", n_clicks=0),
            ],
            gap="xs",
            wrap="nowrap",
        ),
        dmc.Select(
            id="scenario-select",
            data=[],
            value=None,
            placeholder="Gespeichertes Szenario auswählen",
            clearable=True,
            searchable=True,
            nothingFoundMessage="Keine Szenarien",
            comboboxProps={"withinPortal": False},
        ),
        dmc.Group(
            [
                dmc.Button("Laden", id="scenario-load-button", n_clicks=0, variant="light"),
                dmc.Button(
                    "Löschen",
                    id="scenario-delete-button",
                    n_clicks=0,
                    variant="subtle",
                    color="red",
                ),
            ],
            gap="xs",
            grow=True,
        ),
        html.Div(id="scenario-status", className="scenario-status"),
        html.Div(id="last-inputs-status", className="scenario-status"),
        dmc.Divider(),
        dmc.Button(
            "Alle Daten in diesem Browser löschen",
            id="clear-browser-data-button",
            n_clicks=0,
            variant="subtle",
            color="red",
            size="xs",
        ),
    ],
    gap="sm",
)

_header = dmc.AppShellHeader(
    dmc.Group(
        [
            dmc.Group(
                [
                    dmc.Burger(id="navbar-burger", opened=False, hiddenFrom="sm", size="sm"),
                    html.Div("F", className="brand-mark"),
                    html.Div(
                        [
                            html.Div("FINANZPLAN", className="brand-name"),
                            html.Div("Persönliche Vorsorgeplanung", className="brand-caption"),
                        ]
                    ),
                ],
                gap="sm",
                wrap="nowrap",
            ),
            dmc.Popover(
                [
                    dmc.PopoverTarget(
                        dmc.Button("Szenarien", id="scenario-menu-button", variant="light")
                    ),
                    dmc.PopoverDropdown(_scenario_manager),
                ],
                width=360,
                position="bottom-end",
                withArrow=True,
                shadow="md",
                keepMounted=True,
            ),
        ],
        justify="space-between",
        h="100%",
        px="md",
        wrap="nowrap",
    ),
    className="app-header",
)

# --- inputs (left) -----------------------------------------------------------------------

_income_group = _group(
    "income",
    "Einkommen & Alter",
    "CHF",
    [
        number_input(
            "monthly-income-input",
            "Dein monatliches Nettoeinkommen",
            5000,
            0,
            100,
            "CHF/Monat",
            description="Frei verfügbares Einkommen nach Abzügen.",
        ),
        segmented(
            "income-period-input",
            "Zeitraum",
            [{"label": "Monatlich", "value": "monthly"}, {"label": "Jährlich", "value": "yearly"}],
            "monthly",
        ),
        segmented(
            "income-type-input",
            "Einkommensart",
            [{"label": "Netto", "value": "net"}, {"label": "Brutto", "value": "gross"}],
            "net",
        ),
        html.Div(
            select(
                "canton-input",
                "Kanton für Nettoschätzung",
                [{"label": f"{name} ({code})", "value": code} for code, name in CANTONS],
                "ZH",
                "Nur für Brutto relevant; wird zur groben Steuer-Nettoschätzung verwendet.",
                searchable=True,
            ),
            id="canton-control",
            style={"display": "none"},
        ),
        dmc.Text(id="income-preview", className="income-preview"),
        dmc.SimpleGrid(
            [
                number_input("current-age-input", "Aktuelles Alter", 35, 18, 1, "Jahre", 80, decimals=0),
                number_input(
                    "retirement-age-input",
                    "Pensionierung mit",
                    65,
                    config.MIN_RETIREMENT_AGE,
                    1,
                    "Jahren",
                    config.MAX_RETIREMENT_AGE + 5,
                    decimals=0,
                ),
            ],
            cols=2,
            spacing="sm",
        ),
    ],
)

_balances_group = _group(
    "balances",
    "Bisherige Guthaben",
    "Σ",
    [
        dmc.Text("Deine bereits vorhandenen Guthaben in der Vorsorge.", size="xs", c="dimmed"),
        number_input(
            "pillar2-initial-input",
            "2. Säule (Pensionskasse)",
            0,
            0,
            1000,
            "CHF",
            description="Stand gemäss aktuellem PK-Ausweis",
        ),
        number_input(
            "pillar3a-initial-input",
            "Säule 3a",
            0,
            0,
            1000,
            "CHF",
            description="Optional; leer entspricht 0 CHF",
        ),
        number_input(
            "pillar3b-initial-input",
            "Freies Vermögen 3b",
            0,
            0,
            1000,
            "CHF",
            description="Optional; leer entspricht 0 CHF",
        ),
    ],
)

_ahv_group = _group(
    "ahv",
    "AHV-Rente",
    "AHV",
    [
        dmc.Text(
            "Die AHV ist eine Rente und kein persönliches Altersguthaben. Die unverbindliche "
            "Schätzung verwendet dein durchschnittliches Jahreseinkommen und die Beitragsjahre "
            "bei Pensionierung.",
            size="xs",
            c="dimmed",
        ),
        number_input(
            "ahv-average-income-input",
            "Massgebendes durchschnittliches Jahreseinkommen",
            100000,
            0,
            1000,
            "CHF/Jahr",
            description="Für die Schätzung; wenn möglich aus IK/AHV-Auszug",
        ),
        number_input(
            "ahv-contribution-years-input",
            "Beitragsjahre bei Pensionierung",
            44,
            0,
            1,
            "von 44",
            44,
            description="Anpassen, falls du Beitragslücken erwartest",
            decimals=0,
        ),
    ],
)

_pillar2_group = _group(
    "pillar2",
    "2. Säule (Pensionskasse)",
    "Ⅱ",
    [
        segmented(
            "pillar2-mode-input",
            "Berechnungsgrundlage",
            [
                {"label": "BVG-Schätzung", "value": "minimum"},
                {"label": "Eigene PK-Werte", "value": "custom"},
            ],
            "minimum",
            "Die BVG-Schätzung ist vereinfacht; dein PK-Ausweis ist genauer.",
        ),
        html.Div(
            [
                number_input("pillar2-employee-input", "Dein Beitrag (Arbeitnehmer)", None, 0, 10, "CHF/Mt."),
                number_input("pillar2-employer-input", "Beitrag Arbeitgeber", None, 0, 10, "CHF/Mt."),
                number_input("pillar2-return-input", "Verzinsung gemäss PK-Ausweis", None, 0, 0.05, "%", 20),
            ],
            id="pillar2-custom-fields",
            className="field-stack",
            style={"display": "none"},
        ),
    ],
)

_pillar3a_group = _group(
    "pillar3a",
    "Säule 3a",
    "3a",
    [
        segmented(
            "savings-mode-input",
            "Beitragsart",
            [
                {"label": "Sparquote", "value": "rate"},
                {"label": "Fester Betrag", "value": "amount"},
            ],
            "rate",
        ),
        html.Div(
            number_input(
                "pillar3a-rate-input",
                "Sparquote vom Nettoeinkommen",
                10,
                0,
                0.5,
                "%",
                100,
                description="Wird auf das modellierte 3a-Maximum begrenzt",
            ),
            id="rate-control",
        ),
        html.Div(
            number_input(
                "pillar3a-amount-input",
                "Monatlicher 3a-Betrag",
                350,
                0,
                0.01,
                "CHF/Mt.",
                config.PILLAR3A_MONTHLY_MAX,
                description=(
                    f"Modell-Limit: {money(config.PILLAR3A_ANNUAL_MAX)}/Jahr "
                    f"(ca. {money(config.PILLAR3A_MONTHLY_MAX, 2)}/Monat)"
                ),
            ),
            id="amount-control",
            style={"display": "none"},
        ),
    ],
)

_pillar3b_group = _group(
    "pillar3b",
    "Freies Sparen 3b & Rendite",
    "3b",
    [
        number_input(
            "pillar3b-amount-input",
            "Monatlicher 3b-Beitrag",
            500,
            0,
            100,
            "CHF/Mt.",
            description="Flexibles Sparen ohne 3a-Modell-Limit",
        ),
        segmented(
            "return-input",
            "Angenommene Rendite",
            RETURN_OPTIONS,
            "0.04",
            "Vorsichtig · ausgewogen · chancenorientiert; gilt für 3a und 3b",
        ),
    ],
)

_navbar = dmc.AppShellNavbar(
    [
        dmc.Text("DEINE AUSGANGSLAGE", className="eyebrow"),
        dmc.Text(
            "Passe die Werte an – die Prognose aktualisiert sich sofort.",
            size="xs",
            c="dimmed",
            mb="sm",
        ),
        dmc.Accordion(
            [
                _income_group,
                _balances_group,
                _ahv_group,
                _pillar2_group,
                _pillar3a_group,
                _pillar3b_group,
            ],
            multiple=True,
            value=["income", "balances"],
            variant="separated",
            chevronPosition="right",
            className="input-groups",
        ),
    ],
    p="md",
    className="input-navbar",
)

# --- results (right) -----------------------------------------------------------------------

_welcome_notice = html.Div(
    dmc.Alert(
        [
            dmc.List(
                [
                    dmc.ListItem(
                        [
                            html.Strong("Keine Beratung. "),
                            "Der Finanzplan zeigt vereinfachte Schätzungen ohne Gewähr. Er "
                            "ersetzt keine Finanz-, Steuer- oder Vorsorgeberatung.",
                        ]
                    ),
                    dmc.ListItem(
                        [
                            html.Strong("Deine Daten bleiben bei dir. "),
                            "Eingaben und Szenarien werden nur in diesem Browser auf deinem "
                            "Gerät gespeichert. Der Server speichert nichts, und andere Nutzer "
                            "sehen deine Daten nicht.",
                        ]
                    ),
                    dmc.ListItem(
                        [
                            html.Strong("Gerät und Browser zählen. "),
                            "Auf einem anderen Gerät oder nach dem Löschen der Browserdaten sind "
                            "deine Szenarien nicht vorhanden. Auf fremden Geräten ein privates "
                            "Fenster nutzen oder unter „Szenarien“ „Alle Daten in diesem Browser "
                            "löschen“.",
                        ]
                    ),
                ],
                size="sm",
                spacing=6,
            ),
            dmc.Button("Verstanden", id="welcome-dismiss", n_clicks=0, mt="md", size="sm"),
        ],
        title="Willkommen! Drei Dinge vorab",
        color="forest",
        variant="light",
        radius="lg",
    ),
    id="welcome-notice",
    className="welcome-notice",
    hidden=True,
    **{"aria-label": "Hinweise zur Nutzung"},
)

_results = html.Div(
    [
        dmc.Group(
            [
                html.Div(
                    [
                        dmc.Text("DEIN VORSORGE-AUSBLICK", className="eyebrow"),
                        dmc.Title("Heute planen. Morgen sicherer sein.", order=2, className="page-title"),
                    ]
                ),
                dmc.SegmentedControl(
                    id="display-basis-input",
                    data=[
                        {"label": "Nominal", "value": "nominal"},
                        {"label": "Real · heutige Kaufkraft", "value": "real"},
                    ],
                    value="nominal",
                    size="xs",
                ),
            ],
            justify="space-between",
            align="flex-end",
            gap="sm",
        ),
        html.Div(id="calculation-notice", className="calculation-notice"),
        dmc.Tabs(
            [
                dmc.TabsList(
                    [
                        dmc.TabsTab("Übersicht", value="overview"),
                        dmc.TabsTab("Vorsorge", value="pension"),
                        dmc.TabsTab("Annahmen", value="assumptions"),
                    ]
                ),
                dmc.TabsPanel(html.Div(id="overview-section"), value="overview", pt="md"),
                dmc.TabsPanel(html.Div(id="pension-section"), value="pension", pt="md"),
                dmc.TabsPanel(html.Div(id="assumptions-section"), value="assumptions", pt="md"),
            ],
            id="result-tabs",
            value="overview",
            # Inactive tabs stay in the page (hidden) so they always show the latest results.
            keepMounted=True,
            keepMountedMode="display-none",
            className="result-tabs",
        ),
        html.Footer(
            [
                html.Span("Finanzplan · Schweizer Vorsorge"),
                html.Span(
                    "Keine Finanzberatung · Deine Daten bleiben in deinem Browser",
                    className="footer-note",
                ),
                html.Button(
                    "Hinweise anzeigen",
                    id="welcome-show",
                    n_clicks=0,
                    className="footer-link",
                ),
            ],
            className="page-footer",
        ),
    ],
    className="results-column",
)

layout = dmc.MantineProvider(
    [
        # Per-user data lives only in this browser's localStorage; the server keeps nothing.
        dcc.Store(id=SCENARIOS_STORE_ID, storage_type="local"),
        dcc.Store(id=LAST_INPUTS_STORE_ID, storage_type="local"),
        dcc.Store(id=NOTICE_STORE_ID, storage_type="local"),
        dcc.Interval(id="scenario-initial-load", interval=1, max_intervals=1),
        dcc.Interval(id="last-inputs-initial-load", interval=1, max_intervals=1),
        dcc.ConfirmDialog(
            id="clear-browser-data-confirm",
            message=(
                "Alle gespeicherten Szenarien und die gemerkten Eingaben in diesem Browser "
                "werden gelöscht. Das kann nicht rückgängig gemacht werden. Fortfahren?"
            ),
        ),
        html.Div(id="clear-browser-data-done", hidden=True),
        dmc.AppShell(
            [
                _header,
                _navbar,
                dmc.AppShellMain([_welcome_notice, _results], className="main-area"),
            ],
            id="app-shell",
            header={"height": 64},
            navbar={
                "width": NAVBAR_WIDTH,
                "breakpoint": MOBILE_BREAKPOINT,
                "collapsed": {"mobile": True},
            },
            padding="md",
        ),
    ],
    theme=MANTINE_THEME,
    forceColorScheme="light",
)
