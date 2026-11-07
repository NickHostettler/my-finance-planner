"""Edge cases and input validation of the calculation core."""

import pytest

from personal_finance import config
from personal_finance.calculator import FinanceCalculator
from personal_finance.core import ahv
from personal_finance.core.income import normalize_income
from personal_finance.core.pillar_2 import Pillar2Calculator
from personal_finance.core.pillar_3a import Pillar3aCalculator
from personal_finance.core.pillar_3b import Pillar3bCalculator
from personal_finance.core.savings import SavingsCalculator


# --- income -----------------------------------------------------------------------


@pytest.mark.parametrize("amount", [None, 0, -100, float("nan"), float("inf")])
def test_income_must_be_a_positive_finite_number(amount):
    with pytest.raises(ValueError, match="größer als 0"):
        normalize_income(amount, "monthly", "net", 35, "ZH")


@pytest.mark.parametrize(
    ("period", "income_type", "canton", "message"),
    [
        ("weekly", "net", "ZH", "Zeitraum"),
        ("monthly", "taxed", "ZH", "Brutto oder Netto"),
        ("monthly", "gross", "XX", "Kanton"),
    ],
)
def test_income_rejects_unknown_choices(period, income_type, canton, message):
    with pytest.raises(ValueError, match=message):
        normalize_income(5000, period, income_type, 35, canton)


# --- configuration ------------------------------------------------------------------


def test_youngest_age_group_has_its_own_pillar2_rate():
    assert config.get_pillar2_contribution_rate(20) == (
        config.PILLAR2_CONTRIBUTION_RATES["age_under_25"]
    )


# --- AHV ----------------------------------------------------------------------------


def test_missing_ahv_pension_stays_missing():
    assert ahv.project_pension_basis(None, 30, 0.01, "nominal") is None


@pytest.mark.parametrize(
    ("pension", "years", "inflation", "basis"),
    [
        (float("nan"), 30, 0.01, "nominal"),
        (-1, 30, 0.01, "nominal"),
        (2000, -1, 0.01, "nominal"),
        (2000, 30, -1, "nominal"),
        (2000, 30, 0.01, "future"),
    ],
)
def test_ahv_projection_rejects_invalid_values(pension, years, inflation, basis):
    with pytest.raises(ValueError, match="AHV-Rentenprojektion"):
        ahv.project_pension_basis(pension, years, inflation, basis)


# --- pillar 2 / 3a / 3b without interest or without time left -------------------------


def test_pillar2_capital_is_zero_when_already_at_retirement_age():
    result = Pillar2Calculator(annual_net_income=80000, current_age=65).calculate()

    assert result.annual_contribution_total > 0
    assert result.estimated_capital_at_retirement == 0


def test_pillar2_without_interest_just_adds_up_contributions():
    calc = Pillar2Calculator(annual_net_income=80000, current_age=35)
    calc.ASSUMED_ANNUAL_RETURN = 0

    result = calc.calculate()

    assert result.estimated_capital_at_retirement == pytest.approx(
        result.annual_contribution_total * 30
    )


@pytest.mark.parametrize("calculator_class", [Pillar3aCalculator, Pillar3bCalculator])
def test_third_pillar_without_interest_has_no_investment_gains(calculator_class):
    calc = calculator_class(annual_net_income=60000, current_age=35, assumed_annual_return=0)

    result = calc.calculate_by_monthly_amount(300)

    assert result.total_at_retirement == pytest.approx(300 * 12 * 30)
    assert result.investment_gains == 0


# --- savings --------------------------------------------------------------------------


@pytest.mark.parametrize("rate", [-0.01, 1.01])
def test_savings_rate_must_be_between_zero_and_one(rate):
    with pytest.raises(ValueError, match="zwischen 0 und 1"):
        SavingsCalculator(monthly_net_income=5000).analyze_by_savings_rate(rate)


def test_negative_monthly_savings_are_rejected():
    with pytest.raises(ValueError, match="nicht negativ"):
        SavingsCalculator(monthly_net_income=5000).analyze_by_monthly_amount(-1)


# --- finance calculator ---------------------------------------------------------------


@pytest.fixture
def calculator():
    return FinanceCalculator(monthly_net_income=5000, current_age=35, retirement_age=65)


@pytest.mark.parametrize(
    "method", ["calculate_pillar3a", "calculate_pillar3b", "calculate_savings_analysis"]
)
def test_rate_or_amount_is_required(calculator, method):
    with pytest.raises(ValueError, match="savings_rate oder monthly_amount"):
        getattr(calculator, method)()


def test_pillar3b_can_be_calculated_from_a_savings_rate(calculator):
    result = calculator.calculate_pillar3b(savings_rate=0.10)

    assert result.monthly_savings == pytest.approx(500)


def test_calculator_analyses_savings_by_monthly_amount(calculator):
    assert calculator.calculate_savings_analysis(monthly_amount=500).savings_rate == 0.1


def test_summary_without_third_pillar_scenarios_contains_only_pillar2(calculator):
    pillar2 = calculator.calculate_pillar2()
    savings = calculator.calculate_savings_analysis(savings_rate=0.10)

    summary = calculator._create_summary(pillar2, {}, {}, savings)

    assert summary["total_retirement_capital_best_case"] == pillar2.estimated_capital_at_retirement
    assert summary["total_retirement_capital_moderate"] == pillar2.estimated_capital_at_retirement
    assert summary["pillar3a_scenarios_count"] == summary["pillar3b_scenarios_count"] == 0


def test_income_below_bvg_threshold_gets_a_hint():
    calc = FinanceCalculator(monthly_net_income=1000, current_age=35)

    recommendations = calc.complete_analysis().summary["recommendations"]

    assert any("unterhalb der BVG-Mindestversicherung" in text for text in recommendations)


def test_very_high_savings_rate_gets_a_warning(calculator):
    recommendations = calculator.complete_analysis(pillar3a_savings_rate=0.30).summary[
        "recommendations"
    ]

    assert any("sehr hoch" in text for text in recommendations)
