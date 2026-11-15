"""Life phases in the inputs: rows, titles and the phases they give (issue #33)."""

from contextvars import copy_context

import pytest
from dash import no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict

from personal_finance.core.life_phases import LifePhase, validate_phases
from personal_finance.dashboard import life_view
from personal_finance.dashboard.callbacks import edit_life_phases, update_life_controls
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


EMPTY = (None, None, None, None)
ROWS3 = [(37, 100, 7_200, None), (44, 60, 4_300, 1_500), (None, 80, 5_800, 600), EMPTY, EMPTY]


def edit(action, rows=(EMPTY,) * 5, plan="on", current_age=35, retirement_age=65, income=7_200):
    return life_view.edit_rows(action, list(rows), plan, current_age, retirement_age, income)


class TestTemplates:
    def test_full_time(self):
        assert edit(life_view.FULL, ROWS3) == [(None, 100, 7_200, None)] + [EMPTY] * 4

    def test_part_time_with_children(self):
        # 100 % until 37, 60 % until 44 (7'200 x 0.6 = 4'320), then 80 % (5'760).
        assert edit(life_view.KIDS) == [
            (37, 100, 7_200, None),
            (44, 60, 4_320, None),
            (None, 80, 5_760, None),
            EMPTY,
            EMPTY,
        ]

    def test_break(self):
        assert edit(life_view.BREAK)[:3] == [
            (37, 100, 7_200, None),
            (39, 0, 0, None),
            (None, 100, 7_200, None),
        ]

    def test_without_an_income_the_amounts_stay_empty(self):
        assert edit(life_view.KIDS, income=None)[1] == (44, 60, None, None)

    def test_too_few_years_for_a_template(self):
        # At 56 with retirement at 65 the 60 % phase would end at 65.
        assert edit(life_view.KIDS, current_age=56) is None
        assert edit(life_view.BREAK, current_age=61) is None

    def test_planning_starts_with_full_time_only_without_phases(self):
        assert edit(life_view.PLAN)[0] == (None, 100, 7_200, None)
        assert edit(life_view.PLAN, ROWS3) is None  # e.g. a loaded scenario
        assert edit(life_view.PLAN, plan="off") is None

    @pytest.mark.parametrize(("current_age", "retirement_age"), [(None, 65), (35, None), (65, 65)])
    def test_nothing_without_valid_ages(self, current_age, retirement_age):
        assert edit(life_view.FULL, current_age=current_age, retirement_age=retirement_age) is None


class TestAddAndRemove:
    def test_remove_clears_the_last_phase(self):
        assert edit(life_view.REMOVE, ROWS3) == ROWS3[:2] + [EMPTY] * 3

    def test_at_least_one_phase_stays(self):
        assert edit(life_view.REMOVE, [(None, 100, 7_200, None)] + [EMPTY] * 4) is None

    def test_add_splits_the_last_phase_in_the_middle(self):
        # Last phase 45 … 64: the middle is 45 + 19 // 2 = 54.
        assert edit(life_view.ADD, ROWS3)[2:4] == [(54, 80, 5_800, 600), (None, 80, 5_800, 600)]
        # One phase 35 … 64: 35 + 29 // 2 = 49.
        one = edit(life_view.ADD, [(None, 100, 7_200, None)] + [EMPTY] * 4)
        assert one[:2] == [(49, 100, 7_200, None), (None, 100, 7_200, None)]

    def test_add_keeps_the_last_phase_at_least_one_year(self):
        assert edit(life_view.ADD, [(None, 100, 7_200, None)] + [EMPTY] * 4, current_age=63)[0] == (
            63,
            100,
            7_200,
            None,
        )
        assert edit(life_view.ADD, [(None, 100, 7_200, None)] + [EMPTY] * 4, current_age=64) is None

    @pytest.mark.parametrize(
        "rows",
        [
            [EMPTY] * 5,  # nothing to split
            [
                (36, 100, 1, None),
                (37, 100, 1, None),
                (38, 100, 1, None),
                (39, 100, 1, None),
                (None, 100, 1, None),
            ],
            [(None, 100, 7_200, None), (None, 60, 4_300, None)] + [EMPTY] * 3,  # «bis» missing
        ],
    )
    def test_add_not_possible(self, rows):
        assert edit(life_view.ADD, rows) is None


class TestEditCallback:
    def run(self, trigger, fields=None, income=7_200, period="monthly"):
        fields = fields if fields is not None else [None] * 20

        def _run():
            context_value.set(
                AttributeDict(triggered_inputs=[{"prop_id": f"{trigger}.n_clicks", "value": 1}])
            )
            return edit_life_phases(1, 1, 1, 1, 1, "on", 35, 65, income, period, *fields)

        return copy_context().run(_run)

    def test_template_from_a_yearly_income(self):
        result = self.run(life_view.FULL, income=86_400, period="yearly")

        assert result[:4] == [None, 100, 7_200, None]
        assert result[4:] == [None] * 16

    def test_emptied_fields_count_as_empty(self):
        fields = [None, 100, 7_200, ""] + [""] * 16
        result = self.run(life_view.ADD, fields)

        assert result[:8] == [49, 100, 7_200, None, None, 100, 7_200, None]

    def test_nothing_to_change(self):
        assert self.run(life_view.REMOVE, income="") == [no_update] * 20
