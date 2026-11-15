"""End-to-end check of the life phases (issue #33): plan, save, reload, see the gap."""

import json

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e


def _digits(page, selector):
    return page.locator(selector).input_value().replace("’", "")


def _open_group(user, name="Lebensphasen & Familie"):
    # Person B has the same groups (hidden): only person A's or the shared ones.
    scope = "#shared-groups" if name == "Kinder" else "#person-a-inputs"
    user.page.locator(scope).get_by_text(name, exact=True).click()
    user.page.wait_for_timeout(300)


def test_life_phases_from_a_template_survive_a_reload(alice):
    alice.open()
    page = alice.page
    _open_group(alice)

    page.locator("#life-plan-input").get_by_text("Phasen planen").click()
    alice.wait_until_idle()
    # Planning starts with full time: the income from above (net 5'000 by default).
    assert _digits(page, "#life-1-workload-input") == "100"
    assert _digits(page, "#life-1-income-input") == "5000"
    assert not page.locator("#life-row-2").is_visible()

    page.get_by_role("button", name="Teilzeit mit Kindern").click()
    alice.wait_until_idle()
    assert page.locator("#life-row-3").is_visible()
    assert _digits(page, "#life-2-to-input") == "44"
    assert _digits(page, "#life-2-workload-input") == "60"
    assert "ab 45 bis zur Pensionierung" in page.locator("#life-row-3-title").inner_text()

    _open_group(alice, "Kinder")
    page.fill("#life-child-1-input", "37")
    page.press("#life-child-1-input", "Tab")
    alice.wait_until_idle()
    alice.save_scenario("Teilzeit")

    alice.reload()

    _open_group(alice)
    _open_group(alice, "Kinder")
    assert _digits(page, "#life-2-workload-input") == "60"
    assert _digits(page, "#life-child-1-input") == "37"
    stored = json.loads(alice.local_storage()["pf-scenarios"])["scenarios"]["Teilzeit"]["values"]
    person_a, household = stored["persons"]["a"], stored["household"]
    assert (person_a["life_plan"], person_a["life_2_workload"], household["life_child_1"]) == (
        "on",
        60,
        37,
    )
    page.get_by_role("tab", name="Lebensphasen").click()
    section = page.locator("#life-section")
    assert "Vorsorgelücke bei Pensionierung" in section.inner_text()
    assert "Mit deinen Lebensphasen gerechnet" in page.locator("#overview-section").inner_text()
    assert alice.errors == []


def test_add_and_remove_a_phase(alice):
    alice.open()
    page = alice.page
    _open_group(alice)
    page.locator("#life-plan-input").get_by_text("Phasen planen").click()
    alice.wait_until_idle()

    page.get_by_role("button", name="+ Phase").click()
    alice.wait_until_idle()
    # One phase 35 … 64 is split in the middle: 35 … 49 and 50 … 64.
    assert page.locator("#life-row-2").is_visible()
    assert _digits(page, "#life-1-to-input") == "49"

    page.get_by_role("button", name="− Phase").click()
    alice.wait_until_idle()
    assert not page.locator("#life-row-2").is_visible()
    assert alice.errors == []
