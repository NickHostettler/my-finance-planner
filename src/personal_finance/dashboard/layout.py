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
# Only in the open page (not in localStorage): the purchase age that a loaded scenario or the
# remembered inputs set, so that loading does not fill in the highest amounts (#40).
HOME_PREFILL_SKIP_STORE_ID = "home-prefill-skip"

NAVBAR_WIDTH = 350
MOBILE_BREAKPOINT = 768  # px; below this the inputs move behind the burger menu

CANTONS = [
    ("ZH", "Zürich"),
    ("BE", "Bern"),
    ("LU", "Luzern"),
    ("UR", "Uri"),
    ("SZ", "Schwyz"),
    ("OW", "Obwalden"),
    ("NW", "Nidwalden"),
    ("GL", "Glarus"),
    ("ZG", "Zug"),
    ("FR", "Freiburg"),
    ("SO", "Solothurn"),
    ("BS", "Basel-Stadt"),
    ("BL", "Basel-Landschaft"),
    ("SH", "Schaffhausen"),
    ("AR", "Appenzell Ausserrhoden"),
    ("AI", "Appenzell Innerrhoden"),
    ("SG", "St. Gallen"),
    ("GR", "Graubünden"),
    ("AG", "Aargau"),
    ("TG", "Thurgau"),
    ("TI", "Tessin"),
    ("VD", "Waadt"),
    ("VS", "Wallis"),
    ("NE", "Neuenburg"),
    ("GE", "Genf"),
    ("JU", "Jura"),
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
                # Not keepMounted: hidden content would be rendered with React's <Activity>,
                # which defers updates, so Dash never finished "loading" the fields in it (CI).
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
                number_input(
                    "current-age-input", "Aktuelles Alter", 35, 18, 1, "Jahre", 80, decimals=0
                ),
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
        number_input(
            "salary-growth-input",
            "Jährliche Lohnzunahme",
            browser_store.FIELD_DEFAULTS["salary_growth"],
            0,
            0.1,
            "%",
            config.SALARY_GROWTH_MAX * 100,
            description=(
                "Nominal pro Jahr. Mit dem Lohn steigen die Beiträge an die 2. Säule; "
                "3a- und 3b-Beträge bleiben fest."
            ),
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
                number_input(
                    "pillar2-employee-input", "Dein Beitrag (Arbeitnehmer)", None, 0, 10, "CHF/Mt."
                ),
                number_input(
                    "pillar2-employer-input", "Beitrag Arbeitgeber", None, 0, 10, "CHF/Mt."
                ),
                number_input(
                    "pillar2-return-input", "Verzinsung gemäss PK-Ausweis", None, 0, 0.05, "%", 20
                ),
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
        dmc.Button(
            "Maximalbetrag einsetzen",
            id="pillar3a-max-button",
            n_clicks=0,
            variant="light",
            size="xs",
            fullWidth=True,
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

_home_defaults = browser_store.FIELD_DEFAULTS

# Hints below the purchase money fields; with a planned purchase a callback adds the highest
# amount at the purchase age (#40).
HOME_AMOUNT_HINTS = {
    "home-savings-input": "Inkl. Geld für die Kaufnebenkosten",
    "home-pillar3a-input": "Zählt als harte Eigenmittel",
    "home-pillar2-input": "Zählt nicht als harte Eigenmittel",
}

_home_group = _group(
    "home",
    "Wohneigentum",
    "⌂",
    [
        segmented(
            "home-plan-input",
            "Eigenheim",
            [
                {"label": "Kein Kauf geplant", "value": "off"},
                {"label": "Kauf planen", "value": "on"},
            ],
            _home_defaults["home_plan"],
            "Selbst bewohntes Eigentum. Ohne Kauf bleibt die Prognose unverändert.",
        ),
        html.Div(
            [
                number_input(
                    "home-price-input",
                    "Kaufpreis",
                    _home_defaults["home_price"],
                    0,
                    10000,
                    "CHF",
                ),
                number_input(
                    "home-purchase-age-input",
                    "Kauf mit Alter",
                    None,
                    18,
                    1,
                    "Jahren",
                    config.MAX_RETIREMENT_AGE,
                    description="Leer = heute (dein aktuelles Alter)",
                    decimals=0,
                ),
                dmc.Text("Eigenkapital für den Kauf", fw=600, size="sm", mt="xs"),
                dmc.Text(
                    "Wird mit den Höchstbeträgen zum Kaufalter ausgefüllt, sobald du den Kauf "
                    "planst oder das Kaufalter änderst. Du kannst weniger einsetzen.",
                    size="xs",
                    c="dimmed",
                ),
                number_input(
                    "home-savings-input",
                    "Erspartes und Wertschriften",
                    _home_defaults["home_savings"],
                    0,
                    1000,
                    "CHF",
                    description=HOME_AMOUNT_HINTS["home-savings-input"],
                ),
                number_input(
                    "home-pillar3a-input",
                    "Aus der Säule 3a",
                    _home_defaults["home_pillar3a"],
                    0,
                    1000,
                    "CHF",
                    description=HOME_AMOUNT_HINTS["home-pillar3a-input"],
                ),
                number_input(
                    "home-pillar2-input",
                    "Aus der Pensionskasse (Vorbezug)",
                    _home_defaults["home_pillar2"],
                    0,
                    1000,
                    "CHF",
                    description=HOME_AMOUNT_HINTS["home-pillar2-input"],
                ),
                dmc.Button(
                    "Höchstbeträge zum Kaufalter einsetzen",
                    id="home-max-button",
                    n_clicks=0,
                    variant="light",
                    size="xs",
                    fullWidth=True,
                ),
                dmc.Text("Tragbarkeit", fw=600, size="sm", mt="xs"),
                number_input(
                    "home-gross-income-input",
                    "Bruttoeinkommen des Haushalts",
                    None,
                    0,
                    1000,
                    "CHF/Jahr",
                    description="Leer = aus deinen Einkommensangaben",
                ),
                number_input(
                    "home-imputed-rate-input",
                    "Kalkulatorischer Zins",
                    _home_defaults["home_imputed_rate"],
                    0,
                    0.25,
                    "%",
                    15,
                    description="So rechnen Banken die Tragbarkeit, nicht dein echter Zins",
                ),
                dmc.Text("Hypothek in der Prognose", fw=600, size="sm", mt="xs"),
                number_input(
                    "home-mortgage-rate-input",
                    "Effektiver Hypothekarzins",
                    _home_defaults["home_mortgage_rate"],
                    0,
                    0.05,
                    "%",
                    15,
                    description="Dein erwarteter Zins für die Zinskosten",
                ),
                segmented(
                    "home-amortisation-input",
                    "Amortisation der 2. Hypothek",
                    [
                        {"label": "Direkt", "value": "direct"},
                        {"label": "Indirekt über 3a", "value": "indirect"},
                    ],
                    _home_defaults["home_amortisation"],
                    "Direkt sinkt die Schuld jedes Jahr; indirekt sparst du in ein verpfändetes "
                    "3a-Konto.",
                ),
            ],
            id="home-fields",
            className="field-stack",
            style={"display": "none"},
        ),
    ],
)


def life_input_id(field: str) -> str:
    """Component id of a life phase field: "life_1_to" -> "life-1-to-input"."""
    return field.replace("_", "-") + "-input"


_life_defaults = browser_store.FIELD_DEFAULTS


def _life_row(row: int):
    """One phase: until age, workload, income and child costs (hidden while unused)."""

    def field(part: str, label: str, step: float, unit: str, maximum=None, decimals=None):
        return number_input(
            life_input_id(f"life_{row}_{part}"),
            label,
            None,
            0,
            step,
            unit,
            maximum,
            decimals=decimals,
        )

    return html.Div(
        [
            dmc.Text(f"Phase {row}", id=f"life-row-{row}-title", fw=600, size="sm"),
            dmc.SimpleGrid(
                [
                    html.Div(
                        field("to", "Bis Alter", 1, "J.", config.MAX_RETIREMENT_AGE, 0),
                        id=f"life-row-{row}-to",
                    ),
                    field("workload", "Pensum", 10, "%", 100),
                    field("income", "Einkommen", 100, "CHF/Mt."),
                    field("costs", "Kinderkosten", 100, "CHF/Mt."),
                ],
                cols=2,
                spacing="xs",
                verticalSpacing="xs",
            ),
        ],
        id=f"life-row-{row}",
        className="life-row",
        style={"display": "none"},
    )


_life_group = _group(
    "life",
    "Lebensphasen & Familie",
    "↻",
    [
        segmented(
            "life-plan-input",
            "Erwerbsleben",
            [
                {"label": "Wie heute", "value": "off"},
                {"label": "Phasen planen", "value": "on"},
            ],
            _life_defaults["life_plan"],
            "Teilzeit, Unterbrüche und Kinder bis zur Pensionierung. «Wie heute» rechnet mit "
            "deinem Einkommen von oben.",
        ),
        html.Div(
            [
                dmc.Text(
                    "Einkommen pro Monat wie oben (netto oder brutto), in heutigen Franken; die "
                    "Lohnzunahme kommt dazu. Die erste Phase beginnt heute, die letzte dauert bis "
                    "zur Pensionierung.",
                    size="xs",
                    c="dimmed",
                ),
                dmc.Group(
                    [
                        dmc.Button(
                            "100 %",
                            id="life-template-full",
                            n_clicks=0,
                            variant="light",
                            size="compact-xs",
                        ),
                        dmc.Button(
                            "Teilzeit mit Kindern",
                            id="life-template-kids",
                            n_clicks=0,
                            variant="light",
                            size="compact-xs",
                        ),
                        dmc.Button(
                            "Unterbruch",
                            id="life-template-break",
                            n_clicks=0,
                            variant="light",
                            size="compact-xs",
                        ),
                    ],
                    gap=6,
                ),
                *[_life_row(row) for row in range(1, browser_store.LIFE_PHASE_ROWS + 1)],
                dmc.Group(
                    [
                        dmc.Button(
                            "+ Phase", id="life-add-button", n_clicks=0, variant="light", size="xs"
                        ),
                        dmc.Button(
                            "− Phase",
                            id="life-remove-button",
                            n_clicks=0,
                            variant="subtle",
                            size="xs",
                        ),
                    ],
                    gap="xs",
                    grow=True,
                ),
                segmented(
                    life_input_id("life_coordination"),
                    "Koordinationsabzug der Pensionskasse",
                    [
                        {"label": "Fix (BVG)", "value": "fixed"},
                        {"label": "Nach Pensum", "value": "workload"},
                    ],
                    _life_defaults["life_coordination"],
                    "Gesetzlich gilt der volle Abzug auch bei Teilzeit; viele Kassen passen ihn "
                    "ans Pensum an. Siehe PK-Reglement.",
                ),
                dmc.Text("Kinder", fw=600, size="sm", mt="xs"),
                dmc.Text(
                    "Dein Alter bei der Geburt, auch für geplante Kinder. Nur Jahrgänge, keine "
                    "Namen; alles bleibt in diesem Browser.",
                    size="xs",
                    c="dimmed",
                ),
                dmc.SimpleGrid(
                    [
                        number_input(
                            life_input_id(f"life_child_{child}"),
                            f"Kind {child}",
                            None,
                            0,
                            1,
                            "J.",
                            config.MAX_RETIREMENT_AGE,
                            decimals=0,
                        )
                        for child in range(1, browser_store.LIFE_CHILDREN + 1)
                    ],
                    cols=2,
                    spacing="xs",
                    verticalSpacing="xs",
                ),
                segmented(
                    life_input_id("life_role"),
                    "Urlaub bei der Geburt (EO)",
                    [
                        {"label": "Mutter · 14 Wo.", "value": "mother"},
                        {"label": "Anderer · 2 Wo.", "value": "other"},
                    ],
                    _life_defaults["life_role"],
                ),
                segmented(
                    life_input_id("life_credit_share"),
                    "AHV-Erziehungsgutschriften",
                    [
                        {"label": "Ganz", "value": "full"},
                        {"label": "Hälftig (verheiratet)", "value": "half"},
                    ],
                    _life_defaults["life_credit_share"],
                ),
                number_input(
                    life_input_id("life_child_allowance"),
                    "Kinderzulage pro Kind",
                    _life_defaults["life_child_allowance"],
                    0,
                    5,
                    "CHF/Mt.",
                    description="Bis 16; Mindestbetrag, viele Kantone zahlen mehr",
                ),
                number_input(
                    life_input_id("life_education_allowance"),
                    "Ausbildungszulage pro Kind",
                    _life_defaults["life_education_allowance"],
                    0,
                    5,
                    "CHF/Mt.",
                    description="Von 16 bis höchstens 25",
                ),
            ],
            id="life-fields",
            className="field-stack",
            style={"display": "none"},
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
                _life_group,
                _home_group,
            ],
            multiple=True,
            value=["income", "balances"],
            variant="separated",
            chevronPosition="right",
            # Collapsed groups are hidden with display:none. Mantine's default (React's
            # <Activity>) defers updates inside them, which left Dash waiting forever for the
            # fields in closed groups on slow machines (seen in CI).
            keepMounted=True,
            keepMountedMode="display-none",
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
                        dmc.Title(
                            "Heute planen. Morgen sicherer sein.", order=2, className="page-title"
                        ),
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
                        dmc.TabsTab("Wohneigentum", value="home"),
                        dmc.TabsTab("Annahmen", value="assumptions"),
                    ]
                ),
                dmc.TabsPanel(html.Div(id="overview-section"), value="overview", pt="md"),
                dmc.TabsPanel(html.Div(id="pension-section"), value="pension", pt="md"),
                dmc.TabsPanel(html.Div(id="home-section"), value="home", pt="md"),
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
        dcc.Store(id=HOME_PREFILL_SKIP_STORE_ID, storage_type="memory"),
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
