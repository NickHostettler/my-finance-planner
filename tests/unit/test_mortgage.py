"""Mortgage after the purchase: direct/indirect amortisation, retirement (issue #27).

Example: mortgage 800'000, 1st mortgage 666'666.67, 2nd mortgage 133'333.33 amortised in
10 years = 13'333.33 per year, 20 years until retirement, interest 2 %.
"""

import math

import pytest

from personal_finance import config
from personal_finance.core.mortgage import (
    DIRECT,
    INDIRECT,
    amortisation_plan,
    retirement_affordability,
)

MORTGAGE, FIRST = 800_000, 800_000 - 400_000 / 3
SECOND = MORTGAGE - FIRST


def plan(mode, **changes):
    arguments = dict(
        mortgage=MORTGAGE, first_mortgage=FIRST, years=10, horizon=20, rate=0.02, mode=mode
    )
    return amortisation_plan(**{**arguments, **changes})


class TestDirect:
    def test_debt_falls_every_year_until_the_first_mortgage(self):
        result = plan(DIRECT)

        assert result.annual_amortisation == pytest.approx(SECOND / 10)
        assert (result.annual_direct, result.annual_pledged) == (result.annual_amortisation, 0)
        assert len(result.debt) == 21
        assert result.debt[0] == MORTGAGE
        assert result.debt[1] == pytest.approx(MORTGAGE - SECOND / 10)
        assert result.debt[10] == pytest.approx(FIRST)
        assert result.debt[-1] == pytest.approx(FIRST)
        assert set(result.pledged_3a) == {0}

    def test_interest_on_the_debt_of_each_year(self):
        result = plan(DIRECT)

        assert len(result.interest) == 20
        assert result.interest[0] == pytest.approx(16_000)
        # 10 years falling from 800'000, then 10 years on the 1st mortgage.
        expected = sum((MORTGAGE - SECOND / 10 * year) * 0.02 for year in range(10))
        expected += 10 * FIRST * 0.02
        assert result.total_interest == pytest.approx(expected)


class TestIndirect:
    def test_debt_stays_until_the_pledged_3a_repays_it(self):
        result = plan(INDIRECT, pledged_return=0.0)

        assert result.annual_pledged == pytest.approx(SECOND / 10)
        assert result.annual_direct == pytest.approx(0)
        assert all(debt == MORTGAGE for debt in result.debt[:10])
        assert result.debt[10] == pytest.approx(FIRST)
        assert result.pledged_3a[9] == pytest.approx(SECOND / 10 * 9)
        assert result.pledged_3a[10] == pytest.approx(0, abs=1e-6)  # no return: nothing left

    def test_return_on_the_pledged_3a_stays_in_3a(self):
        result = plan(INDIRECT, pledged_return=0.04)
        payments = SECOND / 10
        saved = sum(payments * 1.04 ** (10 - year) for year in range(10))

        assert result.debt[10] == pytest.approx(FIRST)
        assert result.pledged_3a[10] == pytest.approx(saved - SECOND)
        assert result.pledged_3a[11] == pytest.approx((saved - SECOND) * 1.04)

    def test_more_interest_than_direct(self):
        assert plan(INDIRECT).total_interest > plan(DIRECT).total_interest

    def test_payments_beyond_the_3a_limit_are_repaid_directly(self):
        result = plan(INDIRECT, pledged_cap=5_000)

        assert result.annual_pledged == 5_000
        assert result.annual_direct == pytest.approx(SECOND / 10 - 5_000)
        assert result.debt[5] == pytest.approx(MORTGAGE - 5 * (SECOND / 10 - 5_000))
        assert result.debt[10] == pytest.approx(FIRST)

    def test_negative_return_leaves_part_of_the_debt(self):
        result = plan(INDIRECT, pledged_return=-0.1)

        assert result.pledged_3a[10] == 0
        assert result.debt[10] > FIRST


def test_no_second_mortgage_means_no_amortisation():
    for mode in (DIRECT, INDIRECT):
        result = plan(mode, mortgage=500_000, first_mortgage=500_000)
        assert result.annual_amortisation == 0
        assert set(result.debt) == {500_000}


def test_amortisation_until_retirement():
    result = plan(DIRECT, years=5, horizon=5)

    assert len(result.debt) == 6
    assert result.debt[-1] == pytest.approx(FIRST)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"mortgage": -1}, "Hypothek muss"),
        ({"first_mortgage": MORTGAGE + 1}, "1. Hypothek"),
        ({"years": 0}, "Amortisationsdauer"),
        ({"horizon": 5}, "bis zur Pensionierung"),
        ({"rate": 0.2}, "Hypothekarzins"),
        ({"rate": None}, "Hypothekarzins"),
        ({"rate": math.nan}, "Hypothekarzins"),
        ({"mode": "other"}, "direkte oder indirekte"),
        ({"pledged_return": True}, "Rendite"),
        ({"pledged_cap": -1}, "3a-Limit"),
    ],
)
def test_invalid_inputs(changes, message):
    with pytest.raises(ValueError, match=message):
        plan(**{"mode": DIRECT, **changes})


class TestRetirement:
    def test_costs_against_pensions(self):
        # Costs: 600'000 x 5 % + 900'000 x 1 % = 39'000.
        # Income: 500'000 x 5 % = 25'000 + AHV 36'000 = 61'000 -> 63.9 %.
        result = retirement_affordability(600_000, 900_000, 500_000, 36_000)

        assert result.annual_costs == pytest.approx(39_000)
        assert result.pension_income == pytest.approx(25_000)
        assert result.annual_income == pytest.approx(61_000)
        assert result.cost_to_income == pytest.approx(39_000 / 61_000)
        assert result.affordable is False

    def test_affordable_with_little_debt(self):
        result = retirement_affordability(200_000, 900_000, 800_000, 36_000)

        assert result.cost_to_income == pytest.approx(19_000 / 76_000)
        assert result.affordable is True

    def test_exactly_one_third_is_affordable(self):
        result = retirement_affordability(0, 1_000_000, 0, 30_000, maintenance_rate=0.01)

        assert result.cost_to_income == pytest.approx(config.HOME_MAX_COST_TO_INCOME)
        assert result.affordable is True

    def test_without_ahv_estimate_only_the_pension_fund_counts(self):
        result = retirement_affordability(0, 500_000, 400_000)

        assert result.ahv_income is None
        assert result.annual_income == pytest.approx(20_000)

    def test_without_income(self):
        assert retirement_affordability(100, 100, 0).cost_to_income == math.inf
        assert retirement_affordability(0, 0, 0).cost_to_income == 0

    @pytest.mark.parametrize(
        ("arguments", "message"),
        [
            ((-1, 1, 1), "Hypothek bei Pensionierung"),
            ((1, -1, 1), "Kaufpreis"),
            ((1, 1, None), "Kapital der 2. Säule"),
            ((1, 1, 1, -5), "AHV-Rente"),
            ((1, 1, 1, None, 2), "kalkulatorische Zins"),
            ((1, 1, 1, None, 0.05, -1), "Unterhaltssatz"),
            ((1, 1, 1, None, 0.05, 0.01, "5"), "Umwandlungssatz"),
        ],
    )
    def test_invalid_inputs(self, arguments, message):
        with pytest.raises(ValueError, match=message):
            retirement_affordability(*arguments)
