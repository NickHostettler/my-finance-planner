"""Check every result tab in a real browser on a phone and a desktop width.

For each width and tab: page width (no horizontal scrolling), JavaScript errors, and a
full-page screenshot. With ``--home`` a home purchase is planned first, so that the
"Wohneigentum" tab shows all its content; with ``--life`` life phases with a child; with
``--household`` two persons (the personal tabs are then checked for both; with ``--home`` the
purchase is joint). The options can be combined.

    uv run python scripts/ui_check.py <output folder> [--home] [--life] [--household]

Needs the e2e dependency group (``uv sync --group e2e``, ``uv run playwright install
chromium``). Exit code 1 if a tab scrolls sideways or the page reports errors.
"""

import argparse
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

VIEWPORTS = {"phone": {"width": 390, "height": 844}, "desktop": {"width": 1440, "height": 1000}}
TABS = ["Übersicht", "Vorsorge", "Wohneigentum", "Lebensphasen", "Haushalt", "Annahmen"]
PERSONAL_TABS = ["Übersicht", "Vorsorge", "Lebensphasen"]
IDLE = "() => !document.querySelector('[data-dash-is-loading=\"true\"]')"
PAGE_WIDTH = "() => document.documentElement.scrollWidth"
# Outermost elements that are wider than the screen while their parent is not.
WIDE_ELEMENTS = """() => [...document.querySelectorAll('body *')]
    .filter(e => e.parentElement && e.offsetParent !== null
        && e.getBoundingClientRect().width > window.innerWidth + 1
        && e.parentElement.getBoundingClientRect().width <= window.innerWidth + 1)
    .slice(0, 5)
    .map(e => `${e.tagName}.${String(e.className).slice(0, 60)}`
        + ` (${Math.round(e.getBoundingClientRect().width)} px)`)"""


def start_server() -> tuple:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = subprocess.Popen(
        [sys.executable, "-m", "personal_finance", "--no-browser", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/"
    for _ in range(60):
        try:
            urllib.request.urlopen(url, timeout=1)
            return server, url
        except OSError:
            time.sleep(0.5)
    server.terminate()
    raise SystemExit("Der Server ist nicht gestartet.")


def idle(page) -> None:
    page.wait_for_function(IDLE)
    page.wait_for_timeout(800)


def fill(page, selector: str, value: str) -> None:
    page.fill(selector, value)
    page.press(selector, "Tab")
    idle(page)


def plan_household(page, phone: bool) -> None:
    """Two persons: person B is 33 and has own balances."""
    if phone:
        page.click("#navbar-burger")
        page.wait_for_timeout(500)
    page.locator("#household-input").get_by_text("Zwei Personen").click()
    idle(page)
    page.locator("#input-person-input").get_by_text("Person B").click()
    idle(page)
    fill(page, "#b-current-age-input", "33")
    fill(page, "#b-pillar2-initial-input", "90000")
    fill(page, "#b-pillar3b-initial-input", "80000")
    page.locator("#input-person-input").get_by_text("Person A").click()
    idle(page)
    if phone:
        page.click("#navbar-burger")
        page.wait_for_timeout(500)


def plan_home_purchase(page, phone: bool) -> None:
    if phone:
        page.click("#navbar-burger")
        page.wait_for_timeout(500)
    fill(page, "#pillar2-initial-input", "120000")
    fill(page, "#pillar3b-initial-input", "150000")
    page.locator(".input-navbar").get_by_text("Wohneigentum", exact=True).click()
    page.wait_for_timeout(300)
    page.locator("#home-plan-input").get_by_text("Kauf planen").click()
    idle(page)
    fill(page, "#home-purchase-age-input", "40")
    fill(page, "#home-pillar2-input", "50000")
    fill(page, "#home-gross-income-input", "180000")
    if phone:
        page.click("#navbar-burger")
        page.wait_for_timeout(500)


def plan_life_phases(page, phone: bool) -> None:
    """Part time while the children are small, with one child and child costs."""
    if phone:
        page.click("#navbar-burger")
        page.wait_for_timeout(500)
    page.locator("#person-a-inputs").get_by_text("Lebensphasen & Familie", exact=True).click()
    page.wait_for_timeout(300)
    page.locator("#life-plan-input").get_by_text("Phasen planen").click()
    idle(page)
    page.get_by_role("button", name="Teilzeit mit Kindern").click()
    idle(page)
    fill(page, "#life-2-costs-input", "1500")
    page.locator("#shared-groups").get_by_text("Kinder", exact=True).click()
    page.wait_for_timeout(300)
    fill(page, "#life-child-1-input", "37")
    if phone:
        page.click("#navbar-burger")
        page.wait_for_timeout(500)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path, help="Ordner für die Screenshots")
    parser.add_argument("--home", action="store_true", help="vorher einen Kauf planen")
    parser.add_argument(
        "--life", action="store_true", help="vorher Lebensphasen mit einem Kind planen"
    )
    parser.add_argument(
        "--household", action="store_true", help="vorher eine zweite Person erfassen"
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    problems = []
    server, url = start_server()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for name, viewport in VIEWPORTS.items():
                page = browser.new_page(viewport=viewport)
                errors = []
                page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
                page.goto(url)
                page.wait_for_selector("#monthly-income-input")
                idle(page)
                if page.locator("#welcome-dismiss").is_visible():
                    page.click("#welcome-dismiss")
                if args.household:
                    plan_household(page, phone=name == "phone")
                if args.life:
                    plan_life_phases(page, phone=name == "phone")
                if args.home:
                    plan_home_purchase(page, phone=name == "phone")
                views = [(tab, "") for tab in TABS]
                if args.household:
                    views += [(tab, "B") for tab in PERSONAL_TABS]
                for tab, person in views:
                    if person:
                        page.locator("#result-person-input").get_by_text("Person B").click()
                    page.get_by_role("tab", name=tab).click()
                    idle(page)
                    tab = f"{tab}-{person}" if person else tab
                    width = page.evaluate(PAGE_WIDTH)
                    status = "ok" if width <= viewport["width"] else "ZU BREIT"
                    print(f"{name:8} {tab:13} Seitenbreite {width:5} px  {status}")
                    if width > viewport["width"]:
                        problems.append(f"{name}/{tab}: {width} px")
                        for element in page.evaluate(WIDE_ELEMENTS):
                            print(f"         zu breit ab: {element}")
                    shot = args.out / f"{name}-{tab.lower().replace('ü', 'ue')}.png"
                    page.screenshot(path=str(shot), full_page=True)
                if errors:
                    problems.append(f"{name}: JavaScript-Fehler {errors}")
                page.close()
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)

    print(f"Screenshots: {args.out}")
    for problem in problems:
        print(f"PROBLEM {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
