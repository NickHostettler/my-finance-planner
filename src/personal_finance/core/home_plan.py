"""A planned home purchase in the personal plan.

Combines the inputs of the "Wohneigentum" section with the rules in
:mod:`personal_finance.core.home`. All functions are pure and raise ``ValueError`` with a
German message for invalid inputs.
"""

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from personal_finance import config
from personal_finance.core import home, mortgage, wef
from personal_finance.core.home import HomeAssessment, MaxPrice
from personal_finance.core.mortgage import AmortisationPlan, RetirementAffordability
from personal_finance.core.projection import project_balance
from personal_finance.core.wef import WithdrawalLimit


@dataclass(frozen=True)
class Pot:
    """One savings pot of the projection (2nd pillar, 3a or 3b)."""

    annual_contribution: Union[float, Sequence[float]]  # one amount or one per year
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
    income from the income inputs. Empty equity amounts count as 0 CHF; the dashboard fills
    them with :func:`suggested_amounts` (#40).
    """

    price: Any
    savings: Any
    pillar3a: Any
    pillar2: Any
    purchase_age: Any
    gross_income: Any
    imputed_rate: Any  # decimal, e.g. 0.05
    mortgage_rate: Any = config.HOME_MORTGAGE_RATE  # effective rate, decimal
    amortisation: Any = mortgage.DIRECT


@dataclass(frozen=True)
class MortgageOutcome:
    """The purchase with one way of amortising (#27). Lists per year from today, nominal."""

    plan: AmortisationPlan
    paths: Paths  # 2nd pillar, 3a (incl. pledged 3a) and 3b
    property_value: List[float]  # price from the purchase on (no change in value)
    debt: List[float]
    net_wealth: List[float]  # paths + property - debt
    retirement: RetirementAffordability


@dataclass(frozen=True)
class AvailableFunds:
    """The most that could go into the purchase at the purchase age (nominal CHF, #40).

    ``savings`` are the projected free assets (3b). ``pillar3a`` and ``pillar2`` are the WEF
    limits on the projected balances (``pillar2`` is 0 if no advance withdrawal is possible).
    """

    savings: float
    pillar3a: float
    pillar2: float

    @property
    def hard(self) -> float:
        return self.savings + self.pillar3a

    @property
    def total(self) -> float:
        return self.hard + self.pillar2


@dataclass(frozen=True)
class HomePlan:
    purchase_age: int
    years_until_purchase: int
    gross_income: float
    gross_income_from_net: bool  # no gross income known: the net income was used
    assessment: HomeAssessment
    max_price: MaxPrice
    # Money for the purchase (#26) and the most that would be available (#40)
    savings: float
    pillar3a_used: float
    pillar2_used: float
    available: AvailableFunds
    max_price_available: MaxPrice  # with all of ``available`` and the same income
    balances_at_purchase: Tuple[float, float, float]  # 2nd pillar, 3a, 3b (nominal)
    pillar2_limit: WithdrawalLimit
    pillar3a_limit: WithdrawalLimit
    savings_outside_3b: float  # savings not covered by the projected free assets (3b)
    without_purchase: Paths
    # Mortgage (#27): the chosen way of amortising and both ways for the comparison
    amortisation: str
    mortgage_rate: float
    outcomes: Dict[str, MortgageOutcome]

    @property
    def outcome(self) -> MortgageOutcome:
        return self.outcomes[self.amortisation]

    @property
    def required_equity(self) -> float:
        """Minimum equity for the price (hard equity and pension fund money together)."""
        return self.assessment.price * config.HOME_MIN_EQUITY_RATE

    @property
    def required_hard_equity(self) -> float:
        """Minimum share of the equity that must not come from the pension fund."""
        return self.assessment.price * config.HOME_MIN_HARD_EQUITY_RATE

    @property
    def required_funds(self) -> float:
        """Minimum money for the purchase: the minimum equity plus the purchase costs."""
        return self.required_equity + self.assessment.purchase_costs

    @property
    def required_hard_funds(self) -> float:
        """Minimum savings and 3a: the minimum hard equity plus the purchase costs."""
        return self.required_hard_equity + self.assessment.purchase_costs

    @property
    def with_purchase(self) -> Paths:
        return self.outcome.paths

    def net_wealth_without_purchase(self) -> List[float]:
        paths = self.without_purchase
        return [sum(values) for values in zip(paths.pillar2, paths.pillar3a, paths.pillar3b)]

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
            f"Mit dem geplanten Kauf mit {self.purchase_age} Jahren: "
            + ", ".join(parts)
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


@dataclass(frozen=True)
class _AtPurchase:
    """The projection without a purchase and what it allows at the purchase age."""

    without: Paths
    balances: Tuple[float, float, float]  # 2nd pillar, 3a, 3b (nominal)
    pillar2_limit: WithdrawalLimit
    pillar3a_limit: WithdrawalLimit

    @property
    def available(self) -> AvailableFunds:
        return AvailableFunds(
            self.balances[2], self.pillar3a_limit.maximum, self.pillar2_limit.maximum
        )


def _at_purchase(
    age: int, current_age: int, retirement_age: int, pot_2: Pot, pot_3a: Pot, pot_3b: Pot
) -> _AtPurchase:
    years = retirement_age - current_age
    at_purchase = age - current_age
    without = Paths(pot_2.path(years), pot_3a.path(years), pot_3b.path(years))
    balance_2 = without.pillar2[at_purchase]
    half_rule_age = config.WEF_PILLAR2_HALF_RULE_AGE
    balance_at_50 = (
        without.pillar2[half_rule_age - current_age]
        if current_age <= half_rule_age <= retirement_age
        else None  # already older than 50: the balance at 50 is not known
    )
    return _AtPurchase(
        without=without,
        balances=(balance_2, without.pillar3a[at_purchase], without.pillar3b[at_purchase]),
        pillar2_limit=wef.pillar2_limit(balance_2, age, retirement_age, balance_at_50),
        pillar3a_limit=wef.pillar3a_limit(without.pillar3a[at_purchase]),
    )


def available_funds(
    purchase_age_value: Any,
    current_age: int,
    retirement_age: int,
    pot_2: Pot,
    pot_3a: Pot,
    pot_3b: Pot,
) -> AvailableFunds:
    """The most that could go into a purchase at the entered age (empty = now, #40)."""
    age = purchase_age(purchase_age_value, current_age, retirement_age)
    return _at_purchase(age, current_age, retirement_age, pot_2, pot_3a, pot_3b).available


def suggested_amounts(
    price: Any,
    available: AvailableFunds,
    purchase_costs_rate: float = config.HOME_PURCHASE_COSTS_RATE,
) -> Tuple[float, float, float]:
    """The highest amounts from savings, 3a and the pension fund for buying at ``price`` (#40).

    Each source gives as much as is available, but no more than the purchase needs: savings
    and 3a pay the purchase costs, and the equity together may not exceed the price. The
    sources are used in the order savings, 3a, pension fund, so that the pension fund money
    (which also lowers the disability and death benefits) is used last. If less than the
    minimum advance withdrawal is still open, nothing comes from the pension fund. Amounts in
    whole CHF, rounded down.
    """
    price = home.validate_price(price)
    costs = price * purchase_costs_rate
    savings = math.floor(min(available.savings, price + costs))
    pillar3a = math.floor(min(available.pillar3a, price + costs - savings))
    hard_equity = max(0.0, savings + pillar3a - costs)
    pillar2 = math.floor(min(available.pillar2, price - hard_equity))
    if pillar2 < config.WEF_PILLAR2_MIN_AMOUNT:
        pillar2 = 0
    return float(savings), float(pillar3a), float(pillar2)


def plan_purchase(
    inputs: HomeInputs,
    current_age: int,
    retirement_age: int,
    income_gross_annual: float,
    income_is_net: bool,
    pot_2: Pot,
    pot_3a: Pot,
    pot_3b: Pot,
    ahv_annual_at_retirement: Optional[float] = None,
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
        ahv_annual_at_retirement: Nominal AHV pension per year, for the check in retirement
            (``None`` if not estimated).
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
    state = _at_purchase(age, current_age, retirement_age, pot_2, pot_3a, pot_3b)
    available = state.available
    max_price_available = home.max_affordable_price(
        available.savings,
        available.pillar3a,
        available.pillar2,
        gross_income,
        years_left,
        inputs.imputed_rate,
    )
    without = state.without
    balance_3b = state.balances[2]
    limit_2, limit_3a = state.pillar2_limit, state.pillar3a_limit
    pillar2_used = wef.check_amount(pillar2, limit_2, "aus der Pensionskasse")
    pillar3a_used = wef.check_amount(pillar3a, limit_3a, "aus der Säule 3a")
    savings = assessment.hard_funds - pillar3a_used

    pillar2_path = pot_2.path(years, {at_purchase: pillar2_used})
    pillar3a_path = pot_3a.path(years, {at_purchase: pillar3a_used})
    pillar3b_path = pot_3b.path(years, {at_purchase: savings})
    before = [0.0] * at_purchase
    property_value = before + [assessment.price] * (years - at_purchase + 1)

    # The pledged 3a payments share the yearly 3a limit with the 3a plan; with life phases the
    # plan pays a different amount each year, so the highest one from the purchase on counts.
    plan_3a = pot_3a.annual_contribution
    if isinstance(plan_3a, Sequence):
        plan_3a = max(plan_3a[at_purchase:], default=0.0)

    def outcome(mode: str) -> MortgageOutcome:
        plan = mortgage.amortisation_plan(
            assessment.mortgage,
            assessment.first_mortgage,
            assessment.amortisation_years,
            years - at_purchase,
            inputs.mortgage_rate,
            mode,
            pledged_return=pot_3a.annual_return,
            pledged_cap=max(0.0, config.PILLAR3A_ANNUAL_MAX - plan_3a),
        )
        pledged_3a = before + list(plan.pledged_3a)
        paths = Paths(
            pillar2_path,
            [plan_3a + pledged for plan_3a, pledged in zip(pillar3a_path, pledged_3a)],
            pillar3b_path,
        )
        debt = before + list(plan.debt)
        net_wealth = [
            sum(values) - owed
            for *values, owed in zip(
                paths.pillar2, paths.pillar3a, paths.pillar3b, property_value, debt
            )
        ]
        return MortgageOutcome(
            plan=plan,
            paths=paths,
            property_value=property_value,
            debt=debt,
            net_wealth=net_wealth,
            retirement=mortgage.retirement_affordability(
                debt[-1],
                assessment.price,
                paths.pillar2[-1],
                ahv_annual_at_retirement,
                imputed_rate=inputs.imputed_rate,
            ),
        )

    if inputs.amortisation not in mortgage.MODES:
        raise ValueError("Bitte wähle direkte oder indirekte Amortisation.")
    outcomes = {mode: outcome(mode) for mode in mortgage.MODES}
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
        available=available,
        max_price_available=max_price_available,
        balances_at_purchase=state.balances,
        pillar2_limit=limit_2,
        pillar3a_limit=limit_3a,
        savings_outside_3b=max(0.0, savings - balance_3b),
        without_purchase=without,
        amortisation=inputs.amortisation,
        mortgage_rate=float(inputs.mortgage_rate),  # validated by amortisation_plan
        outcomes=outcomes,
    )
