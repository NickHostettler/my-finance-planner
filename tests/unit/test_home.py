"""Home ownership core: equity rules, affordability and the maximum price (issue #24).

The worked examples are calculated by hand in the comments.
"""

import math

import pytest

from personal_finance import config
from personal_finance.core import home
from personal_finance.core.home import (
    LIMIT_AFFORDABILITY,
    LIMIT_EQUITY,
    LIMIT_HARD_EQUITY,
    STATUS_AFFORDABLE,
    STATUS_NOT_AFFORDABLE,
    STATUS_TIGHT,
    assess_purchase,
    max_affordable_price,
)

# Price 1'000'000, purchase costs 3 % = 30'000, paid from savings/3a.
# Hard funds 140'000 + 30'000 = 170'000 -> hard equity 140'000 (14 %).
# With 60'000 from the pension fund: equity 200'000 = exactly 20 %.
EXAMPLE = {
    "price": 1_000_000,
    "savings": 140_000,
    "pillar3a": 30_000,
    "pillar2": 60_000,
    "gross_annual_income": 200_000,
    "years_until_retirement": 30,
    "imputed_rate": 0.05,
    "purchase_costs_rate": 0.03,
    "maintenance_rate": 0.01,
}
# Mortgage 800'000: 1st 666'666.67, 2nd 133'333.33 amortised in 15 years = 8'888.89/year.
# Costs: interest 40'000 + maintenance 10'000 + amortisation 8'888.89 = 58'888.89.
EXAMPLE_COSTS = 40_000 + 10_000 + 400_000 / 3 / 15


def assess(**overrides):
    return assess_purchase(**{**EXAMPLE, **overrides})


def price_limit(**overrides):
    arguments = {**EXAMPLE, **overrides}
    del arguments["price"]
    return max_affordable_price(**arguments)


class TestWorkedExample:
    def test_mortgage_and_equity(self):
        result = assess()

        assert result.purchase_costs == pytest.approx(30_000)
        assert result.hard_funds == pytest.approx(170_000)
        assert result.hard_equity == pytest.approx(140_000)
        assert result.pension_funds == 60_000
        assert result.total_equity == pytest.approx(200_000)
        assert result.equity_ratio == pytest.approx(0.20)
        assert result.hard_equity_ratio == pytest.approx(0.14)
        assert result.mortgage == pytest.approx(800_000)
        assert result.loan_to_value == pytest.approx(0.80)
        assert result.first_mortgage == pytest.approx(2_000_000 / 3)
        assert result.second_mortgage == pytest.approx(400_000 / 3)

    def test_costs_and_affordability(self):
        result = assess()

        assert result.amortisation_years == 15
        assert result.annual_amortisation == pytest.approx(8_888.89, abs=0.01)
        assert result.annual_imputed_interest == pytest.approx(40_000)
        assert result.annual_maintenance == pytest.approx(10_000)
        assert result.annual_costs == pytest.approx(EXAMPLE_COSTS)
        assert result.monthly_costs == pytest.approx(EXAMPLE_COSTS / 12)
        assert result.cost_to_income == pytest.approx(EXAMPLE_COSTS / 200_000)  # 29.4 %
        assert result.status == STATUS_AFFORDABLE
        assert result.reasons == ()
        assert result.missing_equity == result.missing_hard_equity == 0

    def test_lower_imputed_rate_lowers_the_costs(self):
        result = assess(imputed_rate=0.045)

        assert result.annual_imputed_interest == pytest.approx(36_000)

    def test_no_second_mortgage_means_no_amortisation(self):
        # 400'000 equity -> mortgage 600'000 is below 2/3 of the price.
        result = assess(savings=340_000, pillar3a=30_000, pillar2=60_000)

        assert result.second_mortgage == 0
        assert result.annual_amortisation == 0
        assert result.annual_costs == pytest.approx(600_000 * 0.05 + 10_000)

    def test_equity_equal_to_the_price_needs_no_mortgage(self):
        result = assess(savings=1_000_000, pillar3a=30_000, pillar2=0)

        assert result.mortgage == 0
        assert result.annual_costs == pytest.approx(10_000)
        assert result.status == STATUS_AFFORDABLE


class TestAmortisationByRetirement:
    @pytest.mark.parametrize(("years_left", "expected"), [(30, 15), (15, 15), (10, 10), (1, 1)])
    def test_second_mortgage_is_repaid_by_retirement(self, years_left, expected):
        result = assess(years_until_retirement=years_left)

        assert result.amortisation_years == expected
        assert result.annual_amortisation == pytest.approx(400_000 / 3 / expected)

    def test_helper_caps_at_fifteen_years(self):
        assert home.amortisation_years(40) == config.HOME_AMORTISATION_MAX_YEARS


class TestLimits:
    def test_exactly_twenty_percent_equity_is_enough(self):
        assert assess().missing_equity == 0

    def test_one_franc_less_than_twenty_percent_is_not_affordable(self):
        result = assess(pillar2=59_999)

        assert result.missing_equity == pytest.approx(1)
        assert result.status == STATUS_NOT_AFFORDABLE
        assert result.reasons == ("Es fehlen CHF 1 Eigenmittel (mindestens 20% des Kaufpreises).",)

    def test_exactly_ten_percent_hard_equity_is_enough(self):
        # Hard funds 130'000 - costs 30'000 = 100'000 = 10 %; the rest from the pension fund.
        result = assess(savings=100_000, pillar2=100_000)

        assert result.hard_equity == pytest.approx(100_000)
        assert result.missing_hard_equity == 0
        assert result.status == STATUS_AFFORDABLE

    def test_pension_money_does_not_replace_hard_equity(self):
        result = assess(savings=82_000, pillar2=118_000)

        assert result.total_equity == pytest.approx(200_000)
        assert result.missing_equity == 0
        assert result.missing_hard_equity == pytest.approx(18_000)
        assert result.status == STATUS_NOT_AFFORDABLE
        assert "Es fehlen CHF 18’000 harte Eigenmittel" in result.reasons[0]

    def test_costs_of_exactly_one_third_are_still_affordable_but_tight(self):
        result = assess(gross_annual_income=EXAMPLE_COSTS * 3)

        assert result.cost_to_income == pytest.approx(1 / 3)
        assert result.status == STATUS_TIGHT
        assert "nahe an der Grenze" in result.reasons[0]

    def test_costs_above_one_third_are_not_affordable(self):
        result = assess(gross_annual_income=EXAMPLE_COSTS * 3 - 1)

        assert result.status == STATUS_NOT_AFFORDABLE
        assert "erlaubt ist höchstens ⅓ (33.3 %)" in result.reasons[0]

    @pytest.mark.parametrize(
        ("ratio", "status"),
        [(0.30, STATUS_AFFORDABLE), (0.31, STATUS_TIGHT), (0.34, STATUS_NOT_AFFORDABLE)],
    )
    def test_traffic_light_thresholds(self, ratio, status):
        assert assess(gross_annual_income=EXAMPLE_COSTS / ratio).status == status

    def test_uncovered_purchase_costs_are_reported(self):
        result = assess(savings=10_000, pillar3a=0, pillar2=190_000)

        assert result.missing_purchase_costs == pytest.approx(20_000)
        assert result.hard_equity == 0
        assert result.status == STATUS_NOT_AFFORDABLE
        assert result.reasons[0].startswith("Die Kaufnebenkosten von CHF 30’000 sind nicht gedeckt")
        assert len(result.reasons) == 3  # costs, hard equity and total equity are missing

    def test_all_problems_are_listed(self):
        result = assess(savings=0, pillar3a=50_000, pillar2=0, gross_annual_income=50_000)

        assert result.status == STATUS_NOT_AFFORDABLE
        assert [reason.split(" ")[2] for reason in result.reasons] == [
            "CHF",  # Es fehlen CHF ... harte Eigenmittel
            "CHF",  # Es fehlen CHF ... Eigenmittel
            "betragen",  # Die Wohnkosten betragen ...
        ]


class TestValidation:
    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"price": 0}, "Kaufpreis"),
            ({"price": None}, "Kaufpreis"),
            ({"price": -1}, "Kaufpreis"),
            ({"price": math.nan}, "Kaufpreis"),
            ({"price": math.inf}, "Kaufpreis"),
            ({"price": "viel"}, "Kaufpreis"),
            ({"price": [1]}, "Kaufpreis"),
            ({"price": True}, "Kaufpreis"),
            ({"savings": -1}, "Ersparte"),
            ({"pillar3a": math.nan}, "3a-Geld"),
            ({"pillar2": None}, "Pensionskassengeld"),
            ({"gross_annual_income": 0}, "Bruttoeinkommen"),
            ({"years_until_retirement": 0}, "Pensionierung"),
            ({"years_until_retirement": 2.5}, "Pensionierung"),
            ({"years_until_retirement": True}, "Pensionierung"),
            ({"imputed_rate": 0}, "kalkulatorische Zins"),
            ({"imputed_rate": 0.16}, "kalkulatorische Zins"),
            ({"purchase_costs_rate": -0.01}, "Kaufnebenkosten"),
            ({"purchase_costs_rate": 0.11}, "Kaufnebenkosten"),
            ({"maintenance_rate": 0.06}, "Unterhalt"),
        ],
    )
    def test_invalid_inputs_are_rejected_with_a_message(self, overrides, message):
        with pytest.raises(ValueError, match=message):
            assess(**overrides)

    def test_equity_above_price_and_costs_is_rejected(self):
        with pytest.raises(ValueError, match="höher als Kaufpreis"):
            assess(savings=2_000_000)

    def test_max_price_validates_the_same_inputs(self):
        with pytest.raises(ValueError, match="Bruttoeinkommen"):
            price_limit(gross_annual_income=-5)


class TestMaxPrice:
    def test_limited_by_affordability(self):
        # No purchase costs, 300'000 hard equity, income 120'000 -> budget 40'000 per year.
        # With a 2nd mortgage: 0.05 (P - 300'000) + 0.01 P + (P/3 - 300'000) / 15 = 40'000
        # -> P (0.06 + 1/45) = 75'000 -> P = 912'162.16
        result = price_limit(
            savings=300_000,
            pillar3a=0,
            pillar2=0,
            gross_annual_income=120_000,
            purchase_costs_rate=0,
        )

        assert result.limited_by == LIMIT_AFFORDABILITY
        assert result.price == pytest.approx(75_000 / (0.06 + 1 / 45))

    def test_limited_by_total_equity(self):
        # 100'000 hard equity allow 1'000'000 (10 %) but only 500'000 (20 %) in total.
        result = price_limit(
            savings=100_000, pillar3a=0, pillar2=0, gross_annual_income=1_000_000,
            purchase_costs_rate=0,
        )

        assert result == home.MaxPrice(price=pytest.approx(500_000), limited_by=LIMIT_EQUITY)

    def test_limited_by_hard_equity(self):
        # 50'000 hard + 200'000 pension money: 20 % allows 1'250'000, 10 % hard only 500'000.
        result = price_limit(
            savings=30_000, pillar3a=20_000, pillar2=200_000, gross_annual_income=1_000_000,
            purchase_costs_rate=0,
        )

        assert result.limited_by == LIMIT_HARD_EQUITY
        assert result.price == pytest.approx(500_000)

    def test_purchase_costs_lower_the_maximum(self):
        # 100'000 must cover 3 % costs and 20 % equity: P = 100'000 / 0.23.
        result = price_limit(
            savings=100_000, pillar3a=0, pillar2=0, gross_annual_income=1_000_000
        )

        assert result.price == pytest.approx(100_000 / 0.23)

    def test_without_hard_equity_nothing_is_affordable(self):
        result = price_limit(savings=0, pillar3a=0, pillar2=200_000)

        assert result == home.MaxPrice(price=0, limited_by=LIMIT_HARD_EQUITY)

    @pytest.mark.parametrize("income", [90_000, 150_000, 250_000])
    def test_maximum_is_affordable_and_a_bit_more_is_not(self, income):
        result = price_limit(gross_annual_income=income)

        assert assess(price=result.price, gross_annual_income=income).status != (
            STATUS_NOT_AFFORDABLE
        )
        assert assess(price=result.price * 1.001, gross_annual_income=income).status == (
            STATUS_NOT_AFFORDABLE
        )

    def test_shorter_time_to_retirement_lowers_the_maximum(self):
        long_term = price_limit(gross_annual_income=150_000)
        short_term = price_limit(gross_annual_income=150_000, years_until_retirement=5)

        assert short_term.price < long_term.price
