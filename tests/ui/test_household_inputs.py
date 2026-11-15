"""Inputs for two persons and the household (issues #43, #47)."""

from contextvars import copy_context

from dash._callback_context import context_value
from dash._utils import AttributeDict

from personal_finance.dashboard import callbacks
from personal_finance.dashboard.app import app
from personal_finance.dashboard.callbacks import (
    SCENARIO_INPUT_IDS,
    edit_life_phases,
    person_values,
    update_household_controls,
    update_income_controls_b,
)
from personal_finance.dashboard.layout import input_id, person_id
from personal_finance.storage import browser_store
from tests.unit.test_browser_store import sample_values

SHOWN, HIDDEN = {"display": "block"}, {"display": "none"}


def _component(component_id):
    return next(
        component
        for component in app.layout._traverse()
        if getattr(component, "id", None) == component_id
    )


class TestIds:
    def test_ids_follow_the_field_names(self):
        assert input_id("income") == "monthly-income-input"
        assert input_id("b_income") == "b-monthly-income-input"
        assert input_id("initial_2") == "pillar2-initial-input"
        assert input_id("b_assumed_return") == "b-return-input"
        assert input_id("b_life_3_costs") == "b-life-3-costs-input"
        assert input_id("household_relationship") == "household-relationship-input"
        assert person_id("income-preview", "b") == "b-income-preview"
        assert person_id("income-preview") == "income-preview"

    def test_person_b_has_the_same_inputs_as_person_a(self):
        ids = {getattr(component, "id", None) for component in app.layout._traverse()}
        for field in browser_store.PERSON_FIELDS:
            assert input_id(field) in ids
            assert "b-" + input_id(field) in ids
        assert len(SCENARIO_INPUT_IDS) == len(set(SCENARIO_INPUT_IDS))

    def test_person_b_starts_with_the_start_values(self):
        defaults = browser_store.PERSON_B_DEFAULTS
        assert _component("b-monthly-income-input").value == defaults["income"]
        assert _component("b-current-age-input").value == defaults["current_age"]
        assert _component("b-return-input").value == "0.04"
        assert _component("b-home-savings-input").value == 0
        assert _component("b-life-role-input").value == "other"
        assert _component("household-input").value == "off"
        assert _component("person-b-inputs").style == HIDDEN

    def test_controls_of_person_b_are_registered(self):
        for output in (
            "b-pillar2-custom-fields.style",
            "b-income-preview.children",
            "b-pillar3a-amount-input.value",  # with allow_duplicate: "..id.value@hash.."
        ):
            assert any(output in key for key in app.callback_map)


class TestHouseholdControls:
    def test_one_person(self):
        result = update_household_controls("off", "b", "unmarried", "off", "on")
        person_switch, inputs_a, inputs_b, eyebrow, group, credits, children = result[:7]
        assert (person_switch, inputs_a, inputs_b) == (HIDDEN, SHOWN, HIDDEN)
        assert (eyebrow, group, credits) == (HIDDEN, HIDDEN, HIDDEN)
        # Person B's phases do not count while planning for one person.
        assert children == HIDDEN
        assert result[7] == callbacks.CHILDREN_HINTS["off"]
        assert result[8:10] == [SHOWN, SHOWN]  # each person's credit share
        assert result[10:12] == [HIDDEN, HIDDEN]  # titles above the purchase money
        assert result[12] == HIDDEN  # person B's purchase money
        assert result[13] == "Leer = heute (dein aktuelles Alter)"

    def test_two_persons_show_the_chosen_person(self):
        result = update_household_controls("on", "b", "married", "off", "on")
        assert result[:3] == [SHOWN, HIDDEN, SHOWN]
        assert result[3:6] == [SHOWN, SHOWN, HIDDEN]  # married: credits always half
        assert result[6] == SHOWN  # person B plans phases
        assert result[7] == callbacks.CHILDREN_HINTS["on"]
        assert result[8:10] == [HIDDEN, HIDDEN]
        assert result[10:12] == [SHOWN, SHOWN]
        assert result[12] == {"display": "grid"}
        assert result[13] == "Alter von Person A; leer = heute"

    def test_unmarried_couples_choose_how_to_share_the_credits(self):
        result = update_household_controls("on", "a", "unmarried", "on", "off")
        assert result[:3] == [SHOWN, SHOWN, HIDDEN]
        assert result[5] == SHOWN
        assert result[6] == SHOWN  # person A plans phases

    def test_income_label_of_person_b(self):
        label, unit, *_ = update_income_controls_b("yearly", "gross")
        assert (label, unit) == ("Jährliches Bruttoeinkommen von Person B", "CHF/Jahr")


def test_templates_of_person_b():
    def run():
        context_value.set(
            AttributeDict(
                triggered_inputs=[{"prop_id": "b-life-template-full.n_clicks", "value": 1}]
            )
        )
        return edit_life_phases(1, 1, 1, 1, 1, "on", 33, 64, 6_000, "monthly", *[None] * 20)

    assert copy_context().run(run)[:4] == [None, 100, 6_000, None]


def test_person_values_use_the_names_of_person_a():
    values = sample_values()
    b = person_values(values, "b")
    assert (b["income"], b["current_age"], b["home_savings"]) == (98_000, 33, 40_000)
    assert b["home_price"] == values["home_price"]  # household fields stay
    assert person_values(values, "a") == values
