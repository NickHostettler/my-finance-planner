"""A planned home purchase by one person or by a household of two (v1.3).

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
    them with :func:`suggested_amounts` (#40). A household purchase takes the amounts from
    each :class:`Member` instead.
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
    """The purchase with one way of amortising (#27). Lists per year from today, nominal.

    For a household the paths are the sums of both persons until the first retirement.
    """

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


def _total_funds(funds: Sequence[AvailableFunds]) -> AvailableFunds:
    if len(funds) == 1:
        return funds[0]
    return AvailableFunds(
        sum(item.savings for item in funds),
        sum(item.pillar3a for item in funds),
        sum(item.pillar2 for item in funds),
    )


@dataclass(frozen=True)
class Member:
    """One person who buys: own projection, income and money for the purchase (#44).

    A single plan has one member without a ``label``; a household has two ("Person A",
    "Person B"). ``savings``, ``pillar3a`` and ``pillar2`` are what this person puts into the
    purchase (empty = 0 CHF). ``income_annual`` is the yearly gross income, or the net income
    if ``income_is_net``.
    """

    current_age: int
    retirement_age: int
    pot_2: Pot
    pot_3a: Pot
    pot_3b: Pot
    label: str = ""
    income_annual: float = 0.0
    income_is_net: bool = False
    ahv_annual_at_retirement: Optional[float] = None  # nominal, None if not estimated
    savings: Any = None
    pillar3a: Any = None
    pillar2: Any = None

    @property
    def years(self) -> int:
        return self.retirement_age - self.current_age

    @property
    def pots(self) -> Tuple[Pot, Pot, Pot]:
        return self.pot_2, self.pot_3a, self.pot_3b


@dataclass(frozen=True)
class PersonPurchase:
    """What a purchase means for one person: money used and the own projection (#42).

    Paths run from today until this person's retirement. A withdrawal lowers only the
    projection of the person whose money it is.
    """

    label: str
    purchase_age: int
    years_until_purchase: int
    savings: float
    pillar3a_used: float
    pillar2_used: float
    available: AvailableFunds
    balances_at_purchase: Tuple[float, float, float]  # 2nd pillar, 3a, 3b (nominal)
    pillar2_limit: WithdrawalLimit
    pillar3a_limit: WithdrawalLimit
    savings_outside_3b: float  # savings not covered by the projected free assets (3b)
    without_purchase: Paths
    paths_by_mode: Dict[str, Paths]  # with the purchase, for each way of amortising
    amortisation: str

    @property
    def with_purchase(self) -> Paths:
        return self.paths_by_mode[self.amortisation]

    @property
    def used(self) -> float:
        """Everything this person puts into the purchase."""
        return self.savings + self.pillar3a_used + self.pillar2_used

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
        purchase = "gemeinsamen Kauf" if self.label else "geplanten Kauf"
        return (
            f"Mit dem {purchase} mit {self.purchase_age} Jahren: "
            + ", ".join(parts)
            + " sind ab dann abgezogen. Details im Tab «Wohneigentum»."
        )


@dataclass(frozen=True)
class HomePlan:
    """The planned purchase of one person or of a household (``members``).

    Equity, affordability and the mortgage use the sums of all members. ``without_purchase``
    and ``outcomes`` are household sums until the first retirement (for one person: until the
    retirement); each member's own projection is in ``members``.
    """

    years_until_purchase: int
    gross_income: float
    gross_income_from_net: bool  # no gross income known: a net income was used
    assessment: HomeAssessment
    max_price: MaxPrice
    available: AvailableFunds  # all members together (#40)
    max_price_available: MaxPrice  # with all of ``available`` and the same income
    without_purchase: Paths
    # Mortgage (#27): the chosen way of amortising and both ways for the comparison
    amortisation: str
    mortgage_rate: float
    outcomes: Dict[str, MortgageOutcome]
    members: Tuple[PersonPurchase, ...]

    @property
    def household(self) -> bool:
        return len(self.members) > 1

    @property
    def purchase_age(self) -> int:
        """Age of the (first) person at the purchase."""
        return self.members[0].purchase_age

    @property
    def timing(self) -> str:
        """When the purchase is: "Kauf mit 40 Jahren" or "Kauf in 5 Jahren (Person A 40, …)"."""
        if not self.household:
            return f"Kauf mit {self.purchase_age} Jahren"
        years = self.years_until_purchase
        when = "heute" if years == 0 else f"in {years} Jahr" + ("en" if years > 1 else "")
        ages = ", ".join(f"{member.label} {member.purchase_age}" for member in self.members)
        return f"Kauf {when} ({ages})"

    @property
    def horizon(self) -> str:
        """The end of the household paths: "Pensionierung" or "ersten Pensionierung"."""
        return "ersten Pensionierung" if self.household else "Pensionierung"

    @property
    def savings(self) -> float:
        return sum(member.savings for member in self.members)

    @property
    def pillar3a_used(self) -> float:
        return sum(member.pillar3a_used for member in self.members)

    @property
    def pillar2_used(self) -> float:
        return sum(member.pillar2_used for member in self.members)

    @property
    def savings_outside_3b(self) -> float:
        return sum(member.savings_outside_3b for member in self.members)

    # The WEF details of the first person (all there is in a single plan).
    @property
    def balances_at_purchase(self) -> Tuple[float, float, float]:
        return self.members[0].balances_at_purchase

    @property
    def pillar2_limit(self) -> WithdrawalLimit:
        return self.members[0].pillar2_limit

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
        """The note of the (first) person, see :meth:`PersonPurchase.withdrawal_note`."""
        return self.members[0].withdrawal_note()


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


def years_until_purchase(value: Any, members: Sequence[Member]) -> int:
    """Years from today until the purchase; ``value`` is the first person's age (empty = now).

    A household buys at least one year before the first retirement in the household.
    """
    first = members[0]
    if len(members) == 1:
        return purchase_age(value, first.current_age, first.retirement_age) - first.current_age
    latest = first.current_age + min(member.years for member in members) - 1
    try:
        age = purchase_age(value, first.current_age, latest + 1)
    except ValueError:
        raise ValueError(
            f"Das Kaufalter von {first.label} muss eine ganze Zahl zwischen "
            f"{first.current_age} und {latest} sein: Der Kauf muss mindestens ein Jahr vor der "
            "ersten Pensionierung im Haushalt liegen."
        ) from None
    return age - first.current_age


def _zero_if_empty(value: Any) -> Any:
    return 0 if value is None else value


def _member_amount(value: Any, message: str) -> float:
    """A household member's amount for the purchase: at least 0 CHF (empty = 0)."""
    value = _zero_if_empty(value)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(message)
    return float(value)


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


def _member_at_purchase(member: Member, years_until: int) -> _AtPurchase:
    return _at_purchase(
        member.current_age + years_until, member.current_age, member.retirement_age, *member.pots
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


def available_funds_by_member(
    purchase_age_value: Any, members: Sequence[Member]
) -> Tuple[AvailableFunds, ...]:
    """What each member could put in at the purchase (age of the first person, #42)."""
    years_until = years_until_purchase(purchase_age_value, members)
    return tuple(_member_at_purchase(member, years_until).available for member in members)


def suggested_amounts_by_member(
    price: Any,
    available: Sequence[AvailableFunds],
    purchase_costs_rate: float = config.HOME_PURCHASE_COSTS_RATE,
) -> Tuple[Tuple[float, float, float], ...]:
    """The highest amounts of each member for buying at ``price`` (#40, #42).

    Like :func:`suggested_amounts`; the sources are used in the order savings of everyone,
    3a of everyone, pension funds of everyone (the first person first in each). Together the
    amounts cover no more than the purchase needs. A pension fund withdrawal below the
    minimum is left out. Amounts in whole CHF, rounded down.
    """
    price = home.validate_price(price)
    costs = price * purchase_costs_rate
    hard_open = price + costs
    savings = []
    for funds in available:
        amount = math.floor(min(funds.savings, hard_open))
        savings.append(amount)
        hard_open -= amount
    pillar3a = []
    for funds in available:
        amount = math.floor(min(funds.pillar3a, hard_open))
        pillar3a.append(amount)
        hard_open -= amount
    hard_equity = max(0.0, sum(savings) + sum(pillar3a) - costs)
    pension_open = price - hard_equity
    pillar2 = []
    for funds in available:
        amount = math.floor(min(funds.pillar2, pension_open))
        if amount < config.WEF_PILLAR2_MIN_AMOUNT:
            amount = 0
        pillar2.append(amount)
        pension_open -= amount
    return tuple(
        (float(item_savings), float(item_3a), float(item_2))
        for item_savings, item_3a, item_2 in zip(savings, pillar3a, pillar2)
    )


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
    return suggested_amounts_by_member(price, [available], purchase_costs_rate)[0]


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
    """Check the planned purchase of one person and its effect on the projection.

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
    member = Member(
        current_age,
        retirement_age,
        pot_2,
        pot_3a,
        pot_3b,
        income_annual=income_gross_annual,
        income_is_net=income_is_net,
        ahv_annual_at_retirement=ahv_annual_at_retirement,
        savings=inputs.savings,
        pillar3a=inputs.pillar3a,
        pillar2=inputs.pillar2,
    )
    return plan_joint_purchase(inputs, (member,))


def _pledged_path(
    share: float, pledged: Sequence[float], before: int, years: int, rate: float
) -> List[float]:
    """A member's share of the pledged 3a from today until the own retirement.

    After the household horizon (the first retirement) the rest keeps its return.
    """
    path = [0.0] * before + [share * value for value in pledged]
    while len(path) < years + 1:
        path.append(path[-1] * (1 + rate))
    return path


def _check_member_amounts(member: Member) -> None:
    label = member.label
    _member_amount(member.savings, f"{label}: Das Ersparte muss mindestens 0 CHF betragen.")
    _member_amount(
        member.pillar3a, f"{label}: Das 3a-Geld für den Kauf muss mindestens 0 CHF betragen."
    )
    _member_amount(
        member.pillar2,
        f"{label}: Das Pensionskassengeld für den Kauf muss mindestens 0 CHF betragen.",
    )


def plan_joint_purchase(inputs: HomeInputs, members: Sequence[Member]) -> HomePlan:
    """Check a purchase by one or two persons and its effect on their projections (#42, #46).

    The price, the timing (age of the first person), the gross income (empty = the incomes of
    all members), the rates and the amortisation come from ``inputs``; the money for the
    purchase comes from each member (the amounts in ``inputs`` are not used). Equity and
    affordability use the sums. Each withdrawal is checked against the WEF limits of the
    person whose money it is and lowers only that person's projection.

    Model assumptions for a household (MODELLANNAHME): the 2nd mortgage is amortised until
    the first retirement, which also ends the household paths; the pledged 3a is shared by
    the free 3a room of each member; the check in retirement uses the debt at the first
    retirement and the pensions of all members at their own retirement.
    """
    members = tuple(members)
    household = len(members) > 1
    years_until = years_until_purchase(inputs.purchase_age, members)
    horizon = min(member.years for member in members)
    years_left = horizon - years_until
    if inputs.gross_income is None:
        gross_income = sum(member.income_annual for member in members)
        from_net = any(member.income_is_net for member in members)
    else:
        gross_income, from_net = inputs.gross_income, False

    if household:
        for member in members:
            _check_member_amounts(member)
    savings_in = [_zero_if_empty(member.savings) for member in members]
    pillar3a_in = [_zero_if_empty(member.pillar3a) for member in members]
    pillar2_in = [_zero_if_empty(member.pillar2) for member in members]

    def total(amounts: List[Any]) -> Any:
        # One person: the entered value as is, so that home.py checks it with its messages.
        return amounts[0] if not household else sum(amounts)

    assessment = home.assess_purchase(
        inputs.price,
        total(savings_in),
        total(pillar3a_in),
        total(pillar2_in),
        gross_income,
        years_left,
        inputs.imputed_rate,
    )
    max_price = home.max_affordable_price(
        total(savings_in),
        total(pillar3a_in),
        total(pillar2_in),
        gross_income,
        years_left,
        inputs.imputed_rate,
    )
    states = [_member_at_purchase(member, years_until) for member in members]
    available = _total_funds([state.available for state in states])
    max_price_available = home.max_affordable_price(
        available.savings,
        available.pillar3a,
        available.pillar2,
        gross_income,
        years_left,
        inputs.imputed_rate,
    )

    def source(member: Member, text: str) -> str:
        return f"{text} von {member.label}" if household else text

    used = []
    for member, state, savings, pillar3a, pillar2 in zip(
        members, states, savings_in, pillar3a_in, pillar2_in
    ):
        pillar2_used = wef.check_amount(
            pillar2, state.pillar2_limit, source(member, "aus der Pensionskasse")
        )
        pillar3a_used = wef.check_amount(
            pillar3a, state.pillar3a_limit, source(member, "aus der Säule 3a")
        )
        used.append((float(savings), pillar3a_used, pillar2_used))

    base_paths = []
    rooms = []
    for member, (savings, pillar3a_used, pillar2_used) in zip(members, used):
        base_paths.append(
            Paths(
                member.pot_2.path(member.years, {years_until: pillar2_used}),
                member.pot_3a.path(member.years, {years_until: pillar3a_used}),
                member.pot_3b.path(member.years, {years_until: savings}),
            )
        )
        # The pledged 3a payments share the yearly 3a limit with the 3a plan; with life phases
        # the plan pays a different amount each year, so the highest one from the purchase on.
        plan_3a = member.pot_3a.annual_contribution
        if isinstance(plan_3a, Sequence):
            plan_3a = max(plan_3a[years_until:], default=0.0)
        rooms.append(max(0.0, config.PILLAR3A_ANNUAL_MAX - plan_3a))
    room = sum(rooms)
    if room > 0:
        shares = [item / room for item in rooms]
    else:
        shares = [1.0] + [0.0] * (len(members) - 1)
    # One person: the 3a return. Two: weighted by the share of the pledged payments.
    pledged_return = sum(
        share * member.pot_3a.annual_return for share, member in zip(shares, members)
    )

    if inputs.amortisation not in mortgage.MODES:
        raise ValueError("Bitte wähle direkte oder indirekte Amortisation.")
    plans = {
        mode: mortgage.amortisation_plan(
            assessment.mortgage,
            assessment.first_mortgage,
            assessment.amortisation_years,
            years_left,
            inputs.mortgage_rate,
            mode,
            pledged_return=pledged_return,
            pledged_cap=room,
        )
        for mode in mortgage.MODES
    }
    member_paths = []
    for member, paths, share in zip(members, base_paths, shares):
        by_mode = {}
        for mode, plan in plans.items():
            pledged = _pledged_path(
                share, plan.pledged_3a, years_until, member.years, member.pot_3a.annual_return
            )
            by_mode[mode] = Paths(
                paths.pillar2,
                [value + extra for value, extra in zip(paths.pillar3a, pledged)],
                paths.pillar3b,
            )
        member_paths.append(by_mode)

    def household_paths(all_paths: Sequence[Paths]) -> Paths:
        """The sum of all members until the first retirement."""

        def summed(name: str) -> List[float]:
            return [
                sum(values)
                for values in zip(*(getattr(paths, name)[: horizon + 1] for paths in all_paths))
            ]

        return Paths(summed("pillar2"), summed("pillar3a"), summed("pillar3b"))

    before = [0.0] * years_until
    property_value = before + [assessment.price] * (years_left + 1)
    ahv_values = [member.ahv_annual_at_retirement for member in members]
    ahv_total = None if None in ahv_values else sum(ahv_values)

    def outcome(mode: str) -> MortgageOutcome:
        plan = plans[mode]
        paths = household_paths([by_mode[mode] for by_mode in member_paths])
        debt = before + list(plan.debt)
        net_wealth = [
            sum(values) - owed
            for *values, owed in zip(
                paths.pillar2, paths.pillar3a, paths.pillar3b, property_value, debt
            )
        ]
        pension_capital = sum(by_mode[mode].pillar2[-1] for by_mode in member_paths)
        return MortgageOutcome(
            plan=plan,
            paths=paths,
            property_value=property_value,
            debt=debt,
            net_wealth=net_wealth,
            retirement=mortgage.retirement_affordability(
                debt[-1],
                assessment.price,
                pension_capital,
                ahv_total,
                imputed_rate=inputs.imputed_rate,
            ),
        )

    outcomes = {mode: outcome(mode) for mode in mortgage.MODES}
    purchases = tuple(
        PersonPurchase(
            label=member.label,
            purchase_age=member.current_age + years_until,
            years_until_purchase=years_until,
            savings=savings,
            pillar3a_used=pillar3a_used,
            pillar2_used=pillar2_used,
            available=state.available,
            balances_at_purchase=state.balances,
            pillar2_limit=state.pillar2_limit,
            pillar3a_limit=state.pillar3a_limit,
            savings_outside_3b=max(0.0, savings - state.balances[2]),
            without_purchase=state.without,
            paths_by_mode=by_mode,
            amortisation=inputs.amortisation,
        )
        for member, state, (savings, pillar3a_used, pillar2_used), by_mode in zip(
            members, states, used, member_paths
        )
    )
    return HomePlan(
        years_until_purchase=years_until,
        gross_income=assessment.gross_annual_income,
        gross_income_from_net=from_net,
        assessment=assessment,
        max_price=max_price,
        available=available,
        max_price_available=max_price_available,
        without_purchase=household_paths([state.without for state in states]),
        amortisation=inputs.amortisation,
        mortgage_rate=float(inputs.mortgage_rate),  # validated by amortisation_plan
        outcomes=outcomes,
        members=purchases,
    )
