"""End-to-end check in a real browser: users never see each other's data (issue #4).

Two isolated browser contexts play two users ("Alice" and "Bob") against one server.
Requires the optional ``e2e`` dependency group and a browser:

    uv sync --group e2e
    uv run playwright install chromium        # or: set E2E_BROWSER_CHANNEL=msedge
    uv run pytest tests/e2e

Skipped automatically when Playwright is not installed.
"""


import pytest

playwright_api = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e

SECRET_INCOME = "987600"  # the income field uses step=100


def test_data_survives_reload_in_own_browser(alice):
    alice.open()
    alice.set_income(SECRET_INCOME)
    alice.save_scenario("Alice geheim")

    alice.reload()

    assert alice.income() == SECRET_INCOME
    assert "Alice geheim" in alice.dropdown_options()
    assert alice.stored_scenario_names() == ["Alice geheim"]
    assert alice.errors == []


def test_other_user_sees_nothing(alice, bob):
    alice.open()
    alice.set_income(SECRET_INCOME)
    alice.save_scenario("Alice geheim")

    bob.open()

    assert bob.income() != SECRET_INCOME
    assert bob.dropdown_options() == []
    assert bob.stored_scenario_names() == []
    assert not any(SECRET_INCOME in value for value in bob.local_storage().values())
    assert SECRET_INCOME not in bob.page.content()
    assert bob.errors == []
