"""Rendering of the results section (cards, charts, assumptions)."""

from typing import List, Optional, Tuple

from dash import html

from personal_finance import config
from personal_finance.core import ahv
from personal_finance.core.projection import project_balance
from personal_finance.dashboard.components import (
    chart_card,
    metric_card,
    money,
)
from personal_finance.dashboard.figures import (
    comparison_figure,
    composition_figure,
    projection_figure,
)


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
        project_balance(
            pillar2.annual_contribution_total,
            years,
            pillar2_return,
            initial_2,
            inflation_rate,
        )[-1]
        + project_balance(
            pillar3a.annual_savings,
            years,
            assumed_return,
            initial_3a,
            inflation_rate,
        )[-1]
        + project_balance(
            pillar3b.annual_savings,
            years,
            assumed_return,
            initial_3b,
            inflation_rate,
        )[-1]
    )
    ages = list(range(current_age, retirement_age + 1))
    pillar2_values = project_balance(
        pillar2.annual_contribution_total,
        years,
        pillar2_return,
        initial_2,
        inflation_rate,
    )
    pillar3a_values = project_balance(
        pillar3a.annual_savings,
        years,
        assumed_return,
        initial_3a,
        inflation_rate,
    )
    pillar3b_values = project_balance(
        pillar3b.annual_savings,
        years,
        assumed_return,
        initial_3b,
        inflation_rate,
    )
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
                        metric_card(
                            "Projiziertes Vorsorgekapital",
                            money(total),
                            f"bei Pensionierung mit {retirement_age} Jahren · "
                            f"{'heutige Kaufkraft' if display_basis == 'real' else 'nominal'}",
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
                                metric_card(
                                    "Vereinfachte AHV-Schätzung",
                                    (
                                        money(ahv_estimated_display)
                                        if ahv_estimated_display is not None
                                        else "Angaben fehlen"
                                    ),
                                    (
                                        f"{money(ahv_estimated_display * 13)} pro Jahr inkl. 13. Rente · "
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
                        chart_card(
                            "So kann dein Vermögen wachsen",
                            f"Kumulierte Modellprojektion · {basis_detail}",
                            growth,
                            height=390,
                            class_name="growth-card",
                        ),
                        chart_card(
                            "Einzahlungen & Wachstum",
                            f"Verhältnis der Beiträge zum Zuwachs · {basis_detail}",
                            composition,
                            height=300,
                            class_name="composition-card",
                        ),
                    ],
                    className="charts-grid",
                ),
                chart_card(
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
                                                html.Strong(money(initial_2), className="detail-value"),
                                            ],
                                            className="detail-row",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Startguthaben 3a", className="detail-label"),
                                                html.Strong(money(initial_3a), className="detail-value"),
                                            ],
                                            className="detail-row",
                                        ),
                                        html.Div(
                                            [
                                                html.Span("Startguthaben 3b", className="detail-label"),
                                                html.Strong(money(initial_3b), className="detail-value"),
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
                                                html.Strong(money(monthly_savings), className="detail-value"),
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
                                                    money(income - monthly_savings),
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
                                                    f"{money(config.PILLAR3A_ANNUAL_MAX)} pro Jahr begrenzt."
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
                                                    "Schätzung: AHV/IV/EO "
                                                    f"{config.AHV_IV_EO_RATE:.1%}, ALV "
                                                    f"{config.ALV_RATE:.1%} und NBU "
                                                    f"{config.NBU_RATE:.1%} (Annahme) bis "
                                                    f"{money(config.ALV_MAX_INSURED_ANNUAL_SALARY)} "
                                                    "pro Jahr, Krankenkasse "
                                                    f"{money(config.AVERAGE_HEALTH_INSURANCE_MONTHLY)}"
                                                    "/Monat."
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
