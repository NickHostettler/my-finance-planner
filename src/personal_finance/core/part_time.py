"""Part time and breaks: what they do to the 2nd pillar, pillar 3a and the AHV (#31).

The "part-time trap": the BVG coordination deduction is by law the same at any workload, so
part time lowers the insured salary more than the income; below the entry threshold there is
no pension fund at all. Years without income leave gaps in the AHV unless contributions are
paid as a non-employed person. :func:`compare_with_full_time` shows the gap in CHF compared
with working full time until retirement.

* :func:`pension_years`: per year the insured salary, the pension fund contributions, the 3a
  limit (7'373 with a pension fund, 20 % of the income up to 36'864 without) and 3a/3b.
* :func:`ahv_monthly_pension`: the AHV estimate with lower incomes in some years and
  education credits for the years with children under 16.

All functions are pure and raise ``ValueError`` with a German message for invalid inputs.
"""

import math
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

from personal_finance import config
from personal_finance.core import ahv
from personal_finance.core.family import validate_birth_ages
from personal_finance.core.home_plan import Paths, Pot
from personal_finance.core.life_phases import (
    FIXED,
    COORDINATION_MODES,
    YearlyPlan,
    full_time_phase,
    insured_salary,
    scaled_pillar2_by_year,
    yearly_plan,
)

ESTIMATE = "minimum"  # BVG estimate (same value as the dashboard's "pillar2-mode-input")
OWN = "custom"  # own contributions from the pension fund certificate
CREDIT_SHARES = (1.0, 0.5)  # education credits in full or half (married couples)


@dataclass(frozen=True)
class Pillar2Setup:
    """How the 2nd pillar is calculated.

    ``ESTIMATE``: the BVG rules with the chosen coordination deduction. ``OWN``: the user's
    yearly contributions today (``own_total``, employee and employer), in proportion to the
    income of each year.
    """

    mode: str = ESTIMATE
    coordination: str = FIXED
    own_total: float = 0.0


@dataclass(frozen=True)
class PensionYear:
    """One year of the plan. Amounts per year, nominal."""

    age: int
    workload: float
    annual_income: float
    insured_salary: Optional[float]  # None with own contributions (not known)
    pillar2: float
    pillar3a_limit: float
    pillar3a: float
    pillar3b: float

    @property
    def has_pension_fund(self) -> bool:
        return self.pillar2 > 0


@dataclass(frozen=True)
class PensionGap:
    """The plan with life phases compared with working full time until retirement."""

    yearly: YearlyPlan  # the plan's values per year (income, child costs, …)
    plan: Tuple[PensionYear, ...]
    full_time: Tuple[PensionYear, ...]
    plan_paths: Paths  # balances from today (index 0) until retirement, nominal
    full_time_paths: Paths
    ahv_plan: Optional[float]  # monthly pension in today's CHF; None without AHV inputs
    ahv_full_time: Optional[float]
    education_credit_years: int  # years with a credit within the contribution years
    years_without_income: Tuple[int, ...]  # ages: AHV contributions as a non-employed person

    @staticmethod
    def _capital(paths: Paths) -> float:
        return paths.pillar2[-1] + paths.pillar3a[-1] + paths.pillar3b[-1]

    @property
    def capital_plan(self) -> float:
        return self._capital(self.plan_paths)

    @property
    def capital_full_time(self) -> float:
        return self._capital(self.full_time_paths)

    @property
    def capital_gap(self) -> float:
        """How much less retirement capital the plan gives (negative: more)."""
        return self.capital_full_time - self.capital_plan

    @property
    def ahv_gap(self) -> Optional[float]:
        """How much less AHV per month the plan gives; ``None`` without AHV inputs."""
        if self.ahv_plan is None or self.ahv_full_time is None:
            return None
        return self.ahv_full_time - self.ahv_plan


def pillar3a_limit(annual_income: float, has_pension_fund: bool) -> float:
    """The highest 3a contribution of one year.

    With a pension fund the small limit; without one 20 % of the income from work, at most
    the large limit. Without an income from work nothing.
    """
    if annual_income <= 0:
        return 0.0
    if has_pension_fund:
        return float(config.PILLAR3A_ANNUAL_MAX)
    return min(annual_income * config.PILLAR3A_LARGE_RATE, config.PILLAR3A_LARGE_MAX)


def _setup(setup: Any) -> Pillar2Setup:
    if not isinstance(setup, Pillar2Setup) or setup.mode not in (ESTIMATE, OWN):
        raise ValueError("Bitte wähle eine Berechnungsgrundlage für die 2. Säule.")
    if setup.coordination not in COORDINATION_MODES:
        raise ValueError("Bitte wähle einen fixen oder einen pensumabhängigen Koordinationsabzug.")
    own = setup.own_total
    if (
        isinstance(own, bool)
        or not isinstance(own, (int, float))
        or not math.isfinite(own)
        or own < 0
    ):
        raise ValueError("Die Beiträge an die Pensionskasse müssen mindestens 0 CHF betragen.")
    return setup


def pension_years(
    plan: YearlyPlan, current_age: int, setup: Pillar2Setup, base_monthly_income: float
) -> Tuple[PensionYear, ...]:
    """The 2nd pillar, the 3a limit and the savings of each year of ``plan``.

    ``base_monthly_income`` is the income of the income input: own contributions belong to
    it and change in proportion to the income of each year.
    """
    setup = _setup(setup)
    incomes = plan.annual_income
    if setup.mode == OWN:
        salaries: List[Optional[float]] = [None] * len(incomes)
        pillar2 = scaled_pillar2_by_year(setup.own_total, base_monthly_income, plan.monthly_income)
    else:
        rate = config.get_pillar2_contribution_rate(current_age)
        salaries = [
            insured_salary(income, workload, setup.coordination)
            for income, workload in zip(incomes, plan.workload)
        ]
        pillar2 = [salary * rate for salary in salaries]
    years = []
    for index, age in enumerate(plan.ages):
        limit = pillar3a_limit(incomes[index], pillar2[index] > 0)
        years.append(
            PensionYear(
                age=age,
                workload=plan.workload[index],
                annual_income=incomes[index],
                insured_salary=salaries[index],
                pillar2=pillar2[index],
                pillar3a_limit=limit,
                pillar3a=min(plan.pillar3a[index], limit),
                pillar3b=plan.pillar3b[index],
            )
        )
    return tuple(years)


def education_credit_ages(child_birth_ages: Any, from_age: int, to_age: int) -> List[int]:
    """The ages from ``from_age`` to ``to_age`` with an education credit.

    ``child_birth_ages`` are the parent's ages at the births. A credit counts for the years
    after the birth up to the year in which the child turns 16; one credit per year.
    """
    births = validate_birth_ages(child_birth_ages)
    limit = ahv.EDUCATION_CREDIT_CHILD_AGE
    return [
        age
        for age in range(from_age, to_age + 1)
        if any(birth < age <= birth + limit for birth in births)
    ]


def ahv_monthly_pension(
    average_income: float,
    contribution_years: int,
    retirement_age: int,
    income_ratios: Sequence[float],
    child_birth_ages: Any = (),
    credit_share: float = 1.0,
) -> float:
    """AHV pension per month in today's CHF with life phases and education credits.

    ``average_income`` is the average yearly income entered for working as today until
    retirement. The contribution years are the last ``contribution_years`` before retirement;
    ``income_ratios`` are the income of each year from today compared with the income input
    (1 = as today, 0.6 = 60 % of it). Earlier years count with the entered average. Each year
    with a child under 16 adds the education credit (``credit_share``: 1 or 0.5 for married
    couples). MODELLANNAHME: incomes and credits in today's CHF, no AHV contributions are
    missing.
    """
    if credit_share not in CREDIT_SHARES:
        raise ValueError("Die Erziehungsgutschriften zählen ganz oder hälftig.")
    if (
        isinstance(contribution_years, bool)
        or not isinstance(contribution_years, int)
        or not 0 <= contribution_years <= ahv.FULL_CONTRIBUTION_YEARS
    ):
        raise ValueError(
            f"Die AHV-Beitragsjahre müssen eine ganze Zahl zwischen 0 und "
            f"{ahv.FULL_CONTRIBUTION_YEARS} sein."
        )
    if contribution_years == 0:
        return ahv.estimate_monthly_old_age_pension(average_income, 0)
    counted = list(income_ratios)[-contribution_years:]
    earlier = contribution_years - len(counted)
    credits = len(
        education_credit_ages(
            child_birth_ages, retirement_age - contribution_years, retirement_age - 1
        )
    )
    total = average_income * (earlier + sum(counted)) + (
        credits * ahv.EDUCATION_CREDIT * credit_share
    )
    return ahv.estimate_monthly_old_age_pension(total / contribution_years, contribution_years)


def _paths(years: Sequence[PensionYear], initial: Sequence[float], returns: Sequence[float]):
    count = len(years)
    pillar2_return, free_return = returns
    return Paths(
        Pot([year.pillar2 for year in years], pillar2_return, initial[0]).path(count),
        Pot([year.pillar3a for year in years], free_return, initial[1]).path(count),
        Pot([year.pillar3b for year in years], free_return, initial[2]).path(count),
    )


def compare_with_full_time(
    phases: Any,
    current_age: int,
    retirement_age: int,
    base_monthly_income: float,
    salary_growth: Any,
    pillar3a_monthly: float,
    pillar3b_monthly: float,
    setup: Pillar2Setup,
    initial: Tuple[float, float, float],
    returns: Tuple[float, float],
    ahv_average_income: Optional[float] = None,
    ahv_contribution_years: int = ahv.FULL_CONTRIBUTION_YEARS,
    child_birth_ages: Any = (),
    credit_share: float = 1.0,
) -> PensionGap:
    """The plan with ``phases`` and the same plan at 100 % until retirement.

    Args:
        phases: The life phases (see :func:`personal_finance.core.life_phases.validate_phases`).
        current_age, retirement_age: From the general inputs.
        base_monthly_income: The income of the income input (full time, today).
        salary_growth: Yearly salary growth (decimal).
        pillar3a_monthly, pillar3b_monthly: The plan's monthly savings.
        setup: How the 2nd pillar is calculated.
        initial: Balances today: 2nd pillar, 3a, 3b.
        returns: Yearly return of the 2nd pillar and of 3a/3b.
        ahv_average_income, ahv_contribution_years: The AHV inputs (``None``: no estimate).
        child_birth_ages, credit_share: For the education credits.
    """
    if (
        isinstance(base_monthly_income, bool)
        or not isinstance(base_monthly_income, (int, float))
        or not math.isfinite(base_monthly_income)
        or base_monthly_income <= 0
    ):
        raise ValueError("Das Einkommen muss grösser als 0 CHF sein.")
    plan = yearly_plan(
        phases, current_age, retirement_age, salary_growth, pillar3a_monthly, pillar3b_monthly
    )
    full = yearly_plan(
        [full_time_phase(current_age, retirement_age, base_monthly_income)],
        current_age,
        retirement_age,
        salary_growth,
        pillar3a_monthly,
        pillar3b_monthly,
    )
    plan_years = pension_years(plan, current_age, setup, base_monthly_income)
    full_years = pension_years(full, current_age, setup, base_monthly_income)

    ahv_plan = ahv_full = None
    credit_years = 0
    if ahv_average_income is not None:
        ratios = [
            planned / full_time
            for planned, full_time in zip(plan.monthly_income, full.monthly_income)
        ]
        ahv_plan = ahv_monthly_pension(
            ahv_average_income,
            ahv_contribution_years,
            retirement_age,
            ratios,
            child_birth_ages,
            credit_share,
        )
        ahv_full = ahv_monthly_pension(
            ahv_average_income,
            ahv_contribution_years,
            retirement_age,
            [1.0] * len(ratios),
            child_birth_ages,
            credit_share,
        )
        credit_years = len(
            education_credit_ages(
                child_birth_ages,
                retirement_age - ahv_contribution_years,
                retirement_age - 1,
            )
        )
    return PensionGap(
        yearly=plan,
        plan=plan_years,
        full_time=full_years,
        plan_paths=_paths(plan_years, initial, returns),
        full_time_paths=_paths(full_years, initial, returns),
        ahv_plan=ahv_plan,
        ahv_full_time=ahv_full,
        education_credit_years=credit_years,
        years_without_income=tuple(year.age for year in plan_years if year.annual_income == 0),
    )
