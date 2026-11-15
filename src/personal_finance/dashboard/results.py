"""Rendering of the results tabs: overview, pension details and model assumptions."""

from typing import Optional, Tuple

import dash_mantine_components as dmc
from dash import html

from personal_finance import config
from personal_finance.core import ahv
from personal_finance.core.projection import deflate, project_balance
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
    ahv_contribution_years: int,
    display_basis: str = "nominal",
    salary_growth: float = 0,
    paths=None,
    purchase_note: Optional[str] = None,
    per_year=None,
    ahv_monthly_today: Optional[float] = None,
    life_note: Optional[str] = None,
    ahv_note: Optional[str] = None,
) -> Tuple[object, object, object, str]:
    """Return the overview, pension and assumption tabs and the calculation notice.

    ``paths`` (nominal 2nd pillar, 3a and 3b balances per year) replaces the projection of
    the savings plan, e.g. with the withdrawals for a planned home purchase; then
    ``purchase_note`` explains it in the overview. With life phases (#33) ``per_year`` gives
    the contributions of each year (2nd pillar, 3a, 3b) and ``life_note`` explains them.
    ``ahv_monthly_today`` is the AHV estimate per month in today's CHF (``None``: no AHV
    inputs); ``ahv_note`` adds to the AHV card, e.g. the cap of a married couple (v1.3).
    """
    pillar2 = analysis.pillar2
    years = analysis.years_to_retirement
    real = display_basis == "real"
    inflation_rate = config.INFLATION_RATE if real else 0
    basis_detail = (
        f"Reale Werte in heutiger Kaufkraft · {config.INFLATION_RATE:.0%} Inflation pro Jahr"
        if real
        else "Nominale CHF · ohne Inflationsbereinigung"
    )
    ahv_estimated_display = ahv.project_pension_basis(
        ahv_monthly_today,
        years,
        config.INFLATION_RATE,
        display_basis,
    )
    if paths is None:
        pillar2_values = project_balance(
            pillar2.contributions(), years, pillar2_return, initial_2, inflation_rate
        )
        pillar3a_values = project_balance(
            pillar3a.annual_savings, years, assumed_return, initial_3a, inflation_rate
        )
        pillar3b_values = project_balance(
            pillar3b.annual_savings, years, assumed_return, initial_3b, inflation_rate
        )
    else:
        pillar2_values = deflate(paths.pillar2, inflation_rate)
        pillar3a_values = deflate(paths.pillar3a, inflation_rate)
        pillar3b_values = deflate(paths.pillar3b, inflation_rate)
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
        per_year=per_year,
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
            *([dmc.Text(life_note, className="results-subtitle life-note")] if life_note else []),
            *(
                [dmc.Text(purchase_note, className="results-subtitle purchase-note")]
                if purchase_note
                else []
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
                        f"AG {money(pillar2.annual_contribution_employer / 12)}/Monat"
                        + (
                            f" · wächst mit dem Lohn ({salary_growth:.1%}/Jahr)"
                            if salary_growth
                            else ""
                        ),
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
                                        + (f" · {ahv_note}" if ahv_note else "")
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
                            _detail_row(
                                "Verbleibend nach 3a & 3b", money(income - monthly_savings)
                            ),
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
                            "die BVG-Grenzbeträge ab 1.1.2027 für Eintrittsschwelle, "
                            "Koordinationsabzug und koordinierten Lohn vom modellierten "
                            "Jahresnettoeinkommen ab, wendet einen altersabhängigen Beitragssatz "
                            "an und teilt den Beitrag 50/50. Da das Tool nicht mit einem separat "
                            "erfassten Bruttolohn und dem Reglement deiner PK rechnet, kann die "
                            "Schätzung von deiner tatsächlichen Vorsorge abweichen."
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
                        "Lohnzunahme",
                        f"Dein Lohn steigt im Modell um {salary_growth:.1%} pro Jahr (nominal, "
                        "einstellbar unter «Einkommen & Alter»). Damit steigen die Beiträge an "
                        "die 2. Säule im gleichen Verhältnis. In der vereinfachten "
                        "BVG-Schätzung wächst der versicherte Lohn; Koordinationsabzug und "
                        "Beitragssatz bleiben gleich. 3a- und "
                        "3b-Beträge, die AHV-Schätzung und die Tragbarkeit eines Hauskaufs "
                        "rechnen weiter mit den heutigen Angaben.",
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
                        "Wohneigentum · Eigenmittel und Tragbarkeit",
                        f"Mindestens {config.HOME_MIN_EQUITY_RATE:.0%} des Kaufpreises müssen "
                        f"Eigenmittel sein, davon {config.HOME_MIN_HARD_EQUITY_RATE:.0%} «hart», "
                        "also nicht aus der Pensionskasse (Erspartes, Wertschriften, Säule 3a). "
                        "Die 2. Hypothek (der Teil über ⅔ des Kaufpreises) wird in höchstens "
                        f"{config.HOME_AMORTISATION_MAX_YEARS} Jahren und spätestens bis zur "
                        "Pensionierung amortisiert. Tragbar ist ein Kauf, wenn kalkulatorischer "
                        f"Zins ({config.HOME_IMPUTED_INTEREST_RATE:.0%}, einstellbar), "
                        f"{config.HOME_MAINTENANCE_RATE:.0%} Unterhalt und Amortisation höchstens "
                        "⅓ des Bruttoeinkommens ausmachen; ab "
                        f"{config.HOME_TIGHT_COST_TO_INCOME:.0%} gilt er als knapp. "
                        f"Kaufnebenkosten von {config.HOME_PURCHASE_COSTS_RATE:.0%} sind eine "
                        "Modellannahme und werden aus Erspartem oder 3a bezahlt. Der "
                        "Belehnungswert der Bank ist dem Kaufpreis gleichgesetzt. Die "
                        "Mindestanforderungen stammen aus den Richtlinien der Bankiervereinigung "
                        "(gültig ab 1.1.2025), die übrigen Werte aus der üblichen Bankpraxis. "
                        f"Stand {config.HOME_RULES_AS_OF}.",
                        [_link("FINMA zu den SBVg-Richtlinien", config.HOME_SBVG_SOURCE_URL)],
                    ),
                    _assumption(
                        "Wohneigentum · Vorbezug aus 2. Säule und 3a (WEF)",
                        "Aus der Pensionskasse sind mindestens "
                        f"{money(config.WEF_PILLAR2_MIN_AMOUNT)} pro Vorbezug nötig, höchstens "
                        f"alle {config.WEF_MIN_YEARS_BETWEEN_WITHDRAWALS} Jahre und bis "
                        f"{config.WEF_PILLAR2_DEADLINE_YEARS} Jahre vor der Pensionierung. Ab "
                        f"Alter {config.WEF_PILLAR2_HALF_RULE_AGE} ist höchstens das Guthaben im "
                        f"Alter {config.WEF_PILLAR2_HALF_RULE_AGE} oder die Hälfte des aktuellen "
                        "Guthabens verfügbar (der höhere Betrag); ohne diese Angabe rechnet das "
                        "Modell vorsichtig mit der Hälfte. Einkäufe der letzten "
                        f"{config.WEF_BUY_IN_LOCK_YEARS} Jahre dürfen nicht vorbezogen werden. "
                        "Das 3a-Guthaben lässt sich ganz beziehen. Beim Planen eines Kaufs füllt "
                        "die App die Höchstbeträge zum Kaufalter ein: zuerst das freie Vermögen "
                        "(3b), dann 3a, zuletzt die Pensionskasse, und nur so viel, wie Kaufpreis "
                        "und Kaufnebenkosten brauchen. Das ist ein Startwert, keine Empfehlung; "
                        "du kannst weniger einsetzen. Bezogenes Geld fehlt in der "
                        "Prognose ab dem Kauf; eine Rückzahlung, die Steuer auf den Bezug und "
                        "tiefere Leistungen bei Invalidität und Tod sind nicht berechnet. Das "
                        "Reglement deiner Pensionskasse kann strenger sein. "
                        f"Stand {config.HOME_RULES_AS_OF}.",
                        [_link("BVG Art. 30c (Fedlex)", config.WEF_BVG_SOURCE_URL)],
                    ),
                    _assumption(
                        "Wohneigentum · Hypothek in der Prognose",
                        "Die Immobilie bleibt im Modell zum Kaufpreis, ohne Wertveränderung. Die "
                        "Zinskosten rechnet es mit deinem effektiven Hypothekarzins (Standard "
                        f"{config.HOME_MORTGAGE_RATE:.0%}) und nimmt an, dass du Zins, Unterhalt "
                        "und Amortisation aus dem laufenden Einkommen bezahlst. Bei indirekter "
                        "Amortisation fliesst der Betrag in ein verpfändetes 3a-Konto, soweit "
                        f"neben deinem 3a-Plan Platz im Limit von "
                        f"{money(config.PILLAR3A_ANNUAL_MAX)} bleibt. Für die Tragbarkeit im "
                        "Alter schätzt das Modell die Rente der 2. Säule mit einem "
                        f"Umwandlungssatz von {config.HOME_RETIREMENT_CONVERSION_RATE:.0%} "
                        "(Modellannahme). Steuern sind nicht berechnet; der Eigenmietwert "
                        f"entfällt ab dem {config.HOME_IMPUTED_RENTAL_VALUE_END}.",
                    ),
                    _assumption(
                        "Lebensphasen · Teilzeit und Unterbrüche",
                        "Phaseneinkommen gelten in heutigen Franken, die Lohnzunahme kommt "
                        "dazu. Versichert ist in der 2. Säule nur ein Jahreslohn über "
                        f"{money(config.PILLAR2_MIN_SALARY)}; davon geht der Koordinationsabzug "
                        f"von {money(config.PILLAR2_COORDINATION_DEDUCTION)} ab, gesetzlich "
                        "auch bei Teilzeit voll, wahlweise ans Pensum angepasst. Eigene "
                        "PK-Beiträge ändern im Verhältnis zum Einkommen (Modellannahme). Ohne "
                        "Pensionskasse darfst du in die Säule 3a bis "
                        f"{config.PILLAR3A_LARGE_RATE:.0%} des Erwerbseinkommens einzahlen, "
                        f"höchstens {money(config.PILLAR3A_LARGE_MAX)}; ohne Erwerb gar nicht. "
                        "Für die AHV senken tiefere Einkommen den Durchschnitt; für jedes Jahr "
                        "mit einem Kind unter 16 zählt eine Erziehungsgutschrift von "
                        f"{money(ahv.EDUCATION_CREDIT)} (bei Ehepaaren hälftig). Fehlende "
                        "Beitragsjahre ohne Erwerb rechnet das Modell nicht.",
                        [
                            _link(
                                "Erziehungsgutschriften (Merkblatt 1.07)", ahv.EDUCATION_CREDIT_URL
                            )
                        ],
                    ),
                    _assumption(
                        "Familie · Zulagen und Erwerbsersatz",
                        f"Kinderzulage mindestens {money(config.CHILD_ALLOWANCE_MONTHLY)} pro "
                        f"Monat bis {config.CHILD_ALLOWANCE_UNTIL_AGE}, Ausbildungszulage "
                        f"mindestens {money(config.EDUCATION_ALLOWANCE_MONTHLY)} bis höchstens "
                        f"{config.EDUCATION_ALLOWANCE_UNTIL_AGE}; die Kantone zahlen oft mehr. "
                        "Das Modell rechnet in ganzen Jahren und nimmt an, dass Kinder ab 16 "
                        "in Ausbildung sind. Bei einer Geburt zahlt die EO "
                        f"{config.PARENTAL_ALLOWANCE_RATE:.0%} des Lohns, höchstens "
                        f"{money(config.PARENTAL_ALLOWANCE_DAILY_MAX)} pro Tag, für "
                        f"{config.MATERNITY_LEAVE_DAYS} Tage (Mutter) oder "
                        f"{config.OTHER_PARENT_LEAVE_DAYS} Tage (anderer Elternteil); der Rest "
                        "des Lohns fällt im Modell weg. Kinderkosten steigen mit der Inflation. "
                        f"Stand {config.FAMILY_RULES_AS_OF}.",
                        [
                            _link("Familienzulagen (BSV)", config.FAMILY_ALLOWANCE_SOURCE_URL),
                            _link(
                                "Erwerbsersatz bei Elternschaft (BSV)",
                                config.PARENTAL_LEAVE_SOURCE_URL,
                            ),
                        ],
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
                "individuelle Finanz-, Steuer- oder Hypothekarberatung. BVG- und 3a-Werte "
                "können je nach Vorsorgeplan und geltenden gesetzlichen Limiten abweichen. "
                "Über Hypothek und Vorbezug entscheiden Banken und Pensionskassen "
                "individuell.",
                title="Modell statt Beratung",
                color="gray",
                variant="light",
                radius="lg",
            ),
        ],
        gap="md",
    )

    return overview, pension, assumptions, ""
