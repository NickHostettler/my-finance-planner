"""End-to-end checks of the household planning with two persons (issue #45).

Separate personal projections, a joint purchase with money of both, saving and loading,
older scenarios of one person and the phone width.
"""

import json

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e


def _digits(page, selector):
    return page.locator(selector).input_value().replace("’", "")


def _fill(user, selector, value):
    user.page.fill(selector, value)
    user.page.press(selector, "Tab")
    user.wait_until_idle()


def _choose(user, control, label):
    user.page.locator(control).get_by_text(label, exact=True).click()
    user.wait_until_idle()


def _plan_two_persons(user):
    """Person A (35) and person B (33) with own balances; both put money into the purchase."""
    page = user.page
    _fill(user, "#pillar2-initial-input", "120000")
    _fill(user, "#pillar3b-initial-input", "150000")
    _choose(user, "#household-input", "Zwei Personen")
    _choose(user, "#input-person-input", "Person B")
    assert page.locator("#person-b-inputs").is_visible()
    assert not page.locator("#person-a-inputs").is_visible()
    _fill(user, "#b-current-age-input", "33")
    _fill(user, "#b-monthly-income-input", "6000")
    _fill(user, "#b-pillar2-initial-input", "80000")
    _fill(user, "#b-pillar3b-initial-input", "60000")
    page.locator("#shared-groups").get_by_text("Wohneigentum", exact=True).click()
    _choose(user, "#home-plan-input", "Kauf planen")


def _load_scenario(user, name):
    user.open_scenarios()
    user.page.locator("#scenario-select").click()
    user.page.get_by_role("option", name=name).click()
    user.page.click("#scenario-load-button")
    user.wait_until_idle()


def test_two_persons_with_a_joint_purchase_survive_save_and_reload(alice):
    alice.open()
    page = alice.page
    _plan_two_persons(alice)

    # Price 900'000: all free assets of both (150'000 + 60'000), then both pension funds.
    assert _digits(page, "#home-savings-input") == "150000"
    assert _digits(page, "#b-home-savings-input") == "60000"
    assert _digits(page, "#home-pillar2-input") == "120000"
    assert _digits(page, "#b-home-pillar2-input") == "80000"

    page.get_by_role("tab", name="Haushalt").click()
    household = page.locator("#household-section").inner_text()
    assert "Persönliche Vorsorge im Vergleich" in household
    assert "Kaufmittel je Person" in household
    page.get_by_role("tab", name="Wohneigentum").click()
    assert page.locator("#home-section .traffic-light").first.is_visible()
    assert "Vorsorgegeld von Person B für den Kauf (WEF)" in (
        page.locator("#home-section").inner_text()
    )

    # The personal results of person B: only person B's withdrawal is taken off.
    _choose(alice, "#result-person-input", "Person B")
    page.get_by_role("tab", name="Übersicht").click()
    overview_b = page.locator("#b-overview-section")
    assert overview_b.is_visible()
    assert not page.locator("#overview-section").is_visible()
    assert "Person B · 33 Jahre" in overview_b.inner_text()
    assert "Vorbezug Pensionskasse CHF 80’000" in overview_b.inner_text()

    alice.save_scenario("Zu zweit")
    alice.reload()

    assert page.locator("#household-input input:checked").get_attribute("value") == "on"
    assert _digits(page, "#b-current-age-input") == "33"
    assert _digits(page, "#b-home-pillar2-input") == "80000"
    stored = json.loads(alice.local_storage()["pf-scenarios"])
    values = stored["scenarios"]["Zu zweit"]["values"]
    assert stored["version"] == 2
    assert values["household"]["household"] == "on"
    assert (values["persons"]["a"]["current_age"], values["persons"]["b"]["current_age"]) == (
        35,
        33,
    )
    assert values["persons"]["b"]["home_pillar2"] == 80_000
    assert alice.errors == []


def test_an_error_of_person_b_stays_with_person_b(alice):
    alice.open()
    page = alice.page
    _choose(alice, "#household-input", "Zwei Personen")
    _choose(alice, "#input-person-input", "Person B")
    _fill(alice, "#b-current-age-input", "")

    _choose(alice, "#result-person-input", "Person B")
    assert "Person B: Bitte wähle dein aktuelles Alter" in (
        page.locator("#b-overview-section").inner_text()
    )
    _choose(alice, "#result-person-input", "Person A")
    assert "Projiziertes Vorsorgekapital" in page.locator("#overview-section").inner_text()
    assert alice.errors == []


def test_a_scenario_of_one_person_from_v1_2_loads_as_person_a(alice):
    alice.open()
    page = alice.page
    old = {
        "version": 1,
        "scenarios": {
            "Aus v1.2": {
                "values": {"income": 6400, "current_age": 41, "retirement_age": 65},
                "updated_at": "2026-11-01T10:00:00+00:00",
            }
        },
    }
    page.evaluate("data => localStorage.setItem('pf-scenarios', JSON.stringify(data))", old)
    alice.reload()

    _load_scenario(alice, "Aus v1.2")

    assert alice.income() == "6400"
    assert _digits(page, "#current-age-input") == "41"
    assert page.locator("#household-input input:checked").get_attribute("value") == "off"
    assert not page.locator("#person-b-inputs").is_visible()
    assert alice.errors == []


def test_phone_with_two_persons_never_scrolls_sideways(phone_user):
    phone_user.open()
    page = phone_user.page
    page.click("#navbar-burger")
    page.wait_for_timeout(500)
    _plan_two_persons(phone_user)
    page.click("#navbar-burger")
    page.wait_for_timeout(500)

    for person in ("Person A", "Person B"):
        _choose(phone_user, "#result-person-input", person)
        for tab in ["Übersicht", "Vorsorge", "Wohneigentum", "Lebensphasen", "Haushalt"]:
            page.get_by_role("tab", name=tab).click()
            page.wait_for_timeout(500)
            assert page.evaluate(
                "() => document.documentElement.scrollWidth <= window.innerWidth"
            ), (person, tab)
    assert phone_user.errors == []
