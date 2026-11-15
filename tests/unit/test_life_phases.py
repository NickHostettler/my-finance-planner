"""Life phases: changing workload and income until retirement (issue #30)."""

import math

import pytest

from personal_finance import config
from personal_finance.core.life_phases import (
    MAX_PHASES,
    LifePhase,
    estimated_pillar2_by_year,
    full_time_phase,
    scaled_pillar2_by_year,
    validate_phases,
    yearly_plan,
)
from personal_finance.core.pillar_2 import estimated_contributions, growing_contributions
from personal_finance.core.projection import project_balance

# The example from the issue: full time until 33, 60 % while the children are small, then 80 %.
PHASES = [
    LifePhase(30, 33, 1.0, 7_500),
    LifePhase(34, 40, 0.6, 4_500),
    LifePhase(41, 65, 0.8, 6_400),
]


def plan(phases=PHASES, current_age=30, retirement_age=66, growth=0, pillar3a=300, pillar3b=200):
    return yearly_plan(phases, current_age, retirement_age, growth, pillar3a, pillar3b)


class TestYearlyPlan:
    def test_one_value_per_year_until_the_year_before_retirement(self):
        result = plan()

        assert result.ages == tuple(range(30, 66))  # 36 years: 30 … 65
        assert len(result.monthly_income) == len(result.pillar3a) == 36

    def test_values_change_at_the_phase_boundaries(self):
        result = plan()

        # Index = age - 30.
        assert result.monthly_income[3] == 7_500  # 33
        assert result.monthly_income[4] == 4_500  # 34
        assert result.monthly_income[10] == 4_500  # 40
        assert result.monthly_income[11] == 6_400  # 41
        assert result.workload[3:5] == (1.0, 0.6)
        assert result.annual_income[4] == 54_000  # 4'500 x 12

    def test_salary_growth_is_added_from_today(self):
        result = plan(growth=0.01)

        assert result.monthly_income[0] == 7_500
        # Age 34 is 4 years from today: 4'500 x 1.01^4 = 4'500 x 1.0406040 = 4'682.72
        assert result.monthly_income[4] == pytest.approx(4_500 * 1.01**4)
        assert result.monthly_income[4] == pytest.approx(4_682.72, abs=0.01)

    def test_plan_savings_unless_a_phase_has_its_own(self):
        phases = [PHASES[0], LifePhase(34, 40, 0.6, 4_500, pillar3a=0, pillar3b=50), PHASES[2]]

        result = plan(phases)

        assert result.pillar3a[:5] == (3_600, 3_600, 3_600, 3_600, 0)  # 300 x 12, then 0
        assert result.pillar3b[3:5] == (2_400, 600)  # 200 x 12, then 50 x 12
        assert result.pillar3a[11] == 3_600  # back to the plan at 41

    def test_3a_stays_within_the_limit(self):
        result = plan(pillar3a=1_000)

        assert set(result.pillar3a) == {config.PILLAR3A_ANNUAL_MAX}  # not 12'000

    def test_no_3a_in_a_year_without_income(self):
        break_ = [PHASES[0], LifePhase(34, 40, 0, 0), PHASES[2]]

        result = plan(break_)

        assert result.pillar3a[4:11] == (0,) * 7  # 34 … 40: no income from work
        assert result.pillar3b[4] == 2_400  # free savings go on
        assert result.workload[4] == 0

    def test_phases_in_any_order_and_starting_before_today(self):
        assert plan(list(reversed(PHASES)), current_age=31).monthly_income[0] == 7_500

    def test_nothing_to_plan_at_retirement(self):
        result = plan(current_age=66)

        assert result.ages == ()
        assert result.annual_income == []

    def test_invalid_salary_growth(self):
        with pytest.raises(ValueError, match="Lohnzunahme"):
            plan(growth=0.5)


class TestValidation:
    @pytest.mark.parametrize(
        ("phases", "message"),
        [
            ([], "mindestens eine Lebensphase"),
            (None, "mindestens eine Lebensphase"),
            ("30-65", "mindestens eine Lebensphase"),
            ([LifePhase(30, 65, 1, 5_000)] * (MAX_PHASES + 1), "höchstens 10"),
            ([{"from_age": 30}], "Phase 1 ist ungültig"),
            ([LifePhase(True, 65, 1, 5_000)], "Phase 1: Bitte gib das Alter «von»"),
            ([LifePhase(30, 65.5, 1, 5_000)], "Phase 1: Bitte gib das Alter «bis»"),
            ([LifePhase(30, math.nan, 1, 5_000)], "Alter «bis»"),
            ([LifePhase(65, 30, 1, 5_000)], "nicht kleiner sein als «von»"),
            ([LifePhase(30, 65, 1.2, 5_000)], "Pensum muss zwischen 0 und 100"),
            ([LifePhase(30, 65, -0.1, 5_000)], "Pensum muss zwischen 0 und 100"),
            ([LifePhase(30, 65, None, 5_000)], "Pensum"),
            ([LifePhase(30, 65, 1, -1)], "Einkommen muss mindestens 0"),
            ([LifePhase(30, 65, 1, "5000")], "Einkommen"),
            ([LifePhase(30, 65, 0, 5_000)], "Pensum von 0 % gibt es kein Erwerbseinkommen"),
            ([LifePhase(30, 65, 1, 5_000, pillar3a=-1)], "3a-Betrag"),
            ([LifePhase(30, 65, 1, 5_000, pillar3b=math.inf)], "3b-Betrag"),
        ],
    )
    def test_invalid_phases(self, phases, message):
        with pytest.raises(ValueError, match=message):
            validate_phases(phases, 30, 66)

    def test_second_phase_is_named_in_the_message(self):
        with pytest.raises(ValueError, match="Phase 2: Das Pensum"):
            validate_phases([PHASES[0], LifePhase(34, 65, 2, 4_500)], 30, 66)

    def test_overlap(self):
        with pytest.raises(ValueError, match="34–40 und 40–65 überschneiden sich"):
            validate_phases([PHASES[0], PHASES[1], LifePhase(40, 65, 0.8, 6_400)], 30, 66)

    def test_gap(self):
        with pytest.raises(ValueError, match="Zwischen Alter 33 und 35 fehlt eine Phase"):
            validate_phases([PHASES[0], LifePhase(35, 65, 0.8, 6_400)], 30, 66)

    def test_must_start_today_at_the_latest(self):
        with pytest.raises(ValueError, match=r"spätestens bei deinem aktuellen Alter \(29\)"):
            validate_phases(PHASES, 29, 66)

    def test_must_last_until_the_year_before_retirement(self):
        with pytest.raises(ValueError, match=r"Jahr vor der Pensionierung \(Alter 66\)"):
            validate_phases(PHASES, 30, 67)

    def test_valid_phases_are_returned_sorted_as_numbers(self):
        result = validate_phases([PHASES[2], PHASES[0], LifePhase(34.0, 40, 0.6, 4_500)], 30, 66)

        assert [phase.from_age for phase in result] == [30, 34, 41]
        assert isinstance(result[1].from_age, int)


class TestPillar2:
    def test_estimate_follows_the_income_of_each_year(self):
        result = plan()
        contributions = estimated_pillar2_by_year(result.annual_income, 30)

        # Hand calculation for 34 (60 %): 54'000 - 26'880 coordination deduction = 27'120
        # insured salary x 10 % (rate of age 30) = 2'712.
        assert contributions[4] == pytest.approx(2_712)
        assert contributions[0] > contributions[4] < contributions[11]

    def test_no_bvg_below_the_entry_threshold(self):
        # 1'900 x 12 = 22'800 is below the entry threshold of 23'040.
        low = plan([PHASES[0], LifePhase(34, 40, 0.3, 1_900), PHASES[2]])

        assert estimated_pillar2_by_year(low.annual_income, 30)[4] == 0

    def test_own_contributions_in_proportion_to_the_income(self):
        result = plan()

        # 9'000 a year today with 7'500 a month; at 60 % with 4'500: 9'000 x 0.6 = 5'400.
        contributions = scaled_pillar2_by_year(9_000, 7_500, result.monthly_income)

        assert contributions[0] == 9_000
        assert contributions[4] == pytest.approx(5_400)

    @pytest.mark.parametrize("base", [0, None, -1])
    def test_own_contributions_need_an_income(self, base):
        with pytest.raises(ValueError, match="grösser als 0 CHF"):
            scaled_pillar2_by_year(9_000, base, [7_500])


class TestWithoutPhases:
    """One phase at 100 % gives exactly the projection without life phases."""

    def full_time(self, growth=0.01):
        return plan(
            [full_time_phase(35, 65, 7_200)], current_age=35, retirement_age=65, growth=growth
        )

    def test_full_time_phase_covers_today_until_retirement(self):
        assert full_time_phase(35, 65, 7_200) == LifePhase(35, 64, 1.0, 7_200)
        assert full_time_phase(65, 65, 7_200).to_age == 65

    def test_bvg_estimate_is_unchanged(self):
        result = self.full_time()

        assert estimated_pillar2_by_year(result.annual_income, 35) == pytest.approx(
            estimated_contributions(7_200 * 12, 35, 30, 0.01)
        )

    def test_own_contributions_are_unchanged(self):
        result = self.full_time()

        assert scaled_pillar2_by_year(9_000, 7_200, result.monthly_income) == pytest.approx(
            growing_contributions(9_000, 30, 0.01)
        )

    def test_3a_and_3b_are_unchanged(self):
        result = self.full_time()

        assert project_balance(list(result.pillar3a), 30, 0.04) == pytest.approx(
            project_balance(3_600, 30, 0.04)
        )
        assert set(result.pillar3b) == {2_400}
