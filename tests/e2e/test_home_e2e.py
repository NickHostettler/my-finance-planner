"""End-to-end check of the home purchase inputs (issue #25): they survive a reload."""

import json

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e

PRICE = "750000"
PILLAR2 = "60000"


def _digits(page, selector):
    # Fields show Swiss thousand separators (750’000); compare the plain digits.
    return page.locator(selector).input_value().replace("’", "")


def _fill(user, selector, value):
    user.page.fill(selector, value)
    user.page.press(selector, "Tab")
    user.wait_until_idle()


def test_home_purchase_survives_reload_and_is_stored_in_the_scenario(alice):
    alice.open()
    page = alice.page

    # A withdrawal from the pension fund needs a balance to take it from.
    _fill(alice, "#pillar2-initial-input", "120000")
    # The fields are in a collapsed group and hidden until a purchase is planned.
    page.locator(".input-navbar").get_by_text("Wohneigentum", exact=True).click()
    page.locator("#home-plan-input").get_by_text("Kauf planen").click()
    alice.wait_until_idle()
    _fill(alice, "#home-price-input", PRICE)
    _fill(alice, "#home-pillar2-input", PILLAR2)
    alice.save_scenario("Mit Eigenheim")

    alice.reload()

    assert page.locator("#home-plan-input input:checked").get_attribute("value") == "on"
    assert _digits(page, "#home-price-input") == PRICE
    assert _digits(page, "#home-pillar2-input") == PILLAR2
    scenarios = json.loads(alice.local_storage()["pf-scenarios"])["scenarios"]
    stored = scenarios["Mit Eigenheim"]["values"]
    assert (stored["home_plan"], stored["home_price"], stored["home_pillar2"]) == (
        "on",
        int(PRICE),
        int(PILLAR2),
    )
    page.get_by_role("tab", name="Wohneigentum").click()
    assert page.locator("#home-section .traffic-light").first.is_visible()
    assert alice.errors == []
