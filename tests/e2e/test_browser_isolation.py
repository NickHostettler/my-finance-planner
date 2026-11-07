"""End-to-end check in a real browser: users never see each other's data (issue #4).

Two isolated browser contexts play two users ("Alice" and "Bob") against one server.
Requires the optional ``e2e`` dependency group and a browser:

    uv sync --group e2e
    uv run playwright install chromium        # or: set E2E_BROWSER_CHANNEL=msedge
    uv run pytest tests/e2e

Skipped automatically when Playwright is not installed.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

playwright_api = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.e2e

SECRET_INCOME = "987600"  # the income field uses step=100


def _free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


@pytest.fixture(scope="module")
def base_url():
    port = _free_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "personal_finance", "--no-browser", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/"
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(url, timeout=1)
                break
            except OSError:
                if process.poll() is not None:
                    pytest.fail("dashboard server exited during startup")
                time.sleep(0.5)
        else:
            pytest.fail("dashboard server did not start")
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="module")
def browser():
    channel = os.environ.get("E2E_BROWSER_CHANNEL") or None
    with playwright_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=channel, headless=True)
        yield browser
        browser.close()


class User:
    """One user = one isolated browser context with its own localStorage."""

    def __init__(self, browser, base_url):
        self.context = browser.new_context()
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.base_url = base_url

    def open(self):
        self.page.goto(self.base_url)
        self.page.wait_for_selector("#monthly-income-input")
        self.wait_until_idle()

    def wait_until_idle(self):
        # Dash marks the document while callbacks are pending.
        self.page.wait_for_function(
            "() => !document.querySelector('[data-dash-is-loading=\"true\"]')"
        )
        self.page.wait_for_timeout(800)

    def reload(self):
        self.page.reload()
        self.page.wait_for_selector("#monthly-income-input")
        self.wait_until_idle()

    def income(self):
        return self.page.locator("#monthly-income-input").input_value()

    def set_income(self, value):
        self.page.fill("#monthly-income-input", value)
        self.page.press("#monthly-income-input", "Tab")
        self.wait_until_idle()

    def save_scenario(self, name):
        self.page.fill("#scenario-name-input", name)
        self.page.click("#scenario-save-button")
        self.wait_until_idle()

    def dropdown_options(self):
        button = self.page.locator("#scenario-select")
        button.click()
        self.page.wait_for_timeout(400)
        popup = self.page.locator(f"[id='{button.get_attribute('aria-controls')}']")
        text = popup.inner_text() if popup.count() else ""
        self.page.keyboard.press("Escape")
        return [line.strip() for line in text.splitlines() if line.strip()]

    def local_storage(self):
        return self.page.evaluate("() => Object.fromEntries(Object.entries(localStorage))")

    def stored_scenario_names(self):
        raw = self.local_storage().get("pf-scenarios")
        return sorted(json.loads(raw)["scenarios"]) if raw else []

    def close(self):
        self.context.close()


@pytest.fixture
def alice(browser, base_url):
    user = User(browser, base_url)
    yield user
    user.close()


@pytest.fixture
def bob(browser, base_url):
    user = User(browser, base_url)
    yield user
    user.close()


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
