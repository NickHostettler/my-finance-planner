"""Part time: 2nd pillar, 3a and AHV compared with full time (issue #31)."""

import pytest

from personal_finance import config
from personal_finance.core import ahv
from personal_finance.core.life_phases import (
    BY_WORKLOAD,
    FIXED,
    LifePhase,
    estimated_pillar2_by_year,
    full_time_phase,
    insured_salary,
    yearly_plan,
)
from personal_finance.core.part_time import (
    OWN,
    Pillar2Setup,
    ahv_monthly_pension,
    compare_with_full_time,
    education_credit_ages,
    pension_years,
    pillar3a_limit,
)
from personal_finance.core.pillar_2 import Pillar2Calculator

PHASES = [
    LifePhase(30, 33, 1.0, 7_500),
    LifePhase(34, 40, 0.6, 4_500),
    LifePhase(41, 65, 0.8, 6_400),
]


class TestInsuredSalary:
    @pytest.mark.parametrize(
        ("salary", "expected"),
        [
            (22_800, 0),  # below the entry threshold of 23'040
            (23_040, 0),  # at the threshold: not more than it
            (23_041, 3_840),  # just above: at least the minimum coordinated salary
            (54_000, 27_120),  # 54'000 - 26'880
            (120_000, 65_280),  # up to the upper limit: 92'160 - 26'880
        ],
    )
    def test_fixed_coordination_deduction(self, salary, expected):
        assert insured_salary(salary, 0.6, FIXED) == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("salary", "workload", "expected"),
        [
            (54_000, 0.6, 37_872),  # 54'000 - 0.6 x 26'880 = 54'000 - 16'128
            (120_000, 0.8, 70_656),  # 92'160 - 0.8 x 26'880 = 92'160 - 21'504
            (22_800, 0.3, 0),  # the entry threshold does not depend on the workload
        ],
    )
    def test_coordination_deduction_by_workload(self, salary, workload, expected):
        assert insured_salary(salary, workload, BY_WORKLOAD) == pytest.approx(expected)

    @pytest.mark.parametrize("salary", [10_000, 23_041, 30_000, 54_000, 92_160, 150_000])
    def test_fixed_is_the_same_as_the_bvg_estimate_without_phases(self, salary):
        expected = Pillar2Calculator(salary, 40).calculate()
        assert insured_salary(salary, 1.0) == pytest.approx(expected.insurable_salary)

    def test_estimate_by_workload(self):
        # 37'872 insured x 10 % (age 30) = 3'787.20
        assert estimated_pillar2_by_year([54_000], 30, [0.6], BY_WORKLOAD) == [
            pytest.approx(3_787.20)
        ]

    def test_unknown_coordination(self):
        with pytest.raises(ValueError, match="Koordinationsabzug"):
            insured_salary(54_000, 1, "half")


class TestPillar3aLimit:
    @pytest.mark.parametrize(
        ("income", "pension_fund", "expected"),
        [
            (0, True, 0),  # no income from work
            (80_000, True, 7_373),  # with a pension fund: the small limit
            (80_000, False, 16_000),  # without: 20 % of the income
            (200_000, False, 36_864),  # at most the large limit
        ],
    )
    def test_limit(self, income, pension_fund, expected):
        assert pillar3a_limit(income, pension_fund) == pytest.approx(expected)


def years(phases=PHASES, setup=Pillar2Setup(), pillar3a=300, base=7_500):
    return pension_years(yearly_plan(phases, 30, 66, 0, pillar3a, 200), 30, setup, base)


class TestPensionYears:
    def test_pension_fund_and_3a_limit_per_year(self):
        result = years()

        assert result[0].insured_salary == pytest.approx(63_120)  # 90'000 - 26'880
        assert result[4].insured_salary == pytest.approx(27_120)  # 54'000 - 26'880
        assert result[4].pillar2 == pytest.approx(2_712)  # x 10 %
        assert result[4].has_pension_fund
        assert result[4].pillar3a_limit == config.PILLAR3A_ANNUAL_MAX
        assert result[4].pillar3a == 3_600  # 300 x 12
        assert result[4].pillar3b == 2_400

    def test_without_pension_fund_the_large_3a_limit(self):
        # 30 % with 1'900 a month: 22'800 a year, below the entry threshold.
        low = [PHASES[0], LifePhase(34, 40, 0.3, 1_900, pillar3a=500), PHASES[2]]

        result = years(low)

        assert result[4].pillar2 == 0
        assert not result[4].has_pension_fund
        assert result[4].pillar3a_limit == pytest.approx(4_560)  # 20 % of 22'800
        assert result[4].pillar3a == pytest.approx(4_560)  # 6'000 wanted, capped

    def test_3a_capped_at_the_small_limit_with_a_pension_fund(self):
        assert years(pillar3a=1_000)[0].pillar3a == config.PILLAR3A_ANNUAL_MAX

    def test_own_contributions_in_proportion_to_the_income(self):
        result = years(setup=Pillar2Setup(OWN, own_total=9_000))

        assert result[0].insured_salary is None
        assert result[4].pillar2 == pytest.approx(5_400)  # 9'000 x 4'500 / 7'500

    @pytest.mark.parametrize(
        ("setup", "message"),
        [
            ("minimum", "Berechnungsgrundlage"),
            (Pillar2Setup("other"), "Berechnungsgrundlage"),
            (Pillar2Setup(coordination="half"), "Koordinationsabzug"),
            (Pillar2Setup(OWN, own_total=-1), "mindestens 0 CHF"),
            (Pillar2Setup(OWN, own_total=True), "mindestens 0 CHF"),
            (Pillar2Setup(OWN, own_total=float("nan")), "mindestens 0 CHF"),
        ],
    )
    def test_invalid_setup(self, setup, message):
        with pytest.raises(ValueError, match=message):
            years(setup=setup)


class TestEducationCredits:
    def test_after_the_birth_until_the_year_the_child_turns_16(self):
        # Born when the parent was 32: credits from 33 until 48 (16 years).
        assert education_credit_ages([32], 21, 64) == list(range(33, 49))

    def test_one_credit_per_year_with_several_children(self):
        # 32 and 35: 33 … 51, overlapping years count once.
        assert education_credit_ages([32, 35], 21, 64) == list(range(33, 52))

    def test_only_within_the_contribution_years(self):
        assert education_credit_ages([32], 40, 64) == list(range(40, 49))

    @pytest.mark.parametrize("births", ["32", [-1], [True], ["32"], [32.5], None])
    def test_invalid_birth_ages(self, births):
        with pytest.raises(ValueError, match="Alter bei der Geburt"):
            education_credit_ages(births, 21, 64)


class TestAhv:
    def test_as_today_without_phases_and_children(self):
        assert ahv_monthly_pension(60_000, 44, 65, [1.0] * 30) == pytest.approx(
            ahv.estimate_monthly_old_age_pension(60_000, 44)
        )

    def test_lower_income_lowers_the_average(self):
        # 30 years until 65, 10 of them at half the income; the 14 earlier years count with
        # the average: 60'000 x (14 + 10 x 0.5 + 20) / 44 = 53'181.82
        ratios = [0.5] * 10 + [1.0] * 20

        assert ahv_monthly_pension(60_000, 44, 65, ratios) == pytest.approx(
            ahv.estimate_monthly_old_age_pension(60_000 * 39 / 44, 44)
        )

    def test_education_credits_raise_the_average(self):
        # 16 credits of 46'080 = 737'280, spread over 44 years: + 16'756.36 a year.
        full = ahv_monthly_pension(60_000, 44, 65, [1.0] * 30, [32])
        half = ahv_monthly_pension(60_000, 44, 65, [1.0] * 30, [32], credit_share=0.5)

        assert ahv.EDUCATION_CREDIT == 46_080
        assert full == pytest.approx(
            ahv.estimate_monthly_old_age_pension(60_000 + 16 * 46_080 / 44, 44)
        )
        assert half == pytest.approx(
            ahv.estimate_monthly_old_age_pension(60_000 + 8 * 46_080 / 44, 44)
        )

    def test_only_the_last_contribution_years_count(self):
        # 50 years until retirement, 44 contribution years: the first 6 do not count.
        ratios = [0.0] * 6 + [1.0] * 44

        assert ahv_monthly_pension(60_000, 44, 65, ratios) == pytest.approx(
            ahv.estimate_monthly_old_age_pension(60_000, 44)
        )

    def test_without_contribution_years(self):
        assert ahv_monthly_pension(60_000, 0, 65, [1.0] * 30) == 0

    @pytest.mark.parametrize(
        ("years", "share", "message"),
        [
            (44, 0.7, "ganz, hälftig oder gar nicht"),
            (45, 1.0, "Beitragsjahre"),
            (True, 1.0, "Beitragsjahre"),
            (40.0, 1.0, "Beitragsjahre"),
        ],
    )
    def test_invalid_inputs(self, years, share, message):
        with pytest.raises(ValueError, match=message):
            ahv_monthly_pension(60_000, years, 65, [1.0], credit_share=share)


def compare(phases=PHASES, setup=Pillar2Setup(), ahv_income=70_000, children=(33,), **changes):
    arguments = dict(
        current_age=30,
        retirement_age=66,
        base_monthly_income=7_500,
        salary_growth=0,
        pillar3a_monthly=300,
        pillar3b_monthly=200,
        setup=setup,
        initial=(20_000, 10_000, 5_000),
        returns=(0.02, 0.04),
        ahv_average_income=ahv_income,
        ahv_contribution_years=44,
        child_birth_ages=children,
    )
    return compare_with_full_time(phases, **{**arguments, **changes})


class TestCompareWithFullTime:
    def test_part_time_leaves_a_gap_in_the_2nd_pillar_and_the_ahv(self):
        result = compare()

        assert all(year.workload == 1 for year in result.full_time)
        assert result.plan_paths.pillar2[-1] < result.full_time_paths.pillar2[-1]
        assert result.plan_paths.pillar3a == result.full_time_paths.pillar3a  # same 3a
        assert result.capital_gap == pytest.approx(
            result.full_time_paths.pillar2[-1] - result.plan_paths.pillar2[-1]
        )
        assert result.capital_full_time - result.capital_plan == result.capital_gap
        assert result.ahv_gap > 0
        assert result.ahv_full_time - result.ahv_plan == result.ahv_gap

    def test_paths_start_with_today_s_balances(self):
        result = compare()

        assert result.yearly.ages == tuple(year.age for year in result.plan)
        assert result.plan_paths.pillar2[0] == 20_000
        assert result.plan_paths.pillar3a[0] == 10_000
        assert result.plan_paths.pillar3b[0] == 5_000
        assert len(result.plan_paths.pillar2) == 37  # today … retirement at 66

    def test_coordination_by_workload_makes_the_gap_smaller(self):
        fixed = compare()
        by_workload = compare(setup=Pillar2Setup(coordination=BY_WORKLOAD))

        # Full time is the same either way (workload 100 %).
        assert by_workload.full_time_paths == fixed.full_time_paths
        assert by_workload.capital_gap < fixed.capital_gap

    def test_education_credits_count_in_both(self):
        # Child born at 33: credits 34 … 49, all within the 44 contribution years (22 … 65).
        assert compare().education_credit_years == 16
        assert compare(children=()).ahv_plan < compare().ahv_plan

    def test_years_without_income_are_listed(self):
        break_ = [PHASES[0], LifePhase(34, 36, 0, 0), LifePhase(37, 65, 0.8, 6_400)]

        assert compare(break_).years_without_income == (34, 35, 36)
        assert compare().years_without_income == ()

    def test_full_time_phase_has_no_gap(self):
        result = compare([full_time_phase(30, 66, 7_500)])

        assert result.capital_gap == 0
        assert result.ahv_gap == 0

    def test_own_contributions(self):
        result = compare(setup=Pillar2Setup(OWN, own_total=9_000))

        assert result.full_time[0].pillar2 == 9_000
        assert result.plan[4].pillar2 == pytest.approx(5_400)

    def test_without_ahv_inputs(self):
        result = compare(ahv_income=None)

        assert (result.ahv_plan, result.ahv_full_time, result.ahv_gap) == (None, None, None)
        assert result.education_credit_years == 0

    @pytest.mark.parametrize("base", [0, -1, None, True, float("inf")])
    def test_needs_an_income(self, base):
        with pytest.raises(ValueError, match="grösser als 0 CHF"):
            compare(base_monthly_income=base)
