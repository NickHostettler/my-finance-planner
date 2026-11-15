"""A planned home purchase in the personal plan.

Combines the inputs of the "Wohneigentum" section with the rules in
:mod:`personal_finance.core.home`. All functions are pure and raise ``ValueError`` with a
German message for invalid inputs.
"""

import math
from dataclasses import dataclass
from typing import Any

from personal_finance.core import home
from personal_finance.core.home import HomeAssessment, MaxPrice


@dataclass(frozen=True)
class HomeInputs:
    """What the user entered. Amounts in CHF at the time of the purchase.

    ``purchase_age`` and ``gross_income`` may be ``None``: buy now, and take the gross
    income from the income inputs. Empty equity amounts count as 0 CHF.
    """

    price: Any
    savings: Any
    pillar3a: Any
    pillar2: Any
    purchase_age: Any
    gross_income: Any
    imputed_rate: Any  # decimal, e.g. 0.05


@dataclass(frozen=True)
class HomePlan:
    purchase_age: int
    years_until_purchase: int
    gross_income: float
    gross_income_from_net: bool  # no gross income known: the net income was used
    assessment: HomeAssessment
    max_price: MaxPrice


def purchase_age(value: Any, current_age: int, retirement_age: int) -> int:
    """The age at the purchase: empty means now; at least one year before retirement."""
    if value is None:
        value = current_age
    latest = retirement_age - 1
    message = (
        f"Das Kaufalter muss eine ganze Zahl zwischen deinem aktuellen Alter ({current_age}) "
        f"und einem Jahr vor der Pensionierung ({latest}) sein."
    )
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not float(value).is_integer()
    ):
        raise ValueError(message)
    age = int(value)
    if not current_age <= age <= latest:
        raise ValueError(message)
    return age


def _zero_if_empty(value: Any) -> Any:
    return 0 if value is None else value


def plan_purchase(
    inputs: HomeInputs,
    current_age: int,
    retirement_age: int,
    income_gross_annual: float,
    income_is_net: bool,
) -> HomePlan:
    """Check the planned purchase.

    Args:
        inputs: The entered values.
        current_age, retirement_age: From the general inputs.
        income_gross_annual: Yearly income from the income inputs (net if ``income_is_net``).
        income_is_net: The user entered a net income, so the gross income is not known.
    """
    age = purchase_age(inputs.purchase_age, current_age, retirement_age)
    if inputs.gross_income is None:
        gross_income, from_net = income_gross_annual, income_is_net
    else:
        gross_income, from_net = inputs.gross_income, False

    savings = _zero_if_empty(inputs.savings)
    pillar3a = _zero_if_empty(inputs.pillar3a)
    pillar2 = _zero_if_empty(inputs.pillar2)
    years_left = retirement_age - age
    assessment = home.assess_purchase(
        inputs.price, savings, pillar3a, pillar2, gross_income, years_left, inputs.imputed_rate
    )
    max_price = home.max_affordable_price(
        savings, pillar3a, pillar2, gross_income, years_left, inputs.imputed_rate
    )
    return HomePlan(
        purchase_age=age,
        years_until_purchase=age - current_age,
        gross_income=assessment.gross_annual_income,
        gross_income_from_net=from_net,
        assessment=assessment,
        max_price=max_price,
    )
