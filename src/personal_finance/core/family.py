"""Family planning: children, family allowances, parental leave and child costs (#32).

Children are given as the parent's age at each birth (only years, no names). For each year of
the plan :func:`family_years` gives:

* the family allowances by the age of the children: the child allowance until 16, the
  education allowance from 16 until 25 at most (minimum amounts, cantons pay more);
* the parental allowance (EO) in the year of a birth: 80 % of the salary up to a daily
  maximum, 14 weeks for the mother and 2 weeks for the other parent; the lost 20 % (or more
  above the maximum) lower the income of that year;
* the child costs of the phase and what is left of the income after them and the savings.

Model assumptions (MODELLANNAHME): whole years (the year of birth counts fully for the
allowances, the child is in education until 25), the employer pays only the EO allowance
during the leave, incomes as entered (net).

All functions are pure and raise ``ValueError`` with a German message for invalid inputs.
"""

import math
from dataclasses import dataclass
from typing import Any, Sequence, Tuple

from personal_finance import config

MOTHER = "mother"
OTHER_PARENT = "other"
ROLES = (MOTHER, OTHER_PARENT)
MAX_CHILDREN = 10


@dataclass(frozen=True)
class Family:
    """The children and how allowances and leave apply. Allowances per child and month."""

    child_birth_ages: Any = ()  # the parent's age at each birth
    role: Any = MOTHER  # MOTHER (14 weeks EO) or OTHER_PARENT (2 weeks)
    child_allowance: Any = config.CHILD_ALLOWANCE_MONTHLY
    education_allowance: Any = config.EDUCATION_ALLOWANCE_MONTHLY


@dataclass(frozen=True)
class FamilyYear:
    """One year of the plan. Amounts per year, nominal; ``income`` is the year's income."""

    age: int
    children_under_16: int
    children_in_education: int
    allowances: float
    leave_days: int
    leave_allowance: float  # EO paid during the leave
    leave_loss: float  # salary not replaced during the leave
    child_costs: float
    savings: float  # 3a and 3b of the year
    income: float

    @property
    def left_before_savings(self) -> float:
        """Income and allowances after the leave loss and the child costs."""
        return self.income + self.allowances - self.leave_loss - self.child_costs

    @property
    def left_after_savings(self) -> float:
        """What is left for living after the child costs and the savings (may be negative)."""
        return self.left_before_savings - self.savings

    @property
    def costs_exceed_income(self) -> bool:
        return self.left_after_savings < 0


def validate_birth_ages(values: Any) -> Tuple[int, ...]:
    """The parent's ages at the births as whole numbers (at most ``MAX_CHILDREN``)."""
    message = "Bitte gib für jedes Kind dein Alter bei der Geburt als ganze Zahl ein."
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(message)
    if len(values) > MAX_CHILDREN:
        raise ValueError(f"Es sind höchstens {MAX_CHILDREN} Kinder möglich.")
    ages = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(message)
        ages.append(value)
    return tuple(sorted(ages))


def _allowance(value: Any, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"Die {name} muss mindestens 0 CHF pro Monat betragen.")
    return float(value)


def validate_family(family: Any) -> Family:
    if not isinstance(family, Family):
        raise ValueError("Die Angaben zur Familie sind ungültig.")
    if family.role not in ROLES:
        raise ValueError("Bitte wähle, ob du die Mutter oder der andere Elternteil bist.")
    return Family(
        validate_birth_ages(family.child_birth_ages),
        family.role,
        _allowance(family.child_allowance, "Kinderzulage"),
        _allowance(family.education_allowance, "Ausbildungszulage"),
    )


def leave_allowance(monthly_income: float, days: int) -> Tuple[float, float]:
    """EO allowance and unreplaced salary for ``days`` of leave with ``monthly_income``.

    80 % of the daily income (monthly income / 30), at most the daily maximum.
    """
    daily = monthly_income / config.DAYS_PER_MONTH_EO
    allowance = min(daily * config.PARENTAL_ALLOWANCE_RATE, config.PARENTAL_ALLOWANCE_DAILY_MAX)
    return allowance * days, (daily - allowance) * days


def family_years(
    ages: Sequence[int],
    monthly_incomes: Sequence[float],
    child_costs: Sequence[float],
    savings: Sequence[float],
    family: Family,
) -> Tuple[FamilyYear, ...]:
    """Allowances, parental leave, child costs and what is left in each year.

    Args:
        ages: The parent's age in each year of the plan.
        monthly_incomes: The income of each year per month (net, with the salary growth).
        child_costs: The child costs of each year (per year).
        savings: 3a and 3b of each year (per year).
        family: The children and the allowances.
    """
    family = validate_family(family)
    days = config.MATERNITY_LEAVE_DAYS if family.role == MOTHER else config.OTHER_PARENT_LEAVE_DAYS
    years = []
    for age, monthly_income, costs, saved in zip(ages, monthly_incomes, child_costs, savings):
        child_ages = [age - birth for birth in family.child_birth_ages if birth <= age]
        under_16 = sum(1 for child in child_ages if child < config.CHILD_ALLOWANCE_UNTIL_AGE)
        in_education = sum(
            1
            for child in child_ages
            if config.CHILD_ALLOWANCE_UNTIL_AGE <= child < config.EDUCATION_ALLOWANCE_UNTIL_AGE
        )
        # One leave per year with a birth (twins do not double it), only with a salary.
        leave_days = days if 0 in child_ages and monthly_income > 0 else 0
        paid, lost = leave_allowance(monthly_income, leave_days)
        years.append(
            FamilyYear(
                age=age,
                children_under_16=under_16,
                children_in_education=in_education,
                allowances=12
                * (under_16 * family.child_allowance + in_education * family.education_allowance),
                leave_days=leave_days,
                leave_allowance=paid,
                leave_loss=lost,
                child_costs=costs,
                savings=saved,
                income=monthly_income * 12,
            )
        )
    return tuple(years)
