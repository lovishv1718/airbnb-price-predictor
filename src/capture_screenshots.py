"""Capture screenshots of the running web app for the PDF report.

Usage: start the app (python app.py), then run
    python capture_screenshots.py [base_url]
"""
import sys

from playwright.sync_api import sync_playwright

from config import REPORTS_DIR

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
OUT = REPORTS_DIR / "screenshots"


def shot(page, name, full=False):
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    print("  saved", name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)

        page.goto(f"{BASE}/", wait_until="networkidle")
        shot(page, "01_dashboard_top")
        shot(page, "02_dashboard_full", full=True)

        page.goto(f"{BASE}/explorer?city=Paris", wait_until="networkidle")
        shot(page, "03_explorer_paris_points")
        page.click("#layer button[data-v=heat]")
        shot(page, "04_explorer_paris_heatmap")
        page.click("#layer button[data-v=density]")
        shot(page, "05_explorer_paris_density")
        page.click("#layer button[data-v=points]")
        page.select_option("#city", "London")
        page.wait_for_load_state("networkidle")
        page.uncheck("#rooms input[value='1']")
        page.uncheck("#rooms input[value='2']")
        page.check("#superhost")
        shot(page, "06_explorer_london_filtered")
        # points are drawn on a canvas: click near the map centre until a popup opens
        box = page.locator("#map").bounding_box()
        for dx, dy in [(0, 0), (12, 8), (-15, 10), (20, -12), (-8, -20), (30, 25), (-30, 5)]:
            page.mouse.click(box["x"] + box["width"] / 2 + 40 + dx, box["y"] + box["height"] / 2 + 60 + dy)
            page.wait_for_timeout(400)
            if page.locator(".leaflet-popup").count():
                break
        shot(page, "07_explorer_popup")

        page.goto(f"{BASE}/predict", wait_until="networkidle")
        page.wait_for_selector(".price-big")
        shot(page, "08_predict_paris_default")
        shot(page, "09_predict_paris_full", full=True)
        # second scenario: large family home in Amsterdam on a weekend
        page.select_option("#city", "Amsterdam")
        page.wait_for_timeout(800)
        page.fill("#max_guests", "6"); page.dispatch_event("#max_guests", "input")
        page.fill("#num_bedrooms", "3"); page.dispatch_event("#num_bedrooms", "input")
        page.click("#day button[data-v=weekend]")
        page.check("#is_superhost")
        page.click("#go")
        page.wait_for_timeout(2000)
        shot(page, "10_predict_amsterdam_family", full=True)
        # third scenario: private room in Athens
        page.select_option("#city", "Athens")
        page.wait_for_timeout(800)
        page.click("#room button[data-v='Private room']")
        page.fill("#max_guests", "2"); page.dispatch_event("#max_guests", "input")
        page.fill("#num_bedrooms", "1"); page.dispatch_event("#num_bedrooms", "input")
        page.click("#go")
        page.wait_for_timeout(2000)
        shot(page, "11_predict_athens_private", full=True)
        page.locator("details summary").click()
        shot(page, "12_predict_advanced")

        page.goto(f"{BASE}/model", wait_until="networkidle")
        shot(page, "13_model_top")
        shot(page, "14_model_full", full=True)

        page.goto(f"{BASE}/report", wait_until="networkidle")
        shot(page, "15_report_page")

        page.goto(f"{BASE}/api/health", wait_until="networkidle")
        shot(page, "16_api_health")

        mobile = browser.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True)
        mobile.goto(f"{BASE}/", wait_until="networkidle")
        shot(mobile, "17_mobile_dashboard")
        mobile.goto(f"{BASE}/predict", wait_until="networkidle")
        mobile.wait_for_selector(".price-big")
        mobile.locator("#result").scroll_into_view_if_needed()
        shot(mobile, "18_mobile_predict")
        mobile.goto(f"{BASE}/", wait_until="networkidle")
        mobile.click(".menu-btn")
        shot(mobile, "19_mobile_menu")
        browser.close()


if __name__ == "__main__":
    main()
