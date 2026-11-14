"""Issue #4: one user's data must never be visible to another user.

Each simulated user ("session") has its own browser storage. The server side only
runs callbacks; these tests prove it keeps nothing between them.
"""

import copy
import logging
import os
from contextvars import copy_context

import pytest
from dash import no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict

from personal_finance.dashboard import callbacks
from personal_finance.dashboard.callbacks import (
    SCENARIO_INPUT_IDS,
    manage_scenarios,
    remember_dashboard_inputs,
    update_results,
)
from personal_finance.storage import browser_store

SECRET_INCOME = 987654
N_INPUTS = len(SCENARIO_INPUT_IDS)


def inputs(**overrides):
    values = {
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
    values.update(overrides)
    return browser_store.values_to_inputs(values)


def run_callback(trigger, func, *args):
    """Call a Dash callback as if ``trigger`` (component id) had fired."""

    def _run():
        triggered = [{"prop_id": f"{trigger}.value", "value": None}] if trigger else []
        context_value.set(AttributeDict(triggered_inputs=triggered))
        return func(*args)

    return copy_context().run(_run)


class Browser:
    """One user's browser: its own localStorage and its own input values."""

    def __init__(self, **input_overrides):
        self.scenarios = None
        self.last_inputs = None
        self.inputs = inputs(**input_overrides)

    def _scenarios(self, trigger, name=None, selected=None):
        result = run_callback(
            trigger, manage_scenarios, 0, 0, 0, 0, name, selected, self.scenarios, *self.inputs
        )
        if result[-1] is not no_update:
            self.scenarios = result[-1]
        return result

    def open_page(self):
        return self._scenarios("scenario-initial-load")

    def save(self, name):
        return self._scenarios("scenario-save-button", name=name)

    def load(self, name):
        return self._scenarios("scenario-load-button", selected=name)

    def type_input(self):
        store, _ = remember_dashboard_inputs(*self.inputs)
        if store is not no_update:
            self.last_inputs = store

    def restore_last_inputs(self):
        return callbacks.restore_last_inputs(1, self.last_inputs)


def option_names(result):
    return [option["value"] for option in result[0]]


def test_scenarios_saved_by_one_user_are_invisible_to_another():
    alice, bob = Browser(income=SECRET_INCOME), Browser(income=4000)

    alice.save("Alice geheim")

    assert option_names(alice.open_page()) == ["Alice geheim"]
    assert option_names(bob.open_page()) == []
    load_attempt = bob.load("Alice geheim")
    assert "nicht gefunden" in str(load_attempt[2])
    assert SECRET_INCOME not in load_attempt[4 : 4 + N_INPUTS]


def test_last_inputs_are_remembered_per_browser_only():
    alice, bob = Browser(income=SECRET_INCOME), Browser(income=4000)

    alice.type_input()
    bob_restore = bob.restore_last_inputs()
    alice_restore = alice.restore_last_inputs()

    assert bob_restore[:N_INPUTS] == [no_update] * N_INPUTS
    assert alice_restore[0] == SECRET_INCOME


def test_same_scenario_name_in_two_browsers_stays_separate():
    alice, bob = Browser(income=SECRET_INCOME), Browser(income=4000)

    alice.save("Plan")
    bob.save("Plan")

    assert alice.load("Plan")[4] == SECRET_INCOME
    assert bob.load("Plan")[4] == 4000


def test_results_for_one_user_do_not_depend_on_previous_users():
    bob_inputs = inputs(income=4000)

    fresh = repr(update_results(*bob_inputs))
    update_results(*inputs(income=SECRET_INCOME))
    after_other_user = repr(update_results(*bob_inputs))

    assert after_other_user == fresh
    assert str(SECRET_INCOME) not in after_other_user


def _module_state(module):
    return {
        name: copy.deepcopy(value)
        for name, value in vars(module).items()
        if not name.startswith("__") and isinstance(value, (dict, list, set, tuple, str, int))
    }


def test_callbacks_keep_no_module_level_state():
    before = (_module_state(callbacks), _module_state(browser_store))

    alice = Browser(income=SECRET_INCOME)
    alice.save("Alice")
    alice.type_input()
    update_results(*alice.inputs)

    assert (_module_state(callbacks), _module_state(browser_store)) == before


def test_server_writes_no_files(tmp_path, monkeypatch):
    for variable in ("HOME", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "XDG_DATA_HOME", "TMP"):
        monkeypatch.setenv(variable, str(tmp_path))
    monkeypatch.chdir(tmp_path)

    alice = Browser(income=SECRET_INCOME)
    alice.open_page()
    alice.save("Alice")
    alice.load("Alice")
    alice.type_input()
    alice.restore_last_inputs()
    update_results(*alice.inputs)

    assert list(tmp_path.rglob("*")) == []


def test_user_values_are_never_logged_or_printed(caplog, capsys):
    caplog.set_level(logging.DEBUG)

    alice = Browser(income=SECRET_INCOME)
    alice.save("Geheimname-A")
    alice.load("Geheimname-A")
    alice.load("Gibt es nicht")
    alice.type_input()
    update_results(*alice.inputs)

    captured = capsys.readouterr()
    for secret in (str(SECRET_INCOME), "Geheimname-A"):
        assert secret not in caplog.text
        assert secret not in captured.out + captured.err


@pytest.mark.parametrize("module", [callbacks, browser_store])
def test_no_server_side_persistence_modules_are_used(module):
    source = open(module.__file__, encoding="utf-8").read()

    for forbidden in ("sqlite3", "open(", "lru_cache", "pickle", "shelve", "logging"):
        assert forbidden not in source, f"{forbidden} in {os.path.basename(module.__file__)}"
