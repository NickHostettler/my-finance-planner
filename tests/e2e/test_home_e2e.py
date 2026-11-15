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
    household, person_a = stored["household"], stored["persons"]["a"]
    assert (household["home_plan"], household["home_price"], person_a["home_pillar2"]) == (
        "on",
        int(PRICE),
        int(PILLAR2),
    )
    page.get_by_role("tab", name="Wohneigentum").click()
    assert page.locator("#home-section .traffic-light").first.is_visible()
    assert alice.errors == []


def test_planning_fills_the_highest_amounts_and_a_reload_keeps_reductions(alice):
    """Issue #40: filled when planning and for another age, but never by loading."""
    alice.open()
    page = alice.page
    _fill(alice, "#pillar2-initial-input", "120000")
    _fill(alice, "#pillar3b-initial-input", "300000")
    page.locator(".input-navbar").get_by_text("Wohneigentum", exact=True).click()
    page.locator("#home-plan-input").get_by_text("Kauf planen").click()
    alice.wait_until_idle()

    # Buying now for the default price of 900'000: all free assets and the whole PK balance.
    assert _digits(page, "#home-savings-input") == "300000"
    assert _digits(page, "#home-pillar3a-input") == "0"
    assert _digits(page, "#home-pillar2-input") == "120000"

    _fill(alice, "#home-savings-input", "250000")
    alice.reload()
    assert _digits(page, "#home-savings-input") == "250000"

    # Another purchase age: the free assets have grown with the 3b plan until then.
    page.locator(".input-navbar").get_by_text("Wohneigentum", exact=True).click()
    _fill(alice, "#home-purchase-age-input", "40")
    assert int(_digits(page, "#home-savings-input")) > 300_000
    assert alice.errors == []
