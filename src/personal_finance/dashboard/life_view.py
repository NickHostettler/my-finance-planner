"""Life phases and family in the dashboard (#33): the inputs as phases and the result tab."""

import dataclasses
import math
from dataclasses import dataclass
from typing import Any, Callable, List, Mapping, Optional, Sequence, Tuple

import dash_mantine_components as dmc
from dash import html

from personal_finance import config
from personal_finance.core import ahv
from personal_finance.core.family import Family, FamilyYear, family_years
from personal_finance.core.life_phases import BY_WORKLOAD, LifePhase, validate_phases
from personal_finance.core.part_time import PensionGap, Pillar2Setup, compare_with_full_time
from personal_finance.core.projection import deflate
from personal_finance.dashboard.components import chart_card, metric_card, money, section_card
from personal_finance.dashboard.figures import gap_figure, phases_figure
from personal_finance.storage import browser_store

ROWS = range(1, browser_store.LIFE_PHASE_ROWS + 1)


def used_rows(workloads: Sequence[Any]) -> int:
    """How many phase rows are used: the leading rows with a workload."""
    count = 0
    for workload in workloads:
        if workload is None or workload == "":
            break
        count += 1
    return count


def _whole(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and float(value).is_integer()
    )


def row_titles(current_age: Any, to_ages: Sequence[Any], visible: int) -> List[str]:
    """Titles like "Phase 2 · ab 34"; the last visible phase lasts until retirement."""
    titles = []
    start: Optional[int] = int(current_age) if _whole(current_age) else None
    for row, to_age in enumerate(to_ages, start=1):
        title = f"Phase {row}" + ("" if start is None else f" · ab {start}")
        if row == visible:
            title += " bis zur Pensionierung"
        titles.append(title)
        start = int(to_age) + 1 if _whole(to_age) else None
    return titles


def phases_from_values(values: Mapping[str, Any], current_age: int, retirement_age: int):
    """The life phases from the stored inputs (``browser_store`` field names).

    The first phase starts today, each next one the year after the previous «bis Alter», the
    last one lasts until retirement. Workloads in percent become decimals. Incomes are monthly
    on the basis of the income input. Raises ``ValueError`` with a German message.
    """
    rows = [
        {part: values.get(f"life_{row}_{part}") for part in browser_store.LIFE_ROW_PARTS}
        for row in ROWS
    ]
    count = used_rows([row["workload"] for row in rows])
    if count == 0:
        raise ValueError("Bitte lege mindestens eine Lebensphase an oder wähle eine Vorlage.")
    phases = []
    start = current_age
    for number, row in enumerate(rows[:count], start=1):
        last = number == count
        if last:
            to_age = retirement_age - 1
        else:
            to_age = row["to"]
            if to_age is None:
                raise ValueError(
                    f"Phase {number}: Bitte gib an, bis zu welchem Alter die Phase dauert."
                )
            if to_age < start:
                raise ValueError(
                    f"Phase {number}: Das Alter «bis» ({to_age}) muss mindestens {start} sein."
                )
            if to_age >= retirement_age - 1:
                raise ValueError(
                    f"Phase {number}: Das Alter «bis» ({to_age}) muss vor der letzten Phase "
                    f"enden, also spätestens bei {retirement_age - 2}."
                )
        workload = row["workload"]
        phases.append(
            LifePhase(
                start,
                max(start, to_age),
                workload / 100 if isinstance(workload, (int, float)) else workload,
                row["income"],
                child_costs=row["costs"],
            )
        )
        if not last:
            start = to_age + 1
    return phases


def child_birth_ages(values: Mapping[str, Any]) -> Tuple[int, ...]:
    """The parent's ages at the births from the filled-in child fields."""
    return tuple(
        values[f"life_child_{child}"]
        for child in range(1, browser_store.LIFE_CHILDREN + 1)
        if values.get(f"life_child_{child}") is not None
    )


# --- the plan with life phases -------------------------------------------------------------


@dataclass(frozen=True)
class LifeOutcome:
    """The plan with life phases and family, compared with full time."""

    phases: Tuple[LifePhase, ...]  # incomes as entered (basis of the income input)
    gap: PensionGap
    family: Tuple[FamilyYear, ...]
    birth_ages: Tuple[int, ...]
    coordination: str

    @property
    def contributions(self) -> Tuple[List[float], List[float], List[float]]:
        """What the projection pays in each year: 2nd pillar, 3a, 3b."""
        years = self.gap.plan
        return (
            [year.pillar2 for year in years],
            [year.pillar3a for year in years],
            [year.pillar3b for year in years],
        )

    def note(self) -> str:
        """One sentence for the overview."""
        gap = self.gap.capital_gap
        change = (
            f"{money(gap)} weniger Vorsorgekapital"
            if gap >= 0
            else f"{money(-gap)} mehr Vorsorgekapital"
        )
        return (
            f"Mit deinen Lebensphasen gerechnet: {change} bei Pensionierung als bei 100 %. "
            "Details im Tab «Lebensphasen»."
        )


def plan_life(
    values: Mapping[str, Any],
    *,
    current_age: int,
    retirement_age: int,
    monthly_net_income: float,
    to_net: Callable[[Any], Any],
    salary_growth: float,
    pillar3a_monthly: float,
    pillar3b_monthly: float,
    pillar2_mode: str,
    own_total: float,
    initial: Tuple[float, float, float],
    returns: Tuple[float, float],
    ahv_average_income: Optional[float],
    ahv_contribution_years: int,
) -> LifeOutcome:
    """The plan from the inputs (``browser_store`` field names). Raises ``ValueError``.

    ``to_net`` turns a monthly phase income (basis of the income input) into a net income.
    """
    phases = validate_phases(
        phases_from_values(values, current_age, retirement_age), current_age, retirement_age
    )
    net_phases = [dataclasses.replace(phase, income=to_net(phase.income)) for phase in phases]
    births = child_birth_ages(values)
    coordination = values["life_coordination"]
    gap = compare_with_full_time(
        net_phases,
        current_age=current_age,
        retirement_age=retirement_age,
        base_monthly_income=monthly_net_income,
        salary_growth=salary_growth,
        pillar3a_monthly=pillar3a_monthly,
        pillar3b_monthly=pillar3b_monthly,
        setup=Pillar2Setup(pillar2_mode, coordination, own_total),
        initial=initial,
        returns=returns,
        ahv_average_income=ahv_average_income,
        ahv_contribution_years=ahv_contribution_years,
        child_birth_ages=births,
        credit_share=0.5 if values["life_credit_share"] == "half" else 1.0,
    )
    yearly = gap.yearly
    family = family_years(
        yearly.ages,
        yearly.monthly_income,
        yearly.child_costs,
        [year.pillar3a + year.pillar3b for year in gap.plan],
        Family(
            births,
            values["life_role"],
            values["life_child_allowance"],
            values["life_education_allowance"],
        ),
    )
    return LifeOutcome(tuple(phases), gap, family, births, coordination)


# --- the "Lebensphasen" tab ------------------------------------------------------------------


def _detail_row(label: str, value: str):
    return html.Div(
        [
            html.Span(label, className="detail-label"),
            html.Strong(value, className="detail-value"),
        ],
        className="detail-row",
    )


def age_ranges(ages: Sequence[int]) -> str:
    """Ages as ranges: [34, 35, 36, 40] -> "34–36, 40"."""
    ranges: List[List[int]] = []
    for age in ages:
        if ranges and age == ranges[-1][1] + 1:
            ranges[-1][1] = age
        else:
            ranges.append([age, age])
    return ", ".join(str(a) if a == b else f"{a}–{b}" for a, b in ranges)


def planning_hint():
    """Shown while no life phases are planned."""
    return section_card(
        "Lebensphasen planen",
        "",
        [
            dmc.Text(
                "Teilzeit, ein Unterbruch oder Kinder? Wähle links unter «Lebensphasen & "
                "Familie» «Phasen planen». Dann siehst du hier, wie sich das auf deine "
                "Pensionskasse, die Säule 3a und die AHV auswirkt, verglichen mit 100 % bis zur "
                "Pensionierung.",
                size="sm",
            ),
            dmc.Text(
                "Ohne Lebensphasen bleiben alle anderen Ergebnisse unverändert.",
                size="xs",
                c="dimmed",
                mt="xs",
            ),
        ],
        class_name="life-intro-card",
    )


def error_message(message: str):
    return html.Div(
        [html.Strong("Lebensphasen: Eingaben prüfen"), html.P(message)],
        className="validation-message",
    )


def _phase_table(outcome: LifeOutcome):
    def cell(value):
        return dmc.TableTd(value)

    rows = []
    for phase in outcome.phases:
        years = [year for year in outcome.gap.plan if phase.from_age <= year.age <= phase.to_age]
        if not years:
            continue
        first = years[0]
        start = max(phase.from_age, first.age)
        rows.append(
            dmc.TableTr(
                [
                    cell(f"{start}–{phase.to_age}"),
                    cell(f"{phase.workload:.0%}"),
                    cell(money(first.annual_income / 12)),
                    cell(
                        "eigene Werte"
                        if first.insured_salary is None
                        else money(first.insured_salary)
                    ),
                    cell(money(first.pillar2)),
                    cell(money(first.pillar3a_limit)),
                ]
            )
        )
    header = ["Alter", "Pensum", "Netto/Mt.", "Versich. Lohn", "PK pro Jahr", "3a-Limit"]
    return section_card(
        "Pro Phase",
        "Werte im ersten Jahr der Phase · nominal",
        [
            dmc.TableScrollContainer(
                dmc.Table(
                    [
                        dmc.TableThead(dmc.TableTr([dmc.TableTh(text) for text in header])),
                        dmc.TableTbody(rows),
                    ],
                    striped=True,
                    fz="sm",
                    className="phase-table",
                ),
                minWidth=360,
            ),
            dmc.Text(
                "Versicherter Lohn: Jahreslohn über der Eintrittsschwelle von "
                f"{money(config.PILLAR2_MIN_SALARY)} minus Koordinationsabzug "
                + (
                    "(an dein Pensum angepasst)."
                    if outcome.coordination == BY_WORKLOAD
                    else f"({money(config.PILLAR2_COORDINATION_DEDUCTION)}, auch bei Teilzeit)."
                )
                + " Ohne Pensionskasse gilt die grosse 3a.",
                size="xs",
                c="dimmed",
                mt="sm",
            ),
        ],
        class_name="phase-table-card",
    )


def _family_card(outcome: LifeOutcome):
    years = outcome.family
    allowances = sum(year.allowances for year in years)
    leave = sum(year.leave_allowance for year in years)
    loss = sum(year.leave_loss for year in years)
    costs = sum(year.child_costs for year in years)
    rows = [
        _detail_row("Familienzulagen bis zur Pensionierung", money(allowances)),
        _detail_row("Erwerbsersatz (EO) bei Geburten", money(leave)),
        _detail_row("Lohnausfall trotz EO", money(loss)),
        _detail_row("Kinderkosten bis zur Pensionierung", money(costs)),
        _detail_row(
            "Jahre mit AHV-Erziehungsgutschrift",
            str(outcome.gap.education_credit_years)
            if outcome.gap.ahv_plan is not None
            else "AHV-Angaben fehlen",
        ),
    ]
    return section_card(
        "Familie",
        "Summen ab heute, nominal · Zulagen nach Alter der Kinder",
        [html.Div(rows, className="detail-list")],
        class_name="family-card",
    )


def _hints(outcome: LifeOutcome) -> List[Any]:
    gap = outcome.gap
    alerts = []
    short = [year for year in outcome.family if year.costs_exceed_income]
    if short:
        alerts.append(
            dmc.Alert(
                f"Mit {age_ranges([year.age for year in short])} reichen Einkommen und Zulagen "
                "nicht für Kinderkosten und Sparen (3a, 3b): Es fehlen bis zu "
                f"{money(max(-year.left_after_savings for year in short))} pro Jahr. Prüfe die "
                "Kinderkosten oder spare in diesen Jahren weniger.",
                title="Ausgaben höher als das Einkommen",
                color="yellow",
                variant="light",
                radius="lg",
                className="life-shortfall-hint",
            )
        )
    tips = []
    if gap.capital_gap > 0.5:
        tips.append(
            "Ein Einkauf in die Pensionskasse kann die Lücke verkleinern und ist steuerlich "
            "abziehbar. Wie viel möglich ist, steht auf deinem PK-Ausweis."
        )
        if outcome.coordination != BY_WORKLOAD:
            tips.append(
                "Frag deine Pensionskasse, ob sie den Koordinationsabzug ans Pensum anpasst. "
                "Dann ist bei Teilzeit mehr Lohn versichert (links umstellbar)."
            )
    if any(year.annual_income > 0 and not year.has_pension_fund for year in gap.plan):
        tips.append(
            "In Jahren ohne Pensionskasse darfst du mehr in die Säule 3a einzahlen: 20 % des "
            f"Erwerbseinkommens, höchstens {money(config.PILLAR3A_LARGE_MAX)}."
        )
    if gap.years_without_income:
        tips.append(
            f"Ohne Erwerb (mit {age_ranges(gap.years_without_income)}) zahlst du die "
            "AHV-Beiträge selbst als Nichterwerbstätige, sonst fehlen Beitragsjahre. "
            "Verheiratete sind gedeckt, wenn der Partner mindestens den doppelten "
            "Mindestbeitrag zahlt."
        )
    if tips:
        alerts.append(
            dmc.Alert(
                dmc.List([dmc.ListItem(tip) for tip in tips], size="sm", spacing=4),
                title="Hinweise, keine Beratung",
                color="gray",
                variant="light",
                radius="lg",
                className="life-tips",
            )
        )
    return alerts


def life_section(
    outcome: Optional[LifeOutcome],
    error: Optional[str] = None,
    display_basis: str = "nominal",
):
    """Contents of the tab: hint without life phases, the error, or the comparison."""
    if error is not None:
        return error_message(error)
    if outcome is None:
        return planning_hint()

    gap = outcome.gap
    real = display_basis == "real"
    inflation = config.INFLATION_RATE if real else 0
    basis = "heutige Kaufkraft" if real else "nominal"
    current_age = outcome.phases[0].from_age  # the first phase starts today
    ages = list(range(current_age, current_age + len(gap.plan_paths.pillar2)))

    def totals(paths) -> List[float]:
        return deflate(
            [sum(values) for values in zip(paths.pillar2, paths.pillar3a, paths.pillar3b)],
            inflation,
        )

    plan_total, full_total = totals(gap.plan_paths), totals(gap.full_time_paths)
    years = len(gap.plan)

    def ahv_shown(monthly_today: Optional[float]) -> Optional[float]:
        return ahv.project_pension_basis(monthly_today, years, config.INFLATION_RATE, display_basis)

    ahv_plan, ahv_full = ahv_shown(gap.ahv_plan), ahv_shown(gap.ahv_full_time)
    capital_gap = full_total[-1] - plan_total[-1]
    metrics = dmc.SimpleGrid(
        [
            metric_card(
                "Vorsorgelücke bei Pensionierung",
                money(capital_gap),
                f"Mit Plan {money(plan_total[-1])} · bei 100 % {money(full_total[-1])} · {basis}",
                "dark",
                "Δ",
            ),
            metric_card(
                "AHV-Lücke pro Monat",
                "Angaben fehlen" if ahv_plan is None else money(ahv_full - ahv_plan),
                "Für die AHV links unter «AHV-Rente» das Einkommen angeben"
                if ahv_plan is None
                else f"Mit Plan {money(ahv_plan)} · bei 100 % {money(ahv_full)} · "
                "inkl. Erziehungsgutschriften",
                "green",
                "AHV",
            ),
        ],
        cols={"base": 1, "xs": 2},
        spacing="md",
    )
    yearly = gap.yearly
    charts = dmc.Grid(
        [
            dmc.GridCol(
                chart_card(
                    "Pensum und Einkommen",
                    "Einkommen pro Monat, nominal mit Lohnzunahme · ★ Geburt",
                    phases_figure(
                        yearly.ages, yearly.workload, yearly.monthly_income, outcome.birth_ages
                    ),
                    height=300,
                    class_name="phases-card",
                ),
                span={"base": 12, "lg": 6},
            ),
            dmc.GridCol(
                chart_card(
                    "Alterskapital mit Plan und bei 100 %",
                    f"2. Säule, 3a und 3b · gestrichelt bei 100 % · {basis}",
                    gap_figure(ages, plan_total, full_total),
                    height=300,
                    class_name="gap-card",
                ),
                span={"base": 12, "lg": 6},
            ),
        ],
        gap="md",
    )
    return dmc.Stack(
        [
            metrics,
            charts,
            dmc.Grid(
                [
                    dmc.GridCol(_phase_table(outcome), span={"base": 12, "lg": 7}),
                    dmc.GridCol(_family_card(outcome), span={"base": 12, "lg": 5}),
                ],
                gap="md",
            ),
            *_hints(outcome),
        ],
        gap="md",
    )


# --- editing the rows: templates, add and remove ----------------------------------------------

FULL = "life-template-full"
KIDS = "life-template-kids"
BREAK = "life-template-break"
ADD = "life-add-button"
REMOVE = "life-remove-button"
PLAN = "life-plan-input"

Row = Tuple[Any, Any, Any, Any]  # until age, workload in %, income per month, child costs
_EMPTY: Row = (None, None, None, None)


def _rounded(amount: Optional[float]) -> Optional[float]:
    return None if amount is None else round(amount)


def _template(name: str, start: int, last_year: int, income: Optional[float]):
    """The rows of a template, or ``None`` if there are too few years until retirement."""

    def share(factor: float) -> Optional[float]:
        return None if income is None else _rounded(income * factor)

    if name == FULL:
        return [(None, 100, share(1), None)]
    if name == KIDS:
        # Full time for 3 years, 60 % for 7 years while the children are small, then 80 %.
        rows = [(start + 2, 100, share(1), None), (start + 9, 60, share(0.6), None)]
        rows.append((None, 80, share(0.8), None))
    else:
        # Full time for 3 years, a break of 2 years, then full time again.
        rows = [(start + 2, 100, share(1), None), (start + 4, 0, 0, None)]
        rows.append((None, 100, share(1), None))
    if rows[-2][0] > last_year - 1:
        return None
    return rows


def edit_rows(
    action: Any,
    rows: Sequence[Row],
    plan: Any,
    current_age: Any,
    retirement_age: Any,
    monthly_income: Optional[float],
) -> Optional[List[Row]]:
    """The phase rows after a template, «+ Phase» or «− Phase»; ``None``: nothing changes.

    Switching life phases on fills in full time while no phase exists yet, so that loading a
    scenario keeps its phases. ``monthly_income`` is the income of the income input per month
    (``None`` if not known): templates use it times the workload.
    """
    if not (_whole(current_age) and _whole(retirement_age)) or retirement_age <= current_age:
        return None
    start, last_year = int(current_age), int(retirement_age) - 1
    used = used_rows([row[1] for row in rows])
    if action == PLAN:
        if plan != "on" or used:
            return None
        action = FULL
    if action in (FULL, KIDS, BREAK):
        template = _template(action, start, last_year, monthly_income)
        if template is None:
            return None
        return template + [_EMPTY] * (len(rows) - len(template))
    new = [tuple(row) for row in rows]
    if action == REMOVE:
        if used < 2:
            return None
        new[used - 1] = _EMPTY
        return new
    # ADD: split the last phase in the middle of its years.
    if used in (0, len(rows)):
        return None
    begin = start
    for row in rows[: used - 1]:
        if not _whole(row[0]):
            return None
        begin = int(row[0]) + 1
    middle = begin + (last_year - begin) // 2
    if middle >= last_year:  # the last phase has only one year left (or none)
        return None
    last = rows[used - 1]
    new[used - 1] = (middle, last[1], last[2], last[3])
    new[used] = (None, last[1], last[2], last[3])
    return new
