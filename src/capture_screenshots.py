"""Capture screenshots of the running web app for the PDF report.

Usage: start the app (python app.py), then run
    python capture_screenshots.py [base_url]
"""
import json
import sys

from playwright.sync_api import sync_playwright

from config import REPORTS_DIR

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
OUT = REPORTS_DIR / "screenshots"


def shot(page, name, full=False):
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    print("  saved", name)


# Route Planner demo: the Paris listing closest to each landmark (fixed, so the report is reproducible)
LANDMARKS = [("Eiffel Tower", 48.8584, 2.2945), ("Arc de Triomphe", 48.8738, 2.2950), ("Sacré-Cœur", 48.8867, 2.3431),
             ("Gare du Nord", 48.8809, 2.3553), ("République", 48.8673, 2.3637), ("Bastille", 48.8532, 2.3692),
             ("Notre-Dame", 48.8530, 2.3499), ("Louvre", 48.8606, 2.3376), ("Montparnasse", 48.8421, 2.3219)]


def capture_route(page):
    page.goto(f"{BASE}/route?city=Paris", wait_until="networkidle")
    page.wait_for_function("rows.length > 0")
    page.evaluate("""(marks) => {
        stops = marks.map(([, la, lo]) => {
            let best = -1, bd = Infinity;
            rows.forEach((r, i) => { const d = (r[0] - la) ** 2 + ((r[1] - lo) * 0.66) ** 2;
                                     if (d < bd && !stops.includes(i)) { bd = d; best = i; } });
            return best; });
        start = 0; render(); fitStops();
    }""", LANDMARKS)
    page.select_option("#target", "5")  # Eiffel Tower -> Bastille
    page.click("#go")
    page.wait_for_selector(".algo")
    page.evaluate("window.scrollTo(0, 0)")
    shot(page, "20_route_map")
    page.uncheck("[data-layer=exact]"); page.uncheck("[data-layer=path]"); page.check("[data-layer=heur]")
    shot(page, "21_route_map_heuristic")
    page.check("[data-layer=exact]"); page.check("[data-layer=path]"); page.uncheck("[data-layer=heur]")
    page.wait_for_timeout(800)
    page.locator("#results .algo-grid").screenshot(path=str(OUT / "22_route_algorithms.png"))
    page.locator("#results .g2").screenshot(path=str(OUT / "23_route_tables.png"))
    print("  saved 22_route_algorithms, 23_route_tables")
    example = page.evaluate("result")
    example["landmarks"] = [m[0] for m in LANDMARKS]
    example["prices"] = page.evaluate("stops.map(i => rows[i][2])")
    (REPORTS_DIR / "route_example.json").write_text(json.dumps(example, indent=1), encoding="utf-8")


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

        capture_route(page)

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
