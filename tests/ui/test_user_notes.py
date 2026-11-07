"""Issue #11: welcome notice, no-advice and privacy hints, delete-all-data control."""

from contextvars import copy_context

from dash import dcc, html, no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict

from personal_finance.dashboard import app
from personal_finance.dashboard.callbacks import NOTICE_VERSION, toggle_welcome_notice
from personal_finance.dashboard.layout import STORAGE_KEY_PREFIX


def _components():
    return list(app.layout._traverse())


def _by_id(component_id):
    return next(c for c in _components() if getattr(c, "id", None) == component_id)


def _text(component):
    if isinstance(component, str):
        return component
    children = getattr(component, "children", None)
    if children is None:
        return ""
    if not isinstance(children, (list, tuple)):
        children = [children]
    return " ".join(_text(child) for child in children)


def _toggle(trigger, store_data):
    def _run():
        triggered = [{"prop_id": f"{trigger}.n_clicks", "value": 1}] if trigger else []
        context_value.set(AttributeDict(triggered_inputs=triggered))
        return toggle_welcome_notice(1, 0, 0, store_data)

    return copy_context().run(_run)


# --- welcome notice ------------------------------------------------------------------


def test_notice_covers_no_advice_privacy_and_device_scope():
    text = _text(_by_id("welcome-notice"))

    assert "Keine Beratung" in text
    assert "nur in diesem Browser" in text
    assert "Der Server speichert nichts" in text
    assert "anderen Gerät" in text


def test_notice_is_hidden_until_the_browser_state_is_known():
    # Hidden in the initial HTML so returning users never see it flash up.
    assert _by_id("welcome-notice").hidden is True


def test_first_visit_shows_notice():
    assert _toggle("scenario-initial-load", None) == (False, no_update)


def test_acknowledged_browser_does_not_show_notice_again():
    acknowledged = {"version": NOTICE_VERSION, "acknowledged": True}

    assert _toggle("scenario-initial-load", acknowledged) == (True, no_update)


def test_older_acknowledgement_shows_updated_notice_again():
    outdated = {"version": NOTICE_VERSION - 1, "acknowledged": True}

    assert _toggle("scenario-initial-load", outdated)[0] is False


def test_dismiss_hides_and_remembers_in_browser():
    hidden, store = _toggle("welcome-dismiss", None)

    assert hidden is True
    assert store == {"version": NOTICE_VERSION, "acknowledged": True}


def test_footer_link_reopens_notice():
    acknowledged = {"version": NOTICE_VERSION, "acknowledged": True}

    assert _toggle("welcome-show", acknowledged) == (False, no_update)


# --- permanent hints -----------------------------------------------------------------


def test_footer_states_no_advice_and_local_data():
    footer = next(c for c in _components() if isinstance(c, html.Footer))
    text = _text(footer)

    assert "Keine Finanzberatung" in text
    assert "Deine Daten bleiben in deinem Browser" in text
    assert "Hinweise anzeigen" in text


# --- delete all data in this browser -------------------------------------------------


def test_delete_all_control_asks_for_confirmation():
    button = _by_id("clear-browser-data-button")
    dialog = _by_id("clear-browser-data-confirm")

    assert "Alle Daten in diesem Browser löschen" in _text(button)
    assert isinstance(dialog, dcc.ConfirmDialog)
    assert "nicht rückgängig" in dialog.message


def test_every_browser_store_uses_the_prefix_that_delete_all_removes():
    stores = [c for c in _components() if isinstance(c, dcc.Store)]

    assert stores, "expected browser stores in the layout"
    for store in stores:
        assert store.storage_type == "local"
        assert store.id.startswith(STORAGE_KEY_PREFIX), store.id
