"""A planned home purchase in the personal plan (issues #25–#27)."""

import math

import pytest

from personal_finance import config
from personal_finance.core import home, mortgage
from personal_finance.core.home_plan import HomeInputs, Pot, plan_purchase, purchase_age
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


def plan(inputs=INPUTS, current_age=35, retirement_age=65, income=200_000, income_is_net=False,
         pots=POTS, ahv_annual=None, **changes):
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
            80_000, 50_000, 170_000
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

        assert note.startswith("Mit dem geplanten Kauf mit 45 Jahren: Vorbezug Pensionskasse "
                               "CHF 80’000, Bezug 3a CHF 50’000, Erspartes aus dem freien "
                               "Vermögen CHF 170’000 sind ab dann abgezogen.")
        only_3a = plan(savings=0, pillar3a=0, pillar2=0, price=100_000,
                       pots=(Pot(0, 0, 0), Pot(0, 0, 0), Pot(0, 0, 0)))
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
                paths.pillar2[year] + paths.pillar3a[year] + paths.pillar3b[year]
                + outcome.property_value[year] - outcome.debt[year]
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
        [({"amortisation": "monthly"}, "direkte oder indirekte"),
         ({"mortgage_rate": -0.01}, "Hypothekarzins")],
    )
    def test_invalid_mortgage_inputs(self, changes, message):
        with pytest.raises(ValueError, match=message):
            self.later(**changes)


def test_projection_without_withdrawals_is_unchanged():
    assert project_balance(1000, 3, 0.05, 500) == project_balance(1000, 3, 0.05, 500, 0, {})
    assert project_balance(0, 1, 0, 100, withdrawals={0: 30}) == [70, 70]
    assert project_balance(0, 2, 0, 100, withdrawals={1: 300}) == [100, 0, 0]
