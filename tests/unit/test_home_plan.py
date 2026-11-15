"""A planned home purchase in the personal plan (issues #25–#27)."""

import math

import pytest

from personal_finance.core import home
from personal_finance.core.home_plan import HomeInputs, plan_purchase, purchase_age

INPUTS = HomeInputs(
    price=1_000_000,
    savings=170_000,
    pillar3a=0,
    pillar2=60_000,
    purchase_age=None,
    gross_income=None,
    imputed_rate=0.05,
)


def plan(inputs=INPUTS, current_age=35, retirement_age=65, income=200_000, income_is_net=False,
         **changes):
    return plan_purchase(
        HomeInputs(**{**inputs.__dict__, **changes}),
        current_age,
        retirement_age,
        income,
        income_is_net,
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
