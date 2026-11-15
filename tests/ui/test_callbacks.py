"""Dashboard callbacks: validation messages, helper controls and scenario actions."""

from contextvars import copy_context

import pytest
from dash import no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict

from personal_finance.dashboard import app, callbacks
from personal_finance.dashboard.callbacks import (
    SCENARIO_INPUT_IDS,
    ask_before_clearing_browser_data,
    manage_scenarios,
    remember_dashboard_inputs,
    restore_last_inputs,
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
    "home_plan": "off",
    "home_price": 900_000,
    "home_purchase_age": None,
    "home_savings": 200_000,
    "home_pillar3a": 0,
    "home_pillar2": 0,
    "home_gross_income": None,
    "home_imputed_rate": 5,
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


def test_results_fill_all_tabs():
    overview, pension, home, assumptions, _ = results()

    texts = [repr(section) for section in (overview, pension, home, assumptions)]
    assert "Projiziertes Vorsorgekapital" in texts[0]
    assert "Dein Sparplan" in texts[1]
    assert "Wohneigentum planen" in texts[2]
    assert "Modell statt Beratung" in texts[3]


# --- the "Wohneigentum" tab (issue #25) ----------------------------------------------------

HOME = {
    # Enough in the pension fund and free assets for the purchase today (age 35).
    "initial_2": 100_000,
    "initial_3b": 200_000,
    "home_plan": "on",
    "home_price": 1_000_000,
    "home_savings": 170_000,
    "home_pillar3a": 0,
    "home_pillar2": 60_000,
    "home_gross_income": 200_000,
    "home_imputed_rate": 5,
}


def texts(component):
    """All texts in a component tree (children, titles and aria labels), joined."""
    found = []
    for node in [component, *component._traverse()]:
        for prop in ("children", "title", "aria-label"):
            value = getattr(node, prop, None)
            if isinstance(value, str):
                found.append(value)
    return " ".join(found)


def home_tab(**overrides):
    return results(**{**HOME, **overrides})[2]


def test_home_tab_shows_the_assessment_with_traffic_light():
    tab = home_tab()
    text = texts(tab)

    assert "Tragbar" in text
    assert "Ampel: Tragbar" in text
    assert "CHF 200’000" in text  # equity
    assert "CHF 800’000" in text  # mortgage
    assert "Maximal finanzierbarer Kaufpreis" in text
    lamps = [node for node in tab._traverse() if "lamp-on" in str(getattr(node, "className", ""))]
    assert [lamp.className for lamp in lamps] == ["lamp lamp-green lamp-on"]


@pytest.mark.parametrize(
    ("overrides", "headline", "reason"),
    [
        ({"home_gross_income": 185_000}, "Knapp tragbar", "nahe an der Grenze"),
        ({"home_savings": 100_000, "home_pillar2": 130_000, "initial_2": 200_000},
         "Nicht tragbar", "harte Eigenmittel"),
        ({"home_gross_income": 120_000}, "Nicht tragbar", "erlaubt ist höchstens"),
    ],
)
def test_home_tab_explains_why_a_purchase_is_tight_or_not_affordable(overrides, headline, reason):
    text = texts(home_tab(**overrides))

    assert f"Ampel: {headline}" in text
    assert reason in text


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"home_price": None}, "Kaufpreis"),
        ({"home_price": ""}, "Kaufpreis"),
        ({"home_imputed_rate": 0}, "kalkulatorische Zins"),
        ({"home_imputed_rate": None}, "kalkulatorische Zins"),
        ({"home_savings": -5}, "Ersparte"),
        ({"home_purchase_age": 65}, "Kaufalter"),
        ({"home_purchase_age": 30}, "Kaufalter"),
        ({"home_savings": 2_000_000}, "höher als Kaufpreis"),
    ],
)
def test_invalid_home_inputs_show_a_message_only_in_the_home_tab(overrides, message):
    overview, _, home, _, _ = results(**{**HOME, **overrides})

    assert home.className == "validation-message"
    assert "Wohneigentum" in home.children[0].children
    assert message in home.children[1].children
    assert getattr(overview, "className", None) != "validation-message"


def test_home_tab_uses_the_income_inputs_without_an_entered_gross_income():
    net = texts(home_tab(home_gross_income=None))
    gross = texts(home_tab(home_gross_income=None, income_type="gross", income=16_000))

    assert "Bruttoeinkommen fehlt" in net
    assert "CHF 86’400" in net  # 7'200 net per month x 12
    assert "Bruttoeinkommen fehlt" not in gross
    assert "CHF 192’000" in gross  # 16'000 gross per month x 12


def test_without_a_planned_purchase_the_other_tabs_stay_the_same():
    # Regression: the "off" switch must give exactly the results of v1.0.
    not_planned = results(**{**HOME, "home_plan": "off"})
    before_home_ownership = results(initial_2=100_000, initial_3b=200_000)

    assert [repr(section) for section in not_planned[:2]] == [
        repr(section) for section in before_home_ownership[:2]
    ]
    assert "Wohneigentum planen" in texts(not_planned[2])


def test_invalid_purchase_leaves_the_other_tabs_without_purchase():
    invalid = results(**{**HOME, "home_price": None})
    not_planned = results(**{**HOME, "home_plan": "off"})

    assert repr(invalid[0]) == repr(not_planned[0])


# --- money from the 2nd pillar and 3a (issue #26) ----------------------------------------


def metric_values(component):
    return [
        node.children
        for node in component._traverse()
        if getattr(node, "className", None) == "metric-value"
    ]


def chf(text):
    return float(text.replace("CHF ", "").replace("’", "").replace("/Monat", ""))


def test_withdrawals_lower_the_retirement_capital_in_overview_and_home_tab():
    planned = results(**{**HOME, "home_pillar3a": 10_000, "initial_3a": 20_000})
    not_planned = results(**{**HOME, "home_pillar3a": 10_000, "initial_3a": 20_000,
                             "home_plan": "off"})

    with_purchase, without = metric_values(planned[0]), metric_values(not_planned[0])
    # Overview: total, 2nd pillar, 3a and 3b are lower after the purchase.
    for index in range(4):
        assert chf(with_purchase[index]) < chf(without[index])
    assert "Mit dem geplanten Kauf mit 35 Jahren: Vorbezug Pensionskasse CHF 60’000, " \
           "Bezug 3a CHF 10’000, Erspartes aus dem freien Vermögen CHF 170’000" \
        in texts(planned[0])

    home = texts(planned[2])
    assert "Vorsorge mit und ohne Kauf" in home
    assert "Möglicher Vorbezug" in home
    assert f"ohne Kauf {without[1]}" in home  # 2nd pillar card names the value without purchase
    figure = next(node.figure for node in planned[2]._traverse() if hasattr(node, "figure")
                  and node.figure.data[0].name == "2. Säule ohne Kauf")
    pillar2_without, pillar2_with = figure.data[0].y, figure.data[1].y
    assert pillar2_without[0] == 100_000
    assert pillar2_with[0] == 40_000  # 60'000 withdrawn at once
    assert chf(without[1]) == pytest.approx(pillar2_without[-1], abs=1)


def test_real_view_shows_the_home_capital_in_todays_purchasing_power():
    nominal = texts(results(**HOME)[2])
    real = texts(results(**{**HOME, "display_basis": "real"})[2])

    assert "Gestrichelt ohne Kauf · nominal" in nominal
    assert "Gestrichelt ohne Kauf · heutige Kaufkraft" in real


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"home_pillar2": 10_000}, "mindestens CHF 20’000"),
        ({"home_pillar2": 150_000}, "höchstens CHF 100’000"),
        ({"home_pillar2": 60_000, "home_purchase_age": 63}, "bis Alter 62"),
        ({"home_pillar3a": 5_000}, "Säule 3a ist zum Kaufzeitpunkt nicht möglich"),
        ({"home_pillar3a": -1}, "3a-Geld"),
    ],
)
def test_withdrawals_beyond_the_rules_are_explained(overrides, message):
    home = results(**{**HOME, **overrides})[2]

    assert home.className == "validation-message"
    assert message in home.children[1].children


def test_from_50_only_the_balance_at_50_or_half_can_be_withdrawn():
    # Today 55: the balance at 50 is not known, so the model takes half (cautious).
    home = texts(results(**{**HOME, "current_age": 55, "home_pillar2": 50_000})[2])

    assert "Möglicher Vorbezug" in home
    assert "CHF 50’000" in home
    assert "vorsichtig mit der Hälfte" in home


def test_savings_beyond_the_free_assets_are_assumed_to_come_from_outside():
    home = texts(results(**{**HOME, "initial_3b": 50_000})[2])

    assert "Erspartes ausserhalb der Prognose" in home
    assert "CHF 120’000" in home  # 170'000 savings - 50'000 free assets


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


def test_remembering_stores_the_current_inputs():
    inputs = callbacks._to_components(browser_store.values_to_inputs(VALID_INPUTS))

    store, status = remember_dashboard_inputs(*inputs)

    assert browser_store.read_last_inputs(store) == browser_store.sanitize_values(VALID_INPUTS)
    assert status == ""


def test_last_inputs_report_an_error_instead_of_failing():
    incomplete_inputs = browser_store.values_to_inputs(VALID_INPUTS)[:-1]

    store, status = remember_dashboard_inputs(*incomplete_inputs)

    assert store is no_update
    assert "konnten nicht gemerkt" in status.children


def test_restoring_fills_the_fields_or_changes_nothing():
    remembered = browser_store.make_last_inputs(VALID_INPUTS)

    restored = restore_last_inputs(1, remembered)

    assert restored == callbacks._to_components(browser_store.values_to_inputs(VALID_INPUTS))
    assert restored[SCENARIO_INPUT_IDS.index("return-input")] == "0.04"
    assert restore_last_inputs(1, None) == [no_update] * len(SCENARIO_INPUT_IDS)


def test_no_callback_reads_and_writes_the_same_property():
    # A callback that reads and writes the same fields made Dash wait forever (CI, #36).
    for key, callback in app.callback_map.items():
        outputs = {output.split("@")[0] for output in key.strip(".").split("...")}
        inputs = {f"{item['id']}.{item['property']}" for item in callback["inputs"]}
        assert not outputs & inputs, key
