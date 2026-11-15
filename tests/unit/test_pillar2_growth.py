"""Tests for salary-linked second-pillar contributions."""

import math

import pytest

from personal_finance import config
from personal_finance.core.pillar_2 import (
    Pillar2Calculator,
    Pillar2Result,
    estimated_contributions,
    growing_contributions,
    validate_salary_growth,
)
from personal_finance.core.projection import project_balance


@pytest.mark.parametrize(
    "growth",
    [True, False, None, "0.01", math.nan, math.inf, -0.01, config.SALARY_GROWTH_MAX + 0.01],
)
def test_invalid_salary_growth_is_rejected(growth):
    with pytest.raises(ValueError, match="jährliche Lohnzunahme"):
        validate_salary_growth(growth)


@pytest.mark.parametrize("growth", [0, 0.05, config.SALARY_GROWTH_MAX])
def test_valid_salary_growth_is_returned_as_a_float(growth):
    assert validate_salary_growth(growth) == float(growth)


def test_growing_contributions_increase_each_year():
    assert growing_contributions(1000, 3, 0.1) == pytest.approx([1000, 1100, 1210])


def test_estimated_contributions_match_current_estimate_without_growth():
    income = 84_000
    expected = Pillar2Calculator(income, 35).calculate().annual_contribution_total

    assert estimated_contributions(income, 35, 3, 0) == [expected] * 3


def test_estimated_contributions_follow_the_growing_income():
    income = 60_000
    contributions = estimated_contributions(income, 35, 3, 0.1)
    expected = [
        Pillar2Calculator(income * (1.1**year), 35).calculate().annual_contribution_total
        for year in range(3)
    ]

    assert contributions == pytest.approx(expected)
    assert contributions[0] < contributions[1] < contributions[2]


def test_pillar2_result_contributions_supports_fixed_and_growing_amounts():
    result = Pillar2Result(100, 100, 200, 0, 0, 2, 500)

    assert result.contributions() == 200
    result.annual_contributions = [200, 300]
    assert result.contributions() == [200, 300]


def test_projection_uses_each_years_contribution():
    assert project_balance([100, 200], 2, 0.1) == pytest.approx([0, 110, 341])
