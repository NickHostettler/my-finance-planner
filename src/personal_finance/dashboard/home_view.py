"""Rendering of the "Wohneigentum" result tab (one person or a household, v1.3)."""

from typing import Optional, Union

import dash_mantine_components as dmc
from dash import html

from personal_finance import config
from personal_finance.core import home, mortgage
from personal_finance.core.home_plan import HomePlan, PersonPurchase
from personal_finance.core.projection import deflate
from personal_finance.dashboard.components import chart_card, metric_card, money, section_card
from personal_finance.dashboard.figures import wealth_figure, withdrawal_figure
from personal_finance.dashboard.household_view import contributions_card

# Traffic light: status -> (lit lamp, text colour tone)
_LIGHTS = {
    home.STATUS_AFFORDABLE: "green",
    home.STATUS_TIGHT: "orange",
    home.STATUS_NOT_AFFORDABLE: "red",
}
_HEADLINES = {
    home.STATUS_AFFORDABLE: "Tragbar",
    home.STATUS_TIGHT: "Knapp tragbar",
    home.STATUS_NOT_AFFORDABLE: "Nicht tragbar",
}


def _percent(ratio: float) -> str:
    return f"{ratio * 100:.1f} %"


def _detail_row(label: str, value: str):
    return html.Div(
        [
            html.Span(label, className="detail-label"),
            html.Strong(value, className="detail-value"),
        ],
        className="detail-row",
    )


def traffic_light(status: str):
    """Three lamps; the one for ``status`` is lit (also announced for screen readers)."""
    lit = _LIGHTS[status]
    return html.Div(
        [
            html.Span(className=f"lamp lamp-{color}" + (" lamp-on" if color == lit else ""))
            for color in ("red", "orange", "green")
        ],
        className="traffic-light",
        role="img",
        **{"aria-label": f"Ampel: {_HEADLINES[status]}"},
    )


def planning_hint():
    """Shown while no purchase is planned."""
    return section_card(
        "Wohneigentum planen",
        "",
        [
            dmc.Text(
                "Du planst ein Eigenheim? Wähle links unter «Wohneigentum» «Kauf planen». Dann "
                "siehst du hier, ob der Kauf tragbar ist, wie viel Eigenkapital und Hypothek "
                "du brauchst und welchen Preis du dir höchstens leisten kannst.",
                size="sm",
            ),
            dmc.Text(
                "Ohne Kauf bleiben alle anderen Ergebnisse unverändert.",
                size="xs",
                c="dimmed",
                mt="xs",
            ),
        ],
        class_name="home-intro-card",
    )


def error_message(message: str):
    return html.Div(
        [html.Strong("Wohneigentum: Eingaben prüfen"), html.P(message)],
        className="validation-message",
    )


def _hints(title: str, items):
    return dmc.Alert(
        dmc.List([dmc.ListItem(item) for item in items], size="sm", spacing=4),
        title=title,
        color="gray",
        variant="light",
        radius="lg",
    )


def equity_card(plan: HomePlan):
    """What the price needs at least, what is available at the purchase age and what is used."""
    result = plan.assessment
    available = plan.available
    used_hard = result.hard_funds
    used_total = result.hard_funds + result.pension_funds

    def status(used: float, needed: float) -> str:
        return "reicht" if used + 0.005 >= needed else f"es fehlen {money(needed - used)}"

    return section_card(
        "Eigenmittel: Bedarf und verfügbare Mittel",
        f"{plan.timing} · Beträge zum Kaufzeitpunkt, nominal",
        [
            dmc.Text("Mindestens nötig", fw=600, size="sm"),
            html.Div(
                [
                    _detail_row(
                        f"Eigenmittel ({config.HOME_MIN_EQUITY_RATE:.0%} des Kaufpreises)",
                        money(plan.required_equity),
                    ),
                    _detail_row(
                        f"davon hart, ohne Pensionskasse ({config.HOME_MIN_HARD_EQUITY_RATE:.0%})",
                        money(plan.required_hard_equity),
                    ),
                    _detail_row(
                        "dazu Kaufnebenkosten aus Erspartem oder 3a",
                        money(result.purchase_costs),
                    ),
                    _detail_row("Mindestbedarf insgesamt", money(plan.required_funds)),
                ],
                className="detail-list",
            ),
            dmc.Text("Verfügbar zum Kaufalter (Prognose)", fw=600, size="sm", mt="sm"),
            html.Div(
                [
                    _detail_row("Freies Vermögen (3b)", money(available.savings)),
                    _detail_row("Säule 3a", money(available.pillar3a)),
                    _detail_row(
                        "Vorbezug Pensionskasse",
                        money(available.pillar2) if available.pillar2 > 0 else "nicht möglich",
                    ),
                    _detail_row("Verfügbar insgesamt", money(available.total)),
                ],
                className="detail-list",
            ),
            dmc.Text("Eingesetzt", fw=600, size="sm", mt="sm"),
            html.Div(
                [
                    _detail_row(
                        f"Hart (Erspartes und 3a) · nötig {money(plan.required_hard_funds)}",
                        f"{money(used_hard)} · {status(used_hard, plan.required_hard_funds)}",
                    ),
                    _detail_row(
                        f"Insgesamt · nötig {money(plan.required_funds)}",
                        f"{money(used_total)} · {status(used_total, plan.required_funds)}",
                    ),
                ],
                className="detail-list",
            ),
        ],
        class_name="equity-card",
    )


def pension_money_section(
    plan: Union[HomePlan, PersonPurchase],
    display_basis: str,
    label: str = "",
    with_hints: bool = True,
):
    """Money from the 2nd pillar and 3a (WEF) and its effect on the retirement capital.

    ``plan`` is the plan of one person or one person of a household (``label``).
    """
    of = f" von {label}" if label else ""
    real = display_basis == "real"
    inflation = config.INFLATION_RATE if real else 0
    without, with_purchase = plan.without_purchase, plan.with_purchase
    pillar2_without = deflate(without.pillar2, inflation)
    pillar2_with = deflate(with_purchase.pillar2, inflation)
    pillar3a_without = deflate(without.pillar3a, inflation)
    pillar3a_with = deflate(with_purchase.pillar3a, inflation)
    current_age = plan.purchase_age - plan.years_until_purchase
    ages = list(range(current_age, current_age + len(pillar2_with)))
    basis = "heutige Kaufkraft" if real else "nominal"

    def gap(without_value: float, with_value: float) -> str:
        return f"ohne Kauf {money(without_value)} · {money(with_value - without_value)}"

    balance_2, balance_3a, balance_3b = plan.balances_at_purchase
    limit = plan.pillar2_limit
    rows = [
        _detail_row("Pensionskasse zum Kaufzeitpunkt (Prognose)", money(balance_2)),
        _detail_row(
            "Möglicher Vorbezug",
            money(limit.maximum) if limit.maximum > 0 else "nicht möglich",
        ),
        _detail_row("Geplanter Vorbezug", money(plan.pillar2_used)),
        _detail_row("Säule 3a zum Kaufzeitpunkt (Prognose)", money(balance_3a)),
        _detail_row("Geplanter Bezug 3a", money(plan.pillar3a_used)),
        _detail_row("Freies Vermögen 3b zum Kaufzeitpunkt (Prognose)", money(balance_3b)),
        _detail_row("Erspartes für den Kauf", money(plan.savings)),
    ]
    notes = [dmc.Text(reason, size="xs", c="dimmed") for reason in limit.reasons]
    if plan.savings_outside_3b > 0:
        whose = f"das freie Vermögen von {label}" if label else "dein freies Vermögen"
        where = f"bei {label}" if label else "links"
        notes.append(
            dmc.Alert(
                f"Laut Prognose reicht {whose} (3b) zum Kaufzeitpunkt nicht für das "
                f"Ersparte. Das Modell nimmt an, dass die fehlenden "
                f"{money(plan.savings_outside_3b)} von ausserhalb kommen, z. B. von einem "
                "Sparkonto, einer Schenkung oder einem Erbvorbezug. Trage das vorhandene "
                f"Vermögen {where} unter «Bisherige Guthaben» ein, damit es mitgerechnet wird.",
                title="Erspartes ausserhalb der Prognose",
                color="yellow",
                variant="light",
                radius="lg",
                className="home-savings-hint",
            )
        )

    hints = _hints(
        "Gut zu wissen zum Vorbezug",
        [
            "Ein Vorbezug senkt nicht nur das Alterskapital: Je nach Kasse sinken auch "
            "die Leistungen bei Invalidität und Tod. Eine Zusatzversicherung kann die "
            "Lücke schliessen.",
            "Beim Verkauf des Eigenheims musst du den Vorbezug zurückzahlen. "
            f"Einkäufe der letzten {config.WEF_BUY_IN_LOCK_YEARS} Jahre dürfen nicht "
            "vorbezogen werden.",
            "Der Bezug wird separat und zu einem tieferen Satz als Kapitalleistung "
            "besteuert. Das Tool berechnet diese Steuer nicht; sie hängt von Kanton, "
            "Gemeinde und Betrag ab.",
            "Statt eines Vorbezugs kannst du das Guthaben auch verpfänden: Das Geld "
            "bleibt in der Kasse und die Leistungen bleiben gleich, dafür gewährt die "
            "Bank eine höhere Hypothek. Die Wohnkosten steigen entsprechend.",
            "Pensionskassen dürfen strengere Regeln haben (z. B. eine frühere Frist vor "
            "der Pensionierung). Prüfe das Reglement deiner Kasse.",
        ],
    )
    return dmc.Stack(
        [
            *([dmc.Title(label, order=4, className="card-title person-title")] if label else []),
            dmc.SimpleGrid(
                [
                    metric_card(
                        f"2. Säule{of} bei Pensionierung",
                        money(pillar2_with[-1]),
                        gap(pillar2_without[-1], pillar2_with[-1]),
                        "green",
                        "Ⅱ",
                    ),
                    metric_card(
                        f"3a{of} bei Pensionierung",
                        money(pillar3a_with[-1]),
                        gap(pillar3a_without[-1], pillar3a_with[-1]),
                        "blue",
                        "3a",
                    ),
                ],
                cols={"base": 1, "xs": 2},
                spacing="md",
            ),
            dmc.Grid(
                [
                    dmc.GridCol(
                        chart_card(
                            f"Vorsorge{of} mit und ohne Kauf",
                            f"Gestrichelt ohne Kauf · {basis}",
                            withdrawal_figure(
                                ages,
                                pillar2_without,
                                pillar2_with,
                                pillar3a_without,
                                pillar3a_with,
                            ),
                            height=320,
                            class_name="withdrawal-card",
                        ),
                        span={"base": 12, "lg": 7},
                    ),
                    dmc.GridCol(
                        section_card(
                            f"Vorsorgegeld{of} für den Kauf (WEF)",
                            "Beträge zum Kaufzeitpunkt, nominal",
                            [html.Div(rows, className="detail-list"), *notes],
                            class_name="wef-card",
                        ),
                        span={"base": 12, "lg": 5},
                    ),
                ],
                gap="md",
            ),
            *([hints] if with_hints else []),
        ],
        gap="md",
    )


_MODE_LABELS = {mortgage.DIRECT: "Direkt", mortgage.INDIRECT: "Indirekt über 3a"}


def mortgage_section(plan: HomePlan, display_basis: str):
    """Mortgage, amortisation and net wealth until retirement; affordability in retirement."""
    real = display_basis == "real"
    inflation = config.INFLATION_RATE if real else 0
    basis = "heutige Kaufkraft" if real else "nominal"
    outcome = plan.outcome
    paths = outcome.paths
    savings = deflate(
        [sum(values) for values in zip(paths.pillar2, paths.pillar3a, paths.pillar3b)], inflation
    )
    property_value = deflate(outcome.property_value, inflation)
    debt = deflate(outcome.debt, inflation)
    net_wealth = deflate(outcome.net_wealth, inflation)
    net_without = deflate(plan.net_wealth_without_purchase(), inflation)
    current_age = plan.purchase_age - plan.years_until_purchase
    ages = list(range(current_age, current_age + len(debt)))
    at_retirement = (1 + inflation) ** (len(debt) - 1)  # nominal -> chosen basis
    amortisation = outcome.plan
    assessment = plan.assessment
    # A household is computed until the first retirement (v1.3).
    at = "bei der ersten Pensionierung" if plan.household else "bei Pensionierung"
    until = f"bis zur {plan.horizon}"

    cards = dmc.SimpleGrid(
        [
            metric_card(
                f"Hypothek {at}",
                money(debt[-1]),
                f"Start {money(assessment.mortgage)} · {_MODE_LABELS[plan.amortisation]} "
                "amortisiert",
                "blue",
                "%",
            ),
            metric_card(
                f"Zinskosten {until}",
                money(amortisation.total_interest),
                f"Effektiver Zins {plan.mortgage_rate:.2%} · nominal, ohne Steuern",
                "gold",
                "Σ",
            ),
            metric_card(
                f"Nettovermögen {at}",
                money(net_wealth[-1]),
                f"Vermögen + Immobilie − Hypothek · ohne Kauf {money(net_without[-1])}",
                "dark",
                "=",
            ),
        ],
        cols={"base": 1, "sm": 3},
        spacing="md",
    )

    def comparison_row(label, values):
        return dmc.TableTr([dmc.TableTd(label)] + [dmc.TableTd(value) for value in values])

    outcomes = [plan.outcomes[mode] for mode in mortgage.MODES]
    comparison = section_card(
        "Direkt oder indirekt amortisieren?",
        f"{at[0].upper()}{at[1:]} · {basis} · Zinskosten nominal",
        [
            dmc.TableScrollContainer(
                dmc.Table(
                    [
                        dmc.TableThead(
                            dmc.TableTr(
                                [dmc.TableTh("")]
                                + [
                                    dmc.TableTh(
                                        _MODE_LABELS[mode]
                                        + (" (gewählt)" if mode == plan.amortisation else "")
                                    )
                                    for mode in mortgage.MODES
                                ]
                            )
                        ),
                        dmc.TableTbody(
                            [
                                comparison_row(
                                    "Amortisation pro Jahr",
                                    [money(item.plan.annual_amortisation) for item in outcomes],
                                ),
                                comparison_row(
                                    "davon in verpfändete 3a",
                                    [money(item.plan.annual_pledged) for item in outcomes],
                                ),
                                comparison_row(
                                    "Hypothek",
                                    [money(item.debt[-1] / at_retirement) for item in outcomes],
                                ),
                                comparison_row(
                                    "Säule 3a",
                                    [
                                        money(item.paths.pillar3a[-1] / at_retirement)
                                        for item in outcomes
                                    ],
                                ),
                                comparison_row(
                                    "Zinskosten bis dahin",
                                    [money(item.plan.total_interest) for item in outcomes],
                                ),
                                comparison_row(
                                    "Nettovermögen",
                                    [
                                        money(item.net_wealth[-1] / at_retirement)
                                        for item in outcomes
                                    ],
                                ),
                            ]
                        ),
                    ],
                    striped=True,
                    fz="sm",
                    className="comparison-table",
                ),
                minWidth=360,
            ),
            dmc.Text(
                "Indirekt bleibt die Schuld bis zum Ende der Amortisation gleich hoch, deshalb "
                "sind die Zinsen höher. Dafür wächst das 3a-Geld mit der Rendite, und die "
                "3a-Einzahlungen senken das steuerbare Einkommen. Die Steuern rechnet das Tool "
                "nicht.",
                size="xs",
                c="dimmed",
                mt="sm",
            ),
        ],
        class_name="amortisation-card",
    )

    notes = []
    if plan.amortisation == mortgage.INDIRECT and (
        amortisation.annual_pledged < amortisation.annual_amortisation - 0.005
    ):
        notes.append(
            dmc.Alert(
                f"In die Säule 3a passen neben {'euren 3a-Plänen' if plan.household else 'deinem 3a-Plan'} nur noch "
                f"{money(amortisation.annual_pledged)} pro Jahr (Limit "
                f"{money(config.PILLAR3A_ANNUAL_MAX)}). Die restlichen "
                f"{money(amortisation.annual_direct)} pro Jahr werden direkt amortisiert.",
                title="3a-Limit erreicht",
                color="yellow",
                variant="light",
                radius="lg",
                className="pledged-cap-hint",
            )
        )

    retirement = outcome.retirement
    status = home.STATUS_AFFORDABLE if retirement.affordable else home.STATUS_NOT_AFFORDABLE
    ratio = (
        _percent(retirement.cost_to_income) if retirement.cost_to_income != float("inf") else "–"
    )
    retirement_rows = [
        _detail_row(
            "Wohnkosten pro Monat",
            money(retirement.annual_costs / at_retirement / 12),
        ),
        _detail_row(
            f"Rente 2. Säule pro Monat (Umwandlungssatz "
            f"{config.HOME_RETIREMENT_CONVERSION_RATE:.1%})",
            money(retirement.pension_income / at_retirement / 12),
        ),
        _detail_row(
            "AHV pro Monat (Jahresbetrag / 12)",
            "Angaben fehlen"
            if retirement.ahv_income is None
            else money(retirement.ahv_income / at_retirement / 12),
        ),
        _detail_row("Anteil der Wohnkosten an den Renten", ratio),
    ]
    retirement_card = section_card(
        "Tragbarkeit im Alter",
        f"{'Wenn beide pensioniert sind' if plan.household else 'Nach der Pensionierung'} · "
        f"{basis} · höchstens ⅓ der Renten",
        [
            dmc.Group(
                [
                    traffic_light(status),
                    html.Div(
                        "Im Alter tragbar" if retirement.affordable else "Im Alter nicht tragbar",
                        className=f"traffic-headline traffic-{_LIGHTS[status]}",
                    ),
                ],
                gap="md",
                wrap="nowrap",
            ),
            html.Div(retirement_rows, className="detail-list"),
            dmc.Text(
                "Kalkulatorischer Zins auf der Resthypothek plus Unterhalt, verglichen mit AHV "
                "und Rente aus der 2. Säule. 3a- und freies Vermögen sind nicht eingerechnet."
                + (
                    (
                        " Für die AHV gebt bei beiden Personen unter «AHV-Rente» das Einkommen an."
                        if plan.household
                        else " Für die AHV gib links unter «AHV-Rente» dein Einkommen an."
                    )
                    if retirement.ahv_income is None
                    else ""
                ),
                size="xs",
                c="dimmed",
                mt="xs",
            ),
        ],
        class_name="retirement-card",
    )

    return dmc.Stack(
        [
            dmc.Title(f"Hypothek und Vermögen {until}", order=4, className="card-title"),
            cards,
            chart_card(
                "Vermögen, Hypothek und Nettovermögen",
                f"Immobilie zum Kaufpreis, ohne Wertveränderung · {basis}",
                wealth_figure(ages, savings, property_value, debt, net_wealth),
                height=360,
                class_name="wealth-card",
            ),
            *notes,
            dmc.Grid(
                [
                    dmc.GridCol(comparison, span={"base": 12, "lg": 7}),
                    dmc.GridCol(retirement_card, span={"base": 12, "lg": 5}),
                ],
                gap="md",
            ),
            dmc.Alert(
                f"Ab dem {config.HOME_IMPUTED_RENTAL_VALUE_END} wird der Eigenmietwert "
                "abgeschafft (Volksabstimmung vom 28. September 2025). Dann entfällt auch der "
                "Abzug der Schuldzinsen weitgehend, und der Steuervorteil einer hohen "
                "Hypothek sinkt. Das Tool berechnet keine Steuern; frag deine "
                "Steuerverwaltung oder Bank, was das für dich bedeutet.",
                title="Eigenmietwert und Steuern",
                color="blue",
                variant="light",
                radius="lg",
                className="imputed-rent-hint",
            ),
        ],
        gap="md",
    )


def home_section(
    plan: Optional[HomePlan], error: Optional[str] = None, display_basis: str = "nominal"
):
    """Contents of the tab: hint without a purchase, the error, or the assessment."""
    if error is not None:
        return error_message(error)
    if plan is None:
        return planning_hint()

    result = plan.assessment
    reasons = result.reasons or ("Alle Regeln zu Eigenmitteln und Tragbarkeit sind erfüllt.",)
    limit_share = _percent(config.HOME_MAX_COST_TO_INCOME)
    affordability = section_card(
        "Tragbarkeit",
        f"Wohnkosten {_percent(result.cost_to_income)} des Bruttoeinkommens · "
        f"erlaubt sind höchstens ⅓ ({limit_share})",
        [
            dmc.Group(
                [
                    traffic_light(result.status),
                    html.Div(
                        _HEADLINES[result.status],
                        className=f"traffic-headline traffic-{_LIGHTS[result.status]}",
                    ),
                ],
                gap="md",
                wrap="nowrap",
            ),
            dmc.List(
                [dmc.ListItem(reason) for reason in reasons],
                size="sm",
                spacing=4,
                mt="sm",
                className="home-reasons",
            ),
        ],
        class_name="affordability-card",
    )

    max_price = plan.max_price
    max_available = plan.max_price_available
    metrics = dmc.SimpleGrid(
        [
            metric_card(
                "Eigenmittel",
                money(result.total_equity),
                f"{_percent(result.equity_ratio)} des Kaufpreises · davon hart "
                f"{money(result.hard_equity)} ({_percent(result.hard_equity_ratio)})",
                "green",
                "EM",
            ),
            metric_card(
                "Hypothek",
                money(result.mortgage),
                f"Belehnung {_percent(result.loan_to_value)} · 2. Hypothek "
                f"{money(result.second_mortgage)}",
                "blue",
                "%",
            ),
            metric_card(
                "Wohnkosten für die Tragbarkeit",
                f"{money(result.monthly_costs)}/Monat",
                f"Kalkulatorischer Zins, Unterhalt und Amortisation · "
                f"{money(result.annual_costs)}/Jahr",
                "gold",
                "⌂",
            ),
            metric_card(
                "Maximal finanzierbarer Kaufpreis",
                money(max_price.price),
                f"Mit dem eingesetzten Eigenkapital · begrenzt durch {max_price.limited_by}",
                "dark",
                "↑",
            ),
            metric_card(
                "Höchster Kaufpreis zum Kaufzeitpunkt"
                if plan.household
                else f"Höchster Kaufpreis mit {plan.purchase_age} Jahren",
                money(max_available.price),
                f"Mit allen verfügbaren Mitteln ({money(plan.available.total)}) · begrenzt "
                f"durch {max_available.limited_by}",
                "dark",
                "⇡",
            ),
        ],
        cols={"base": 1, "xs": 2},
        spacing="md",
    )

    equity = equity_card(plan)

    details = section_card(
        "Finanzierung im Detail",
        f"{plan.timing} · Beträge zum Kaufzeitpunkt",
        [
            html.Div(
                [
                    _detail_row("Kaufpreis", money(result.price)),
                    _detail_row(
                        f"Kaufnebenkosten ({config.HOME_PURCHASE_COSTS_RATE:.0%})",
                        money(result.purchase_costs),
                    ),
                    _detail_row("Erspartes und 3a (harte Mittel)", money(result.hard_funds)),
                    _detail_row("Aus der Pensionskasse", money(result.pension_funds)),
                    _detail_row("1. Hypothek (bis ⅔ des Preises)", money(result.first_mortgage)),
                    _detail_row(
                        f"2. Hypothek, amortisiert in {result.amortisation_years} Jahren",
                        f"{money(result.second_mortgage)} · {money(result.annual_amortisation)}/Jahr",
                    ),
                    _detail_row(
                        "Kalkulatorischer Zins pro Jahr", money(result.annual_imputed_interest)
                    ),
                    _detail_row(
                        f"Unterhalt und Nebenkosten ({config.HOME_MAINTENANCE_RATE:.0%})",
                        money(result.annual_maintenance),
                    ),
                    _detail_row("Bruttoeinkommen für die Tragbarkeit", money(plan.gross_income)),
                ],
                className="detail-list",
            )
        ],
        class_name="home-details-card",
    )

    hints = []
    if plan.gross_income_from_net:
        hints.append(
            dmc.Alert(
                ("Mindestens eine Person hat" if plan.household else "Du hast")
                + " ein Nettoeinkommen angegeben. Banken rechnen mit dem Bruttoeinkommen; "
                "hier wird vorsichtig das Nettoeinkommen verwendet. Für eine genauere Prüfung "
                "trage links unter «Wohneigentum» das Bruttoeinkommen des Haushalts ein.",
                title="Bruttoeinkommen fehlt",
                color="yellow",
                variant="light",
                radius="lg",
                className="home-income-hint",
            )
        )
    hints.append(
        dmc.Alert(
            "Die Prüfung folgt den üblichen Regeln von Banken und keiner Bankzusage. Banken "
            "prüfen jeden Kauf individuell und können strenger oder grosszügiger sein.",
            title="Modell statt Hypothekarberatung",
            color="gray",
            variant="light",
            radius="lg",
        )
    )

    return dmc.Stack(
        [
            dmc.Grid(
                [
                    dmc.GridCol(affordability, span={"base": 12, "lg": 5}),
                    dmc.GridCol(metrics, span={"base": 12, "lg": 7}),
                ],
                gap="md",
            ),
            dmc.Grid(
                [
                    dmc.GridCol(equity, span={"base": 12, "lg": 6}),
                    dmc.GridCol(details, span={"base": 12, "lg": 6}),
                ],
                gap="md",
            ),
            *(
                [
                    contributions_card(plan),
                    *[
                        pension_money_section(
                            member,
                            display_basis,
                            label=member.label,
                            with_hints=member is plan.members[-1],
                        )
                        for member in plan.members
                    ],
                ]
                if plan.household
                else [pension_money_section(plan, display_basis)]
            ),
            mortgage_section(plan, display_basis),
            *hints,
        ],
        gap="md",
    )
