"""A planned home purchase in the personal plan.

Combines the inputs of the "Wohneigentum" section with the rules in
:mod:`personal_finance.core.home`. All functions are pure and raise ``ValueError`` with a
German message for invalid inputs.
"""

import math
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from personal_finance import config
from personal_finance.core import home, wef
from personal_finance.core.home import HomeAssessment, MaxPrice
from personal_finance.core.projection import project_balance
from personal_finance.core.wef import WithdrawalLimit


@dataclass(frozen=True)
class Pot:
    """One savings pot of the projection (2nd pillar, 3a or 3b)."""

    annual_contribution: float
    annual_return: float
    initial: float

    def path(self, years: int, withdrawals=None) -> List[float]:
        return project_balance(
            self.annual_contribution,
            years,
            self.annual_return,
            self.initial,
            withdrawals=withdrawals,
        )


@dataclass(frozen=True)
class Paths:
    """Nominal balances at the start of each year from today (index 0) to retirement."""

    pillar2: List[float]
    pillar3a: List[float]
    pillar3b: List[float]


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
    # Money for the purchase (#26)
    savings: float
    pillar3a_used: float
    pillar2_used: float
    balances_at_purchase: Tuple[float, float, float]  # 2nd pillar, 3a, 3b (nominal)
    pillar2_limit: WithdrawalLimit
    pillar3a_limit: WithdrawalLimit
    savings_outside_3b: float  # savings not covered by the projected free assets (3b)
    without_purchase: Paths
    with_purchase: Paths

    def withdrawal_note(self) -> Optional[str]:
        """One sentence for the overview: what the purchase takes from the projection."""
        parts = [
            f"{label} {_chf(amount)}"
            for label, amount in (
                ("Vorbezug Pensionskasse", self.pillar2_used),
                ("Bezug 3a", self.pillar3a_used),
                ("Erspartes aus dem freien Vermögen", self.savings - self.savings_outside_3b),
            )
            if amount > 0
        ]
        if not parts:
            return None
        return (
            f"Mit dem geplanten Kauf mit {self.purchase_age} Jahren: " + ", ".join(parts)
            + " sind ab dann abgezogen. Details im Tab «Wohneigentum»."
        )


def _chf(value: float) -> str:
    return f"CHF {value:,.0f}".replace(",", "’")


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
    pot_2: Pot,
    pot_3a: Pot,
    pot_3b: Pot,
) -> HomePlan:
    """Check the planned purchase and its effect on the projection.

    Args:
        inputs: The entered values.
        current_age, retirement_age: From the general inputs.
        income_gross_annual: Yearly income from the income inputs (net if ``income_is_net``).
        income_is_net: The user entered a net income, so the gross income is not known.
        pot_2, pot_3a, pot_3b: The pots of the projection without a purchase. At the
            purchase, the pension fund and 3a money and the savings are taken out of them
            (savings from the free assets 3b, as far as they reach).
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

    years = retirement_age - current_age
    at_purchase = age - current_age
    without = Paths(pot_2.path(years), pot_3a.path(years), pot_3b.path(years))
    balance_2 = without.pillar2[at_purchase]
    balance_3a = without.pillar3a[at_purchase]
    balance_3b = without.pillar3b[at_purchase]
    half_rule_age = config.WEF_PILLAR2_HALF_RULE_AGE
    balance_at_50 = (
        without.pillar2[half_rule_age - current_age]
        if current_age <= half_rule_age <= retirement_age
        else None  # already older than 50: the balance at 50 is not known
    )
    limit_2 = wef.pillar2_limit(balance_2, age, retirement_age, balance_at_50)
    limit_3a = wef.pillar3a_limit(balance_3a)
    pillar2_used = wef.check_amount(pillar2, limit_2, "aus der Pensionskasse")
    pillar3a_used = wef.check_amount(pillar3a, limit_3a, "aus der Säule 3a")
    savings = assessment.hard_funds - pillar3a_used

    with_purchase = Paths(
        pot_2.path(years, {at_purchase: pillar2_used}),
        pot_3a.path(years, {at_purchase: pillar3a_used}),
        pot_3b.path(years, {at_purchase: savings}),
    )
    return HomePlan(
        purchase_age=age,
        years_until_purchase=at_purchase,
        gross_income=assessment.gross_annual_income,
        gross_income_from_net=from_net,
        assessment=assessment,
        max_price=max_price,
        savings=savings,
        pillar3a_used=pillar3a_used,
        pillar2_used=pillar2_used,
        balances_at_purchase=(balance_2, balance_3a, balance_3b),
        pillar2_limit=limit_2,
        pillar3a_limit=limit_3a,
        savings_outside_3b=max(0.0, savings - balance_3b),
        without_purchase=without,
        with_purchase=with_purchase,
    )
