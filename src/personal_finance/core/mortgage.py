"""Mortgage after the purchase: amortisation and affordability in retirement.

* :func:`amortisation_plan`: debt, pledged 3a and interest year by year, with direct or
  indirect amortisation of the 2nd mortgage.
* :func:`retirement_affordability`: do the pensions cover the housing costs?

Direct amortisation repays the 2nd mortgage every year, so the debt and the interest fall.
Indirect amortisation pays the same amount into a pledged pillar 3a account instead: the
debt stays the same until the end of the amortisation period, then the 3a money repays
the 2nd mortgage. 3a contributions are capped per year; what does not fit into 3a is
repaid directly.

All functions are pure and raise ``ValueError`` with a German message for invalid inputs.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from personal_finance import config

DIRECT = "direct"
INDIRECT = "indirect"
MODES = (DIRECT, INDIRECT)
MAX_MORTGAGE_RATE = 0.15


@dataclass(frozen=True)
class AmortisationPlan:
    """Values per year since the purchase (index 0 = purchase, last = retirement)."""

    mode: str
    years: int                    # amortisation period of the 2nd mortgage
    annual_amortisation: float    # 2nd mortgage / years
    annual_direct: float          # repaid directly per year
    annual_pledged: float         # paid into the pledged 3a per year (indirect)
    debt: Tuple[float, ...]       # mortgage debt at the start of each year
    pledged_3a: Tuple[float, ...]  # pledged 3a balance at the start of each year
    interest: Tuple[float, ...]   # interest paid in each year until retirement
    total_interest: float


@dataclass(frozen=True)
class RetirementAffordability:
    """Housing costs and pensions per year after retirement (CHF)."""

    annual_costs: float           # imputed interest on the remaining debt + maintenance
    pension_income: float         # 2nd pillar pension (from the capital)
    ahv_income: Optional[float]   # None: no AHV estimate available
    annual_income: float
    cost_to_income: float         # inf without any income
    affordable: bool


def _number(value, message: str, minimum: float = 0.0, maximum: float = math.inf) -> float:
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(message)
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(message)
    return float(value)


def _whole(value, message: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(message)
    return value


def amortisation_plan(
    mortgage,
    first_mortgage,
    years: int,
    horizon: int,
    rate,
    mode: str,
    pledged_return=0.0,
    pledged_cap=math.inf,
) -> AmortisationPlan:
    """Debt, pledged 3a and interest from the purchase until retirement.

    Args:
        mortgage: Mortgage at the purchase.
        first_mortgage: Part that does not have to be amortised (at most the mortgage).
        years: Amortisation period of the 2nd mortgage (at least 1).
        horizon: Years from the purchase until retirement (at least ``years``).
        rate: Effective mortgage interest rate.
        mode: :data:`DIRECT` or :data:`INDIRECT`.
        pledged_return: Return of the pledged 3a account (indirect).
        pledged_cap: Highest yearly payment into the pledged 3a (indirect).
    """
    mortgage = _number(mortgage, "Die Hypothek muss mindestens 0 CHF betragen.")
    first_mortgage = _number(
        first_mortgage,
        "Die 1. Hypothek muss zwischen 0 CHF und der ganzen Hypothek liegen.",
        maximum=mortgage,
    )
    years = _whole(years, "Die Amortisationsdauer muss mindestens ein Jahr betragen.", 1)
    horizon = _whole(
        horizon, "Die Amortisation muss bis zur Pensionierung abgeschlossen sein.", years
    )
    rate = _number(
        rate,
        f"Der Hypothekarzins muss zwischen 0 % und {MAX_MORTGAGE_RATE:.0%} liegen.",
        maximum=MAX_MORTGAGE_RATE,
    )
    if mode not in MODES:
        raise ValueError("Bitte wähle direkte oder indirekte Amortisation.")
    pledged_return = _number(
        pledged_return, "Die Rendite des 3a-Kontos ist ungültig.", minimum=-0.5, maximum=1
    )
    if pledged_cap != math.inf:  # no limit by default
        pledged_cap = _number(pledged_cap, "Das 3a-Limit muss mindestens 0 CHF betragen.")

    annual = (mortgage - first_mortgage) / years
    pledged = min(annual, pledged_cap) if mode == INDIRECT else 0.0
    direct = annual - pledged

    debt: List[float] = [mortgage]
    pot: List[float] = [0.0]
    for year in range(1, horizon + 1):
        # 3a payments at the start of the year (like the 3a projection), then the return.
        payment = pledged if year <= years else 0.0
        balance = (pot[-1] + payment) * (1 + pledged_return)
        remaining = mortgage - direct * min(year, years)
        if year == years and pledged > 0:
            # End of the period: the pledged 3a repays the indirectly amortised part.
            repaid = min(balance, pledged * years)
            balance -= repaid
            remaining -= repaid
        elif year > years:
            remaining = debt[-1]
        pot.append(balance)
        debt.append(remaining)

    interest = tuple(value * rate for value in debt[:-1])
    return AmortisationPlan(
        mode=mode,
        years=years,
        annual_amortisation=annual,
        annual_direct=direct,
        annual_pledged=pledged,
        debt=tuple(debt),
        pledged_3a=tuple(pot),
        interest=interest,
        total_interest=sum(interest),
    )


def retirement_affordability(
    debt,
    price,
    pension_capital,
    ahv_annual=None,
    imputed_rate=config.HOME_IMPUTED_INTEREST_RATE,
    maintenance_rate=config.HOME_MAINTENANCE_RATE,
    conversion_rate=config.HOME_RETIREMENT_CONVERSION_RATE,
) -> RetirementAffordability:
    """Housing costs after retirement against the pensions (AHV + 2nd pillar).

    Banks keep using the imputed rate in retirement; the 2nd mortgage is amortised by then,
    so there is no amortisation left.
    """
    debt = _number(debt, "Die Hypothek bei Pensionierung muss mindestens 0 CHF betragen.")
    price = _number(price, "Der Kaufpreis muss mindestens 0 CHF betragen.")
    capital = _number(
        pension_capital, "Das Kapital der 2. Säule muss mindestens 0 CHF betragen."
    )
    if ahv_annual is not None:
        ahv_annual = _number(ahv_annual, "Die AHV-Rente muss mindestens 0 CHF betragen.")
    imputed_rate = _number(imputed_rate, "Der kalkulatorische Zins ist ungültig.", maximum=1)
    maintenance_rate = _number(maintenance_rate, "Der Unterhaltssatz ist ungültig.", maximum=1)
    conversion_rate = _number(conversion_rate, "Der Umwandlungssatz ist ungültig.", maximum=1)

    costs = debt * imputed_rate + price * maintenance_rate
    pension = capital * conversion_rate
    income = pension + (ahv_annual or 0.0)
    ratio = costs / income if income > 0 else (math.inf if costs > 0 else 0.0)
    return RetirementAffordability(
        annual_costs=costs,
        pension_income=pension,
        ahv_income=ahv_annual,
        annual_income=income,
        cost_to_income=ratio,
        affordable=ratio <= config.HOME_MAX_COST_TO_INCOME + 1e-9,
    )
