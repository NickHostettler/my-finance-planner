"""Rendering of the results tabs: overview, pension details and model assumptions."""

from typing import Optional, Tuple

import dash_mantine_components as dmc
from dash import html

from personal_finance import config
from personal_finance.core import ahv
from personal_finance.core.projection import project_balance
from personal_finance.dashboard.components import (
    chart_card,
    metric_card,
    money,
    section_card,
)
from personal_finance.dashboard.figures import (
    comparison_figure,
    composition_figure,
    projection_figure,
)

AHV_13TH_PENSION_URL = (
    "https://www.ahv-iv.ch/de/Sozialversicherungen/"
    "Alters-und-Hinterlassenenversicherung-AHV/13-AHV-Rente"
)


def _link(text: str, url: str):
    return html.A(text, href=url, target="_blank", rel="noopener noreferrer")


def _detail_row(label: str, value: str):
    return html.Div(
        [
            html.Span(label, className="detail-label"),
            html.Strong(value, className="detail-value"),
        ],
        className="detail-row",
    )


def _assumption(title: str, text: str, links=None):
    children = [
        dmc.Text(title, className="assumption-title"),
        dmc.Text(text, className="assumption-text"),
    ]
    if links:
        children.append(html.Div(links, className="assumption-source-links"))
    return dmc.Paper(children, withBorder=True, p="md", className="assumption-item")


def results_view(
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
) -> Tuple[object, object, object, str]:
    """Return the contents of the three result tabs and the calculation notice."""
    pillar2 = analysis.pillar2
    years = analysis.years_to_retirement
    real = display_basis == "real"
    inflation_rate = config.INFLATION_RATE if real else 0
    basis_detail = (
        f"Reale Werte in heutiger Kaufkraft · {config.INFLATION_RATE:.0%} Inflation pro Jahr"
        if real
        else "Nominale CHF · ohne Inflationsbereinigung"
    )
    ahv_estimated_today = (
        ahv.estimate_monthly_old_age_pension(ahv_average_income, ahv_contribution_years)
        if ahv_average_income is not None
        else None
    )
    ahv_estimated_display = ahv.project_pension_basis(
        ahv_estimated_today,
        years,
        config.INFLATION_RATE,
        display_basis,
    )
    pillar2_values = project_balance(
        pillar2.annual_contribution_total, years, pillar2_return, initial_2, inflation_rate
    )
    pillar3a_values = project_balance(
        pillar3a.annual_savings, years, assumed_return, initial_3a, inflation_rate
    )
    pillar3b_values = project_balance(
        pillar3b.annual_savings, years, assumed_return, initial_3b, inflation_rate
    )
    total = pillar2_values[-1] + pillar3a_values[-1] + pillar3b_values[-1]
    ages = list(range(current_age, retirement_age + 1))
    growth = projection_figure(ages, pillar2_values, pillar3a_values, pillar3b_values)
    composition = composition_figure(
        pillar2,
        pillar3a,
        pillar3b,
        initial_2,
        initial_3a,
        initial_3b,
        pillar2_return,
        inflation_rate,
    )
    comparison = comparison_figure(
        pillar2_values[-1],
        pillar3a_values[-1],
        pillar3b_values[-1],
        total,
    )
    monthly_savings = pillar3a.monthly_savings + pillar3b.monthly_savings
    savings_rate = monthly_savings / income * 100

    overview = dmc.Stack(
        [
            dmc.Text(
                f"{years} Jahre Anlagehorizont · Modellrendite {assumed_return:.0%} für 3a und 3b · "
                f"{'reale CHF' if real else 'nominale CHF'}",
                className="results-subtitle",
            ),
            dmc.SimpleGrid(
                [
                    metric_card(
                        "Projiziertes Vorsorgekapital",
                        money(total),
                        f"bei Pensionierung mit {retirement_age} Jahren · "
                        f"{'heutige Kaufkraft' if real else 'nominal'}",
                        "dark",
                        "↗",
                    ),
                    metric_card(
                        "2. Säule",
                        money(pillar2_values[-1]),
                        f"AN {money(pillar2.annual_contribution_employee / 12)} · "
                        f"AG {money(pillar2.annual_contribution_employer / 12)}/Monat",
                        "green",
                        "Ⅱ",
                    ),
                    metric_card(
                        "Dein 3a-Plan",
                        money(pillar3a_values[-1]),
                        f"{money(pillar3a.monthly_savings)}/Monat · gebunden",
                        "blue",
                        "3a",
                    ),
                    metric_card(
                        "Dein 3b-Plan",
                        money(pillar3b_values[-1]),
                        f"{money(pillar3b.monthly_savings)}/Monat · frei",
                        "gold",
                        "3b",
                    ),
                ],
                cols={"base": 1, "xs": 2, "xl": 4},
                spacing="md",
            ),
            dmc.Grid(
                [
                    dmc.GridCol(
                        chart_card(
                            "So kann dein Vermögen wachsen",
                            f"Kumulierte Modellprojektion · {basis_detail}",
                            growth,
                            height=380,
                            class_name="growth-card",
                        ),
                        span={"base": 12, "lg": 8},
                    ),
                    dmc.GridCol(
                        section_card(
                            "AHV-Rente",
                            "Monatliches Ruhestandseinkommen, separat vom angesparten "
                            "Vorsorgekapital. Die Jahresbeträge berücksichtigen 13 Altersrenten.",
                            [
                                metric_card(
                                    "Vereinfachte AHV-Schätzung",
                                    (
                                        money(ahv_estimated_display)
                                        if ahv_estimated_display is not None
                                        else "Angaben fehlen"
                                    ),
                                    (
                                        f"{money(ahv_estimated_display * 13)} pro Jahr inkl. "
                                        f"13. Rente · {ahv_contribution_years}/"
                                        f"{ahv.FULL_CONTRIBUTION_YEARS} Beitragsjahre"
                                        if ahv_estimated_display is not None
                                        else "Durchschnittliches Jahreseinkommen eingeben"
                                    ),
                                    "green",
                                    "≈",
                                )
                            ],
                            class_name="ahv-card",
                        ),
                        span={"base": 12, "lg": 4},
                    ),
                ],
                gap="md",
            ),
        ],
        gap="md",
    )

    pension = dmc.Stack(
        [
            dmc.Grid(
                [
                    dmc.GridCol(
                        chart_card(
                            "Deine Vorsorgebausteine im Vergleich",
                            f"Projiziertes Kapital bei Pensionierung · {basis_detail}",
                            comparison,
                            height=300,
                            class_name="comparison-card",
                        ),
                        span={"base": 12, "lg": 7},
                    ),
                    dmc.GridCol(
                        chart_card(
                            "Einzahlungen & Wachstum",
                            f"Verhältnis der Beiträge zum Zuwachs · {basis_detail}",
                            composition,
                            height=300,
                            class_name="composition-card",
                        ),
                        span={"base": 12, "lg": 5},
                    ),
                ],
                gap="md",
            ),
            section_card(
                "Dein Sparplan",
                "",
                [
                    html.Div(
                        [
                            _detail_row("Startguthaben 2. Säule", money(initial_2)),
                            _detail_row("Startguthaben 3a", money(initial_3a)),
                            _detail_row("Startguthaben 3b", money(initial_3b)),
                            _detail_row(
                                "BVG-Modell",
                                (
                                    f"Eigene PK-Werte · {pillar2_return:.2%} Verzinsung"
                                    if pillar2_mode == "custom"
                                    else f"Vereinfachte BVG-Schätzung · {pillar2_return:.0%}"
                                ),
                            ),
                            _detail_row("Monatliches Sparen", money(monthly_savings)),
                            _detail_row("Sparquote vom Netto", f"{savings_rate:.1f} %"),
                            _detail_row("Verbleibend nach 3a & 3b", money(income - monthly_savings)),
                        ],
                        className="detail-list",
                    )
                ],
                class_name="plan-card",
            ),
        ],
        gap="md",
    )

    assumptions = dmc.Stack(
        [
            dmc.SimpleGrid(
                [
                    _assumption(
                        (
                            "2. Säule · eigene PK-Werte"
                            if pillar2_mode == "custom"
                            else "2. Säule · vereinfachte BVG-Schätzung"
                        ),
                        (
                            "Deine angegebenen Beiträge ersetzen die vereinfachte Schätzung. Das "
                            "Dashboard prüft sie nicht gegen den gesetzlichen Mindestbeitrag oder "
                            "das Reglement deiner Pensionskasse."
                            if pillar2_mode == "custom"
                            else "Keine offizielle BVG-Mindestberechnung: Das Modell zieht einen "
                            "festen Koordinationsabzug vom Jahresnettoeinkommen ab, wendet einen "
                            "altersabhängigen Beitragssatz an und teilt den Beitrag 50/50. Reale "
                            "Eintrittsschwellen, versicherter Lohn und Reglement deiner PK können "
                            "abweichen."
                        ),
                    ),
                    _assumption(
                        (
                            "2. Säule · gewählte Verzinsung"
                            if pillar2_mode == "custom"
                            else "2. Säule · Verzinsung der Schätzung"
                        ),
                        (
                            "Du kannst die Verzinsung im Modus «Eigene PK-Werte» anhand deines "
                            "Pensionskassenausweises festlegen. Deine angegebenen monatlichen "
                            "Arbeitnehmer- und Arbeitgeberbeiträge werden auf Jahreswerte "
                            "hochgerechnet; Startguthaben und Beiträge werden mit deinem "
                            f"gewählten Satz von {pillar2_return:.2%} pro Jahr verzinst."
                            if pillar2_mode == "custom"
                            else f"Die vereinfachte BVG-Schätzung verwendet fest "
                            f"{pillar2_return:.0%} pro Jahr. Dieser Wert ist nicht in diesem "
                            "Modus änderbar und muss nicht dem Zinssatz deiner Pensionskasse "
                            "entsprechen. Für einen eigenen Zinssatz wähle links «Eigene "
                            "PK-Werte»."
                        ),
                    ),
                    _assumption(
                        "3a und 3b · Rendite & Einzahlungen",
                        f"Für beide Säulen gilt deine gewählte Rendite von {assumed_return:.0%} "
                        "pro Jahr. Einzahlungen werden jährlich zu Jahresbeginn gutgeschrieben "
                        "und danach verzinst; die nominalen Beiträge werden nicht automatisch "
                        "mit der Inflation erhöht. 3a-Einzahlungen sind im Modell auf "
                        f"{money(config.PILLAR3A_ANNUAL_MAX)} pro Jahr begrenzt.",
                    ),
                    _assumption(
                        "AHV-Rente · vereinfachte Schätzung",
                        "Die Schätzung interpoliert nur zwischen Mindest- und Maximalrente der "
                        "Vollrentenskala 44 und kürzt proportional nach den eingegebenen "
                        "Beitragsjahren. Sie berücksichtigt weder die genaue Rententabelle noch "
                        "Erziehungs-/Betreuungsgutschriften, Einkommensteilung, Beitragslücken "
                        "im IK oder Übergangszuschläge. Die 13. Altersrente ist im Jahresbetrag "
                        "enthalten. Die AHV wird separat als Renteneinkommen angezeigt und nicht "
                        "zum Vorsorgekapital addiert. Im Nominalmodus wird die Schätzung in "
                        "heutigen CHF vereinfachend mit der Inflation hochgerechnet; in der "
                        "Realansicht bleibt sie in heutiger Kaufkraft.",
                        [
                            _link("AHV-Merkblatt 3.01", ahv.OFFICIAL_LEAFLET_URL),
                            " · ",
                            _link("Information zur 13. AHV-Rente", AHV_13TH_PENSION_URL),
                        ],
                    ),
                    _assumption(
                        "Inflation & Kaufkraft",
                        f"Die Modellannahme beträgt {config.INFLATION_RATE:.0%} Inflation pro "
                        "Jahr. "
                        + (
                            "In der realen Ansicht wird die jährliche Inflation von den "
                            "zukünftigen Kapitalwerten abgezogen. Die Werte zeigen die Kaufkraft "
                            "in heutigen CHF."
                            if real
                            else "In der nominalen Ansicht wird Inflation nicht abgezogen. Die "
                            "Werte sind zukünftige CHF und entsprechen daher nicht der heutigen "
                            "Kaufkraft."
                        ),
                    ),
                    _assumption(
                        "Nicht berücksichtigt",
                        "Die AHV-Schätzung ist keine offizielle Rentenberechnung. Lohn- und "
                        "Beitragsentwicklung, Änderungen von Rendite oder PK-Reglement, Gebühren "
                        "sowie Steuern auf Vorsorgebeiträge, Renten und Auszahlungen werden "
                        "nicht berechnet. Falls du Brutto eingibst, ist auch die Umrechnung zum "
                        "Nettolohn nur eine grobe kantonale Schätzung: AHV/IV/EO "
                        f"{config.AHV_IV_EO_RATE:.1%}, ALV {config.ALV_RATE:.1%} und NBU "
                        f"{config.NBU_RATE:.1%} (Annahme) bis "
                        f"{money(config.ALV_MAX_INSURED_ANNUAL_SALARY)} pro Jahr, Krankenkasse "
                        f"{money(config.AVERAGE_HEALTH_INSURANCE_MONTHLY)}/Monat.",
                    ),
                ],
                cols={"base": 1, "md": 2},
                spacing="md",
            ),
            dmc.Alert(
                "Die Projektion basiert auf vereinfachten Annahmen und ersetzt keine "
                "individuelle Finanz- oder Steuerberatung. BVG- und 3a-Werte können je nach "
                "Vorsorgeplan und geltenden gesetzlichen Limiten abweichen.",
                title="Modell statt Beratung",
                color="gray",
                variant="light",
                radius="lg",
            ),
        ],
        gap="md",
    )

    return overview, pension, assumptions, ""
