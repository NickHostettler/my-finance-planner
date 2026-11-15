"""Issue #40: the purchase money is filled with the highest amounts at the purchase age."""

from contextvars import copy_context

import pytest
from dash import no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict

from personal_finance.dashboard import callbacks
from personal_finance.dashboard.callbacks import (
    SCENARIO_INPUT_IDS,
    fill_home_maximum,
    manage_scenarios,
    restore_last_inputs,
    update_home_amount_hints,
)
from personal_finance.dashboard.callbacks import HOME_AMOUNT_IDS
from personal_finance.dashboard.layout import HOME_AMOUNT_HINTS
from personal_finance.storage import browser_store
from tests.ui.test_callbacks import HOME, VALID_INPUTS, home_tab, texts

# One person: person B's purchase fields (3 to 5) stay as they are.
KEEP_B = [no_update] * 3
UNCHANGED = [no_update] * 3 + KEEP_B + [None]


def components(**overrides):
    """The input field values by component id, as the browser sends them."""
    values = browser_store.values_to_inputs({**VALID_INPUTS, **HOME, **overrides})
    return dict(zip(SCENARIO_INPUT_IDS, callbacks._to_components(values)))


def fill(trigger="home-plan-input", skip=None, **overrides):
    fields = components(**overrides)
    others = [fields[component_id] for component_id in callbacks._PREFILL_STATE_IDS]

    def _run():
        context_value.set(
            AttributeDict(triggered_inputs=[{"prop_id": f"{trigger}.value", "value": None}])
        )
        return fill_home_maximum(
            fields["home-plan-input"], fields["home-purchase-age-input"], 1, skip, *others
        )

    return copy_context().run(_run)


def hints(**overrides):
    fields = components(**overrides)
    return update_home_amount_hints(
        *[fields[component_id] for component_id in callbacks._HINT_INPUT_IDS]
    )


# --- filling the fields ----------------------------------------------------------------


def test_planning_a_purchase_fills_the_highest_amounts():
    # Today (35): free assets 200'000, no 3a, PK 100'000. Price 1'000'000 + 30'000 costs:
    # savings 200'000 (170'000 hard equity after the costs), the PK may add its 100'000.
    assert fill() == [200_000, 0, 100_000, *KEEP_B, None]


def test_a_later_purchase_uses_the_projection_at_that_age():
    now = fill()
    later = fill(trigger="home-purchase-age-input", home_purchase_age=45)

    assert later[0] > now[0]  # the free assets grow with the 3b plan until then
    assert later[2] > now[2]  # and the pension fund with the contributions


def test_no_more_than_the_purchase_needs():
    # Price 150'000 + 4'500 costs: the free assets alone pay for it.
    assert fill(home_price=150_000) == [154_500, 0, 0, *KEEP_B, None]


def test_loading_keeps_the_loaded_amounts_once():
    loaded = {"plan": "on", "age": None}

    assert fill(skip=loaded) == UNCHANGED
    # An emptied age field sends "" instead of None.
    assert fill(skip=loaded, home_purchase_age="") == UNCHANGED
    # Another age than the loaded one is a change by the user.
    assert fill(skip=loaded, home_purchase_age=45)[:3] != UNCHANGED[:3]


def test_button_fills_even_right_after_loading():
    assert fill("home-max-button", skip={"plan": "on", "age": None}) == [
        200_000,
        0,
        100_000,
        *KEEP_B,
        None,
    ]


@pytest.mark.parametrize(
    "overrides",
    [{"home_plan": "off"}, {"home_price": None}, {"home_purchase_age": 70}, {"current_age": None}],
)
def test_nothing_is_filled_without_a_valid_purchase(overrides):
    assert fill(**overrides) == UNCHANGED


def test_loading_a_scenario_or_the_last_inputs_sets_the_guard():
    inputs = browser_store.values_to_inputs({**VALID_INPUTS, **HOME, "home_purchase_age": 45})
    store = browser_store.save_scenario(
        None, "Kauf", browser_store.values_from_inputs(list(inputs))
    )

    def _load():
        context_value.set(
            AttributeDict(triggered_inputs=[{"prop_id": "scenario-load-button.n_clicks"}])
        )
        return manage_scenarios(0, 0, 1, 0, None, "Kauf", store, *inputs)

    loaded = copy_context().run(_load)
    restored = restore_last_inputs(
        1, browser_store.make_last_inputs(browser_store.load_scenario(store, "Kauf"))
    )

    assert loaded[4 + len(SCENARIO_INPUT_IDS)] == {"plan": "on", "age": 45}
    assert restored[-1] == {"plan": "on", "age": 45}
    assert restore_last_inputs(1, None)[-1] is no_update


# --- hints below the fields --------------------------------------------------------------


def test_hints_show_the_highest_amounts_at_the_purchase_age():
    savings, pillar3a, pillar2, *person_b = hints()

    assert (
        savings == "Freies Vermögen zum Kaufalter: CHF 200’000 · inkl. Geld für die Kaufnebenkosten"
    )
    assert pillar3a == "3a zum Kaufalter: CHF 0 · zählt als harte Eigenmittel"
    assert pillar2 == "Höchstens CHF 100’000 zum Kaufalter · zählt nicht als harte Eigenmittel"
    # One person: person B's fields keep their texts.
    assert person_b == [HOME_AMOUNT_HINTS[i] for i in HOME_AMOUNT_IDS[3:]]


def test_hints_without_an_advance_withdrawal():
    # Retirement at 65: an advance withdrawal is possible until 62.
    assert hints(home_purchase_age=63)[2].startswith("Zum Kaufalter kein Vorbezug möglich")


def test_hints_without_a_planned_purchase_are_the_defaults():
    assert hints(home_plan="off") == [HOME_AMOUNT_HINTS[i] for i in HOME_AMOUNT_IDS]


# --- the "Wohneigentum" tab ------------------------------------------------------------


def test_home_tab_compares_the_minimum_with_what_is_available():
    text = texts(home_tab())

    assert "Eigenmittel: Bedarf und verfügbare Mittel" in text
    # Price 1'000'000: 200'000 equity, 100'000 hard, 30'000 costs, 230'000 together.
    assert "Mindestbedarf insgesamt" in text
    assert "CHF 230’000" in text
    assert "Verfügbar insgesamt" in text
    assert "CHF 300’000" in text  # 200'000 free assets + 100'000 PK
    assert "CHF 170’000 · reicht" in text  # hard: 170'000 for 130'000
    assert "CHF 230’000 · reicht" in text  # together: 170'000 + 60'000 for 230'000


def test_home_tab_shows_what_is_missing():
    text = texts(home_tab(home_savings=100_000, home_pillar2=130_000, initial_2=200_000))

    assert "CHF 100’000 · es fehlen CHF 30’000" in text  # hard: 100'000 for 130'000


def test_home_tab_shows_the_highest_price_with_everything_available():
    text = texts(home_tab())

    assert "Höchster Kaufpreis mit 35 Jahren" in text
    assert "Mit allen verfügbaren Mitteln (CHF 300’000)" in text


def test_home_tab_says_when_no_advance_withdrawal_is_possible():
    text = texts(home_tab(home_purchase_age=63, home_pillar2=0))

    assert "nicht möglich" in text
