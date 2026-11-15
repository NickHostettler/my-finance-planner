"""The "Haushalt" tab (v1.3, #41, #46): both persons side by side and what they share.

Personal results stay personal: the table shows each person's projection at the own
retirement and never adds them up to one retirement capital. Household values (income,
savings, AHV of both, the joint purchase) are shown separately.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence

import dash_mantine_components as dmc
from dash import html

from personal_finance import config
from personal_finance.core import ahv, home
from personal_finance.core.home_plan import HomePlan, Paths
from personal_finance.core.household import Household
from personal_finance.core.projection import deflate
from personal_finance.dashboard.components import metric_card, money, section_card


@dataclass(frozen=True)
class PersonSummary:
    """What the tab shows of one person (nominal paths until the own retirement)."""

    label: str
    current_age: int
    retirement_age: int
    monthly_net_income: float
    monthly_savings: float  # 3a and 3b
    paths: Paths
    ahv_monthly_today: Optional[float]  # after the cap of a married couple
    capital_gap: Optional[float] = None  # life phases: less than at 100 % (nominal)


def planning_hint():
    """Shown while the plan is for one person."""
    return section_card(
        "Zu zweit planen",
        "",
        [
            dmc.Text(
                "Plant ihr zu zweit? Wähle links oben bei «Planung für» «Zwei Personen». Dann "
                "erfasst ihr die Angaben von Person A und Person B getrennt, die Kinder und einen "
                "gemeinsamen Kauf einmal für den Haushalt. Hier siehst du dann beide Personen "
                "nebeneinander und was ihr gemeinsam habt.",
                size="sm",
            ),
            dmc.Text(
                "Mit einer Person bleiben alle Ergebnisse wie bisher.",
                size="xs",
                c="dimmed",
                mt="xs",
            ),
        ],
        class_name="household-intro-card",
    )


def error_message(message: str):
    return html.Div(
        [html.Strong("Haushalt: Eingaben prüfen"), html.P(message)],
        className="validation-message",
    )


def _at_retirement(values: Sequence[float], inflation: float) -> float:
    return deflate(values, inflation)[-1]


def _comparison(people: Sequence[PersonSummary], display_basis: str):
    real = display_basis == "real"
    inflation = config.INFLATION_RATE if real else 0
    basis = "heutige Kaufkraft" if real else "nominal"

    def row(label: str, values: List[str]):
        return dmc.TableTr([dmc.TableTd(label), *[dmc.TableTd(value) for value in values]])

    def ahv_value(person: PersonSummary) -> str:
        shown = ahv.project_pension_basis(
            person.ahv_monthly_today,
            person.retirement_age - person.current_age,
            config.INFLATION_RATE,
            display_basis,
        )
        return "Angaben fehlen" if shown is None else money(shown)

    rows = [
        row("Alter heute", [str(person.current_age) for person in people]),
        row("Pensionierung mit", [str(person.retirement_age) for person in people]),
        row("Nettoeinkommen pro Monat", [money(person.monthly_net_income) for person in people]),
        row(
            "2. Säule bei Pensionierung",
            [money(_at_retirement(person.paths.pillar2, inflation)) for person in people],
        ),
        row(
            "Säule 3a bei Pensionierung",
            [money(_at_retirement(person.paths.pillar3a, inflation)) for person in people],
        ),
        row(
            "Freies Vermögen 3b bei Pensionierung",
            [money(_at_retirement(person.paths.pillar3b, inflation)) for person in people],
        ),
        row("AHV pro Monat", [ahv_value(person) for person in people]),
    ]
    if any(person.capital_gap is not None for person in people):
        rows.append(
            row(
                "Vorsorgelücke durch Lebensphasen",
                [
                    "–" if person.capital_gap is None else money(person.capital_gap)
                    for person in people
                ],
            )
        )
    return section_card(
        "Persönliche Vorsorge im Vergleich",
        f"Jede Person bei ihrer eigenen Pensionierung · {basis}",
        [
            dmc.TableScrollContainer(
                dmc.Table(
                    [
                        dmc.TableThead(
                            dmc.TableTr(
                                [dmc.TableTh("")] + [dmc.TableTh(person.label) for person in people]
                            )
                        ),
                        dmc.TableTbody(rows),
                    ],
                    striped=True,
                    fz="sm",
                    className="household-table",
                ),
                minWidth=340,
            ),
            dmc.Text(
                "Das Vorsorgekapital gehört der jeweiligen Person und wird nicht "
                "zusammengezählt. Ein Vorbezug für den gemeinsamen Kauf senkt nur die Prognose "
                "der Person, deren Geld es ist.",
                size="xs",
                c="dimmed",
                mt="sm",
            ),
        ],
        class_name="household-comparison-card",
    )


def couple_ahv_text(household: Household, capped: bool) -> str:
    """The detail below the AHV of both persons."""
    if not household.married:
        return "Nicht verheiratet: keine Plafonierung, jede Person erhält ihre eigene Rente"
    cap = money(ahv.COUPLE_MAXIMUM_MONTHLY_PENSION)
    if capped:
        return f"Plafoniert: Ehepaare erhalten zusammen höchstens {cap} (heute)"
    return f"Unter der Plafonierung für Ehepaare ({cap} heute)"


def contributions_card(plan: HomePlan):
    """Who puts how much from which source into the joint purchase (#42, #46)."""
    members = plan.members

    def row(label: str, values: List[float], strong: bool = False):
        cells = [money(value) for value in values]
        if strong:
            cells = [html.Strong(cell) for cell in cells]
        return dmc.TableTr([dmc.TableTd(label), *[dmc.TableTd(cell) for cell in cells]])

    def with_total(values: List[float]) -> List[float]:
        return [*values, sum(values)]

    rows = [
        row("Erspartes (freies Vermögen)", with_total([member.savings for member in members])),
        row("Säule 3a", with_total([member.pillar3a_used for member in members])),
        row("Pensionskasse (Vorbezug)", with_total([member.pillar2_used for member in members])),
        row("Eingesetzt", with_total([member.used for member in members]), strong=True),
        row(
            "Verfügbar zum Kaufzeitpunkt",
            with_total([member.available.total for member in members]),
        ),
    ]
    return section_card(
        "Kaufmittel je Person",
        f"{plan.timing} · Beträge zum Kaufzeitpunkt, nominal",
        [
            dmc.TableScrollContainer(
                dmc.Table(
                    [
                        dmc.TableThead(
                            dmc.TableTr(
                                [dmc.TableTh("")]
                                + [dmc.TableTh(member.label) for member in members]
                                + [dmc.TableTh("Haushalt")]
                            )
                        ),
                        dmc.TableTbody(rows),
                    ],
                    striped=True,
                    fz="sm",
                    className="contributions-table",
                ),
                minWidth=340,
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(
                                f"Mindestbedarf ({config.HOME_MIN_EQUITY_RATE:.0%} Eigenmittel "
                                "und Kaufnebenkosten)",
                                className="detail-label",
                            ),
                            html.Strong(money(plan.required_funds), className="detail-value"),
                        ],
                        className="detail-row",
                    ),
                    html.Div(
                        [
                            html.Span(
                                "davon mindestens hart, ohne Pensionskasse",
                                className="detail-label",
                            ),
                            html.Strong(money(plan.required_hard_funds), className="detail-value"),
                        ],
                        className="detail-row",
                    ),
                ],
                className="detail-list",
            ),
            dmc.Text(
                "Jeder Bezug wird mit den Regeln der Person geprüft, deren Guthaben es ist "
                "(Mindestbetrag, Regel ab 50, Frist vor der Pensionierung).",
                size="xs",
                c="dimmed",
                mt="xs",
            ),
        ],
        class_name="contributions-card",
    )


def _hints(household: Household) -> List[str]:
    if household.married:
        return [
            "Verheiratete und eingetragene Partner: Für einen Vorbezug aus Pensionskasse oder "
            "3a braucht es die schriftliche Zustimmung der Ehepartnerin oder des Ehepartners.",
            "Stirbt eine Person, zahlen AHV und Pensionskasse in der Regel eine Witwen- oder "
            "Witwerrente. Ob der Haushalt das Eigenheim dann noch tragen kann, rechnet das Tool "
            "nicht.",
            "Ehepaare werden gemeinsam besteuert. Steuern rechnet das Tool nicht.",
        ]
    return [
        "Ohne Ehe gibt es keine Witwen- oder Witwerrente der AHV. Eine Partnerrente der "
        "Pensionskasse gibt es nur, wenn das Reglement sie vorsieht; oft muss man sie vorher "
        "anmelden.",
        "Beim gemeinsamen Kauf ohne Ehe ist Miteigentum mit festen Anteilen üblich. Viele "
        "Pensionskassen begrenzen den Vorbezug auf den eigenen Anteil. Prüfe das Reglement.",
        "Wer nicht erwerbstätig ist, ist ohne Ehe nicht über die andere Person in der AHV "
        "gedeckt und zahlt die Beiträge selbst.",
    ]


def household_section(
    people: Sequence[PersonSummary],
    household: Household,
    plan: Optional[HomePlan],
    display_basis: str = "nominal",
    capped: bool = False,
    purchase_planned: bool = False,
):
    """Contents of the tab for two persons."""
    ahv_values = [person.ahv_monthly_today for person in people]
    ahv_known = None not in ahv_values
    ahv_total = sum(ahv_values) if ahv_known else None
    if purchase_planned and plan is None:
        purchase, purchase_detail = "Eingaben prüfen", "Details im Tab «Wohneigentum»"
    elif plan is None:
        purchase, purchase_detail = "Kein Kauf geplant", "Unter «Gemeinsam» links planen"
    else:
        headline = {
            home.STATUS_AFFORDABLE: "Tragbar",
            home.STATUS_TIGHT: "Knapp tragbar",
            home.STATUS_NOT_AFFORDABLE: "Nicht tragbar",
        }[plan.assessment.status]
        purchase = headline
        purchase_detail = f"{money(plan.assessment.price)} · {plan.timing}"
    metrics = dmc.SimpleGrid(
        [
            metric_card(
                "Nettoeinkommen des Haushalts",
                f"{money(sum(person.monthly_net_income for person in people))}/Monat",
                " + ".join(money(person.monthly_net_income) for person in people) + " · heute",
                "dark",
                "Σ",
            ),
            metric_card(
                "Sparen für 3a und 3b",
                f"{money(sum(person.monthly_savings for person in people))}/Monat",
                "Beide Personen zusammen",
                "blue",
                "↗",
            ),
            metric_card(
                "AHV beider Personen",
                "Angaben fehlen" if ahv_total is None else f"{money(ahv_total)}/Monat",
                "Für beide unter «AHV-Rente» das Einkommen angeben"
                if ahv_total is None
                else couple_ahv_text(household, capped) + " · in heutigen Franken",
                "green",
                "AHV",
            ),
            metric_card("Gemeinsames Wohneigentum", purchase, purchase_detail, "gold", "⌂"),
        ],
        cols={"base": 1, "xs": 2, "xl": 4},
        spacing="md",
    )
    parts = [metrics, _comparison(people, display_basis)]
    if plan is not None:
        parts.append(contributions_card(plan))
    parts.append(
        dmc.Alert(
            dmc.List([dmc.ListItem(item) for item in _hints(household)], size="sm", spacing=4),
            title="Verheiratet" if household.married else "Nicht verheiratet",
            color="gray",
            variant="light",
            radius="lg",
            className="household-hints",
        )
    )
    return dmc.Stack(parts, gap="md")


def assumptions():
    """The household part of the "Annahmen" tab."""
    return section_card(
        "Haushalt mit zwei Personen",
        "Modellannahmen",
        [
            dmc.List(
                [
                    dmc.ListItem(item)
                    for item in (
                        "Jede Person wird wie eine Einzelperson gerechnet: eigenes Einkommen, "
                        "eigene Pensionskasse, 3a und 3b, eigene AHV und eigene Lebensphasen.",
                        "Kinder gehören zum Haushalt und werden mit dem Alter von Person A bei "
                        "der Geburt erfasst; für Person B zählt der Altersunterschied. "
                        "Familienzulagen werden einmal gerechnet, bei der ersten Person mit "
                        "Lebensphasen.",
                        "Verheiratet (oder eingetragene Partnerschaft): Die "
                        "Erziehungsgutschriften werden hälftig geteilt, die beiden AHV-Renten "
                        "zusammen auf 150 % der Maximalrente begrenzt (Plafonierung, in "
                        "heutigen Franken). Nicht verheiratet: keine Plafonierung, die "
                        "Gutschriften nach eurer Wahl.",
                        "Gemeinsamer Kauf: Eigenmittel und Tragbarkeit mit dem Einkommen und "
                        "den Mitteln beider Personen. Haushaltsprognose, Amortisation und "
                        "Hypothek bis zur ersten Pensionierung; die Tragbarkeit im Alter mit "
                        "der Resthypothek dann und den Renten beider Personen.",
                        "Indirekte Amortisation: Die Einzahlungen in die verpfändete 3a werden "
                        "nach dem freien 3a-Platz beider Personen aufgeteilt.",
                        "Nicht gerechnet: Steuern (auch die gemeinsame Besteuerung von "
                        "Ehepaaren), Güter- und Erbrecht, Leistungen bei Tod und Invalidität.",
                    )
                ],
                size="sm",
                spacing=4,
            )
        ],
        class_name="household-assumptions",
    )


def person_heading(label: str, current_age: int, retirement_age: int):
    """Above the results of one person when planning for two."""
    return dmc.Text(
        f"{label} · {current_age} Jahre · Pensionierung mit {retirement_age}",
        className="person-heading",
    )
