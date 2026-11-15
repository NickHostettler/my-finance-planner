"""Tests for the pure, browser-side scenario storage."""

import copy
import math

import pytest

from personal_finance import config
from personal_finance.storage import browser_store as store


def sample_values(**overrides):
    values = {
        "income": 7200,
        "income_period": "monthly",
        "income_type": "gross",
        "canton": "ZH",
        "current_age": 35,
        "retirement_age": 65,
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
        "home_plan": "on",
        "home_price": 1_100_000,
        "home_purchase_age": 40,
        "home_savings": 180_000,
        "home_pillar3a": 30_000,
        "home_pillar2": 50_000,
        "home_gross_income": 190_000,
        "home_imputed_rate": 4.5,
        "home_mortgage_rate": 1.6,
        "home_amortisation": "indirect",
        "salary_growth": 1.0,
        **LIFE_VALUES,
        **HOUSEHOLD_VALUES,
    }
    values.update(overrides)
    return values


# Life phases (v1.2): full time until 37, 60 % until 44, then 80 %; two children.
LIFE_VALUES = {
    "life_plan": "on",
    "life_coordination": "workload",
    **{
        f"life_{row}_{part}": value
        for row, parts in enumerate(
            [
                (37, 100, 7_200, None),
                (44, 60, 4_300, 1_500),
                (None, 80, 5_800, 600),
                (None, None, None, None),
                (None, None, None, None),
            ],
            start=1,
        )
        for part, value in zip(store.LIFE_ROW_PARTS, parts)
    },
    "life_child_1": 36,
    "life_child_2": 39,
    "life_child_3": None,
    "life_child_4": None,
    "life_role": "mother",
    "life_credit_share": "half",
    "life_child_allowance": 250,
    "life_education_allowance": 300,
}


# Household (v1.3): two unmarried persons; person B with own values in every field.
PERSON_B_VALUES = {
    "income": 98_000,
    "income_period": "yearly",
    "income_type": "gross",
    "canton": "BE",
    "current_age": 33,
    "retirement_age": 64,
    "pillar3a_amount": 600,
    "pillar3b_amount": 250,
    "initial_3a": 22_000,
    "initial_3b": 15_000,
    "initial_2": 60_000,
    "pillar2_mode": "minimum",
    "pillar2_employee": None,
    "pillar2_employer": None,
    "pillar2_return": None,
    "assumed_return": 0.02,
    "ahv_average_income": 90_000,
    "ahv_contribution_years": 44,
    "home_savings": 40_000,
    "home_pillar3a": 0,
    "home_pillar2": 25_000,
    "salary_growth": 0.5,
    "life_plan": "on",
    "life_coordination": "fixed",
    **{
        f"life_{row}_{part}": value
        for row, parts in enumerate(
            [(None, 100, 8_100, 800)] + [(None, None, None, None)] * 4, start=1
        )
        for part, value in zip(store.LIFE_ROW_PARTS, parts)
    },
    "life_role": "other",
    "life_credit_share": "full",
}
HOUSEHOLD_VALUES = {
    "household": "on",
    "household_relationship": "unmarried",
    "household_credits": "a",
    **{store.person_field(field, "b"): value for field, value in PERSON_B_VALUES.items()},
}


# A scenario saved with v1.0.0 (before home ownership): exactly these fields.
V1_0_FIELDS = [
    "income",
    "income_period",
    "income_type",
    "canton",
    "current_age",
    "retirement_age",
    "savings_mode",
    "savings_rate",
    "pillar3a_amount",
    "pillar3b_amount",
    "initial_3a",
    "initial_3b",
    "initial_2",
    "pillar2_mode",
    "pillar2_employee",
    "pillar2_employer",
    "pillar2_return",
    "assumed_return",
    "display_basis",
    "ahv_average_income",
    "ahv_contribution_years",
]


def v1_0_values():
    values = sample_values()
    values.pop("salary_growth")
    values.update(savings_mode="amount", savings_rate=10)
    return {field: values[field] for field in V1_0_FIELDS}


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
        del (
            old["display_basis"],
            old["ahv_contribution_years"],
            old["ahv_average_income"],
            old["salary_growth"],
        )
        state = {"version": 1, "scenarios": {"Alt": {"values": old, "updated_at": ""}}}

        loaded = store.load_scenario(state, "Alt")

        assert loaded["display_basis"] == "nominal"
        assert loaded["ahv_contribution_years"] == 44
        assert loaded["ahv_average_income"] is None
        assert loaded["salary_growth"] == store.FIELD_DEFAULTS["salary_growth"]

    def test_scenarios_from_v1_0_load_without_home_purchase(self):
        old = v1_0_values()
        state = {"version": 1, "scenarios": {"Vor 1.1": {"values": old, "updated_at": ""}}}

        loaded = store.load_scenario(state, "Vor 1.1")

        assert {
            field: loaded[field]
            for field in V1_0_FIELDS
            if field not in {"savings_mode", "savings_rate"}
        } == {
            field: value
            for field, value in old.items()
            if field not in {"savings_mode", "savings_rate"}
        }
        assert "savings_mode" not in loaded
        assert "savings_rate" not in loaded
        # No purchase planned, the home fields get their defaults (empty: buy now).
        assert loaded["home_plan"] == "off"
        assert loaded["home_price"] == store.FIELD_DEFAULTS["home_price"]
        assert loaded["home_imputed_rate"] == 5.0
        assert loaded["home_purchase_age"] is None
        assert loaded["home_gross_income"] is None
        assert (loaded["home_mortgage_rate"], loaded["home_amortisation"]) == (2.0, "direct")
        assert store.values_from_inputs(store.values_to_inputs(loaded)) == loaded

    def test_scenarios_from_v1_1_load_without_life_phases(self):
        old = {
            field: value
            for field, value in sample_values().items()
            if field not in LIFE_VALUES and field not in HOUSEHOLD_VALUES
        }
        state = {"version": 1, "scenarios": {"v1.1": {"values": old, "updated_at": ""}}}

        loaded = store.load_scenario(state, "v1.1")

        assert {field: loaded[field] for field in old} == old
        assert loaded["life_plan"] == "off"
        assert loaded["life_coordination"] == "fixed"
        assert (loaded["life_role"], loaded["life_credit_share"]) == ("mother", "full")
        assert loaded["life_child_allowance"] == config.CHILD_ALLOWANCE_MONTHLY
        assert loaded["life_education_allowance"] == config.EDUCATION_ALLOWANCE_MONTHLY
        # Rows and children stay empty: not used.
        assert loaded["life_1_workload"] is None
        assert loaded["life_child_1"] is None

    def test_life_fields_in_input_order(self):
        assert store.LIFE_FIELDS[:4] == [
            "life_plan",
            "life_coordination",
            "life_1_to",
            "life_1_workload",
        ]
        assert len(store.LIFE_FIELDS) == 2 + 4 * store.LIFE_PHASE_ROWS + store.LIFE_CHILDREN + 4

    def test_remembered_inputs_from_v1_0_get_home_defaults(self):
        old = v1_0_values()

        restored = store.read_last_inputs({"version": 1, "values": old})

        assert restored["home_plan"] == "off"
        assert restored["home_pillar2"] == 0
        assert restored["salary_growth"] == store.FIELD_DEFAULTS["salary_growth"]

    @pytest.mark.parametrize(
        ("rate", "expected"),
        [(5, 250), (100, math.floor(config.PILLAR3A_MONTHLY_MAX * 100) / 100)],
    )
    def test_old_savings_rates_migrate_to_a_fixed_monthly_amount(self, rate, expected):
        old = {
            "income": 5000,
            "income_period": "monthly",
            "income_type": "net",
            "canton": "ZH",
            "current_age": 35,
            "savings_mode": "rate",
            "savings_rate": rate,
            "pillar3a_amount": 350,
        }

        assert store.from_stored(old, 1)["pillar3a_amount"] == expected

    @pytest.mark.parametrize(
        "old",
        [
            {"savings_mode": "amount", "savings_rate": 5, "current_age": 35},
            {"savings_mode": "rate", "savings_rate": None, "current_age": 35},
            {"savings_mode": "rate", "savings_rate": 5},
            {
                "savings_mode": "rate",
                "savings_rate": 5,
                "current_age": 35,
                "income": 5000,
                "income_period": "unknown",
                "income_type": "net",
                "canton": "ZH",
            },
        ],
    )
    def test_unmigratable_savings_rates_leave_the_fixed_amount_unchanged(self, old):
        old["pillar3a_amount"] = 350

        assert store.from_stored(old, 1)["pillar3a_amount"] == 350


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


class TestHouseholdFormat:
    """Version 2 (v1.3): values by household and person; older versions migrate (#43)."""

    def test_stored_by_household_and_person(self):
        stored = store.save_scenario(None, "Zu zweit", sample_values())["scenarios"]["Zu zweit"]

        assert set(stored["values"]) == {"household", "persons"}
        household = stored["values"]["household"]
        a, b = stored["values"]["persons"]["a"], stored["values"]["persons"]["b"]
        assert set(a) == set(b) == set(store.PERSON_FIELDS)
        assert (a["income"], a["current_age"], a["home_savings"]) == (7200, 35, 180_000)
        assert (b["income"], b["current_age"], b["home_savings"]) == (98_000, 33, 40_000)
        assert household["household"] == "on"
        assert household["home_price"] == 1_100_000
        assert household["life_child_1"] == 36  # children belong to the household
        assert "income" not in household

    def test_round_trip_of_both_persons_and_the_household(self):
        state = store.save_scenario(None, "Zu zweit", sample_values())
        loaded = store.load_scenario(state, "Zu zweit")

        assert loaded == sample_values()
        assert loaded["b_income"] == 98_000
        assert loaded["b_life_1_costs"] == 800
        assert store.read_last_inputs(store.make_last_inputs(sample_values())) == sample_values()

    def test_changing_one_person_keeps_the_other(self):
        state = store.save_scenario(None, "Plan", sample_values())
        state = store.save_scenario(state, "Plan", sample_values(b_income=50_000))
        loaded = store.load_scenario(state, "Plan")

        assert (loaded["income"], loaded["b_income"]) == (7200, 50_000)

    def test_v1_2_scenarios_become_person_a(self):
        # Saved with v1.2: flat, with life phases and children, without a household.
        old = {
            field: value
            for field, value in sample_values().items()
            if field not in HOUSEHOLD_VALUES
        }
        state = {"version": 1, "scenarios": {"v1.2": {"values": old, "updated_at": "x"}}}

        loaded = store.load_scenario(state, "v1.2")

        assert {field: loaded[field] for field in old} == old
        assert loaded["household"] == "off"
        assert loaded["household_relationship"] == "married"
        assert loaded["household_credits"] == "half"
        assert loaded["b_income"] == store.PERSON_DEFAULTS["income"]
        assert loaded["b_home_savings"] == 0
        assert loaded["b_life_role"] == "other"
        assert loaded["b_pillar2_employee"] is None
        migrated = store.sanitize_scenarios(state)
        assert migrated["version"] == store.STORAGE_VERSION == 2
        assert migrated["scenarios"]["v1.2"]["values"]["persons"]["a"]["income"] == 7200

    def test_remembered_v1_inputs_become_person_a(self):
        old = {field: value for field, value in sample_values().items() if field != "household"}
        old = {field: value for field, value in old.items() if not field.startswith("b_")}

        restored = store.read_last_inputs({"version": 1, "values": old})

        assert restored["income"] == 7200
        assert restored["household"] == "off"
        assert restored["b_income"] == store.PERSON_DEFAULTS["income"]

    def test_v1_entries_with_person_b_fields_ignore_them(self):
        # A flat entry cannot hold person B: those fields only exist from version 2 on.
        restored = store.from_stored({"income": 1, "b_income": 2}, 1)
        assert (restored["income"], restored["b_income"]) == (1, store.PERSON_DEFAULTS["income"])

    @pytest.mark.parametrize("version", [None, "2", True, 0, -3])
    def test_missing_or_invalid_versions_count_as_the_first(self, version):
        assert store.from_stored({"income": 1}, version)["income"] == 1

    def test_newer_versions_are_read_like_the_current_one(self):
        stored = store.to_stored(sample_values())
        assert store.from_stored(stored, 3) == sample_values()

    @pytest.mark.parametrize(
        "stored",
        [
            None,
            "x",
            {"household": "x", "persons": None},
            {"household": {}, "persons": {"a": "x", "b": []}},
        ],
    )
    def test_corrupt_values_get_the_defaults(self, stored):
        values = store.from_stored(stored)
        assert values["household"] == "off"
        assert values["income"] is None
        assert values["b_income"] == store.PERSON_DEFAULTS["income"]

    def test_person_fields_cannot_come_from_the_household_part(self):
        stored = store.to_stored(sample_values())
        stored["household"]["income"] = 1
        stored["persons"]["a"]["home_price"] = 1

        values = store.from_stored(stored)
        assert (values["income"], values["home_price"]) == (7200, 1_100_000)

    def test_every_field_belongs_to_the_household_or_a_person(self):
        person_b = [store.person_field(field, "b") for field in store.PERSON_FIELDS]
        assert sorted([*store.HOUSEHOLD_FIELDS, *store.PERSON_FIELDS, *person_b]) == sorted(
            store.SCENARIO_FIELDS
        )
        assert store.person_field("income") == "income"
        assert store.person_field("income", "b") == "b_income"


def test_scenarios_with_invalid_names_are_dropped():
    data = {"scenarios": {"   ": {"values": {}}, "Gut": {"values": {}}}}

    assert list(store.sanitize_scenarios(data)["scenarios"]) == ["Gut"]
