"""A household of two persons and their joint home purchase (issues #41, #42, #44, #46)."""

import math

import pytest

from personal_finance import config
from personal_finance.core import ahv, home, mortgage
from personal_finance.core.home_plan import (
    AvailableFunds,
    HomeInputs,
    Member,
    Pot,
    available_funds_by_member,
    plan_joint_purchase,
    plan_purchase,
    suggested_amounts,
    suggested_amounts_by_member,
    years_until_purchase,
)
from personal_finance.core.household import (
    CREDITS_A,
    CREDITS_B,
    CREDITS_HALF,
    MARRIED,
    PERSON_A,
    PERSON_B,
    UNMARRIED,
    Household,
    couple_ahv,
    shift_birth_ages,
    validate_household,
)
from personal_finance.core.part_time import ahv_monthly_pension

INPUTS = HomeInputs(
    price=1_000_000,
    savings=None,  # a household takes the amounts from the members
    pillar3a=None,
    pillar2=None,
    purchase_age=None,
    gross_income=None,
    imputed_rate=0.05,
)

# No contributions and no return: the balances stay the same.
POTS_A = (Pot(0, 0, 150_000), Pot(0, 0, 40_000), Pot(0, 0, 100_000))
POTS_B = (Pot(0, 0, 80_000), Pot(0, 0, 20_000), Pot(0, 0, 60_000))


def member_a(**changes):
    values = dict(
        current_age=40,
        retirement_age=65,
        pot_2=POTS_A[0],
        pot_3a=POTS_A[1],
        pot_3b=POTS_A[2],
        label=PERSON_A,
        income_annual=120_000,
        savings=100_000,
        pillar3a=40_000,
        pillar2=0,
    )
    return Member(**{**values, **changes})


def member_b(**changes):
    values = dict(
        current_age=38,
        retirement_age=64,  # 26 years, one more than person A
        pot_2=POTS_B[0],
        pot_3a=POTS_B[1],
        pot_3b=POTS_B[2],
        label=PERSON_B,
        income_annual=80_000,
        savings=60_000,
        pillar3a=0,
        pillar2=30_000,
    )
    return Member(**{**values, **changes})


def joint(a=None, b=None, **changes):
    inputs = HomeInputs(**{**INPUTS.__dict__, **changes})
    return plan_joint_purchase(inputs, (a or member_a(), b or member_b()))


class TestHousehold:
    def test_married_couples_share_the_credits_half_each(self):
        assert Household(MARRIED, CREDITS_A).credit_shares == (0.5, 0.5)
        assert Household().married

    @pytest.mark.parametrize(
        "credits, shares",
        [(CREDITS_HALF, (0.5, 0.5)), (CREDITS_A, (1.0, 0.0)), (CREDITS_B, (0.0, 1.0))],
    )
    def test_unmarried_parents_choose(self, credits, shares):
        household = validate_household(UNMARRIED, credits)
        assert household.credit_shares == shares
        assert not household.married

    def test_invalid_choices(self):
        with pytest.raises(ValueError, match="verheiratet"):
            validate_household("single")
        with pytest.raises(ValueError, match="Erziehungsgutschriften"):
            validate_household(MARRIED, "both")

    def test_no_credit_share(self):
        # Person B gets none of the credits: as without children.
        with_children = ahv_monthly_pension(60_000, 44, 65, [1.0] * 30, (30,), 0.0)
        assert with_children == ahv_monthly_pension(60_000, 44, 65, [1.0] * 30)


class TestCoupleAhv:
    def test_married_couple_is_capped_at_150_percent(self):
        # 2'560 + 2'000 = 4'560 > 1.5 * 2'560 = 3'840: both times 3'840 / 4'560.
        result = couple_ahv(2560, 2000, married=True)
        assert ahv.COUPLE_MAXIMUM_MONTHLY_PENSION == 3840
        assert result.capped
        assert result.uncapped_total == 4560
        assert result.person_a == pytest.approx(2560 * 3840 / 4560)
        assert result.person_b == pytest.approx(2000 * 3840 / 4560)
        assert result.total == pytest.approx(3840)

    def test_below_the_cap_or_unmarried_unchanged(self):
        assert couple_ahv(1800, 1900, married=True).capped is False
        unmarried = couple_ahv(2560, 2000, married=False)
        assert (unmarried.person_a, unmarried.person_b, unmarried.capped) == (2560, 2000, False)

    def test_unknown_pension(self):
        result = couple_ahv(None, 2000, married=True)
        assert (result.person_a, result.person_b, result.total) == (None, 2000, None)
        assert result.uncapped_total is None and not result.capped

    @pytest.mark.parametrize("value", [-1, math.nan, "2000", True])
    def test_invalid_pension(self, value):
        with pytest.raises(ValueError, match="AHV-Rente"):
            couple_ahv(value, 2000, married=True)


class TestBirthAges:
    def test_seen_from_person_b(self):
        # Person A is 40, person B 38: B was two years younger at each birth.
        assert shift_birth_ages((30, 33), 40, 38) == (28, 31)
        assert shift_birth_ages((30,), 35, 41) == (36,)

    def test_other_values_are_passed_on(self):
        assert shift_birth_ages((30.5, True, None), 40, 38) == (30.5, True, None)

    def test_not_born_yet(self):
        with pytest.raises(ValueError, match="Kind 2: Person B wäre bei der Geburt"):
            shift_birth_ages((30, 5), 40, 30)


class TestTiming:
    def test_one_person_until_one_year_before_retirement(self):
        assert years_until_purchase(None, [member_a()]) == 0
        assert years_until_purchase(64, [member_a()]) == 24

    def test_household_buys_before_the_first_retirement(self):
        early = member_b(current_age=54, retirement_age=64)  # retires in 10 years
        assert years_until_purchase(49, [member_a(), early]) == 9
        with pytest.raises(ValueError, match=r"Person A muss .* zwischen 40 und 49 sein"):
            years_until_purchase(50, [member_a(), early])
        with pytest.raises(ValueError, match="ersten Pensionierung"):
            years_until_purchase(39, [member_a(), early])


class TestJointPurchase:
    def test_equity_and_affordability_use_the_sums(self):
        result = joint()

        # Savings 100'000 + 60'000, 3a 40'000, pension fund 30'000; income 120'000 + 80'000.
        # The household is computed until the first retirement: person A in 25 years.
        expected = home.assess_purchase(1_000_000, 160_000, 40_000, 30_000, 200_000, 25)
        assert result.assessment == expected
        assert result.max_price == home.max_affordable_price(160_000, 40_000, 30_000, 200_000, 25)
        assert result.household
        assert (result.savings, result.pillar3a_used, result.pillar2_used) == (
            160_000,
            40_000,
            30_000,
        )
        assert result.gross_income == 200_000 and result.gross_income_from_net is False
        assert result.horizon == "ersten Pensionierung"

    def test_available_funds_of_both(self):
        result = joint()
        a, b = result.members
        # Person B: the whole pension fund (80'000) is available at 38.
        assert a.available == AvailableFunds(100_000, 40_000, 150_000)
        assert b.available == AvailableFunds(60_000, 20_000, 80_000)
        assert result.available == AvailableFunds(160_000, 60_000, 230_000)
        assert result.max_price_available == home.max_affordable_price(
            160_000, 60_000, 230_000, 200_000, 25
        )
        assert available_funds_by_member(None, [member_a(), member_b()]) == (
            a.available,
            b.available,
        )

    def test_withdrawals_lower_only_the_own_projection(self):
        a, b = joint().members

        # Person A takes no pension fund money, person B 30'000 now.
        assert a.with_purchase.pillar2 == a.without_purchase.pillar2 == [150_000] * 26
        assert b.without_purchase.pillar2 == [80_000] * 27
        assert b.with_purchase.pillar2 == [50_000] * 27
        assert a.with_purchase.pillar3a == [0] * 26  # 40'000 3a used
        assert b.with_purchase.pillar3a == [20_000] * 27
        assert b.with_purchase.pillar3b == [0] * 27  # 60'000 of 60'000 savings
        assert (a.purchase_age, b.purchase_age) == (40, 38)

    def test_household_paths_end_at_the_first_retirement(self):
        result = joint()
        a, b = result.members
        assert len(result.without_purchase.pillar2) == 26
        assert result.without_purchase.pillar2 == [230_000] * 26
        assert result.with_purchase.pillar2 == [
            x + y for x, y in zip(a.with_purchase.pillar2, b.with_purchase.pillar2[:26])
        ]
        assert result.outcome.debt[-1] == pytest.approx(result.assessment.first_mortgage)

    def test_pledged_3a_is_shared_by_the_free_3a_room(self):
        # Neither person pays into 3a: both have the full yearly room, so half each.
        result = joint(amortisation=mortgage.INDIRECT)
        a, b = result.members
        plan = result.outcomes[mortgage.INDIRECT].plan
        assert plan.annual_pledged == pytest.approx(
            min(plan.annual_amortisation, 2 * config.PILLAR3A_ANNUAL_MAX)
        )
        for year in range(1, 26):
            extra_a = (
                a.paths_by_mode[mortgage.INDIRECT].pillar3a[year]
                - a.paths_by_mode[mortgage.DIRECT].pillar3a[year]
            )
            assert extra_a == pytest.approx(plan.pledged_3a[year] / 2)
        # Person B retires a year later; the rest of the pledged 3a stays (no return here).
        extra_b = [
            x - y
            for x, y in zip(
                b.paths_by_mode[mortgage.INDIRECT].pillar3a,
                b.paths_by_mode[mortgage.DIRECT].pillar3a,
            )
        ]
        assert len(extra_b) == 27
        assert extra_b[26] == pytest.approx(extra_b[25])

    def test_pledged_3a_with_a_return_after_the_first_retirement(self):
        b_pots = dict(pot_3a=Pot(0, 0.02, 20_000))
        result = joint(b=member_b(**b_pots), amortisation=mortgage.INDIRECT)
        b = result.members[1]
        extra = [
            x - y
            for x, y in zip(
                b.paths_by_mode[mortgage.INDIRECT].pillar3a,
                b.paths_by_mode[mortgage.DIRECT].pillar3a,
            )
        ]
        assert extra[26] == pytest.approx(extra[25] * 1.02)

    def test_no_3a_room_left(self):
        full = Pot(config.PILLAR3A_ANNUAL_MAX, 0, 40_000)
        result = joint(
            a=member_a(pot_3a=full),
            b=member_b(pot_3a=Pot(config.PILLAR3A_ANNUAL_MAX, 0, 20_000)),
            amortisation=mortgage.INDIRECT,
        )
        assert result.outcome.plan.annual_pledged == 0

    def test_retirement_check_with_both_pensions(self):
        result = joint(
            a=member_a(ahv_annual_at_retirement=30_000),
            b=member_b(ahv_annual_at_retirement=25_000),
        )
        retirement = result.outcome.retirement
        assert retirement.ahv_income == 55_000
        # Pension fund at the own retirement: 150'000 + 50'000.
        assert retirement.pension_income == pytest.approx(
            200_000 * config.HOME_RETIREMENT_CONVERSION_RATE
        )

    def test_retirement_check_without_one_ahv(self):
        result = joint(a=member_a(ahv_annual_at_retirement=30_000))
        assert result.outcome.retirement.ahv_income is None

    def test_gross_income_from_a_net_income_or_entered(self):
        assert joint(b=member_b(income_is_net=True)).gross_income_from_net is True
        entered = joint(gross_income=250_000)
        assert (entered.gross_income, entered.gross_income_from_net) == (250_000, False)

    def test_savings_outside_the_projection(self):
        result = joint(b=member_b(savings=70_000))
        assert result.members[1].savings_outside_3b == 10_000
        assert result.savings_outside_3b == 10_000

    @pytest.mark.parametrize(
        "changes, message",
        [
            ({"savings": -1}, "Person B: Das Ersparte"),
            ({"pillar3a": math.nan}, "Person B: Das 3a-Geld"),
            ({"pillar2": "1"}, "Person B: Das Pensionskassengeld"),
            ({"pillar2": True}, "Person B: Das Pensionskassengeld"),
            ({"pillar2": 100_000}, "Aus der Pensionskasse von Person B sind .* höchstens"),
            ({"pillar2": 10_000}, "aus der Pensionskasse von Person B muss mindestens"),
            ({"pillar3a": 30_000}, "Aus der Säule 3a von Person B sind .* höchstens"),
        ],
    )
    def test_each_amount_is_checked_for_its_person(self, changes, message):
        with pytest.raises(ValueError, match=message):
            joint(b=member_b(**changes))

    def test_timing_and_notes(self):
        now = joint()
        assert now.timing == "Kauf heute (Person A 40, Person B 38)"
        assert joint(purchase_age=41).timing == "Kauf in 1 Jahr (Person A 41, Person B 39)"
        later = joint(purchase_age=45)
        assert later.timing == "Kauf in 5 Jahren (Person A 45, Person B 43)"
        assert later.purchase_age == 45
        assert later.members[1].withdrawal_note() == (
            "Mit dem gemeinsamen Kauf mit 43 Jahren: Vorbezug Pensionskasse CHF 30’000, "
            "Erspartes aus dem freien Vermögen CHF 60’000 sind ab dann abgezogen. Details im "
            "Tab «Wohneigentum»."
        )
        assert later.members[1].used == 90_000

    def test_one_person_is_the_single_plan(self):
        inputs = HomeInputs(**{**INPUTS.__dict__, "savings": 100_000, "pillar3a": 40_000})
        single = plan_purchase(inputs, 40, 65, 120_000, False, *POTS_A)
        joined = plan_joint_purchase(
            inputs, (member_a(label="", savings=100_000, pillar3a=40_000, pillar2=None),)
        )
        assert single == joined
        assert not single.household
        assert single.timing == "Kauf mit 40 Jahren"
        assert single.horizon == "Pensionierung"
        assert single.available == single.members[0].available


class TestSuggestedAmounts:
    AVAILABLE = (AvailableFunds(100_000, 40_000, 150_000), AvailableFunds(60_000, 20_000, 80_000))

    def test_everything_is_used_for_a_high_price(self):
        assert suggested_amounts_by_member(1_000_000, self.AVAILABLE) == (
            (100_000, 40_000, 150_000),
            (60_000, 20_000, 80_000),
        )

    def test_savings_first_then_3a_of_both(self):
        # Price 200'000: costs 6'000, so 206'000 hard money at most. Savings 100'000 + 60'000,
        # then 3a 40'000 of person A and the last 6'000 from person B. Nothing from the
        # pension funds: the hard money already covers the price.
        assert suggested_amounts_by_member(200_000, self.AVAILABLE) == (
            (100_000, 40_000, 0),
            (60_000, 6_000, 0),
        )

    def test_pension_fund_below_the_minimum_is_left_out(self):
        # Price 300'000: costs 9'000; hard 220'000, so hard equity 211'000 and 89'000 open.
        # Person A gives 85'000 from the pension fund; person B's 4'000 is below 20'000.
        available = (AvailableFunds(100_000, 40_000, 85_000), self.AVAILABLE[1])
        assert suggested_amounts_by_member(300_000, available) == (
            (100_000, 40_000, 85_000),
            (60_000, 20_000, 0),
        )

    def test_one_person_like_before(self):
        funds = self.AVAILABLE[0]
        assert suggested_amounts(300_000, funds) == suggested_amounts_by_member(300_000, [funds])[0]
