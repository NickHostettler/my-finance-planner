"""End-to-end checks of the Mantine layout (issue #36): tabs, and phones via the menu."""

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e


def _no_horizontal_scroll(page):
    return page.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")


def _inputs_on_screen(page):
    # Mantine slides the collapsed column out of the screen instead of hiding it.
    box = page.locator(".input-navbar").bounding_box()
    return box["x"] + box["width"] > 0 and box["x"] < page.viewport_size["width"]


def test_every_tab_shows_its_results(alice):
    alice.open()
    page = alice.page

    for tab, expected in [
        ("Vorsorge", "Dein Sparplan"),
        ("Annahmen", "Modell statt Beratung"),
        ("Übersicht", "Projiziertes Vorsorgekapital"),
    ]:
        page.get_by_role("tab", name=tab).click()
        assert page.get_by_role("tabpanel").get_by_text(expected).first.is_visible()
    assert page.locator(".js-plotly-plot").count() == 3
    assert alice.errors == []


def test_phone_hides_inputs_behind_the_menu(phone_user):
    phone_user.open()
    page = phone_user.page

    assert page.locator("#overview-section .metric-value").first.is_visible()
    assert not _inputs_on_screen(page)
    assert _no_horizontal_scroll(page)

    page.click("#navbar-burger")
    page.wait_for_function(
        "() => document.querySelector('.input-navbar').getBoundingClientRect().left >= 0"
    )
    assert _inputs_on_screen(page)
    phone_user.set_income("6400")
    page.click("#navbar-burger")
    page.wait_for_timeout(500)

    assert not _inputs_on_screen(page)
    assert phone_user.income() == "6400"
    assert page.locator("#overview-section .metric-value").first.is_visible()
    assert phone_user.errors == []
