"""End-to-end checks for issue #11: welcome notice and deleting all data in a browser."""

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e

SECRET_INCOME = "987600"  # the income field uses step=100


def test_notice_shows_once_per_browser(alice, bob):
    alice.open()
    assert alice.notice_visible()

    alice.dismiss_notice()
    assert not alice.notice_visible()
    alice.reload()
    assert not alice.notice_visible()

    # Another user (browser) still sees it on the first visit.
    bob.open()
    assert bob.notice_visible()


def test_footer_link_reopens_notice(alice):
    alice.open()
    alice.dismiss_notice()

    alice.reopen_notice()

    assert alice.notice_visible()


def test_delete_all_removes_scenarios_and_remembered_inputs(alice):
    alice.open()
    alice.set_income(SECRET_INCOME)
    alice.save_scenario("Weg damit")
    assert alice.stored_scenario_names() == ["Weg damit"]

    alice.clear_all_data(confirm=True)

    assert alice.stored_scenario_names() == []
    assert alice.dropdown_options() == []
    assert alice.income() != SECRET_INCOME
    assert not any(key.startswith("pf-") and SECRET_INCOME in value
                   for key, value in alice.local_storage().items())
    assert alice.errors == []


def test_cancel_keeps_the_data(alice):
    alice.open()
    alice.set_income(SECRET_INCOME)
    alice.save_scenario("Bleibt")

    alice.clear_all_data(confirm=False)

    assert alice.stored_scenario_names() == ["Bleibt"]
    alice.reload()
    assert alice.income() == SECRET_INCOME
