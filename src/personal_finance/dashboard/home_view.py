"""Rendering of the "Wohneigentum" result tab."""

from typing import Optional

import dash_mantine_components as dmc
from dash import html

from personal_finance import config
from personal_finance.core import home
from personal_finance.core.home_plan import HomePlan
from personal_finance.dashboard.components import metric_card, money, section_card

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


def home_section(plan: Optional[HomePlan], error: Optional[str] = None):
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
            *hints,
        ],
        gap="md",
    )
