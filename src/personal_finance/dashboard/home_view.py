"""Rendering of the "Wohneigentum" result tab."""

from typing import Optional

import dash_mantine_components as dmc
from dash import html

from personal_finance import config
from personal_finance.core import home
from personal_finance.core.home_plan import HomePlan
from personal_finance.core.projection import deflate
from personal_finance.dashboard.components import chart_card, metric_card, money, section_card
from personal_finance.dashboard.figures import withdrawal_figure

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


def pension_money_section(plan: HomePlan, display_basis: str):
    """Money from the 2nd pillar and 3a (WEF) and its effect on the retirement capital."""
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
        notes.append(
            dmc.Alert(
                f"Laut Prognose reicht dein freies Vermögen (3b) zum Kaufzeitpunkt nicht für "
                f"das Ersparte. Das Modell nimmt an, dass die fehlenden "
                f"{money(plan.savings_outside_3b)} von ausserhalb kommen, z. B. von einem "
                "Sparkonto, einer Schenkung oder einem Erbvorbezug. Trage dein vorhandenes "
                "Vermögen links unter «Bisherige Guthaben» ein, damit es mitgerechnet wird.",
                title="Erspartes ausserhalb der Prognose",
                color="yellow",
                variant="light",
                radius="lg",
                className="home-savings-hint",
            )
        )

    return dmc.Stack(
        [
            dmc.SimpleGrid(
                [
                    metric_card(
                        "2. Säule bei Pensionierung",
                        money(pillar2_with[-1]),
                        gap(pillar2_without[-1], pillar2_with[-1]),
                        "green",
                        "Ⅱ",
                    ),
                    metric_card(
                        "3a bei Pensionierung",
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
                            "Vorsorge mit und ohne Kauf",
                            f"Gestrichelt ohne Kauf · {basis}",
                            withdrawal_figure(
                                ages, pillar2_without, pillar2_with, pillar3a_without,
                                pillar3a_with,
                            ),
                            height=320,
                            class_name="withdrawal-card",
                        ),
                        span={"base": 12, "lg": 7},
                    ),
                    dmc.GridCol(
                        section_card(
                            "Vorsorgegeld für den Kauf (WEF)",
                            "Beträge zum Kaufzeitpunkt, nominal",
                            [html.Div(rows, className="detail-list"), *notes],
                            class_name="wef-card",
                        ),
                        span={"base": 12, "lg": 5},
                    ),
                ],
                gap="md",
            ),
            _hints(
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
                f"Mit deinem Eigenkapital und Einkommen · begrenzt durch {max_price.limited_by}",
                "dark",
                "↑",
            ),
        ],
        cols={"base": 1, "xs": 2},
        spacing="md",
    )

    details = section_card(
        "Finanzierung im Detail",
        f"Kauf mit {plan.purchase_age} Jahren · Beträge zum Kaufzeitpunkt",
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
                "Du hast ein Nettoeinkommen angegeben. Banken rechnen mit dem Bruttoeinkommen; "
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
            details,
            pension_money_section(plan, display_basis),
            *hints,
        ],
        gap="md",
    )
