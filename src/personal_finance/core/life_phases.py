"""Life phases: the working life in phases with their own workload and income (#30).

Instead of one income until retirement, the working life is split into phases, e.g. full time
until 33, 60 % while the children are small, then 80 %. From the phases follows a value for
each year until retirement (:func:`yearly_plan`), and the projection pays in year by year:

* 2nd pillar: the BVG estimate from the income of each year
  (:func:`estimated_pillar2_by_year`) or the user's own contributions in proportion to the
  income (:func:`scaled_pillar2_by_year`).
* 3a and 3b: the plan amounts or a phase's own amounts.

Model assumptions (MODELLANNAHME):

* Phase incomes are in today's francs, like the income input; the yearly salary growth is
  added on top, counted from today.
* Pillar 3a needs an income from work: in a year without income nothing is paid in.
* Own pension fund contributions change in proportion to the income.

All functions are pure and raise ``ValueError`` with a German message for invalid inputs.
"""

import math
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

from personal_finance import config
from personal_finance.core.pillar_2 import Pillar2Calculator, validate_salary_growth

MAX_PHASES = 10


@dataclass(frozen=True)
class LifePhase:
    """One phase of the working life. Ages inclusive, amounts in CHF per month.

    ``workload`` is a decimal (0.6 = 60 %). ``income`` is the monthly income of the phase on
    the same basis as the income input (net or gross). ``pillar3a`` and ``pillar3b`` are the
    phase's own monthly savings; ``None`` means the amounts of the plan.
    """

    from_age: Any
    to_age: Any
    workload: Any
    income: Any
    pillar3a: Any = None
    pillar3b: Any = None


@dataclass(frozen=True)
class YearlyPlan:
    """The values of each year from today until the year before retirement."""

    ages: Tuple[int, ...]
    workload: Tuple[float, ...]  # decimal
    monthly_income: Tuple[float, ...]  # nominal, with the salary growth
    pillar3a: Tuple[float, ...]  # per year, within the 3a limit
    pillar3b: Tuple[float, ...]  # per year

    @property
    def annual_income(self) -> List[float]:
        return [income * 12 for income in self.monthly_income]


def _age(value: Any, number: int, which: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not float(value).is_integer()
    ):
        raise ValueError(f"Phase {number}: Bitte gib das Alter {which} als ganze Zahl ein.")
    return int(value)


def _amount(value: Any, message: str) -> float:
    if (
        value is None
        or isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(message)
    return float(value)


def _optional_amount(value: Any, message: str) -> Optional[float]:
    return None if value is None else _amount(value, message)


def _checked(phase: Any, number: int) -> LifePhase:
    if not isinstance(phase, LifePhase):
        raise ValueError(f"Phase {number} ist ungültig.")
    from_age = _age(phase.from_age, number, "«von»")
    to_age = _age(phase.to_age, number, "«bis»")
    if to_age < from_age:
        raise ValueError(
            f"Phase {number}: Das Alter «bis» ({to_age}) darf nicht kleiner sein als «von» "
            f"({from_age})."
        )
    workload = _amount(
        phase.workload, f"Phase {number}: Das Pensum muss zwischen 0 und 100 % liegen."
    )
    if workload > 1:
        raise ValueError(f"Phase {number}: Das Pensum muss zwischen 0 und 100 % liegen.")
    income = _amount(phase.income, f"Phase {number}: Das Einkommen muss mindestens 0 CHF betragen.")
    if workload == 0 and income > 0:
        raise ValueError(
            f"Phase {number}: Bei einem Pensum von 0 % gibt es kein Erwerbseinkommen. Setze das "
            "Einkommen auf 0 CHF oder gib ein Pensum an."
        )
    return LifePhase(
        from_age,
        to_age,
        workload,
        income,
        _optional_amount(
            phase.pillar3a, f"Phase {number}: Der 3a-Betrag muss mindestens 0 CHF betragen."
        ),
        _optional_amount(
            phase.pillar3b, f"Phase {number}: Der 3b-Betrag muss mindestens 0 CHF betragen."
        ),
    )


def validate_phases(phases: Any, current_age: int, retirement_age: int) -> Tuple[LifePhase, ...]:
    """The phases sorted by age, without gaps or overlaps, from today until retirement.

    The first phase starts at the latest today, the last one ends at the earliest in the year
    before retirement. Raises ``ValueError`` with a German message.
    """
    if isinstance(phases, (str, bytes)) or not isinstance(phases, Sequence) or not phases:
        raise ValueError("Bitte lege mindestens eine Lebensphase an.")
    if len(phases) > MAX_PHASES:
        raise ValueError(f"Es sind höchstens {MAX_PHASES} Lebensphasen möglich.")
    checked = sorted(
        (_checked(phase, number) for number, phase in enumerate(phases, start=1)),
        key=lambda phase: phase.from_age,
    )
    for before, after in zip(checked, checked[1:]):
        if after.from_age <= before.to_age:
            raise ValueError(
                f"Die Phasen {before.from_age}–{before.to_age} und {after.from_age}–"
                f"{after.to_age} überschneiden sich."
            )
        if after.from_age > before.to_age + 1:
            raise ValueError(
                f"Zwischen Alter {before.to_age} und {after.from_age} fehlt eine Phase. Die "
                "Phasen müssen lückenlos aneinander anschliessen."
            )
    if checked[0].from_age > current_age:
        raise ValueError(
            f"Die erste Phase muss spätestens bei deinem aktuellen Alter ({current_age}) beginnen."
        )
    last_year = retirement_age - 1
    if checked[-1].to_age < last_year:
        raise ValueError(
            f"Die letzte Phase muss bis zum Jahr vor der Pensionierung (Alter {last_year}) dauern."
        )
    return tuple(checked)


def full_time_phase(current_age: int, retirement_age: int, monthly_income: float) -> LifePhase:
    """One phase at 100 % from today until retirement: the plan without life phases."""
    return LifePhase(current_age, max(current_age, retirement_age - 1), 1.0, monthly_income)


def yearly_plan(
    phases: Any,
    current_age: int,
    retirement_age: int,
    salary_growth: Any,
    pillar3a_monthly: float,
    pillar3b_monthly: float,
) -> YearlyPlan:
    """The values of each year from ``current_age`` until the year before retirement.

    Args:
        phases: The life phases (see :func:`validate_phases`).
        current_age, retirement_age: From the general inputs.
        salary_growth: Yearly salary growth (decimal), added to the phase incomes from today.
        pillar3a_monthly, pillar3b_monthly: The plan's monthly savings, used where a phase has
            no own amount.
    """
    checked = validate_phases(phases, current_age, retirement_age)
    growth = validate_salary_growth(salary_growth)
    ages, workload, income, pillar3a, pillar3b = [], [], [], [], []
    for year, age in enumerate(range(current_age, retirement_age)):
        phase = next(phase for phase in checked if phase.from_age <= age <= phase.to_age)
        monthly_income = phase.income * (1 + growth) ** year
        monthly_3a = pillar3a_monthly if phase.pillar3a is None else phase.pillar3a
        monthly_3b = pillar3b_monthly if phase.pillar3b is None else phase.pillar3b
        ages.append(age)
        workload.append(phase.workload)
        income.append(monthly_income)
        # Pillar 3a needs an income from work.
        pillar3a.append(min(monthly_3a * 12, config.PILLAR3A_ANNUAL_MAX) if monthly_income else 0.0)
        pillar3b.append(monthly_3b * 12)
    return YearlyPlan(tuple(ages), tuple(workload), tuple(income), tuple(pillar3a), tuple(pillar3b))


def estimated_pillar2_by_year(annual_net_incomes: Sequence[float], current_age: int) -> List[float]:
    """The simplified BVG estimate for the income of each year.

    Like :func:`personal_finance.core.pillar_2.estimated_contributions`, the contribution rate
    stays at the one of the current age.
    """
    return [
        Pillar2Calculator(income, current_age).calculate().annual_contribution_total
        for income in annual_net_incomes
    ]


def scaled_pillar2_by_year(
    first_year_total: float, base_monthly_income: float, monthly_incomes: Sequence[float]
) -> List[float]:
    """Own pension fund contributions in proportion to the income of each year.

    ``first_year_total`` is what the user pays in today (employee and employer) with
    ``base_monthly_income``, the income of the income input. MODELLANNAHME: the contributions
    change in proportion to the income.
    """
    base = _amount(base_monthly_income, "Das Einkommen muss grösser als 0 CHF sein.")
    if base == 0:
        raise ValueError("Das Einkommen muss grösser als 0 CHF sein.")
    return [first_year_total * income / base for income in monthly_incomes]
