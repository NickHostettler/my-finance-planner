"""Dashboard callbacks: validation messages, helper controls and scenario actions."""

from contextvars import copy_context

import pytest
from dash import no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict

from personal_finance.dashboard import callbacks
from personal_finance.dashboard.callbacks import (
    SCENARIO_INPUT_IDS,
    ask_before_clearing_browser_data,
    manage_scenarios,
    remember_dashboard_inputs,
    update_income_controls,
    update_income_preview,
    update_results,
)
from personal_finance.dashboard.components import number_input
from personal_finance.storage import browser_store

VALID_INPUTS = {
    "income": 7200,
    "income_period": "monthly",
    "income_type": "net",
    "canton": "ZH",
    "current_age": 35,
    "retirement_age": 65,
    "savings_mode": "rate",
    "savings_rate": 10,
    "pillar3a_amount": 300,
    "pillar3b_amount": 200,
    "initial_3a": 0,
    "initial_3b": 0,
    "initial_2": 0,
    "pillar2_mode": "minimum",
    "pillar2_employee": None,
    "pillar2_employer": None,
    "pillar2_return": None,
    "assumed_return": 0.04,
    "display_basis": "nominal",
    "ahv_average_income": None,
    "ahv_contribution_years": 44,
}


def results(**overrides):
    return update_results(*browser_store.values_to_inputs({**VALID_INPUTS, **overrides}))


def error_text(result):
    *sections, notice = result
    assert notice == ""
    # The message is shown in every result tab, so it is visible whichever tab is open.
    assert all(section.className == "validation-message" for section in sections)
    return sections[0].children[1].children


def run_callback(trigger, func, *args):
    """Call a Dash callback as if ``trigger`` (component id) had fired."""

    def _run():
        triggered = [{"prop_id": f"{trigger}.value", "value": None}] if trigger else []
        context_value.set(AttributeDict(triggered_inputs=triggered))
        return func(*args)

    return copy_context().run(_run)


# --- update_results: every input is validated with a helpful message ----------------


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"current_age": None}, "aktuelles Alter"),
        ({"retirement_age": None}, "aktuelles Alter"),
        ({"current_age": 17}, "mindestens deinem aktuellen Alter"),
        ({"current_age": 50, "retirement_age": 45}, "mindestens deinem aktuellen Alter"),
        ({"income": 0}, "größer als 0"),
        ({"savings_mode": "other"}, "Beitragsart"),
        ({"savings_rate": None}, "Sparquote"),
        ({"savings_rate": float("nan")}, "Sparquote"),
        ({"savings_rate": 101}, "Sparquote"),
        ({"savings_mode": "amount", "pillar3a_amount": None}, "3a-Beitrag"),
        ({"savings_mode": "amount", "pillar3a_amount": float("inf")}, "3a-Beitrag"),
        ({"savings_mode": "amount", "pillar3a_amount": -1}, "3a-Beitrag"),
        ({"pillar3b_amount": None}, "3b-Beitrag"),
        ({"pillar3b_amount": -1}, "3b-Beitrag"),
        ({"initial_3a": -1}, "3a-Guthaben"),
        ({"initial_3b": float("nan")}, "3b-Guthaben"),
        ({"initial_2": -1}, "BVG-Guthaben"),
        ({"pillar2_mode": "other"}, "Berechnungsgrundlage"),
        ({"pillar2_mode": "custom", "pillar2_employee": None}, "Arbeitnehmerbeitrag"),
        (
            {"pillar2_mode": "custom", "pillar2_employee": 100, "pillar2_employer": None},
            "Arbeitgeberbeitrag",
        ),
        (
            {
                "pillar2_mode": "custom",
                "pillar2_employee": 100,
                "pillar2_employer": 100,
                "pillar2_return": None,
            },
            "Verzinsung",
        ),
        ({"assumed_return": None}, "Renditeannahmen"),
        ({"assumed_return": 0.05}, "Renditeannahmen"),
        ({"display_basis": "other"}, "nominale oder reale"),
        ({"ahv_contribution_years": None}, "Beitragsjahre"),
        ({"ahv_contribution_years": 45}, "Beitragsjahre"),
    ],
)
def test_invalid_inputs_show_a_message_instead_of_results(overrides, message):
    assert message in error_text(results(**overrides))


def test_zero_net_income_after_deductions_is_reported(monkeypatch):
    monkeypatch.setattr(callbacks, "normalize_income", lambda *args: (0.0, 100.0))

    assert "0 CHF" in error_text(results(income_type="gross"))


def test_capped_3a_contribution_is_explained():
    notice = results(savings_mode="amount", pillar3a_amount=2000)[-1]

    assert "Modell-Limit" in notice


def test_results_fill_all_three_tabs():
    overview, pension, assumptions, _ = results()

    texts = [repr(section) for section in (overview, pension, assumptions)]
    assert "Projiziertes Vorsorgekapital" in texts[0]
    assert "Dein Sparplan" in texts[1]
    assert "Modell statt Beratung" in texts[2]


# --- values coming from the Mantine input fields ------------------------------------------


def test_return_switch_sends_text_and_is_used_as_number():
    as_text, as_number = results(assumed_return="0.06"), results(assumed_return=0.06)

    assert repr(as_text) == repr(as_number)


def test_unknown_return_text_is_rejected():
    assert "Renditeannahmen" in error_text(results(assumed_return="viel"))


def test_emptied_number_field_counts_as_missing():
    # Mantine number fields send "" instead of None when they are cleared.
    assert "3b-Beitrag" in error_text(results(pillar3b_amount=""))
    overview = results(initial_3a="")[0]  # optional balance: empty means 0
    assert getattr(overview, "className", None) != "validation-message"


def test_fields_receive_the_return_as_text_and_empty_values_as_none():
    values = browser_store.values_to_inputs({**VALID_INPUTS, "assumed_return": None})

    assert callbacks._to_components(values)[SCENARIO_INPUT_IDS.index("return-input")] is None
    stored = callbacks._from_components(callbacks._to_components(
        browser_store.values_to_inputs(VALID_INPUTS)
    ))
    assert stored == browser_store.values_to_inputs(VALID_INPUTS)


# --- small helper callbacks ------------------------------------------------------------


@pytest.mark.parametrize(
    ("period", "income_type", "label", "unit", "canton_display"),
    [
        ("yearly", "gross", "Dein jährliches Bruttoeinkommen", "CHF/Jahr", "block"),
        ("monthly", "net", "Dein monatliches Nettoeinkommen", "CHF/Monat", "none"),
    ],
)
def test_income_controls_follow_period_and_type(period, income_type, label, unit, canton_display):
    shown_label, shown_unit, width, hint, canton_style = update_income_controls(
        period, income_type
    )

    assert (shown_label, shown_unit, canton_style["display"]) == (label, unit, canton_display)
    assert width > 0
    assert hint


def test_income_preview_for_net_gross_and_invalid_income():
    assert "5’000" in update_income_preview(5000, "monthly", "net", 35, "ZH")
    assert "geschätztes Netto" in update_income_preview(90000, "yearly", "gross", None, None)
    assert "größer als 0" in update_income_preview(None, "monthly", "net", 35, "ZH")


def test_clearing_browser_data_asks_for_confirmation_first():
    assert ask_before_clearing_browser_data(1) is True


def test_number_input_without_unit_has_no_unit_label():
    component = number_input("plain-input", "Zahl", 1, minimum=0, step=1)

    assert "rightSection" not in component.to_plotly_json()["props"]


def test_number_input_with_unit_and_whole_numbers_only():
    component = number_input("age-input", "Alter", 35, 18, 1, "Jahre", 80, decimals=0)
    props = component.to_plotly_json()["props"]

    assert (props["rightSection"], props["max"], props["allowDecimal"]) == ("Jahre", 80, False)
    assert props["thousandSeparator"] == "’"


# --- scenario actions in the user's own browser storage ---------------------------------


def scenarios(trigger, store_data, selected=None, name=None):
    inputs = browser_store.values_to_inputs(VALID_INPUTS)
    return run_callback(
        trigger, manage_scenarios, 0, 0, 0, 0, name, selected, store_data, *inputs
    )


def status_text(result):
    return result[2].children


def test_delete_removes_only_the_selected_scenario():
    store = scenarios("scenario-save-button", None, name="A")[-1]
    store = scenarios("scenario-save-button", store, name="B")[-1]

    result = scenarios("scenario-delete-button", store, selected="A")

    assert [option["value"] for option in result[0]] == ["B"]
    assert result[1] is None
    assert "gelöscht" in status_text(result)
    assert list(result[-1]["scenarios"]) == ["B"]


@pytest.mark.parametrize("trigger", ["scenario-load-button", "scenario-delete-button"])
def test_load_and_delete_need_a_selected_scenario(trigger):
    result = scenarios(trigger, None, selected=None)

    assert "zuerst ein gespeichertes Szenario" in status_text(result)
    assert result[-1] is no_update


def test_unknown_trigger_changes_nothing():
    result = scenarios(None, None)

    assert result[0] is no_update
    assert result[2] == ""
    assert result[-1] is no_update


def test_last_inputs_ignore_unrelated_triggers():
    store = browser_store.make_last_inputs(VALID_INPUTS)
    inputs = browser_store.values_to_inputs(VALID_INPUTS)

    result = run_callback(None, remember_dashboard_inputs, 0, *inputs, store)

    assert result[: len(SCENARIO_INPUT_IDS) + 1] == [no_update] * (len(SCENARIO_INPUT_IDS) + 1)
    assert result[-1] == ""


def test_last_inputs_report_an_error_instead_of_failing():
    incomplete_inputs = browser_store.values_to_inputs(VALID_INPUTS)[:-1]

    result = run_callback(
        "monthly-income-input", remember_dashboard_inputs, 0, *incomplete_inputs, None
    )

    assert result[-2] is no_update
    assert "konnten nicht gemerkt" in result[-1].children
