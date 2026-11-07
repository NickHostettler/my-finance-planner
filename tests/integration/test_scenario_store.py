import sqlite3

import pytest

from personal_finance.storage import scenario_store


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / "scenarios.sqlite3"


def sample_values():
    return {
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


def test_scenario_round_trip_and_listing_use_local_database(database_path):
    values = sample_values()

    assert scenario_store.save_scenario("  Basisplan  ", values, database_path) == "Basisplan"

    assert scenario_store.load_scenario("Basisplan", database_path) == values
    scenarios = scenario_store.list_scenarios(database_path)
    assert len(scenarios) == 1
    assert scenarios[0]["name"] == "Basisplan"
    assert scenarios[0]["updated_at"]
    assert database_path.exists()


def test_last_inputs_round_trip_independently_of_named_scenarios(database_path):
    values = sample_values()

    assert scenario_store.load_last_inputs(database_path) is None

    scenario_store.save_last_inputs(values, database_path)

    assert scenario_store.load_last_inputs(database_path) == values
    assert scenario_store.list_scenarios(database_path) == []


def test_last_inputs_are_updated_after_each_save(database_path):
    values = sample_values()
    scenario_store.save_last_inputs(values, database_path)
    values["income"] = 8100

    scenario_store.save_last_inputs(values, database_path)

    assert scenario_store.load_last_inputs(database_path)["income"] == 8100


def test_saving_last_inputs_rejects_incomplete_values(database_path):
    with pytest.raises(ValueError, match="fehlen Eingaben"):
        scenario_store.save_last_inputs({"income": 7200}, database_path)


def test_saving_same_name_updates_existing_scenario(database_path):
    values = sample_values()
    scenario_store.save_scenario("Teilzeit", values, database_path)
    values["income"] = 5000

    scenario_store.save_scenario("Teilzeit", values, database_path)

    assert len(scenario_store.list_scenarios(database_path)) == 1
    assert scenario_store.load_scenario("Teilzeit", database_path)["income"] == 5000


def test_scenario_delete_only_removes_matching_name(database_path):
    scenario_store.save_scenario("Basisplan", sample_values(), database_path)

    assert scenario_store.delete_scenario("Basisplan", database_path)
    assert not scenario_store.delete_scenario("Basisplan", database_path)
    assert scenario_store.list_scenarios(database_path) == []


@pytest.mark.parametrize("name", ["", "  ", "x" * 81, None])
def test_invalid_scenario_names_are_rejected(name, database_path):
    with pytest.raises(ValueError):
        scenario_store.save_scenario(name, sample_values(), database_path)


def test_scenario_fields_are_stored_as_queryable_sql_columns(database_path):
    scenario_store.save_scenario("Basisplan", sample_values(), database_path)

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT income, pillar2_mode, assumed_return, display_basis "
            "FROM scenarios WHERE name = ?",
            ("Basisplan",),
        ).fetchone()

    assert row == (7200, "custom", 0.06, "real")


def test_existing_scenario_database_gets_nominal_display_default(tmp_path):
    database_path = tmp_path / "scenarios.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE scenarios (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                application_version TEXT NOT NULL
            )
            """
        )

    scenario_store.list_scenarios(database_path)

    with sqlite3.connect(database_path) as connection:
        display_basis = connection.execute(
            "SELECT dflt_value FROM pragma_table_info('scenarios') WHERE name = ?",
            ("display_basis",),
        ).fetchone()

    assert display_basis == ("'nominal'",)


def test_existing_scenarios_get_default_ahv_contribution_years(tmp_path):
    database_path = tmp_path / "scenarios.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE scenarios (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                application_version TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO scenarios (name, created_at, updated_at, application_version)
            VALUES ('Alt', '2025-01-01', '2025-01-01', '1')
            """
        )

    scenario_store.list_scenarios(database_path)

    with sqlite3.connect(database_path) as connection:
        ahv_columns = connection.execute(
            "SELECT ahv_average_income, ahv_contribution_years "
            "FROM scenarios WHERE name = ?",
            ("Alt",),
        ).fetchone()

    assert ahv_columns == (None, 44)
