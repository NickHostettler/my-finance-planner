"""Family planning: allowances, parental leave and child costs (issue #32)."""

import math

import pytest

from personal_finance import config
from personal_finance.core.family import (
    MAX_CHILDREN,
    OTHER_PARENT,
    Family,
    FamilyYear,
    family_years,
    leave_allowance,
    validate_birth_ages,
)
from personal_finance.core.life_phases import LifePhase, yearly_plan


def year(age, family=Family((32,)), income=6_000, costs=0, savings=0):
    return family_years([age], [income], [costs], [savings], family)[0]


class TestAllowances:
    @pytest.mark.parametrize(
        ("age", "under_16", "in_education", "allowances"),
        [
            (31, 0, 0, 0),  # before the birth
            (32, 1, 0, 2_580),  # year of birth counts fully: 215 x 12
            (47, 1, 0, 2_580),  # child 15
            (48, 0, 1, 3_216),  # child 16: education allowance 268 x 12
            (56, 0, 1, 3_216),  # child 24
            (57, 0, 0, 0),  # child 25: no more allowance
        ],
    )
    def test_by_the_age_of_the_child(self, age, under_16, in_education, allowances):
        result = year(age)

        assert (result.children_under_16, result.children_in_education) == (under_16, in_education)
        assert result.allowances == allowances

    def test_one_allowance_per_child(self):
        # Children born at 30 and 34; at 47 they are 17 and 13.
        result = year(47, Family((34, 30)))

        assert result.allowances == 12 * (215 + 268)

    def test_cantons_may_pay_more(self):
        result = year(40, Family((32,), child_allowance=300, education_allowance=350))

        assert result.allowances == 3_600

    def test_minimum_amounts(self):
        assert (config.CHILD_ALLOWANCE_MONTHLY, config.EDUCATION_ALLOWANCE_MONTHLY) == (215, 268)


class TestParentalLeave:
    def test_mother_gets_80_percent_for_14_weeks(self):
        # 6'000 / 30 = 200 a day, 80 % = 160; 98 days: 15'680 paid, 3'920 not replaced.
        assert leave_allowance(6_000, 98) == pytest.approx((15_680, 3_920))
        result = year(32)
        assert result.leave_days == 98
        assert result.leave_allowance == pytest.approx(15_680)
        assert result.leave_loss == pytest.approx(3_920)

    def test_daily_maximum(self):
        # 9'000 / 30 = 300 a day, 80 % = 240, capped at 220: 80 a day not replaced.
        paid, lost = leave_allowance(9_000, 98)

        assert paid == pytest.approx(220 * 98)
        assert lost == pytest.approx(80 * 98)

    def test_other_parent_gets_2_weeks(self):
        result = year(32, Family((32,), role=OTHER_PARENT))

        assert result.leave_days == 14
        assert result.leave_allowance == pytest.approx(2_240)  # 160 x 14
        assert result.leave_loss == pytest.approx(560)

    def test_twins_do_not_double_the_leave(self):
        assert year(32, Family((32, 32))).leave_days == 98

    def test_no_leave_without_a_salary_or_birth(self):
        assert year(32, income=0).leave_days == 0
        assert year(33).leave_days == 0
        assert year(33).leave_loss == 0


class TestWhatIsLeft:
    def test_income_allowances_leave_costs_and_savings(self):
        # 72'000 + 2'580 - 3'920 - 12'000 = 58'660; after 6'000 savings 52'660.
        result = year(32, costs=12_000, savings=6_000)

        assert result.income == 72_000
        assert result.left_before_savings == pytest.approx(58_660)
        assert result.left_after_savings == pytest.approx(52_660)
        assert not result.costs_exceed_income

    def test_warning_when_costs_and_savings_exceed_the_income(self):
        # 2'500 x 12 = 30'000 + 2'580 allowances < 30'000 costs + 3'600 savings.
        result = year(40, income=2_500, costs=30_000, savings=3_600)

        assert result.left_after_savings == pytest.approx(-1_020)
        assert result.costs_exceed_income

    def test_with_the_yearly_plan(self):
        phases = [LifePhase(30, 64, 1, 6_000, child_costs=1_000)]
        plan = yearly_plan(phases, 30, 65, 0, 300, 200)
        savings = [a + b for a, b in zip(plan.pillar3a, plan.pillar3b)]

        result = family_years(plan.ages, plan.monthly_income, plan.child_costs, savings, Family())

        assert len(result) == 35
        assert result[0].child_costs == 12_000
        assert result[1].child_costs == pytest.approx(12_000 * (1 + config.INFLATION_RATE))
        assert result[0].savings == 6_000
        assert isinstance(result[0], FamilyYear)


class TestValidation:
    def test_birth_ages_sorted(self):
        assert validate_birth_ages([35, 31]) == (31, 35)

    @pytest.mark.parametrize(
        ("family", "message"),
        [
            ("kids", "Angaben zur Familie"),
            (Family(role="father"), "Mutter oder der andere Elternteil"),
            (Family(child_allowance=-1), "Kinderzulage"),
            (Family(child_allowance=True), "Kinderzulage"),
            (Family(education_allowance=math.nan), "Ausbildungszulage"),
            (Family(education_allowance=None), "Ausbildungszulage"),
            (Family((30,) * (MAX_CHILDREN + 1)), "höchstens 10 Kinder"),
            (Family("32"), "Alter bei der Geburt"),
            (Family((32.5,)), "Alter bei der Geburt"),
        ],
    )
    def test_invalid_family(self, family, message):
        with pytest.raises(ValueError, match=message):
            family_years([30], [6_000], [0], [0], family)

    def test_invalid_child_costs_in_a_phase(self):
        with pytest.raises(ValueError, match="Phase 1: Die Kinderkosten"):
            yearly_plan([LifePhase(30, 64, 1, 6_000, child_costs=-5)], 30, 65, 0, 0, 0)
