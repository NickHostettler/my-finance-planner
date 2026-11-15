"""Life phases in the inputs: rows, titles and the phases they give (issue #33)."""

import pytest

from personal_finance.core.life_phases import LifePhase, validate_phases
from personal_finance.dashboard import life_view
from personal_finance.dashboard.callbacks import update_life_controls
from tests.unit.test_browser_store import LIFE_VALUES


def values(**overrides):
    return {**LIFE_VALUES, **overrides}


class TestRows:
    @pytest.mark.parametrize(
        ("workloads", "used"),
        [
            ([None] * 5, 0),
            ([100, None, None, None, None], 1),
            ([100, 60, 80, None, None], 3),
            ([100, "", 80, None, None], 1),  # an emptied field ends the phases
            ([100, 0, 100, 50, 80], 5),  # 0 % is a phase (a break)
        ],
    )
    def test_used_rows(self, workloads, used):
        assert life_view.used_rows(workloads) == used

    def test_titles_follow_the_previous_phase(self):
        assert life_view.row_titles(35, [37, 44, None, None, None], 3) == [
            "Phase 1 · ab 35",
            "Phase 2 · ab 38",
            "Phase 3 · ab 45 bis zur Pensionierung",
            "Phase 4",
            "Phase 5",
        ]

    def test_titles_without_ages(self):
        assert life_view.row_titles(None, [None, 40.5], 1) == [
            "Phase 1 bis zur Pensionierung",
            "Phase 2",
        ]


class TestPhasesFromValues:
    def test_each_phase_starts_after_the_previous_one(self):
        phases = life_view.phases_from_values(values(), 35, 65)

        assert phases == [
            LifePhase(35, 37, 1.0, 7_200, child_costs=None),
            LifePhase(38, 44, 0.6, 4_300, child_costs=1_500),
            LifePhase(45, 64, 0.8, 5_800, child_costs=600),
        ]
        assert validate_phases(phases, 35, 65)  # without gaps until retirement

    def test_the_last_phase_ignores_its_bis_alter(self):
        phases = life_view.phases_from_values(values(life_3_to=50), 35, 65)

        assert phases[-1].to_age == 64

    def test_invalid_workloads_are_passed_on_for_the_phase_check(self):
        phases = life_view.phases_from_values(values(life_1_workload="viel"), 35, 65)

        with pytest.raises(ValueError, match="Phase 1: Das Pensum"):
            validate_phases(phases, 35, 65)

    @pytest.mark.parametrize(
        ("overrides", "message"),
        [
            ({"life_1_workload": None}, "mindestens eine Lebensphase"),
            ({"life_1_to": None}, "Phase 1: Bitte gib an, bis zu welchem Alter"),
            ({"life_2_to": 37}, r"Phase 2: Das Alter «bis» \(37\) muss mindestens 38 sein"),
            ({"life_2_to": 64}, "spätestens bei 63"),
        ],
    )
    def test_invalid_rows(self, overrides, message):
        with pytest.raises(ValueError, match=message):
            life_view.phases_from_values(values(**overrides), 35, 65)

    def test_children_from_the_filled_in_fields(self):
        assert life_view.child_birth_ages(values(life_child_3=42)) == (36, 39, 42)
        assert life_view.child_birth_ages({}) == ()


class TestControls:
    def controls(self, plan="on", current_age=35, workloads=(100, 60, 80, None, None)):
        to_ages = (37, 44, None, None, None)
        return update_life_controls(plan, current_age, *workloads, *to_ages)

    def test_shows_the_used_rows_and_hides_the_last_bis_alter(self):
        result = self.controls()
        fields, rows, to_fields, titles = result[0], result[1:6], result[6:11], result[11:]

        assert fields == {"display": "grid"}
        assert [row["display"] for row in rows] == ["block"] * 3 + ["none"] * 2
        assert [field["display"] for field in to_fields] == ["block", "block", "none"] + [
            "block"
        ] * 2
        assert titles[2] == "Phase 3 · ab 45 bis zur Pensionierung"

    def test_at_least_one_row_and_hidden_while_not_planned(self):
        result = self.controls(plan="off", workloads=(None,) * 5)

        assert result[0] == {"display": "none"}
        assert result[1] == {"display": "block"}
        assert result[2] == {"display": "none"}
