"""A planned home purchase in the personal plan (issues #25–#27)."""

import math

import pytest

from personal_finance import config
from personal_finance.core import home, mortgage
from personal_finance.core.home_plan import (
    AvailableFunds,
    HomeInputs,
    Pot,
    available_funds,
    plan_purchase,
    purchase_age,
    suggested_amounts,
)
from personal_finance.core.projection import project_balance

INPUTS = HomeInputs(
    price=1_000_000,
    savings=170_000,
    pillar3a=0,
    pillar2=60_000,
    purchase_age=None,
    gross_income=None,
    imputed_rate=0.05,
)


# No contributions and no return: the balances stay the same until the purchase.
POTS = (Pot(0, 0, 100_000), Pot(0, 0, 0), Pot(0, 0, 200_000))


def plan(
    inputs=INPUTS,
    current_age=35,
    retirement_age=65,
    income=200_000,
    income_is_net=False,
    pots=POTS,
    ahv_annual=None,
    **changes,
):
    return plan_purchase(
        HomeInputs(**{**inputs.__dict__, **changes}),
        current_age,
        retirement_age,
        income,
        income_is_net,
        *pots,
        ahv_annual_at_retirement=ahv_annual,
    )


class TestPurchaseAge:
    def test_empty_means_now(self):
        assert purchase_age(None, 35, 65) == 35

    @pytest.mark.parametrize("age", [35, 50, 64, 40.0])
    def test_from_now_until_one_year_before_retirement(self, age):
        assert purchase_age(age, 35, 65) == int(age)

    @pytest.mark.parametrize("age", [34, 65, 70, 40.5, math.nan, "40", True])
    def test_outside_or_not_a_whole_number(self, age):
        with pytest.raises(ValueError, match=r"zwischen deinem aktuellen Alter \(35\).*\(64\)"):
            purchase_age(age, 35, 65)


class TestPlan:
    def test_matches_the_core_assessment(self):
        result = plan()

        expected = home.assess_purchase(1_000_000, 170_000, 0, 60_000, 200_000, 30)
        assert result.assessment == expected
        assert result.max_price == home.max_affordable_price(170_000, 0, 60_000, 200_000, 30)
        assert (result.purchase_age, result.years_until_purchase) == (35, 0)
        assert result.gross_income == 200_000
        assert result.gross_income_from_net is False

    def test_later_purchase_shortens_the_time_to_amortise(self):
        result = plan(purchase_age=55)

        assert result.years_until_purchase == 20
        assert result.assessment.amortisation_years == 10

    def test_net_income_is_flagged_unless_a_gross_income_is_entered(self):
        assert plan(income=120_000, income_is_net=True).gross_income_from_net is True

        entered = plan(income=120_000, income_is_net=True, gross_income=180_000)
        assert entered.gross_income_from_net is False
        assert entered.gross_income == 180_000

    def test_empty_equity_counts_as_zero(self):
        result = plan(savings=200_000, pillar3a=None, pillar2=None)

        assert result.assessment.pension_funds == 0
        assert result.assessment.hard_funds == 200_000

    @pytest.mark.parametrize(
        ("changes", "message"),
        [
            ({"price": None}, "Kaufpreis"),
            ({"savings": -1}, "Ersparte"),
            ({"imputed_rate": None}, "kalkulatorische Zins"),
            ({"gross_income": 0}, "Bruttoeinkommen"),
            ({"purchase_age": 80}, "Kaufalter"),
        ],
    )
    def test_invalid_inputs_raise_a_german_message(self, changes, message):
        with pytest.raises(ValueError, match=message):
            plan(**changes)


class TestWithdrawals:
    """Issue #26: the pension fund, 3a and savings drop at the purchase."""

    POTS = (Pot(10_000, 0.02, 150_000), Pot(7_000, 0.04, 40_000), Pot(6_000, 0.04, 100_000))

    def later(self, **changes):
        arguments = dict(purchase_age=45, pillar3a=50_000, pillar2=80_000, savings=170_000)
        return plan(pots=self.POTS, **{**arguments, **changes})

    def test_balances_drop_at_the_purchase_and_grow_on_afterwards(self):
        result = self.later()
        pot_2, pot_3a, pot_3b = self.POTS

        assert result.without_purchase.pillar2 == pot_2.path(30)
        assert result.with_purchase.pillar2 == project_balance(
            10_000, 30, 0.02, 150_000, withdrawals={10: 80_000}
        )
        assert result.with_purchase.pillar3a == pot_3a.path(30, {10: 50_000})
        assert result.with_purchase.pillar3b == pot_3b.path(30, {10: 170_000})
        # Before the purchase nothing changes.
        assert result.with_purchase.pillar2[:10] == result.without_purchase.pillar2[:10]
        balance_2, balance_3a, balance_3b = result.balances_at_purchase
        assert balance_2 == pot_2.path(30)[10]
        assert result.with_purchase.pillar2[10] == pytest.approx(balance_2 - 80_000)
        assert (result.pillar2_used, result.pillar3a_used, result.savings) == (
            80_000,
            50_000,
            170_000,
        )

    def test_retirement_capital_is_lower_with_the_purchase(self):
        result = self.later()

        assert result.with_purchase.pillar2[-1] < result.without_purchase.pillar2[-1]
        assert result.with_purchase.pillar3a[-1] < result.without_purchase.pillar3a[-1]

    def test_from_50_the_projected_balance_at_50_counts(self):
        result = self.later(purchase_age=55, pillar2=20_000)
        balance_at_50 = self.POTS[0].path(30)[15]

        assert result.pillar2_limit.maximum == pytest.approx(
            max(balance_at_50, result.balances_at_purchase[0] / 2)
        )

    def test_already_older_than_50_uses_half(self):
        result = plan(pots=self.POTS, current_age=52, pillar2=60_000)

        assert result.pillar2_limit.maximum == pytest.approx(75_000)

    def test_savings_beyond_the_free_assets_come_from_outside(self):
        result = plan(pots=(Pot(0, 0, 100_000), Pot(0, 0, 0), Pot(0, 0, 50_000)))

        assert result.savings_outside_3b == 120_000
        assert result.with_purchase.pillar3b == [0.0] * 31

    @pytest.mark.parametrize(
        ("changes", "message"),
        [
            ({"pillar2": 400_000}, "Pensionskasse sind zum Kaufzeitpunkt höchstens"),
            ({"pillar3a": 500_000}, "Säule 3a sind zum Kaufzeitpunkt höchstens"),
        ],
    )
    def test_amounts_beyond_the_balances_are_rejected(self, changes, message):
        with pytest.raises(ValueError, match=message):
            self.later(**changes)

    def test_note_lists_only_what_is_taken(self):
        note = self.later().withdrawal_note()

        assert note.startswith(
            "Mit dem geplanten Kauf mit 45 Jahren: Vorbezug Pensionskasse "
            "CHF 80’000, Bezug 3a CHF 50’000, Erspartes aus dem freien "
            "Vermögen CHF 170’000 sind ab dann abgezogen."
        )
        only_3a = plan(
            savings=0,
            pillar3a=0,
            pillar2=0,
            price=100_000,
            pots=(Pot(0, 0, 0), Pot(0, 0, 0), Pot(0, 0, 0)),
        )
        assert only_3a.withdrawal_note() is None


class TestMortgage:
    """Issue #27: mortgage, amortisation and net wealth in the projection."""

    POTS = (Pot(10_000, 0.02, 150_000), Pot(3_000, 0.04, 40_000), Pot(6_000, 0.04, 100_000))

    def later(self, **changes):
        arguments = dict(purchase_age=45, pillar3a=0, pillar2=0, savings=200_000)
        return plan(pots=self.POTS, **{**arguments, **changes})

    def test_direct_debt_falls_and_net_wealth_counts_the_home(self):
        result = self.later()
        outcome = result.outcome

        assert result.amortisation == mortgage.DIRECT
        assert outcome.debt[:10] == [0.0] * 10  # before the purchase
        assert outcome.debt[10] == pytest.approx(result.assessment.mortgage)
        assert outcome.debt[-1] == pytest.approx(result.assessment.first_mortgage)
        assert outcome.property_value[9:11] == [0.0, 1_000_000]
        assert result.with_purchase.pillar3a == self.POTS[1].path(30)  # 3a untouched
        for year in (0, 10, 30):
            paths = outcome.paths
            assert outcome.net_wealth[year] == pytest.approx(
                paths.pillar2[year]
                + paths.pillar3a[year]
                + paths.pillar3b[year]
                + outcome.property_value[year]
                - outcome.debt[year]
            )
        assert result.net_wealth_without_purchase()[0] == 290_000

    def test_indirect_pays_into_a_pledged_3a_within_the_3a_limit(self):
        result = self.later(amortisation=mortgage.INDIRECT)
        indirect = result.outcome
        direct = result.outcomes[mortgage.DIRECT]

        assert indirect.plan.annual_pledged == pytest.approx(config.PILLAR3A_ANNUAL_MAX - 3_000)
        assert indirect.debt[11] > direct.debt[11]
        assert indirect.paths.pillar3a[11] > direct.paths.pillar3a[11]
        assert indirect.plan.total_interest > direct.plan.total_interest

    def test_3a_per_year_counts_its_highest_amount_from_the_purchase(self):
        # Life phases: 3a 7'000 until the purchase at 45, then 0 and 3'000; 3'000 counts.
        per_year = [7_000] * 10 + [0] * 10 + [3_000] * 10
        pots = (self.POTS[0], Pot(per_year, 0.04, 40_000), self.POTS[2])

        result = plan(
            pots=pots,
            purchase_age=45,
            pillar3a=0,
            pillar2=0,
            savings=200_000,
            amortisation=mortgage.INDIRECT,
        )

        assert result.outcome.plan.annual_pledged == pytest.approx(
            config.PILLAR3A_ANNUAL_MAX - 3_000
        )

    def test_retirement_check_uses_the_pension_after_the_withdrawal(self):
        result = self.later(pillar2=50_000, ahv_annual=30_000)
        retirement = result.outcome.retirement

        assert retirement.ahv_income == 30_000
        assert retirement.pension_income == pytest.approx(
            result.with_purchase.pillar2[-1] * config.HOME_RETIREMENT_CONVERSION_RATE
        )
        assert retirement.annual_costs == pytest.approx(
            result.outcome.debt[-1] * 0.05 + 1_000_000 * config.HOME_MAINTENANCE_RATE
        )

    @pytest.mark.parametrize(
        ("changes", "message"),
        [
            ({"amortisation": "monthly"}, "direkte oder indirekte"),
            ({"mortgage_rate": -0.01}, "Hypothekarzins"),
        ],
    )
    def test_invalid_mortgage_inputs(self, changes, message):
        with pytest.raises(ValueError, match=message):
            self.later(**changes)


class TestAvailableFunds:
    """Issue #40: the most that could go into the purchase at the purchase age."""

    # PK 100'000, 3a 30'000, free assets 200'000; nothing changes until the purchase.
    POTS = (Pot(0, 0, 100_000), Pot(0, 0, 30_000), Pot(0, 0, 200_000))

    def test_balances_and_wef_limits_now(self):
        available = available_funds(None, 35, 65, *self.POTS)

        assert available == AvailableFunds(savings=200_000, pillar3a=30_000, pillar2=100_000)
        assert available.hard == 230_000
        assert available.total == 330_000

    def test_later_purchase_uses_the_projection_at_that_age(self):
        pots = TestWithdrawals.POTS
        result = plan(pots=pots, purchase_age=55, pillar2=20_000)

        available = available_funds(55, 35, 65, *pots)

        assert available == result.available
        assert available.savings == pytest.approx(result.balances_at_purchase[2])
        assert available.pillar3a == pytest.approx(result.balances_at_purchase[1])
        # From 50 the WEF rule limits the pension fund money.
        assert available.pillar2 == pytest.approx(result.pillar2_limit.maximum)
        assert available.pillar2 < result.balances_at_purchase[0]

    def test_no_pension_fund_money_shortly_before_retirement(self):
        # Retirement at 65: an advance withdrawal is possible until 62.
        assert available_funds(63, 35, 65, *self.POTS).pillar2 == 0

    def test_invalid_purchase_age(self):
        with pytest.raises(ValueError, match="Kaufalter"):
            available_funds(70, 35, 65, *self.POTS)


class TestSuggestedAmounts:
    """Issue #40: the fields get the highest amounts, but no more than the purchase needs."""

    def test_everything_available_when_the_purchase_needs_more(self):
        # Price 1'000'000, purchase costs 30'000: savings 200'000 and 3a 30'000 give 200'000
        # hard equity after the costs; the pension fund may add up to 800'000.
        assert suggested_amounts(1_000_000, AvailableFunds(200_000, 30_000, 100_000)) == (
            200_000,
            30_000,
            100_000,
        )

    def test_savings_first_then_3a_then_the_pension_fund(self):
        # Price 500'000 + costs 15'000 = 515'000 are covered by the savings alone.
        amounts = suggested_amounts(500_000, AvailableFunds(600_000, 30_000, 100_000))

        assert amounts == (515_000, 0, 0)
        assessment = home.assess_purchase(500_000, *amounts, 200_000, 30)
        assert assessment.total_equity == pytest.approx(500_000)  # no "too much equity" error

    def test_no_pension_fund_money_below_the_minimum_withdrawal(self):
        # 450'000 + 50'000 - 15'000 costs = 485'000 hard equity: only 15'000 would be open,
        # less than the minimum advance withdrawal of 20'000.
        assert suggested_amounts(500_000, AvailableFunds(450_000, 50_000, 100_000)) == (
            450_000,
            50_000,
            0,
        )

    def test_pension_fund_money_when_savings_do_not_cover_the_costs(self):
        # 10'000 savings do not cover the 30'000 costs: hard equity 0, the PK may give 300'000.
        assert suggested_amounts(1_000_000, AvailableFunds(10_000, 0, 300_000)) == (
            10_000,
            0,
            300_000,
        )

    def test_whole_francs_rounded_down(self):
        amounts = suggested_amounts(1_000_000, AvailableFunds(100_000.7, 0.9, 25_000.5))

        assert amounts == (100_000, 0, 25_000)

    def test_suggested_amounts_pass_the_wef_checks(self):
        pots = TestWithdrawals.POTS
        available = available_funds(55, 35, 65, *pots)
        savings, pillar3a, pillar2 = suggested_amounts(1_000_000, available)

        result = plan(
            pots=pots, purchase_age=55, savings=savings, pillar3a=pillar3a, pillar2=pillar2
        )

        assert (result.savings, result.pillar3a_used, result.pillar2_used) == (
            savings,
            pillar3a,
            pillar2,
        )
        assert result.savings_outside_3b == 0

    def test_invalid_price(self):
        with pytest.raises(ValueError, match="Kaufpreis"):
            suggested_amounts(None, AvailableFunds(0, 0, 0))


def test_highest_price_with_everything_available():
    # 170'000 savings + 60'000 PK entered; available would be 200'000 free assets and 100'000
    # PK (3a: 0). The highest price with all of it uses the same rules and income.
    result = plan()

    assert result.max_price_available == home.max_affordable_price(200_000, 0, 100_000, 200_000, 30)
    assert result.max_price_available.price > result.max_price.price


def test_minimum_equity_of_the_plan():
    result = plan()

    # Price 1'000'000: 20 % equity, of which 10 % hard; purchase costs 3 % from hard funds.
    assert result.required_equity == pytest.approx(200_000)
    assert result.required_hard_equity == pytest.approx(100_000)
    assert result.required_funds == pytest.approx(230_000)
    assert result.required_hard_funds == pytest.approx(130_000)


def test_projection_without_withdrawals_is_unchanged():
    assert project_balance(1000, 3, 0.05, 500) == project_balance(1000, 3, 0.05, 500, 0, {})
    assert project_balance(0, 1, 0, 100, withdrawals={0: 30}) == [70, 70]
    assert project_balance(0, 2, 0, 100, withdrawals={1: 300}) == [100, 0, 0]
