"""Tests for the pure, browser-side scenario storage."""

import copy
import math

import pytest

from personal_finance.storage import browser_store as store


def sample_values(**overrides):
    values = {
        "income": 7200,
        "income_period": "monthly",
        "income_type": "gross",
        "canton": "ZH",
        "current_age": 35,
        "retirement_age": 65,
        "savings_mode": "amount",
        "savings_rate": 10,
        "pillar3a_amount": 350,
        "pillar3b_amount": 500,
        "initial_3a": 10000,
        "initial_3b": 20000,
        "initial_2": 45000,
        "pillar2_mode": "custom",
        "pillar2_employee": 300,
        "pillar2_employer": 450,
        "pillar2_return": 1.5,
        "assumed_return": 0.06,
        "display_basis": "real",
        "ahv_average_income": 65000,
        "ahv_contribution_years": 41,
    }
    values.update(overrides)
    return values


class TestScenarios:
    def test_round_trip_and_sorted_listing(self):
        state = store.save_scenario(None, "Teilzeit", sample_values())
        state = store.save_scenario(state, "basis", sample_values(income=5000))

        assert [item["name"] for item in store.list_scenarios(state)] == ["basis", "Teilzeit"]
        assert store.load_scenario(state, "Teilzeit") == sample_values()
        assert store.load_scenario(state, "basis")["income"] == 5000

    def test_saving_same_name_updates_existing_scenario(self):
        state = store.save_scenario(None, "Plan", sample_values())
        state = store.save_scenario(state, "  Plan  ", sample_values(income=9000))

        assert len(store.list_scenarios(state)) == 1
        assert store.load_scenario(state, "Plan")["income"] == 9000

    def test_delete_only_removes_matching_name(self):
        state = store.save_scenario(None, "A", sample_values())
        state = store.save_scenario(state, "B", sample_values())
        state = store.delete_scenario(state, "A")

        assert [item["name"] for item in store.list_scenarios(state)] == ["B"]
        with pytest.raises(ValueError):
            store.delete_scenario(state, "A")

    def test_loading_unknown_scenario_fails_with_user_message(self):
        with pytest.raises(ValueError, match="nicht gefunden"):
            store.load_scenario(store.empty_scenarios(), "Fehlt")

    @pytest.mark.parametrize("name", ["", "   ", None, 42, "x" * 81])
    def test_invalid_names_are_rejected(self, name):
        with pytest.raises(ValueError):
            store.save_scenario(None, name, sample_values())

    def test_number_of_scenarios_is_limited(self):
        state = None
        for index in range(store.MAX_SCENARIOS):
            state = store.save_scenario(state, f"S{index}", sample_values())

        with pytest.raises(ValueError, match="höchstens"):
            store.save_scenario(state, "Eins zu viel", sample_values())
        # Overwriting an existing one is still allowed at the limit.
        store.save_scenario(state, "S0", sample_values(income=1))

    def test_functions_never_mutate_the_given_state(self):
        state = store.save_scenario(None, "A", sample_values())
        snapshot = copy.deepcopy(state)

        store.save_scenario(state, "B", sample_values())
        store.delete_scenario(state, "A")
        loaded = store.load_scenario(state, "A")
        loaded["income"] = -1

        assert state == snapshot


class TestUntrustedBrowserData:
    @pytest.mark.parametrize(
        "data", [None, "kaputt", 42, [], {}, {"scenarios": "x"}, {"scenarios": {"A": "x"}}]
    )
    def test_corrupt_state_is_treated_as_empty(self, data):
        assert store.list_scenarios(data) == []

    def test_unknown_fields_are_dropped_and_wrong_types_cleared(self):
        cleaned = store.sanitize_values(
            sample_values(income="7200", current_age=35.5, canton=True, evil="<script>")
        )

        assert "evil" not in cleaned
        assert cleaned["income"] is None
        assert cleaned["current_age"] is None
        assert cleaned["canton"] is None

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_non_finite_numbers_are_cleared(self, bad):
        assert store.sanitize_values(sample_values(income=bad))["income"] is None

    def test_integer_fields_accept_whole_floats_from_json(self):
        assert store.sanitize_values(sample_values(current_age=35.0))["current_age"] == 35

    def test_older_entries_get_defaults_for_newer_fields(self):
        old = sample_values()
        del old["display_basis"], old["ahv_contribution_years"], old["ahv_average_income"]
        state = {"version": 1, "scenarios": {"Alt": {"values": old, "updated_at": ""}}}

        loaded = store.load_scenario(state, "Alt")

        assert loaded["display_basis"] == "nominal"
        assert loaded["ahv_contribution_years"] == 44
        assert loaded["ahv_average_income"] is None


class TestLastInputs:
    def test_round_trip(self):
        data = store.make_last_inputs(sample_values())

        assert store.read_last_inputs(data) == sample_values()

    @pytest.mark.parametrize("data", [None, {}, {"values": "x"}, "kaputt"])
    def test_missing_or_corrupt_data_returns_none(self, data):
        assert store.read_last_inputs(data) is None

    def test_inputs_mapping_matches_field_order(self):
        values = sample_values()
        as_inputs = store.values_to_inputs(values)

        assert store.values_from_inputs(as_inputs) == values

    def test_wrong_number_of_inputs_is_rejected(self):
        with pytest.raises(ValueError):
            store.values_from_inputs([1, 2, 3])
