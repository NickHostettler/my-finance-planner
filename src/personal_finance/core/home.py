"""Home ownership: equity (Eigenmittel) and affordability (Tragbarkeit) of a purchase.

Answers two questions for an owner-occupied home:

* :func:`assess_purchase`: Can I afford this price with my income and equity?
* :func:`max_affordable_price`: What is the highest price my income and equity allow?

The rules and their sources are in :mod:`personal_finance.config` (``HOME_*``). The model
treats the purchase price as the bank's lending value (Belehnungswert). It is a model, not a
bank commitment: banks check every purchase individually.

All functions are pure and validate their inputs (``ValueError`` with a German message).
"""

import math
from dataclasses import dataclass
from typing import List, Tuple

from personal_finance import config

STATUS_AFFORDABLE = "tragbar"
STATUS_TIGHT = "knapp"
STATUS_NOT_AFFORDABLE = "nicht tragbar"

LIMIT_AFFORDABILITY = "Tragbarkeit"
LIMIT_EQUITY = "Eigenmittel"
LIMIT_HARD_EQUITY = "harte Eigenmittel"

MAX_IMPUTED_INTEREST_RATE = 0.15
MAX_PURCHASE_COSTS_RATE = 0.10

# Slack for floating-point noise, so that values exactly at a limit count as "within".
_RATIO_TOLERANCE = 1e-9
_CHF_TOLERANCE = 0.005
_BISECTION_STEPS = 200


@dataclass(frozen=True)
class HomeAssessment:
    """Financing and affordability of one purchase (amounts in CHF, rates as decimals)."""

    price: float
    purchase_costs: float          # Kaufnebenkosten, paid from savings/3a
    hard_funds: float              # savings + 3a before purchase costs
    pension_funds: float           # money from the 2nd pillar (not hard equity)
    hard_equity: float             # hard funds left for the price after purchase costs
    total_equity: float            # hard equity + pension funds
    equity_ratio: float
    hard_equity_ratio: float
    mortgage: float
    first_mortgage: float          # up to 2/3 of the price
    second_mortgage: float         # the part that must be amortised
    loan_to_value: float
    amortisation_years: int
    annual_amortisation: float
    annual_imputed_interest: float
    annual_maintenance: float
    annual_costs: float            # imputed interest + maintenance + amortisation
    monthly_costs: float
    gross_annual_income: float
    cost_to_income: float
    missing_equity: float          # up to the minimum share of equity
    missing_hard_equity: float     # up to the minimum share of hard equity
    missing_purchase_costs: float  # purchase costs not covered by savings/3a
    status: str                    # STATUS_AFFORDABLE, STATUS_TIGHT or STATUS_NOT_AFFORDABLE
    reasons: Tuple[str, ...]       # why the purchase is tight or not affordable


@dataclass(frozen=True)
class MaxPrice:
    """Highest affordable price and the rule that limits it (one of the ``LIMIT_*``)."""

    price: float
    limited_by: str


# --- validation and formatting ----------------------------------------------------


def _amount(value, message: str) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError(message)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(message) from None
    if not math.isfinite(number) or number < 0:
        raise ValueError(message)
    return number


def _positive(value, message: str) -> float:
    number = _amount(value, message)
    if number == 0:
        raise ValueError(message)
    return number


def _rate(value, maximum: float, message: str, allow_zero: bool = True) -> float:
    number = _amount(value, message)
    if number > maximum or (number == 0 and not allow_zero):
        raise ValueError(message)
    return number


def _years(value) -> int:
    message = (
        "Der Kauf muss mindestens ein Jahr vor der Pensionierung liegen, damit die "
        "2. Hypothek amortisiert werden kann."
    )
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(message)
    return value


def _validated(
    savings,
    pillar3a,
    pillar2,
    gross_annual_income,
    years_until_retirement,
    imputed_rate,
    purchase_costs_rate,
    maintenance_rate,
):
    return (
        _amount(savings, "Das Ersparte muss mindestens 0 CHF betragen."),
        _amount(pillar3a, "Das 3a-Geld für den Kauf muss mindestens 0 CHF betragen."),
        _amount(pillar2, "Das Pensionskassengeld für den Kauf muss mindestens 0 CHF betragen."),
        _positive(gross_annual_income, "Bitte gib ein Bruttoeinkommen grösser als 0 CHF ein."),
        _years(years_until_retirement),
        _rate(
            imputed_rate,
            MAX_IMPUTED_INTEREST_RATE,
            f"Der kalkulatorische Zins muss grösser als 0 % und höchstens "
            f"{MAX_IMPUTED_INTEREST_RATE:.0%} sein.",
            allow_zero=False,
        ),
        _rate(
            purchase_costs_rate,
            MAX_PURCHASE_COSTS_RATE,
            f"Die Kaufnebenkosten müssen zwischen 0 % und {MAX_PURCHASE_COSTS_RATE:.0%} liegen.",
        ),
        _rate(maintenance_rate, 0.05, "Der Satz für Unterhalt muss zwischen 0 % und 5 % liegen."),
    )


def _chf(value: float) -> str:
    return f"CHF {value:,.0f}".replace(",", "’")


def _percent(ratio: float) -> str:
    return f"{ratio * 100:.1f} %"


# --- shared cost model ----------------------------------------------------------------


def amortisation_years(years_until_retirement: int) -> int:
    """Years to amortise the 2nd mortgage: at most 15, and done by retirement."""
    return min(config.HOME_AMORTISATION_MAX_YEARS, _years(years_until_retirement))


def _mortgage_split(price: float, mortgage: float) -> Tuple[float, float]:
    first = min(mortgage, price * config.HOME_FIRST_MORTGAGE_MAX_RATE)
    return first, mortgage - first


def _annual_costs(
    price: float,
    mortgage: float,
    years: int,
    imputed_rate: float,
    maintenance_rate: float,
) -> Tuple[float, float, float]:
    """Imputed interest, maintenance and amortisation per year."""
    _, second = _mortgage_split(price, mortgage)
    return mortgage * imputed_rate, price * maintenance_rate, second / years


def _equity(price: float, hard_funds: float, pension_funds: float, costs_rate: float):
    """Purchase costs, hard equity, total equity and uncovered purchase costs."""
    purchase_costs = price * costs_rate
    hard_equity = max(0.0, hard_funds - purchase_costs)
    missing_costs = max(0.0, purchase_costs - hard_funds)
    return purchase_costs, hard_equity, hard_equity + pension_funds, missing_costs


# --- public API ---------------------------------------------------------------------


def assess_purchase(
    price,
    savings,
    pillar3a,
    pillar2,
    gross_annual_income,
    years_until_retirement: int,
    imputed_rate=config.HOME_IMPUTED_INTEREST_RATE,
    purchase_costs_rate=config.HOME_PURCHASE_COSTS_RATE,
    maintenance_rate=config.HOME_MAINTENANCE_RATE,
) -> HomeAssessment:
    """Check equity and affordability of buying a home at ``price``.

    Args:
        price: Purchase price (treated as the bank's lending value).
        savings: Savings and securities used for the purchase (hard equity).
        pillar3a: Pillar 3a money used for the purchase (hard equity).
        pillar2: Pension fund money used (advance withdrawal or pledge; not hard equity).
        gross_annual_income: Gross household income per year.
        years_until_retirement: Years from the purchase until retirement (at least 1).
        imputed_rate: Imputed mortgage interest rate for the affordability check.
        purchase_costs_rate: Purchase costs (notary, land register, transfer tax).
        maintenance_rate: Running and maintenance costs per year.
    """
    price = _positive(price, "Bitte gib einen Kaufpreis grösser als 0 CHF ein.")
    (
        savings,
        pillar3a,
        pillar2,
        income,
        years_left,
        imputed_rate,
        purchase_costs_rate,
        maintenance_rate,
    ) = _validated(
        savings,
        pillar3a,
        pillar2,
        gross_annual_income,
        years_until_retirement,
        imputed_rate,
        purchase_costs_rate,
        maintenance_rate,
    )
    hard_funds = savings + pillar3a
    purchase_costs, hard_equity, total_equity, missing_costs = _equity(
        price, hard_funds, pillar2, purchase_costs_rate
    )
    if total_equity > price + _CHF_TOLERANCE:
        raise ValueError(
            "Das eingesetzte Eigenkapital ist höher als Kaufpreis und Kaufnebenkosten. "
            "Bitte gib nur den Betrag ein, den du für den Kauf einsetzen willst."
        )

    mortgage = max(0.0, price - total_equity)
    first, second = _mortgage_split(price, mortgage)
    years = amortisation_years(years_left)
    interest, maintenance, amortisation = _annual_costs(
        price, mortgage, years, imputed_rate, maintenance_rate
    )
    annual_costs = interest + maintenance + amortisation
    cost_to_income = annual_costs / income

    missing_equity = max(0.0, price * config.HOME_MIN_EQUITY_RATE - total_equity)
    missing_hard = max(0.0, price * config.HOME_MIN_HARD_EQUITY_RATE - hard_equity)

    reasons: List[str] = []
    if missing_costs > _CHF_TOLERANCE:
        reasons.append(
            f"Die Kaufnebenkosten von {_chf(purchase_costs)} sind nicht gedeckt: Es fehlen "
            f"{_chf(missing_costs)} aus Erspartem oder 3a."
        )
    if missing_hard > _CHF_TOLERANCE:
        reasons.append(
            f"Es fehlen {_chf(missing_hard)} harte Eigenmittel "
            f"(mindestens {config.HOME_MIN_HARD_EQUITY_RATE:.0%} des Kaufpreises ohne "
            "Pensionskassengeld)."
        )
    if missing_equity > _CHF_TOLERANCE:
        reasons.append(
            f"Es fehlen {_chf(missing_equity)} Eigenmittel "
            f"(mindestens {config.HOME_MIN_EQUITY_RATE:.0%} des Kaufpreises)."
        )
    limit = config.HOME_MAX_COST_TO_INCOME
    if cost_to_income > limit + _RATIO_TOLERANCE:
        reasons.append(
            f"Die Wohnkosten betragen {_percent(cost_to_income)} des Bruttoeinkommens, "
            f"erlaubt ist höchstens ⅓ ({_percent(limit)})."
        )

    if reasons:
        status = STATUS_NOT_AFFORDABLE
    elif cost_to_income > config.HOME_TIGHT_COST_TO_INCOME + _RATIO_TOLERANCE:
        status = STATUS_TIGHT
        reasons.append(
            f"Die Wohnkosten betragen {_percent(cost_to_income)} des Bruttoeinkommens und "
            f"liegen damit nahe an der Grenze von ⅓ ({_percent(limit)})."
        )
    else:
        status = STATUS_AFFORDABLE

    return HomeAssessment(
        price=price,
        purchase_costs=purchase_costs,
        hard_funds=hard_funds,
        pension_funds=pillar2,
        hard_equity=hard_equity,
        total_equity=total_equity,
        equity_ratio=total_equity / price,
        hard_equity_ratio=hard_equity / price,
        mortgage=mortgage,
        first_mortgage=first,
        second_mortgage=second,
        loan_to_value=mortgage / price,
        amortisation_years=years,
        annual_amortisation=amortisation,
        annual_imputed_interest=interest,
        annual_maintenance=maintenance,
        annual_costs=annual_costs,
        monthly_costs=annual_costs / 12,
        gross_annual_income=income,
        cost_to_income=cost_to_income,
        missing_equity=missing_equity,
        missing_hard_equity=missing_hard,
        missing_purchase_costs=missing_costs,
        status=status,
        reasons=tuple(reasons),
    )


def max_affordable_price(
    savings,
    pillar3a,
    pillar2,
    gross_annual_income,
    years_until_retirement: int,
    imputed_rate=config.HOME_IMPUTED_INTEREST_RATE,
    purchase_costs_rate=config.HOME_PURCHASE_COSTS_RATE,
    maintenance_rate=config.HOME_MAINTENANCE_RATE,
) -> MaxPrice:
    """Highest price that meets all equity rules and the affordability limit.

    Same arguments as :func:`assess_purchase`, without the price. All equity is assumed to
    go into the purchase; purchase costs are paid from savings and 3a.
    """
    (
        savings,
        pillar3a,
        pillar2,
        income,
        years_left,
        imputed_rate,
        purchase_costs_rate,
        maintenance_rate,
    ) = _validated(
        savings,
        pillar3a,
        pillar2,
        gross_annual_income,
        years_until_retirement,
        imputed_rate,
        purchase_costs_rate,
        maintenance_rate,
    )
    hard_funds = savings + pillar3a
    years = amortisation_years(years_left)

    # Equity rules are linear in the price: hard funds must cover the purchase costs plus the
    # minimum hard share, all funds the costs plus the minimum total share.
    hard_bound = hard_funds / (config.HOME_MIN_HARD_EQUITY_RATE + purchase_costs_rate)
    equity_bound = (hard_funds + pillar2) / (config.HOME_MIN_EQUITY_RATE + purchase_costs_rate)
    if hard_bound <= equity_bound:
        upper, limited_by = hard_bound, LIMIT_HARD_EQUITY
    else:
        upper, limited_by = equity_bound, LIMIT_EQUITY

    budget = income * config.HOME_MAX_COST_TO_INCOME

    def costs(price: float) -> float:
        _, _, total_equity, _ = _equity(price, hard_funds, pillar2, purchase_costs_rate)
        mortgage = max(0.0, price - total_equity)
        return sum(_annual_costs(price, mortgage, years, imputed_rate, maintenance_rate))

    if costs(upper) <= budget:
        return MaxPrice(price=upper, limited_by=limited_by)

    # The yearly costs grow with the price, so the affordability limit is found by bisection.
    low, high = 0.0, upper
    for _ in range(_BISECTION_STEPS):
        middle = (low + high) / 2
        if costs(middle) <= budget:
            low = middle
        else:
            high = middle
    return MaxPrice(price=low, limited_by=LIMIT_AFFORDABILITY)
