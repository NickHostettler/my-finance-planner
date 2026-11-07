"""Shared fixtures for browser end-to-end tests (see test_browser_isolation.py)."""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

try:
    from playwright import sync_api as playwright_api
except ImportError:  # the test modules skip themselves via importorskip
    playwright_api = None


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
        try:
            browser = playwright.chromium.launch(channel=channel, headless=True)
        except playwright_api.Error as error:
            # In CI (E2E_REQUIRED=1) a missing browser must fail, never silently skip.
            if os.environ.get("E2E_REQUIRED") == "1":
                raise
            pytest.skip(
                "No browser for Playwright: run `uv run playwright install chromium` "
                f"or set E2E_BROWSER_CHANNEL=msedge ({str(error).splitlines()[0]})"
            )
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

    def notice_visible(self):
        return self.page.locator("#welcome-notice").is_visible()

    def dismiss_notice(self):
        self.page.click("#welcome-dismiss")
        self.wait_until_idle()

    def reopen_notice(self):
        self.page.click("#welcome-show")
        self.wait_until_idle()

    def clear_all_data(self, confirm=True):
        """Click 'Alle Daten in diesem Browser löschen' and answer the confirm dialog."""

        def _answer(dialog):
            dialog.accept() if confirm else dialog.dismiss()

        self.page.once("dialog", _answer)
        if confirm:
            with self.page.expect_navigation():
                self.page.click("#clear-browser-data-button")
            self.page.wait_for_selector("#monthly-income-input")
        else:
            self.page.click("#clear-browser-data-button")
        self.wait_until_idle()

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
